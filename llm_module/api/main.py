"""
FastAPI主入口 - 提供RESTful API服务
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from core.extractor import get_extractor, KnowledgeExtractor
from core.qa_engine import get_qa_engine, QAEngine
from core.kg_builder import get_kg_builder, KnowledgeGraphBuilder
from core.data_pipeline import get_preprocessor, DataPreprocessor, RawData, ProcessedData
from models.schemas import (
    ExtractedKnowledge, QueryRequest, QueryResponse,
    JobDescription, Entity, Relation
)
from services.rag_service import get_rag_service, RAGService
from services.neo4j_service import get_neo4j_service, Neo4jService
from utils.config import SERVER_CONFIG
from utils.logger import get_logger, request_id_ctx, trace_id_ctx, check_slow_request
logger = get_logger("api")


# ==================== 请求限流器 ====================

class RateLimiter:
    """轻量级内存限流器 - 滑动窗口算法"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict = {}  # ip -> [timestamp, ...]

    def is_allowed(self, client_id: str) -> bool:
        """检查请求是否允许"""
        import time
        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []

        # 清理过期记录
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if now - t < self._window
        ]

        if len(self._requests[client_id]) >= self._max:
            return False

        self._requests[client_id].append(now)
        return True


_rate_limiter: RateLimiter = None


# 全局服务实例
extractor: KnowledgeExtractor
qa_engine: QAEngine
kg_builder: KnowledgeGraphBuilder
rag_service: RAGService
neo4j_service: Neo4jService
preprocessor: DataPreprocessor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global extractor, qa_engine, kg_builder, rag_service, neo4j_service, preprocessor

    # 启动时初始化
    logger.info("正在初始化服务...")
    extractor = get_extractor()
    qa_engine = get_qa_engine()
    kg_builder = get_kg_builder()
    rag_service = get_rag_service()
    neo4j_service = get_neo4j_service()
    preprocessor = get_preprocessor()
    logger.info("服务初始化完成")
    logger.debug(f"服务初始化详情: extractor={type(extractor).__name__}, qa_engine={type(qa_engine).__name__}, kg_builder={type(kg_builder).__name__}")

    yield

    # 关闭时清理
    logger.info("服务关闭")


# 创建FastAPI应用
app = FastAPI(
    title="岗能智绘 - 大模型服务",
    description="多源异构数据驱动岗位能力动态图谱平台的大模型智能引擎",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS中间件 - 支持环境变量配置白名单
import os
_cors_origins = os.getenv("CORS_ORIGINS", "*")
if _cors_origins == "*":
    _allow_origins = ["*"]
else:
    _allow_origins = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# 请求ID中间件 - 为每个请求生成唯一ID并注入日志上下文
@app.middleware("http")
async def request_id_middleware(request, call_next):
    """为每个请求生成唯一ID并注入日志上下文，同时检测慢请求"""
    import time

    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request_id_ctx.set(req_id)
    trace_id_ctx.set(req_id)  # 复用request_id作为trace_id

    logger.debug(f"请求开始: {request.method} {request.url.path}")

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    response.headers["X-Request-ID"] = req_id

    # 安全头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    logger.debug(f"请求完成: {request.method} {request.url.path} -> {response.status_code} ({duration:.2f}s)")

    # 慢请求告警检查
    check_slow_request(duration, request_id=req_id, path=request.url.path, trace_id=req_id)

    return response


# 限流中间件
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """请求限流 - 每IP每分钟60次"""
    from utils.config import RATE_LIMIT_CONFIG

    if not RATE_LIMIT_CONFIG["enabled"]:
        return await call_next(request)

    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            max_requests=RATE_LIMIT_CONFIG["max_requests_per_minute"],
        )

    # 获取客户端ID（IP地址）
    client_id = request.client.host if request.client else "unknown"

    if not _rate_limiter.is_allowed(client_id):
        logger.warning(f"请求限流: client={client_id}, path={request.url.path}")
        return JSONResponse(
            status_code=429,
            content={
                "code": 429,
                "message": "请求过于频繁，请稍后重试",
                "data": None,
                "request_id": request.headers.get("X-Request-ID", ""),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            },
        )

    return await call_next(request)


# 认证上下文中间件 - 提取JWT令牌注入用户上下文（不强制认证）
AUTH_WHITELIST = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_context_middleware(request: Request, call_next):
    """注入用户上下文（从JWT令牌中提取，不强制认证）"""
    # 白名单路径跳过
    path = request.url.path
    if path in AUTH_WHITELIST or path.startswith("/api/v1/auth/"):
        request.state.user_id = 0
        request.state.user_role = ""
        return await call_next(request)

    # 尝试从Authorization头提取令牌
    request.state.user_id = 0
    request.state.user_role = ""

    try:
        from services.auth_service import get_auth_service
        auth = get_auth_service()
        user = await auth.get_optional_user(request)
        if user:
            request.state.user_id = user.get("user_id", 0)
            request.state.user_role = user.get("role", "")
    except Exception:
        pass  # 认证失败不影响请求

    return await call_next(request)


# 注册Agent路由（避免循环导入，在应用创建后导入）
try:
    from api.agent_routes import router as agent_router
    app.include_router(agent_router)
    logger.info("Agent路由注册成功")
except Exception as e:
    logger.error(f"Agent路由注册失败: {e}", exc_info=True)

# 注册Agent简历上传路由（依赖 python-multipart，单独注册，缺失时不影响核心接口）
try:
    from api.upload_routes import router as upload_router
    app.include_router(upload_router)
    logger.info("Agent上传路由注册成功")
except Exception as e:
    logger.error(f"Agent上传路由注册失败: {e}", exc_info=True)

# 注册v1版本化路由
try:
    from api.v1.routes import router as v1_router
    app.include_router(v1_router)
    logger.info("API v1路由注册成功")
except Exception as e:
    logger.error(f"API v1路由注册失败: {e}", exc_info=True)

# 注册认证路由
try:
    from api.v1.auth_routes import router as auth_router
    app.include_router(auth_router)
    logger.info("Auth路由注册成功")
except Exception as e:
    logger.error(f"Auth路由注册失败: {e}", exc_info=True)

# 注册健康检查路由
try:
    from api.v1.health_routes import router as health_router
    app.include_router(health_router)
    logger.info("Health路由注册成功")
except Exception as e:
    logger.error(f"Health路由注册失败: {e}", exc_info=True)


# ==================== 全局异常处理器 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None,
            "request_id": request.headers.get("X-Request-ID", ""),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局未捕获异常处理 - 返回友好降级消息"""
    req_id = request.headers.get("X-Request-ID", "")
    logger.error(f"未捕获异常 [request_id={req_id}]: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务内部错误，请稍后重试",
            "data": None,
            "request_id": req_id,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
    )


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "岗能智绘 - 大模型服务",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "services": {
            "extractor": extractor is not None,
            "qa_engine": qa_engine is not None,
            "kg_builder": kg_builder is not None,
            "rag_service": rag_service is not None,
            "neo4j": neo4j_service.is_connected() if neo4j_service else False,
            "preprocessor": preprocessor is not None,
        },
    }


@app.post("/extract/jd", response_model=ExtractedKnowledge)
async def extract_from_jd(jd_text: str):
    """
    从岗位描述(JD)中抽取知识

    Args:
        jd_text: 岗位描述文本

    Returns:
        ExtractedKnowledge: 抽取的知识
    """
    if not jd_text or len(jd_text) < 10:
        raise HTTPException(status_code=400, detail="JD文本过短")

    try:
        result = await extractor.extract_from_jd(jd_text)
        return result
    except Exception as e:
        logger.error(f"抽取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"抽取失败: {str(e)}")


@app.post("/extract/skills")
async def extract_skills(text: str):
    """
    从文本中抽取技能关键词

    Args:
        text: 输入文本

    Returns:
        技能列表
    """
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        skills = await extractor.extract_skills_from_text(text)
        return {"skills": skills}
    except Exception as e:
        logger.error(f"技能抽取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"技能抽取失败: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    智能问答

    Args:
        request: 问答请求

    Returns:
        QueryResponse: 问答结果
    """
    # 输入净化
    from utils.security import InputSanitizer
    try:
        request.question = InputSanitizer.sanitize_string(request.question, max_length=5000)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await qa_engine.answer(
            question=request.question,
            context=request.context,
            history=request.history,
        )
        return result
    except Exception as e:
        logger.error(f"问答失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    流式问答 (SSE)

    Args:
        request: 问答请求

    Returns:
        StreamingResponse: 流式输出
    """
    async def generate():
        async for chunk in qa_engine.stream_answer(
            question=request.question,
            context=request.context,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@app.post("/analysis/skill-gap")
async def skill_gap_analysis(
    current_skills: list[str],
    target_job: str,
):
    """
    技能差距分析

    Args:
        current_skills: 当前技能列表
        target_job: 目标岗位

    Returns:
        分析结果
    """
    try:
        result = await qa_engine.skill_gap_analysis(current_skills, target_job)
        return result
    except Exception as e:
        logger.error(f"技能差距分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.post("/analysis/job-match")
async def job_match_analysis(
    job_info: str,
    candidate_info: str,
):
    """
    岗位匹配度评估

    Args:
        job_info: 岗位信息
        candidate_info: 候选人信息

    Returns:
        匹配度评估结果
    """
    try:
        result = await qa_engine.job_match(job_info, candidate_info)
        return result
    except Exception as e:
        logger.error(f"岗位匹配评估失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@app.post("/kg/build")
async def build_knowledge_graph(knowledge: ExtractedKnowledge):
    """
    构建知识图谱

    Args:
        knowledge: 抽取的知识

    Returns:
        构建结果
    """
    try:
        kg_builder.build_from_knowledge(knowledge)
        return {
            "status": "success",
            "entity_count": len(kg_builder.entities),
            "relation_count": len(kg_builder.relations),
        }
    except Exception as e:
        logger.error(f"知识图谱构建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"构建失败: {str(e)}")


@app.get("/kg/entities")
async def get_entities(
    entity_type: str = None,
    name_contains: str = None,
):
    """
    查询知识图谱实体

    Args:
        entity_type: 实体类型过滤
        name_contains: 名称包含过滤

    Returns:
        实体列表
    """
    entities = kg_builder.query_entities(entity_type, name_contains)
    return {"entities": [e.model_dump() for e in entities]}


@app.get("/kg/subgraph/{entity_name}")
async def get_subgraph(entity_name: str, depth: int = 2):
    """
    获取实体的子图

    Args:
        entity_name: 实体名称
        depth: 搜索深度

    Returns:
        子图数据
    """
    try:
        subgraph = kg_builder.get_subgraph(entity_name, depth)
        return subgraph
    except Exception as e:
        logger.error(f"获取子图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取子图失败: {str(e)}")


@app.get("/kg/export")
async def export_kg():
    """
    导出知识图谱

    Returns:
        知识图谱JSON数据
    """
    return kg_builder.export_to_json()


@app.get("/kg/visualize/{entity_name}")
async def visualize_subgraph(entity_name: str, depth: int = 2):
    """
    获取图谱可视化数据（Cytoscape.js格式）

    Args:
        entity_name: 中心实体名称
        depth: 搜索深度

    Returns:
        Cytoscape.js格式的图谱数据 {elements: {nodes: [...], edges: [...]}}
    """
    try:
        subgraph = kg_builder.get_subgraph(entity_name, depth)

        # 颜色映射
        type_colors = {
            "job": "#667eea",
            "skill": "#4ade80",
            "knowledge": "#fbbf24",
            "certificate": "#f87171",
            "tool": "#a78bfa",
            "industry": "#fb923c",
        }

        # 图标映射
        type_icons = {
            "job": "💼",
            "skill": "⚡",
            "knowledge": "📖",
            "certificate": "📜",
            "tool": "🔧",
            "industry": "🏭",
        }

        # 转换为Cytoscape.js格式
        nodes = []
        seen_nodes = set()

        # 添加中心节点
        center_type = kg_builder._get_entity_type(entity_name) or "unknown"
        nodes.append({
            "data": {
                "id": entity_name,
                "label": entity_name,
                "type": center_type,
                "color": type_colors.get(center_type, "#94a3b8"),
                "icon": type_icons.get(center_type, "❓"),
                "is_center": True,
            }
        })
        seen_nodes.add(entity_name)

        # 添加子图中的实体节点
        for entity_data in subgraph.get("entities", []):
            name = entity_data.get("name", "")
            if name and name not in seen_nodes:
                etype = entity_data.get("type", "unknown")
                nodes.append({
                    "data": {
                        "id": name,
                        "label": name,
                        "type": etype,
                        "color": type_colors.get(etype, "#94a3b8"),
                        "icon": type_icons.get(etype, "❓"),
                        "is_center": False,
                    }
                })
                seen_nodes.add(name)

        # 添加边
        edges = []
        seen_edges = set()
        for rel_data in subgraph.get("relations", []):
            source = rel_data.get("source", "")
            target = rel_data.get("target", "")
            rel_type = rel_data.get("type", "")
            edge_key = f"{source}-{rel_type}-{target}"
            if edge_key not in seen_edges and source and target:
                edges.append({
                    "data": {
                        "id": edge_key,
                        "source": source,
                        "target": target,
                        "label": rel_type,
                        "type": rel_type,
                    }
                })
                seen_edges.add(edge_key)

        return {
            "elements": {
                "nodes": nodes,
                "edges": edges,
            },
            "center": entity_name,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        }
    except Exception as e:
        logger.error(f"获取可视化数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取可视化数据失败: {str(e)}")


@app.get("/kg/validate")
async def validate_kg(industry: str = ""):
    """
    执行图谱质量校验

    Args:
        industry: 行业上下文

    Returns:
        校验报告
    """
    try:
        report = kg_builder.validate_graph(industry)
        return report
    except Exception as e:
        logger.error(f"图谱校验失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图谱校验失败: {str(e)}")


@app.post("/kg/fix")
async def fix_kg():
    """
    自动修复常见图谱质量问题

    Returns:
        修复统计
    """
    try:
        fixes = kg_builder.fix_common_issues()
        # 同步修复到持久化
        kg_builder.save_to_persistence()
        return {"message": "图谱修复完成", "fixes": fixes}
    except Exception as e:
        logger.error(f"图谱修复失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图谱修复失败: {str(e)}")


@app.get("/kg/infer/prerequisites")
async def infer_prerequisites(max_depth: int = 5):
    """
    传递推理：推导隐含的前置技能关系

    Args:
        max_depth: 最大推理深度

    Returns:
        推导出的隐含关系列表
    """
    try:
        neo4j_svc = get_neo4j_service()
        if not neo4j_svc.is_connected():
            raise HTTPException(status_code=503, detail="Neo4j未连接，无法执行推理")
        inferred = neo4j_svc.infer_transitive_prerequisites(max_depth)
        return {"inferred_relations": inferred, "count": len(inferred)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"传递推理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"传递推理失败: {str(e)}")


@app.get("/kg/infer/skills/{job_name}")
async def infer_job_skills(job_name: str, max_depth: int = 3):
    """
    路径推理：从岗位推导所有直接和间接需要的技能

    Args:
        job_name: 岗位名称
        max_depth: 最大推理深度

    Returns:
        直接技能 + 间接推导技能
    """
    try:
        neo4j_svc = get_neo4j_service()
        if not neo4j_svc.is_connected():
            raise HTTPException(status_code=503, detail="Neo4j未连接，无法执行推理")
        result = neo4j_svc.infer_skill_requirements(job_name, max_depth)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"技能路径推理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"技能路径推理失败: {str(e)}")


@app.get("/kg/infer/similar/{job_name}")
async def infer_similar_skills(job_name: str):
    """
    类比推理：通过相似岗位推导技能需求

    Args:
        job_name: 岗位名称

    Returns:
        相似岗位及其技能
    """
    try:
        neo4j_svc = get_neo4j_service()
        if not neo4j_svc.is_connected():
            raise HTTPException(status_code=503, detail="Neo4j未连接，无法执行推理")
        result = neo4j_svc.infer_similar_job_skills(job_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"类比推理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"类比推理失败: {str(e)}")


@app.get("/kg/infer/career/{job_name}")
async def infer_career_paths(job_name: str, max_depth: int = 4):
    """
    职业路径推理：推导职业晋升路径

    Args:
        job_name: 起始岗位名称
        max_depth: 最大推理深度

    Returns:
        职业路径及沿路径的技能需求
    """
    try:
        neo4j_svc = get_neo4j_service()
        if not neo4j_svc.is_connected():
            raise HTTPException(status_code=503, detail="Neo4j未连接，无法执行推理")
        result = neo4j_svc.infer_career_paths(job_name, max_depth)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"职业路径推理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"职业路径推理失败: {str(e)}")


# ============== RAG 知识库接口 ==============

@app.post("/rag/add-documents")
async def rag_add_documents(documents: list[str], metadatas: list[dict] = None):
    """
    添加文档到RAG知识库

    Args:
        documents: 文档文本列表
        metadatas: 文档元数据列表

    Returns:
        添加结果
    """
    try:
        ids = await rag_service.add_knowledge_base(documents, metadatas)
        return {
            "status": "success",
            "added_count": len(ids),
            "document_ids": ids,
        }
    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@app.post("/rag/add-jobs")
async def rag_add_jobs(job_descriptions: list[dict]):
    """
    批量添加岗位描述到知识库

    Args:
        job_descriptions: 岗位描述列表
            [{"title": "...", "requirements": "...", "responsibilities": "..."}]

    Returns:
        添加结果
    """
    try:
        ids = await rag_service.add_job_descriptions(job_descriptions)
        return {
            "status": "success",
            "added_count": len(ids),
            "document_ids": ids,
        }
    except Exception as e:
        logger.error(f"添加岗位描述失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@app.post("/rag/add-skills")
async def rag_add_skills(skills: list[dict]):
    """
    批量添加技能定义到知识库

    Args:
        skills: 技能定义列表
            [{"name": "...", "description": "...", "category": "..."}]

    Returns:
        添加结果
    """
    try:
        ids = await rag_service.add_skill_definitions(skills)
        return {
            "status": "success",
            "added_count": len(ids),
            "document_ids": ids,
        }
    except Exception as e:
        logger.error(f"添加技能定义失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@app.post("/rag/query")
async def rag_query(question: str, top_k: int = 5):
    """
    RAG智能查询

    Args:
        question: 用户问题
        top_k: 返回结果数量

    Returns:
        包含答案和来源的结果
    """
    try:
        result = await rag_service.query(question, top_k)
        return result
    except Exception as e:
        logger.error(f"RAG查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.get("/rag/stats")
async def rag_stats():
    """
    获取RAG知识库统计

    Returns:
        统计信息
    """
    try:
        stats = rag_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


# ============== Neo4j 图数据库接口 ==============

@app.get("/neo4j/status")
async def neo4j_status():
    """
    获取Neo4j连接状态

    Returns:
        连接状态
    """
    return {
        "connected": neo4j_service.is_connected() if neo4j_service else False,
    }


@app.get("/neo4j/stats")
async def neo4j_stats():
    """
    获取Neo4j数据库统计

    Returns:
        统计信息
    """
    try:
        stats = neo4j_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取Neo4j统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@app.get("/neo4j/entity/{name}")
async def neo4j_find_entity(name: str):
    """
    查找实体

    Args:
        name: 实体名称

    Returns:
        实体信息
    """
    try:
        entity = neo4j_service.find_entity(name)
        if entity:
            return entity
        else:
            raise HTTPException(status_code=404, detail="实体未找到")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查找实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查找失败: {str(e)}")


@app.get("/neo4j/neighbors/{name}")
async def neo4j_find_neighbors(name: str, depth: int = 2):
    """
    查找邻居节点

    Args:
        name: 实体名称
        depth: 搜索深度

    Returns:
        邻居节点和关系
    """
    try:
        result = neo4j_service.find_neighbors(name, depth)
        return result
    except Exception as e:
        logger.error(f"查找邻居失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查找失败: {str(e)}")


@app.get("/neo4j/search")
async def neo4j_search_by_type(entity_type: str, limit: int = 100):
    """
    按类型搜索实体

    Args:
        entity_type: 实体类型
        limit: 返回数量限制

    Returns:
        实体列表
    """
    try:
        entities = neo4j_service.search_by_type(entity_type, limit)
        return {"entities": entities}
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ============== 数据预处理接口 ==============

@app.post("/preprocess/jd")
async def preprocess_jd(source: str, content: str, metadata: dict = None):
    """
    预处理岗位描述(JD)

    Args:
        source: 数据来源标识
        content: JD文本内容
        metadata: 元数据

    Returns:
        处理后的数据
    """
    try:
        raw_data = RawData(
            source=source,
            content=content,
            metadata=metadata or {},
            data_type="text",
        )
        result = preprocessor.process_jd(raw_data)
        return {
            "source": result.source,
            "content": result.content,
            "metadata": result.metadata,
            "keywords": result.keywords,
        }
    except Exception as e:
        logger.error(f"预处理JD失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预处理失败: {str(e)}")


@app.post("/preprocess/resume")
async def preprocess_resume(source: str, content: str, metadata: dict = None):
    """
    预处理简历

    Args:
        source: 数据来源标识
        content: 简历文本内容
        metadata: 元数据

    Returns:
        处理后的数据
    """
    try:
        raw_data = RawData(
            source=source,
            content=content,
            metadata=metadata or {},
            data_type="text",
        )
        result = preprocessor.process_resume(raw_data)
        return {
            "source": result.source,
            "content": result.content,
            "metadata": result.metadata,
            "keywords": result.keywords,
        }
    except Exception as e:
        logger.error(f"预处理简历失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预处理失败: {str(e)}")


@app.post("/preprocess/batch")
async def preprocess_batch(data_list: list[dict], data_type: str = "auto"):
    """
    批量预处理数据

    Args:
        data_list: 原始数据列表 [{"source": "...", "content": "..."}]
        data_type: 数据类型 (auto/jd/resume/skill)

    Returns:
        处理后的数据列表
    """
    try:
        raw_data_list = [
            RawData(
                source=d.get("source", f"item_{i}"),
                content=d.get("content", ""),
                metadata=d.get("metadata", {}),
                data_type=d.get("data_type", "text"),
            )
            for i, d in enumerate(data_list)
        ]

        results = preprocessor.process_batch(raw_data_list, data_type)

        return {
            "processed_count": len(results),
            "results": [
                {
                    "source": r.source,
                    "content": r.content,
                    "metadata": r.metadata,
                    "keywords": r.keywords,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"批量预处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量预处理失败: {str(e)}")


def main():
    """主函数"""
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
        reload=SERVER_CONFIG["debug"],
    )


if __name__ == "__main__":
    main()
