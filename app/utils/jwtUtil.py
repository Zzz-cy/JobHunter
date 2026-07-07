"""JWT 令牌工具模块 —— 负责令牌的生成、解析与用户身份认证"""

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from models import User

load_dotenv()  # 加载 .env 文件中的环境变量

# JWT 签名密钥，从环境变量读取，避免硬编码泄露
SECRET_KEY = os.getenv("secret_key")
# 签名算法，HS256 为对称加密（同一密钥签名+验签）
ALGORITHM = "HS256"
# 令牌默认过期时间（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 从请求头 Authorization: Bearer <token> 中提取令牌
# tokenUrl 指向登录接口，FastAPI 自动生成 Swagger 文档中的"锁"图标
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT 令牌

    Args:
        data: 要写入令牌载荷的数据，如 {"sub": user.id}（sub = subject，即用户标识）
        expires_delta: 自定义过期时长，不传则使用默认值 ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # exp = expiration，过期时间，JWT 标准字段
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析 JWT 令牌，返回载荷字典

    Args:
        token: JWT 字符串

    Returns:
        载荷字典，包含 sub、exp 等字段

    Raises:
        JWTError: 令牌过期、签名无效或格式错误时抛出
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI 依赖项：从请求头中提取令牌并返回当前用户对象

    使用方式：在路由函数参数中加 current_user: User = Depends(get_current_user)
    如果令牌无效或用户不存在，自动返回 401 错误。

    Args:
        token: 由 oauth2_scheme 自动从请求头提取的 JWT 字符串

    Returns:
        当前登录的 User 模型实例

    Raises:
        HTTPException 401: 令牌无效、过期或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))  # sub 字段存的是用户 id（字符串），转回 int
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await User.get_or_none(id=user_id)
    if user is None:
        raise credentials_exception
    return user
