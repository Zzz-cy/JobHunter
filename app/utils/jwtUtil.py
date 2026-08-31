"""JWT 令牌工具模块 —— 负责令牌的生成、解析与用户身份认证"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User

load_dotenv()  # 加载 .env 文件中的环境变量

# JWT 签名密钥，从环境变量读取，避免硬编码泄露
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
# 签名算法，HS256 为基于 HMAC 的对称签名（同一密钥签名+验签，非加密）
ALGORITHM = "HS256"
# 令牌默认过期时间（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# 从请求头 Authorization: Bearer <token> 中提取令牌
# tokenUrl 指向登录接口，FastAPI 自动生成 Swagger 文档中的"锁"图标
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT。data 写入载荷(如 {"sub": user.id}), 不传过期时长用默认值。"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # exp = 过期时间, JWT 标准字段
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析 JWT 返回载荷。过期/签名无效/格式错误抛 JWTError。"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """依赖项: 解 token 拿当前用户, 无效或用户不存在抛 401。

    用法: 路由参数加 current_user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        # sub 存的是登录时签发的 user.id(数字主键, 已转成字符串)
        # 便于跨服务统一用户标识(LLM 服务也用数字 user_id)
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except (JWTError, ValueError):
        # JWTError: 令牌过期/签名无效/格式错误
        # ValueError: 万一 payload 解析出来 sub 是意料之外的类型(防御性兜底)
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == int(user_id)))
    if user is None:
        raise credentials_exception
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """管理员鉴权: 在 get_current_user 基础上再校 role == 'admin', 非管理员 403。"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
