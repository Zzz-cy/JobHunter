"""
认证相关路由
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import RegisterSchema, Result, LoginSchema, LoginOut, UserOut
from app.services.auth_service import register, login

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=Result, summary="用户注册")
async def register_user(payload: RegisterSchema, db: AsyncSession = Depends(get_db)):
    """
    接收手机号、邮箱和密码，返回成功
    """
    await register(payload, db)
    return Result.success(message="注册成功")


@router.post("/login", response_model=Result[LoginOut], summary="用户登录")
async def login_user(user: LoginSchema, db: AsyncSession = Depends(get_db)):
    """
    接收邮箱和手机号登录，返回token和用户信息
    """
    login_out = await login(user, db)
    return Result.success(data=login_out)
