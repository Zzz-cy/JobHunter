"""
认证API路由 - 用户注册、登录、令牌刷新、用户信息
"""
from __future__ import annotations

import re
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field

from utils.logger import get_logger
logger = get_logger("api.v1.auth_routes")


# ==================== 请求模型 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50,
                          description="用户名（字母数字下划线）")
    password: str = Field(..., min_length=6, max_length=100,
                          description="密码（至少6位）")
    email: Optional[str] = Field(None, description="邮箱")
    industry: Optional[str] = Field(None, description="行业 (it/finance/healthcare/manufacturing/education)")
    role: Optional[str] = Field(None, description="角色 (job_seeker/hr/career_planner/manager)")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


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

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register")
async def register(request: RegisterRequest, req: Request):
    """用户注册（已废弃）

    本服务不再独立管理用户。用户注册请走主服务 backend 的 /auth/register。
    保留路由是为了老前端不报 404, 但返回 410 Gone 提示迁移。
    """
    request_id = req.headers.get("X-Request-ID", "")
    return error_response(
        410,
        "本服务已不再独立鉴权, 请通过主服务 backend /auth/register 注册",
        request_id,
    )


@router.post("/login")
async def login(request: LoginRequest, req: Request):
    """用户登录（已废弃）

    本服务不再独立管理用户。用户登录请走主服务 backend 的 /auth/login,
    拿到 token 后用 Authorization: Bearer <token> 透传给本服务即可。
    """
    request_id = req.headers.get("X-Request-ID", "")
    return error_response(
        410,
        "本服务已不再独立鉴权, 请通过主服务 backend /auth/login 登录",
        request_id,
    )


@router.post("/refresh")
async def refresh(request: RefreshRequest, req: Request):
    """刷新访问令牌（已废弃）

    本服务不再签发令牌。刷新令牌请走主服务 backend。
    """
    request_id = req.headers.get("X-Request-ID", "")
    return error_response(
        410,
        "本服务已不再签发令牌, 刷新请通过主服务 backend /auth/* 接口",
        request_id,
    )


@router.get("/me")
async def get_me(req: Request):
    """获取当前用户信息（需认证）

    ⚠️ 本服务不再管理用户数据, 这里只返回 token 里携带的身份信息。
    完整用户资料请走主服务 backend 的用户接口。
    """
    request_id = req.headers.get("X-Request-ID", "")

    from services.auth_service import get_auth_service
    auth = get_auth_service()
    current_user = await auth.get_current_user(req)

    return success_response({
        "user_id": current_user["user_id"],
        "username": current_user.get("username", ""),
        "role": current_user.get("role", "job_seeker"),
        # 以下字段本服务已无数据, 仅占位避免前端报错
        "email": "",
        "industry": "",
        "created_at": "",
    }, message="用户信息来自令牌(完整资料请查询主服务)", request_id=request_id)
