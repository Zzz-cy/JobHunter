"""认证相关 Schema(注册/登录)。

注册只建账号不发 token; 登录发 JWT + 用户信息。出参绝不包含 password_hash。
"""
from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.base import SchemaBase


# ============================================================
# 注册入参
# ============================================================
class RegisterSchema(SchemaBase):
    """注册请求体。user_code / password_hash 由后端生成。"""

    # 账号(手机号/邮箱至少传一个)
    phone: str | None = Field(
        default=None,
        pattern=r"^1[3-9]\d{9}$",
        description="手机号(明文传输, 后端存库)",
        examples=["13800138000"],
    )
    email: str | None = Field(
        default=None,
        pattern=r"^[\w.+-]+@[\w-]+\.[\w.-]+$",
        description="邮箱",
        examples=["user@example.com"],
    )

    # 密码(明文, 后端哈希)
    password: str = Field(
        min_length=6, max_length=64,
        description="明文密码, 后端哈希成 hash 存库",
        examples=["abc123456"],
    )

    # 资料(可选)
    nickname: str | None = Field(default=None, max_length=64, examples=["张三"])
    avatar_url: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def _check_account(self) -> "RegisterSchema":
        """手机号和邮箱至少传一个, 否则没法登录。"""
        if not self.phone and not self.email:
            raise ValueError("phone 和 email 至少传一个")
        return self


# 登录入参
class LoginSchema(SchemaBase):
    """
    登录请求体(account 手机号或邮箱 + 密码)。
    """

    account: str = Field(
        min_length=4, max_length=128,
        description="手机号或邮箱(不校验格式, 交给数据库)",
        examples=["13800138000"],
    )
    password: str = Field(
        min_length=1, max_length=64,
        description="明文密码",
        examples=["abc123456"],
    )


# 用户信息出参(登录成功后返回的用户对象)
class UserOut(SchemaBase):
    """用户信息出参(登录/个人信息接口复用), 绝不带 password_hash。"""

    id: int
    user_code: str
    phone: str | None = None
    email: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    role: str = "user"
    created_at: datetime | None = None


# 登录出参
class LoginOut(SchemaBase):
    """登录成功出参(token + 用户信息)。"""

    token: str = Field(description="JWT, 前端存 localStorage, 后续请求放 Authorization 头")
    user: UserOut
