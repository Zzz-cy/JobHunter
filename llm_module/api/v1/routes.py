"""
API v1 路由 - 版本化RESTful API

提供完整的会话管理、对话、工作流、监控等接口
统一响应格式：{code, message, data, request_id, timestamp}
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from utils.logger import get_logger
logger = get_logger("api.v1.routes")


# ==================== 认证依赖辅助 ====================

async def _get_optional_user(request: Request) -> dict:
    """获取可选用户信息（从中间件注入的state中读取）"""
    user_id = getattr(request.state, "user_id", 0)
    user_role = getattr(request.state, "user_role", "")
    if user_id and user_id != 0:
        return {"user_id": user_id, "role": user_role}
    return None


# ==================== 统一响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(0, description="状态码，0=成功")
    message: str = Field("success", description="状态消息")
    data: Optional[dict] = Field(None, description="响应数据")
    request_id: str = Field("", description="请求ID")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")


def success_response(data=None, message="success", request_id="") -> dict:
    """构建成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
    }


def error_response(code: int, message: str, request_id: str = "") -> dict:
    """构建错误响应"""
    return {
        "code": code,
        "message": message,
        "data": None,
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
    }


# ==================== 请求模型 ====================

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    industry: Optional[str] = Field(None, description="行业上下文 (it/finance/healthcare/manufacturing/education)")
    role: Optional[str] = Field(None, description="用户角色 (job_seeker/hr/career_planner/manager)")


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    industry: Optional[str] = Field(None, description="行业上下文")
    role: Optional[str] = Field(None, description="用户角色")


class WorkflowRequest(BaseModel):
    """工作流请求"""
    query: str = Field("", max_length=5000, description="查询内容")
    industry: Optional[str] = Field(None, description="行业上下文")
    params: Optional[dict] = Field(None, description="额外参数")


class EvaluationRequest(BaseModel):
    """评价请求"""
    message_id: int = Field(..., description="消息ID")
    user_score: float = Field(0, ge=0, le=5, description="用户评分(0-5)")
    user_feedback: str = Field("", max_length=2000, description="用户反馈")


# ==================== 路由 ====================

router = APIRouter(prefix="/api/v1", tags=["API v1"])


# ========== 会话管理接口 ==========

@router.post("/sessions")
async def create_session(request: CreateSessionRequest, req: Request):
    """创建新会话"""
    from agents.agent_coordinator import get_session_manager

    # 获取用户ID（可选，0=匿名）
    current_user = await _get_optional_user(req)
    user_id = current_user["user_id"] if current_user else 0

    sm = get_session_manager()
    session_id = sm.create_session(
        industry=request.industry or "",
        role=request.role or "",
        user_id=user_id,
    )
    session = sm.get_session(session_id)

    request_id = req.headers.get("X-Request-ID", "")
    return success_response({
        "session_id": session_id,
        "industry": session.get("industry", ""),
        "role": session.get("role", ""),
        "created_at": session.get("created_at", ""),
    }, request_id=request_id)


@router.get("/sessions")
async def list_sessions(req: Request):
    """列出所有会话"""
    from agents.agent_coordinator import get_session_manager

    # 获取用户ID（可选，0=匿名）
    current_user = await _get_optional_user(req)
    user_id = current_user["user_id"] if current_user else None

    sm = get_session_manager()
    sessions = sm.list_sessions(user_id=user_id)

    request_id = req.headers.get("X-Request-ID", "")
    return success_response({"sessions": sessions, "total": len(sessions)}, request_id=request_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, req: Request):
    """获取会话详情"""
    from agents.agent_coordinator import get_session_manager

    # 获取用户ID（可选，0=匿名）
    current_user = await _get_optional_user(req)
    user_id = current_user["user_id"] if current_user else None

    sm = get_session_manager()
    session = sm.get_session(session_id, user_id=user_id)

    request_id = req.headers.get("X-Request-ID", "")
    if not session:
        return error_response(404, f"会话不存在: {session_id}", request_id)

    return success_response({
        "session_id": session_id,
        "industry": session.get("industry", ""),
        "role": session.get("role", ""),
        "message_count": len(session.get("history", [])),
        "created_at": session.get("created_at", ""),
    }, request_id=request_id)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, req: Request):
    """删除会话"""
    from agents.agent_coordinator import get_session_manager

    # 获取用户ID（可选，0=匿名）
    current_user = await _get_optional_user(req)
    user_id = current_user["user_id"] if current_user else None

    sm = get_session_manager()
    success = sm.destroy_session(session_id, user_id=user_id)

    request_id = req.headers.get("X-Request-ID", "")
    if not success:
        return error_response(403, "无权删除此会话", request_id)
    return success_response({"session_id": session_id}, message="会话已删除", request_id=request_id)


# ========== 对话接口 ==========

@router.post("/sessions/{session_id}/chat")
async def session_chat(session_id: str, request: ChatRequest, req: Request):
    """会话内对话 - 支持多轮上下文"""
    from agents.agent_coordinator import get_master_agent, get_session_manager

    request_id = req.headers.get("X-Request-ID", "")

    if not request.message:
        return error_response(400, "消息不能为空", request_id)

    try:
        master = get_master_agent()
        sm = get_session_manager()

        # 配额检查
        current_user = await _get_optional_user(req)
        user_id = current_user["user_id"] if current_user else 0
        user_role = current_user["role"] if current_user else ""
        if user_id:
            from services.quota_service import get_quota_service
            quota = get_quota_service()
            if not quota.check_quota(user_id, tokens_estimate=500, role=user_role):
                return error_response(429, "今日调用次数已达上限，请明天再试", request_id)

        # 获取或创建会话
        if not sm.get_session(session_id):
            sm.create_session(
                session_id=session_id,
                industry=request.industry or "",
                role=request.role or "",
            )

        # 更新行业/角色
        if request.industry:
            sm.set_industry(session_id, request.industry)
        if request.role:
            sm.set_role(session_id, request.role)

        # 记录用户消息
        sm.add_message(session_id, "user", request.message)

        # 获取上下文窗口（最近N轮 + 旧消息摘要）
        history = sm.get_context_window(session_id)
        industry = sm.get_industry(session_id)
        role = sm.get_role(session_id)

        # 带上下文处理
        result = await master.process(
            request.message,
            history=history,
            industry=industry,
            role=role,
        )

        # 记录助手回复
        answer = result.get("answer", "")
        sm.add_message(session_id, "assistant", str(answer))

        # 记录配额使用
        if user_id:
            try:
                from services.quota_service import get_quota_service
                get_quota_service().record_usage(user_id, tokens_used=0)
            except Exception:
                pass

        # 异步触发上下文压缩（如果需要）
        try:
            await sm.compress_context(session_id)
        except Exception:
            pass

        result["session_id"] = session_id
        return success_response(result, request_id=request_id)

    except Exception as e:
        logger.error(f"会话对话失败: {str(e)}", exc_info=True)
        return error_response(500, f"处理失败: {str(e)}", request_id)


@router.get("/sessions/{session_id}/chat/stream")
async def session_chat_stream(session_id: str, message: str, industry: Optional[str] = None, req: Request = None):
    """流式Agent对话 (SSE)"""
    from agents.agent_coordinator import get_master_agent, get_session_manager

    if not message:
        return error_response(400, "消息不能为空")

    sm = get_session_manager()

    # 获取或创建会话
    if not sm.get_session(session_id):
        sm.create_session(
            session_id=session_id,
            industry=industry or "",
        )

    # 记录用户消息
    sm.add_message(session_id, "user", message)

    # 获取会话上下文
    history = sm.get_history(session_id)
    sess_industry = sm.get_industry(session_id)
    role = sm.get_role(session_id)

    async def generate():
        """SSE流式生成"""
        master = get_master_agent()

        # Step 1: 意图识别（发送开始事件）
        intent_result = await master.recognize_intent(message, industry=sess_industry, role=role)
        yield f"data: {__import__('json').dumps({'type': 'intent', 'data': intent_result}, ensure_ascii=False)}\n\n"

        # Step 2: 任务分解
        tasks = await master.decompose_task(intent_result, message, industry=sess_industry)
        yield f"data: {__import__('json').dumps({'type': 'tasks', 'data': [t.to_dict() for t in tasks]}, ensure_ascii=False)}\n\n"

        # Step 3: 执行任务（逐个发送结果）
        results = {}
        independent = [t for t in tasks if not t.depends_on]
        dependent = [t for t in tasks if t.depends_on]

        for task in independent:
            yield f"data: {__import__('json').dumps({'type': 'task_start', 'data': {'task_type': task.task_type}}, ensure_ascii=False)}\n\n"
            # 发送进度事件
            yield f"data: {__import__('json').dumps({'type': 'task_progress', 'data': {'task_type': task.task_type, 'status': 'running', 'progress': 10}}, ensure_ascii=False)}\n\n"
            result = await master._execute_single_task(task)
            results[task.task_type] = result
            # 发送完成进度事件
            yield f"data: {__import__('json').dumps({'type': 'task_progress', 'data': {'task_type': task.task_type, 'status': 'completed' if result.success else 'failed', 'progress': 100}}, ensure_ascii=False)}\n\n"
            yield f"data: {__import__('json').dumps({'type': 'task_result', 'data': {'task_type': task.task_type, 'success': result.success}}, ensure_ascii=False)}\n\n"

        for task in dependent:
            yield f"data: {__import__('json').dumps({'type': 'task_start', 'data': {'task_type': task.task_type}}, ensure_ascii=False)}\n\n"
            yield f"data: {__import__('json').dumps({'type': 'task_progress', 'data': {'task_type': task.task_type, 'status': 'running', 'progress': 10}}, ensure_ascii=False)}\n\n"
            result = await master._execute_single_task(task)
            results[task.task_type] = result
            yield f"data: {__import__('json').dumps({'type': 'task_progress', 'data': {'task_type': task.task_type, 'status': 'completed' if result.success else 'failed', 'progress': 100}}, ensure_ascii=False)}\n\n"
            yield f"data: {__import__('json').dumps({'type': 'task_result', 'data': {'task_type': task.task_type, 'success': result.success}}, ensure_ascii=False)}\n\n"

        # Step 4: 汇总结果
        final = await master.summarize_results(
            intent_result.get("intent", "general_qa"), results, message
        )
        answer = final.get("answer", "")

        # 记录助手回复
        sm.add_message(session_id, "assistant", str(answer))

        yield f"data: {__import__('json').dumps({'type': 'answer', 'data': final}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 50, req: Request = None):
    """获取会话消息历史"""
    from agents.agent_coordinator import get_session_manager

    sm = get_session_manager()
    history = sm.get_history(session_id)

    request_id = (req.headers.get("X-Request-ID", "") if req else "")
    if not sm.get_session(session_id):
        return error_response(404, f"会话不存在: {session_id}", request_id)

    return success_response({
        "session_id": session_id,
        "messages": history[-limit:],
        "total": len(history),
    }, request_id=request_id)


# ========== 工作流接口 ==========

@router.post("/workflows/{workflow_type}")
async def execute_workflow(workflow_type: str, request: WorkflowRequest, req: Request):
    """执行预定义工作流"""
    from agents.agent_coordinator import get_workflow_engine

    request_id = req.headers.get("X-Request-ID", "")

    supported = ["job_analysis", "skill_gap", "learning_path", "trend_analysis", "comprehensive_report"]
    if workflow_type not in supported:
        return error_response(400, f"未知工作流类型: {workflow_type}，支持: {supported}", request_id)

    try:
        engine = get_workflow_engine()
        params = {"query": request.query, "industry": request.industry or ""}
        if request.params:
            params.update(request.params)

        result = await engine.execute_workflow(workflow_type, params)
        return success_response(result, request_id=request_id)
    except Exception as e:
        logger.error(f"工作流执行失败: {str(e)}", exc_info=True)
        return error_response(500, f"工作流执行失败: {str(e)}", request_id)


# ========== 意图/工作流/行业/角色 查询接口 ==========

@router.get("/intents")
async def list_intents(req: Request):
    """列出支持的意图类型"""
    request_id = req.headers.get("X-Request-ID", "")
    intents = [
        {"type": "job_analysis", "description": "岗位能力分析", "example": "Python后端需要什么技能？"},
        {"type": "skill_gap", "description": "能力差距分析", "example": "我会Java，想转数据分析，差什么？"},
        {"type": "learning_path", "description": "学习路径规划", "example": "如何从前端转全栈？"},
        {"type": "trend_prediction", "description": "趋势预测分析", "example": "AI行业未来什么技能最重要？"},
        {"type": "job_compare", "description": "岗位对比分析", "example": "前端和后端的技能要求有什么不同？"},
        {"type": "resume_match", "description": "简历岗位匹配", "example": "我的简历适合投哪些岗位？"},
        {"type": "report_generation", "description": "报告生成", "example": "帮我出一份数据分析行业报告"},
        {"type": "general_qa", "description": "通用问答", "example": "什么是微服务架构？"},
    ]
    return success_response({"intents": intents}, request_id=request_id)


@router.get("/workflows")
async def list_workflows(req: Request):
    """列出支持的工作流"""
    request_id = req.headers.get("X-Request-ID", "")
    workflows = [
        {"type": "job_analysis", "description": "纯岗位分析", "flow": "岗位分析Agent -> 输出"},
        {"type": "skill_gap", "description": "能力差距分析", "flow": "岗位分析Agent -> 差距分析Agent -> 输出"},
        {"type": "learning_path", "description": "完整学习路径规划", "flow": "岗位分析Agent -> 差距分析Agent -> 学习规划Agent -> 输出"},
        {"type": "trend_analysis", "description": "趋势分析", "flow": "趋势预测Agent -> 输出"},
        {"type": "comprehensive_report", "description": "综合报告生成", "flow": "岗位分析Agent + 趋势预测Agent(并行) -> 报告生成Agent -> 输出"},
    ]
    return success_response({"workflows": workflows}, request_id=request_id)


@router.get("/industries")
async def list_industries(req: Request):
    """列出支持的行业"""
    from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY

    request_id = req.headers.get("X-Request-ID", "")
    industries = []
    for key, ctx in INDUSTRY_PROMPT_CONTEXT.items():
        industries.append({
            "code": key,
            "name": ctx.get("industry_name", key),
            "is_default": key == DEFAULT_INDUSTRY,
        })
    return success_response({"industries": industries, "default": DEFAULT_INDUSTRY}, request_id=request_id)


@router.get("/roles")
async def list_roles(req: Request):
    """列出支持的角色"""
    from utils.config import ROLE_CONFIG, DEFAULT_ROLE

    request_id = req.headers.get("X-Request-ID", "")
    roles = []
    for key, cfg in ROLE_CONFIG.items():
        roles.append({
            "code": key,
            "name": cfg.get("name", key),
            "description": cfg.get("description", ""),
            "is_default": key == DEFAULT_ROLE,
        })
    return success_response({"roles": roles, "default": DEFAULT_ROLE}, request_id=request_id)


@router.get("/tools")
async def list_tools(req: Request):
    """列出可用的工具"""
    from agents.agent_coordinator import get_tool_registry

    request_id = req.headers.get("X-Request-ID", "")
    registry = get_tool_registry()
    return success_response({"tools": registry.list_tools()}, request_id=request_id)


@router.get("/model-status")
async def get_model_status(req: Request):
    """获取当前模型状态"""
    from services.llm_service import get_llm_service

    request_id = req.headers.get("X-Request-ID", "")
    llm = get_llm_service()
    status = llm.get_status()
    return success_response({
        "provider": status.get("provider", "unknown"),
        "model": status.get("model", "unknown"),
        "health": status.get("health", {}),
    }, request_id=request_id)


# ========== 评价接口 ==========

@router.post("/evaluations")
async def create_evaluation(request: EvaluationRequest, req: Request):
    """提交用户评价"""
    request_id = req.headers.get("X-Request-ID", "")

    try:
        from services.db_service import get_db_service

        # 获取用户ID（可选）
        current_user = await _get_optional_user(req)
        user_id = current_user["user_id"] if current_user else 0

        db = get_db_service()
        eval_id = db.create_evaluation(
            message_id=request.message_id,
            user_id=user_id,
            user_score=request.user_score,
            user_feedback=request.user_feedback,
        )

        # 低分样本自动标记
        if request.user_score <= 2:
            logger.info(f"低分样本已标记: message_id={request.message_id}, score={request.user_score}")
            try:
                from services.evaluation_service import get_evaluation_service
                # 保存到评价服务的低分样本列表（后续优化用）
            except Exception:
                pass

        return success_response({"evaluation_id": eval_id}, request_id=request_id)
    except Exception as e:
        logger.error(f"创建评价失败: {str(e)}")
        return error_response(500, f"评价创建失败: {str(e)}", request_id)


# ========== 健康检查 ==========

@router.get("/health")
async def health_check_detailed(req: Request):
    """详细健康检查"""
    request_id = req.headers.get("X-Request-ID", "")

    services = {}

    # LLM连通性
    try:
        from services.llm_service import get_llm_service
        llm = get_llm_service()
        llm_status = llm.get_status()
        services["llm"] = {"status": "healthy", "model": llm_status.get("model", "")}
    except Exception:
        services["llm"] = {"status": "unhealthy"}

    # 数据库
    try:
        from services.db_service import get_db_service
        db = get_db_service()
        stats = db.get_stats()
        services["database"] = {"status": "healthy", "type": stats.get("database", "unknown")}
    except Exception:
        services["database"] = {"status": "unhealthy"}

    # Neo4j
    try:
        from services.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()
        services["neo4j"] = {"status": "healthy" if neo4j.is_connected() else "disconnected"}
    except Exception:
        services["neo4j"] = {"status": "unavailable"}

    # RAG
    try:
        from services.rag_service import get_rag_service
        rag = get_rag_service()
        services["rag"] = {"status": "healthy"}
    except Exception:
        services["rag"] = {"status": "unavailable"}

    all_healthy = all(s.get("status") in ("healthy", "disconnected") for s in services.values())

    return success_response({
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
    }, request_id=request_id)


# ========== 监控管理接口 ==========

@router.get("/admin/metrics")
async def get_metrics(req: Request):
    """获取监控指标汇总"""
    from services.metrics_service import get_metrics_collector

    request_id = req.headers.get("X-Request-ID", "")
    metrics = get_metrics_collector()
    summary = metrics.get_summary()

    # 合并会话与追踪统计
    try:
        from agents.agent_coordinator import get_session_manager
        sm = get_session_manager()
        sessions = sm.list_sessions()
        summary["active_sessions"] = len(sessions)
        summary["active_users"] = len({
            s.get("user_id", 0) for s in sessions if s.get("user_id")
        })
    except Exception:
        summary["active_sessions"] = 0
        summary["active_users"] = 0

    try:
        from services.trace_service import get_trace_service
        summary["trace_stats"] = get_trace_service().get_trace_stats()
    except Exception:
        summary["trace_stats"] = {}

    return success_response(summary, request_id=request_id)


@router.get("/admin/metrics/prometheus")
async def get_metrics_prometheus(req: Request):
    """导出Prometheus格式指标"""
    from services.metrics_service import get_metrics_collector

    metrics = get_metrics_collector()
    return StreamingResponse(
        iter([metrics.get_prometheus_format()]),
        media_type="text/plain",
    )


@router.get("/admin/traces")
async def get_traces(limit: int = 20, req: Request = None):
    """获取最近的追踪记录"""
    from services.trace_service import get_trace_service

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    trace_svc = get_trace_service()
    traces = trace_svc.get_recent_traces(limit=limit)
    return success_response({"traces": traces, "total": len(traces)}, request_id=request_id)


@router.get("/admin/traces/slow")
async def get_slow_traces(limit: int = 20, req: Request = None):
    """获取慢请求追踪"""
    from services.trace_service import get_trace_service

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    trace_svc = get_trace_service()
    traces = trace_svc.get_slow_traces(limit=limit)
    return success_response({"slow_traces": traces}, request_id=request_id)


@router.get("/admin/traces/{trace_id}")
async def get_trace_detail(trace_id: str, req: Request):
    """获取单个追踪的详细链路"""
    from services.trace_service import get_trace_service

    request_id = req.headers.get("X-Request-ID", "")
    trace_svc = get_trace_service()
    trace = trace_svc.get_trace(trace_id)
    if not trace:
        return error_response(404, f"追踪不存在: {trace_id}", request_id)
    return success_response(trace.to_dict(), request_id=request_id)


@router.get("/admin/trace-stats")
async def get_trace_stats(req: Request):
    """获取追踪统计"""
    from services.trace_service import get_trace_service

    request_id = req.headers.get("X-Request-ID", "")
    trace_svc = get_trace_service()
    return success_response(trace_svc.get_trace_stats(), request_id=request_id)


# ========== 监控指标数据库查询接口 ==========

class MetricQueryRequest(BaseModel):
    """指标查询请求"""
    metric_name: str = Field("", description="指标名称")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")
    since: str = Field("", description="起始时间 (ISO格式)")


@router.get("/admin/metrics/query")
async def query_metrics_from_db(metric_name: str = "", limit: int = 100,
                                 since: str = "", req: Request = None):
    """从数据库查询监控指标"""
    from services.db_service import get_db_service

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        db = get_db_service()
        metrics = db.query_metrics(metric_name=metric_name, limit=limit, since=since)
        return success_response({"metrics": metrics, "total": len(metrics)}, request_id=request_id)
    except Exception as e:
        return error_response(500, f"指标查询失败: {str(e)}", request_id)


@router.get("/admin/metrics/aggregate")
async def aggregate_metrics(metric_name: str, interval: str = "hour", req: Request = None):
    """聚合监控指标"""
    from services.db_service import get_db_service

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        db = get_db_service()
        result = db.aggregate_metrics(metric_name=metric_name, interval=interval)
        return success_response({"aggregations": result}, request_id=request_id)
    except Exception as e:
        return error_response(500, f"指标聚合失败: {str(e)}", request_id)


# ========== 评价管理接口 ==========

class RegressionCheckRequest(BaseModel):
    """回归检测请求"""
    baseline_scores: dict = Field(..., description="基线各维度得分 {intent_accuracy: 0.8, ...}")


@router.post("/admin/evaluations/batch")
async def run_batch_evaluation(req: Request):
    """运行批量评价流水线"""
    from services.evaluation_service import get_evaluation_service

    request_id = req.headers.get("X-Request-ID", "")
    try:
        svc = get_evaluation_service()
        result = await svc.run_batch_evaluation()
        return success_response(result, request_id=request_id)
    except Exception as e:
        logger.error(f"批量评价失败: {e}", exc_info=True)
        return error_response(500, f"批量评价失败: {str(e)}", request_id)


@router.get("/admin/evaluations/test-set")
async def get_test_set(req: Request):
    """获取当前测试集"""
    from services.evaluation_service import get_evaluation_service

    request_id = req.headers.get("X-Request-ID", "")
    svc = get_evaluation_service()
    return success_response({"test_cases": svc.get_test_set()}, request_id=request_id)


@router.post("/admin/evaluations/regression")
async def run_regression_check(request: RegressionCheckRequest, req: Request):
    """运行回归检测"""
    from services.evaluation_service import get_evaluation_service

    request_id = req.headers.get("X-Request-ID", "")
    try:
        svc = get_evaluation_service()
        result = await svc.run_regression_check(request.baseline_scores)
        return success_response(result, request_id=request_id)
    except Exception as e:
        logger.error(f"回归检测失败: {e}", exc_info=True)
        return error_response(500, f"回归检测失败: {str(e)}", request_id)


@router.get("/admin/evaluations/low-scores")
async def get_low_score_samples(limit: int = 50, req: Request = None):
    """获取低分样本列表"""
    from services.db_service import get_db_service

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        db = get_db_service()
        # 查询低分评价记录
        db.cursor.execute(db._q(
            "SELECT * FROM evaluations WHERE user_score <= 2 OR auto_score <= 2 "
            "ORDER BY created_at DESC LIMIT ?"
        ), (limit,))
        samples = [dict(row) for row in db.cursor.fetchall()]
        return success_response({"low_score_samples": samples, "total": len(samples)}, request_id=request_id)
    except Exception as e:
        return error_response(500, f"低分样本查询失败: {str(e)}", request_id)


# ==================== 告警管理接口 ====================

@router.get("/admin/alerts")
async def get_alerts(req: Request = None):
    """获取当前活跃告警和告警历史"""
    from services.metrics_service import get_alert_engine

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        engine = get_alert_engine()
        # 先执行一次规则检查
        engine.check_all_rules()
        return success_response({
            "active_alerts": [
                {
                    "rule_name": a.rule_name,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp,
                    "resolved": a.resolved,
                }
                for a in engine.get_active_alerts()
            ],
            "alert_history": [
                {
                    "rule_name": a.rule_name,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp,
                    "resolved": a.resolved,
                }
                for a in engine.get_alert_history(limit=50)
            ],
        }, request_id=request_id)
    except Exception as e:
        return error_response(500, f"告警查询失败: {str(e)}", request_id)


@router.get("/admin/alerts/rules")
async def get_alert_rules(req: Request = None):
    """获取告警规则列表"""
    from services.metrics_service import get_alert_engine

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        engine = get_alert_engine()
        return success_response({"rules": engine.get_rules()}, request_id=request_id)
    except Exception as e:
        return error_response(500, f"告警规则查询失败: {str(e)}", request_id)


@router.post("/admin/alerts/check")
async def check_alerts(req: Request = None):
    """手动触发告警规则检查"""
    from services.metrics_service import get_alert_engine

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        engine = get_alert_engine()
        new_alerts = engine.check_all_rules()
        return success_response({
            "triggered_count": len(new_alerts),
            "triggered_alerts": [
                {
                    "rule_name": a.rule_name,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
                for a in new_alerts
            ],
        }, request_id=request_id)
    except Exception as e:
        return error_response(500, f"告警检查失败: {str(e)}", request_id)


@router.post("/admin/alerts/{rule_name}/resolve")
async def resolve_alert(rule_name: str, req: Request = None):
    """解决告警"""
    from services.metrics_service import get_alert_engine

    request_id = req.headers.get("X-Request-ID", "") if req else ""
    try:
        engine = get_alert_engine()
        engine.resolve_alert(rule_name)
        return success_response({"message": f"告警 {rule_name} 已标记为已解决"}, request_id=request_id)
    except Exception as e:
        return error_response(500, f"告警解决失败: {str(e)}", request_id)
