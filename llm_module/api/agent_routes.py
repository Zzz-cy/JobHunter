"""
Agent协同层 API接口
提供RESTful API和WebSocket接口
"""
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.logger import get_logger
logger = get_logger("api.agent_routes")

router = APIRouter(prefix="/agents", tags=["Agent协同"])


# ==================== 认证依赖辅助 ====================

async def _get_optional_user(request: Request) -> dict:
    """获取可选用户信息（从中间件注入的state中读取）。

    user_id 统一转 int：JWT sub 是字符串(如"2")，而库中 user_id 列读出是 int 2，
    字符串直传会导致所有权/续聊判断误判（会话被隐藏或重建）。
    """
    user_id = getattr(request.state, "user_id", 0)
    user_role = getattr(request.state, "user_role", "")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = 0
    if user_id:
        return {"user_id": user_id, "role": user_role}
    return None


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None
    user_job: Optional[str] = None
    # 岗位上下文(主站"问顾问"入口): 定位到具体某条 JD, 顾问针对该岗作答
    # 形如 {"job_id": 6320, "jd_text": "可选, 前端无 job_id 时直接传 JD 文本"}
    context: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    """工作流请求"""
    query: str = ""


@router.post("/chat")
async def agent_chat(request: ChatRequest, req: Request = None):
    """
    Agent智能对话入口 - 支持会话管理和行业上下文
    """
    from agents.agent_coordinator import get_master_agent, get_session_manager
    from utils.security import InputSanitizer

    if not request.message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    try:
        request.message = InputSanitizer.sanitize_string(request.message, max_length=5000)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_id = 0
    if req:
        current_user = await _get_optional_user(req)
        user_id = current_user["user_id"] if current_user else 0
    
    try:
        master = get_master_agent()
        sm = get_session_manager()
    
        session_id = request.session_id
        if not session_id or not sm.get_session(session_id, user_id=user_id if user_id else None):
            session_id = sm.create_session(
                session_id=session_id,
                industry=request.industry or "",
                role=request.role or "",
                user_id=user_id,
            )
    
        if request.industry:
            sm.set_industry(session_id, request.industry)
        if request.role:
            sm.set_role(session_id, request.role)
    
        sm.add_message(session_id, "user", request.message)
    
        history = sm.get_context_window(session_id)
        industry = sm.get_industry(session_id)
        role = sm.get_role(session_id)
    
        user_message = request.message
        if request.user_job:
            user_message = f"[用户职业: {request.user_job}] {request.message}"
    
        # ===== 已登录用户: 取其主库最新简历画像, 让 resume_match/skill_gap 等按真实简历作答 =====
        user_profile = None
        if user_id:
            try:
                from services.db_service import get_db_service
                user_profile = get_db_service().get_user_resume_profile(user_id)
            except Exception as e:
                logger.debug(f"读取用户简历画像失败(降级为用户自述): {e}")
        # ===== 画像注入结束 =====

        # ===== 岗位上下文(主站"问顾问"入口): 有 job_id 就读主库该岗位真实JD, 让顾问针对这条JD作答 =====
        job_context = None
        if request.context:
            try:
                from services.db_service import get_db_service
                ctx = request.context
                jid = ctx.get("job_id")
                job_context = {"job_id": jid}
                if jid:
                    job = get_db_service().get_job(jid)
                    if job:
                        _lo, _hi = job.get("salary_min"), job.get("salary_max")
                        _salary = "薪资面议"
                        if _lo or _hi:
                            _unit = (job.get("salary_unit") or "").strip().lower()
                            _s = f"{int(_lo or 0)}-{int(_hi or 0)}" if _hi else str(int(_lo or 0))
                            _salary = (_s + ("元/月" if _unit in ("month", "月") else "元/年" if _unit in ("year", "年") else "元"))
                        job_context.update({
                            "title": job.get("title", ""),
                            "city": job.get("city", ""),
                            "salary": _salary,
                            "experience": job.get("experience_req", ""),
                            "education": job.get("education_req", ""),
                            "description": (job.get("description_text") or job.get("description") or ""),
                        })
                jd_text = (ctx.get("jd_text") or "").strip()
                if jd_text:
                    job_context["description"] = jd_text
                if not (job_context.get("title") or job_context.get("description")):
                    job_context = None  # 两个来源都没有 → 视为无岗位上下文
            except Exception as e:
                logger.debug(f"解析岗位上下文失败(降级为普通对话): {e}")
                job_context = None
        # ===== 岗位上下文解析结束 =====

        # ========== 总超时保护：多Agent/长生成(简历匹配/报告)可达1-3分钟, 给300秒(对齐nginx proxy_read_timeout 300s) ==========
        try:
            result = await asyncio.wait_for(
                master.process(
                    user_message,
                    history=history,
                    industry=industry,
                    role=role,
                    user_profile=user_profile,
                    job_context=job_context,
                ),
                timeout=300
            )
        except asyncio.TimeoutError:
            from services.metrics_service import get_metrics_collector
            get_metrics_collector().record_request(500, 300.0)
            get_metrics_collector().increment("requests_errors", labels={"type": "timeout"})
            logger.error(f"Agent处理总超时(300s): {request.message[:80]}")
            result = {
                "answer": "抱歉，这条请求处理超时了(可能是上游模型较慢或请求过于复杂)。请稍后重试；若连续失败，可把问题拆小一点再问。",
                "intent": {"intent": "timeout", "confidence": 0},
                "tasks": [],
                "results": {},
            }
        # ========== 总超时保护结束 ==========
    
        answer = result.get("answer", "")
        # 把本次会话真实生成的岗位卡片随消息落库(recommended_jobs 列), 前端历史回放可再渲染/再点
        _cards = result.get("recommended_jobs")
        sm.add_message(
            session_id, "assistant", str(answer),
            recommended_jobs=_cards if isinstance(_cards, list) else None,
        )
    
        try:
            await sm.compress_context(session_id)
        except Exception:
            pass
    
        result["session_id"] = session_id
        return result
    except Exception as e:
        logger.error(f"Agent对话失败: {str(e)}", exc_info=True)
        from services.metrics_service import get_metrics_collector
        get_metrics_collector().increment("requests_errors", labels={"type": "server_error"})
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/workflow/{workflow_type}")
async def execute_workflow(workflow_type: str, request: WorkflowRequest):
    """执行预定义工作流"""
    from agents.agent_coordinator import get_workflow_engine

    try:
        engine = get_workflow_engine()
        result = await asyncio.wait_for(
            engine.execute_workflow(workflow_type, {"query": request.query}),
            timeout=120
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"工作流超时: {workflow_type}")
        raise HTTPException(status_code=504, detail="工作流处理超时，请简化请求后重试")
    except Exception as e:
        logger.error(f"工作流执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")


@router.get("/intents")
async def list_intents():
    """列出支持的意图类型"""
    return {
        "intents": [
            {"type": "job_analysis", "description": "岗位能力分析", "example": "Python后端需要什么技能？"},
            {"type": "skill_gap", "description": "能力差距分析", "example": "我会Java，想转数据分析，差什么？"},
            {"type": "learning_path", "description": "学习路径规划", "example": "如何从前端转全栈？"},
            {"type": "trend_prediction", "description": "趋势预测分析", "example": "AI行业未来什么技能最重要？"},
            {"type": "job_compare", "description": "岗位对比分析", "example": "前端和后端的技能要求有什么不同？"},
            {"type": "resume_match", "description": "简历岗位匹配", "example": "我的简历适合投哪些岗位？"},
            {"type": "report_generation", "description": "报告生成", "example": "帮我出一份数据分析行业报告"},
            {"type": "general_qa", "description": "通用问答", "example": "什么是微服务架构？"},
        ]
    }


@router.get("/workflows")
async def list_workflows():
    """列出支持的工作流"""
    return {
        "workflows": [
            {
                "type": "job_analysis",
                "description": "纯岗位分析",
                "flow": "岗位分析Agent -> 输出",
                "agents": ["岗位分析Agent"]
            },
            {
                "type": "skill_gap",
                "description": "能力差距分析",
                "flow": "岗位分析Agent -> 差距分析Agent -> 输出",
                "agents": ["岗位分析Agent", "差距分析Agent"]
            },
            {
                "type": "learning_path",
                "description": "完整学习路径规划",
                "flow": "岗位分析Agent -> 差距分析Agent -> 学习规划Agent -> 输出",
                "agents": ["岗位分析Agent", "差距分析Agent", "学习规划Agent"]
            },
            {
                "type": "trend_analysis",
                "description": "趋势分析",
                "flow": "趋势预测Agent -> 输出",
                "agents": ["趋势预测Agent"]
            },
            {
                "type": "comprehensive_report",
                "description": "综合报告生成",
                "flow": "岗位分析Agent + 趋势预测Agent(并行) -> 报告生成Agent -> 输出",
                "agents": ["岗位分析Agent", "趋势预测Agent", "报告生成Agent"]
            },
        ]
    }


@router.get("/industries")
async def list_industries():
    """列出支持的行业"""
    from utils.config import INDUSTRY_PROMPT_CONTEXT, DEFAULT_INDUSTRY
    industries = []
    for key, ctx in INDUSTRY_PROMPT_CONTEXT.items():
        industries.append({
            "code": key,
            "name": ctx.get("industry_name", key),
            "is_default": key == DEFAULT_INDUSTRY,
        })
    return {"industries": industries, "default": DEFAULT_INDUSTRY}


@router.get("/model-status")
async def get_model_status():
    """获取当前模型状态"""
    from services.llm_service import get_llm_service
    llm = get_llm_service()
    status = llm.get_status()
    return {
        "provider": status.get("provider", "unknown"),
        "model": status.get("model", "unknown"),
        "default_model": status.get("default_model", ""),
        "health": status.get("health", {}),
    }


class SetDefaultModelRequest(BaseModel):
    """设置平台默认模型请求"""
    model: str = ""


@router.get("/models")
async def list_models():
    """列出可用模型(含成本档位)与当前平台默认模型"""
    from services.llm_service import get_llm_service
    from utils.config import ALL_MODELS, FALLBACK_CONFIGS
    llm = get_llm_service()
    # 可选列表 = 智谱 glm-* + 已配好 key 的跨厂商模型(deepseek/kimi/通义/讯飞星火)
    available = [
        {
            "name": name,
            "provider": cfg.get("provider") or "zhipu",
            "provider_label": cfg.get("provider_label") or "智谱",
            "tier": cfg.get("tier", ""),
            "cost_per_1k": cfg.get("cost_per_1k", 0),
            "json_mode": cfg.get("json_mode", False),
            "tool_call": cfg.get("tool_call", False),
            "max_tokens": cfg.get("max_tokens", 4096),
            "description": cfg.get("description", ""),
        }
        for name, cfg in ALL_MODELS.items()
    ]
    return {
        "provider": "zhipu",
        "current": llm.get_admin_default_model(),
        "admin_default": llm.get_admin_default_model(),
        "available": available,
        "fallback_providers_configured": [p for p, c in FALLBACK_CONFIGS.items() if c.get("api_key")],
    }


@router.post("/models/default")
async def set_default_model(body: SetDefaultModelRequest, req: Request = None):
    """设置平台默认模型(仅管理员)。影响后续生成/分析类任务所用模型; 意图识别等轻任务仍走廉价路由。"""
    from services.llm_service import get_llm_service
    role = ""
    if req:
        cu = await _get_optional_user(req)
        role = (cu or {}).get("role", "")
    if role not in ("admin", "administrator", "超级管理员"):
        raise HTTPException(status_code=403, detail="仅管理员可设置平台默认模型")
    try:
        llm = get_llm_service()
        model = llm.set_admin_default_model(body.model)
        return {"status": "ok", "default_model": model}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"设置默认模型失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"设置失败: {str(e)}")


@router.get("/sessions")
async def list_sessions(req: Request = None):
    """列出所有会话"""
    from agents.agent_coordinator import get_session_manager
    sm = get_session_manager()
    user_id = None
    if req:
        current_user = await _get_optional_user(req)
        user_id = current_user["user_id"] if current_user else None
    return {"sessions": sm.list_sessions(user_id=user_id)}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 200, req: Request = None):
    """获取某会话的完整历史消息(读库, 供前端刷新后续聊/回看)"""
    from agents.agent_coordinator import get_session_manager
    sm = get_session_manager()
    user_id = None
    if req:
        current_user = await _get_optional_user(req)
        user_id = current_user["user_id"] if current_user else None
    result = sm.list_messages(session_id, user_id=user_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=403, detail="无权访问此会话或会话不存在")
    return result


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, req: Request = None):
    """删除会话"""
    from agents.agent_coordinator import get_session_manager
    sm = get_session_manager()
    user_id = None
    if req:
        current_user = await _get_optional_user(req)
        user_id = current_user["user_id"] if current_user else None
    success = sm.destroy_session(session_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=403, detail="无权删除此会话")
    return {"status": "deleted", "session_id": session_id}


@router.get("/roles")
async def list_roles():
    """列出支持的角色"""
    from utils.config import ROLE_CONFIG, DEFAULT_ROLE
    roles = []
    for key, cfg in ROLE_CONFIG.items():
        roles.append({
            "code": key,
            "name": cfg.get("name", key),
            "description": cfg.get("description", ""),
            "is_default": key == DEFAULT_ROLE,
        })
    return {"roles": roles, "default": DEFAULT_ROLE}


@router.get("/tools")
async def list_tools():
    """列出可用的工具"""
    from agents.agent_coordinator import get_tool_registry
    registry = get_tool_registry()
    return {"tools": registry.list_tools()}


@router.post("/evaluations")
async def create_evaluation(
    message_id: int,
    user_score: float = 0,
    user_feedback: str = "",
):
    """提交用户评价"""
    try:
        from services.db_service import get_db_service
        db = get_db_service()
        eval_id = db.create_evaluation(
            message_id=message_id,
            user_score=user_score,
            user_feedback=user_feedback,
        )
        return {"status": "success", "evaluation_id": eval_id}
    except Exception as e:
        logger.error(f"创建评价失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"评价创建失败: {str(e)}")


