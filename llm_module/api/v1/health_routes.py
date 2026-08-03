"""
增强健康检查路由 - 存活/就绪/LLM探测
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from utils.config import HEALTH_CONFIG
from utils.logger import get_logger
logger = get_logger("api.v1.health_routes")


# ==================== 响应辅助 ====================

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


# ==================== 路由 ====================

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("/live")
async def liveness():
    """存活检查 - 进程在运行即返回"""
    return success_response({"status": "alive"})


@router.get("/ready")
async def readiness(req: Request):
    """
    就绪检查 - 所有依赖服务可用

    检查：数据库、LLM服务、Neo4j、ChromaDB
    """
    request_id = req.headers.get("X-Request-ID", "")
    checks = {}
    all_ready = True

    # 数据库检查
    try:
        from services.db_service import get_db_service
        db = get_db_service()
        stats = db.get_stats()
        checks["database"] = {
            "status": "ready",
            "type": stats.get("database", "unknown"),
        }
    except Exception as e:
        checks["database"] = {"status": "not_ready", "error": str(e)}
        all_ready = False

    # LLM服务检查
    try:
        from services.llm_service import get_llm_service
        llm = get_llm_service()
        llm_status = llm.get_status()
        health = llm_status.get("health", {})
        # 检查是否有健康模型
        has_healthy = any(
            v.get("status") in ("healthy", "unknown")
            for v in health.values()
        ) if isinstance(health, dict) else True
        checks["llm"] = {
            "status": "ready" if has_healthy else "degraded",
            "model": llm_status.get("model", "unknown"),
        }
        if not has_healthy:
            all_ready = False
    except Exception as e:
        checks["llm"] = {"status": "not_ready", "error": str(e)}
        all_ready = False

    # Neo4j检查
    try:
        from services.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()
        connected = neo4j.is_connected()
        checks["neo4j"] = {
            "status": "ready" if connected else "disconnected",
        }
        # Neo4j断开不算不可用，只是功能降级
    except Exception:
        checks["neo4j"] = {"status": "unavailable"}

    # 向量数据库检查
    try:
        from services.vector_store import get_vector_store
        vs = get_vector_store()
        vs_stats = vs.get_stats()
        checks["vector_db"] = {
            "status": "ready",
            "using_chromadb": vs_stats.get("using_chromadb", False),
        }
    except Exception:
        checks["vector_db"] = {"status": "unavailable"}

    return success_response({
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }, request_id=request_id)


@router.get("/probe")
async def llm_probe(req: Request):
    """
    LLM连通性探测 - 发送轻量请求验证API可达性

    返回延迟和连通状态
    """
    request_id = req.headers.get("X-Request-ID", "")

    if not HEALTH_CONFIG.get("llm_probe_enabled", True):
        return success_response({
            "llm_reachable": None,
            "message": "LLM探测已禁用",
        }, request_id=request_id)

    try:
        from services.llm_service import get_llm_service
        llm = get_llm_service()

        start = time.time()
        # 发送最小化请求
        result = await llm.chat(
            [{"role": "user", "content": HEALTH_CONFIG.get("llm_probe_prompt", "Hi")}],
            task_type="intent_classification",
        )
        latency = (time.time() - start) * 1000  # 转换为毫秒

        return success_response({
            "llm_reachable": True,
            "latency_ms": round(latency, 1),
            "model": llm.get_status().get("model", "unknown"),
        }, request_id=request_id)

    except Exception as e:
        return success_response({
            "llm_reachable": False,
            "error": str(e),
        }, request_id=request_id)
