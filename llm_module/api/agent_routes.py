"""
Agent协同层 API接口
提供RESTful API和WebSocket接口
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.logger import get_logger
logger = get_logger("api.agent_routes")

router = APIRouter(prefix="/agents", tags=["Agent协同"])


# ==================== 认证依赖辅助 ====================

async def _get_optional_user(request: Request) -> dict:
    """获取可选用户信息（从中间件注入的state中读取）"""
    user_id = getattr(request.state, "user_id", 0)
    user_role = getattr(request.state, "user_role", "")
    if user_id and user_id != 0:
        return {"user_id": user_id, "role": user_role}
    return None


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None
    user_job: Optional[str] = None


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
    
        # ========== 总超时保护：120秒必须返回 ==========
        try:
            result = await asyncio.wait_for(
                master.process(
                    user_message,
                    history=history,
                    industry=industry,
                    role=role,
                ),
                timeout=120
            )
        except asyncio.TimeoutError:
            from services.metrics_service import get_metrics_collector
            get_metrics_collector().record_request(500, 120.0)
            get_metrics_collector().increment("requests_errors", labels={"type": "timeout"})
            logger.error(f"Agent处理总超时(120s): {request.message[:80]}")
            result = {
                "answer": "抱歉，处理您的请求耗时过长，请尝试简化问题后重试。例如直接问'Python后端需要什么技能'。",
                "intent": {"intent": "timeout", "confidence": 0},
                "tasks": [],
                "results": {},
            }
        # ========== 总超时保护结束 ==========
    
        answer = result.get("answer", "")
        sm.add_message(session_id, "assistant", str(answer))
    
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
        "health": status.get("health", {}),
    }


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


