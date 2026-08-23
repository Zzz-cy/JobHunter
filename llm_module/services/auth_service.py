"""
JWT认证服务 - 密码哈希、令牌生成/验证、用户认证
"""
from __future__ import annotations

import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from utils.config import AUTH_CONFIG
from utils.logger import get_logger
logger = get_logger("services.auth_service")

# 安全方案
security = HTTPBearer(auto_error=False)

# 尝试导入JWT库
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT未安装，认证功能不可用")

# 尝试导入密码哈希库
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False
    logger.warning("passlib未安装，密码哈希功能不可用")


class AuthService:
    """JWT认证服务 - 密码哈希、令牌生成/验证"""

    def __init__(self):
        self._secret_key = AUTH_CONFIG["secret_key"]
        self._algorithm = AUTH_CONFIG["algorithm"]
        self._access_token_expire_minutes = AUTH_CONFIG["access_token_expire_minutes"]
        self._refresh_token_expire_days = AUTH_CONFIG["refresh_token_expire_days"]
        self._db = None  # 懒加载，避免循环导入

    def _get_db(self):
        """懒加载数据库服务"""
        if self._db is None:
            from services.db_service import get_db_service
            self._db = get_db_service()
        return self._db

    # ========== 密码管理 ==========

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        if not PASSLIB_AVAILABLE:
            raise RuntimeError("passlib未安装，无法哈希密码")
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        if not PASSLIB_AVAILABLE:
            raise RuntimeError("passlib未安装，无法验证密码")
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.warning(f"密码验证异常: {e}")
            return False

    # ========== 令牌管理 ==========

    def create_access_token(self, user_id: int, username: str, role: str) -> str:
        """创建访问令牌"""
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT未安装，无法创建令牌")
        expire = datetime.utcnow() + timedelta(minutes=self._access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: int) -> str:
        """创建刷新令牌"""
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT未安装，无法创建令牌")
        expire = datetime.utcnow() + timedelta(days=self._refresh_token_expire_days)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌"""
        if not JWT_AVAILABLE:
            return None
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"令牌无效: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """使用刷新令牌获取新的访问令牌"""
        payload = self.decode_token(refresh_token)
        if not payload:
            return None
        if payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # 从数据库获取用户信息
        db = self._get_db()
        user = db.get_user_by_id(user_id)
        if not user:
            return None

        access_token = self.create_access_token(user_id, user["username"], user.get("role", "job_seeker"))
        new_refresh_token = self.create_refresh_token(user_id)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    # ========== FastAPI依赖 ==========

    async def get_current_user(self, request: Request) -> Dict[str, Any]:
        """
        获取当前认证用户（FastAPI Depends用）
        无有效令牌时抛出401异常

        ⚠️ 本服务不再管理用户数据, 用户统一由 backend 管理。
        这里只做纯验签: 用共享密钥校验签名, 通过后直接信任 token 载荷,
        不再查本服务的 user 表(避免跨库 user_id 不一致导致 401)。
        密钥来源: 环境变量 JWT_SECRET_KEY(与 backend 同名同值)。
        """
        credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
        if not credentials:
            raise HTTPException(status_code=401, detail="未提供认证令牌")

        token = credentials.credentials
        payload = self.decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="令牌无效或已过期")

        # 兼容老格式 token(只有 sub, 没有 type); 新格式 token type=="access"
        token_type = payload.get("type")
        if token_type not in (None, "access"):
            raise HTTPException(status_code=401, detail="令牌类型错误，请使用访问令牌")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="令牌内容无效")

        # 直接从 token 读取身份信息, 不查库
        # (role 老格式没有时降级为 job_seeker, 保证旧 token 不会 401)
        return {
            "user_id": user_id,
            "username": payload.get("username", ""),
            "role": payload.get("role", "job_seeker"),
        }

    async def get_optional_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        获取当前用户（可选，向后兼容）
        无令牌时返回None而非抛异常
        """
        try:
            return await self.get_current_user(request)
        except HTTPException:
            return None


# 单例
_auth_service: Any = None


def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
