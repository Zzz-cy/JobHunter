"""
认证相关 Schema(注册/登录)

核心原则:
    - 注册: 只管"创建账号", 不自动登录, 不返回用户信息(前端拿到提示后跳登录页)
    - 登录: 管认证 + 发 token, 返回 token 和用户信息(前端据此进登录态)
    - 任何出参都绝不包含 password_hash

流程:
    注册:  前端传明文 password + phone/email → 校验唯一 → 密码哈希成 hash → 生成 user_code → 存库
    登录:  前端传 account(手机号/邮箱) + password → 查库校验 → 发 JWT
"""
from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.base import SchemaBase


# ============================================================
# 注册入参
# ============================================================
class RegisterSchema(SchemaBase):
    """注册请求体。

    前端只需要传手机号/邮箱 + 密码 + 可选昵称,
    user_code / password_hash 等内部字段由后端生成。
    """

    # ---------- 账号(手机号/邮箱至少传一个) ----------
    phone: str | None = Field(
        default=None,
        pattern=r"^1[3-9]\d{9}$",  # 中国手机号格式
        description="手机号(明文传输, 后端存库)",
        examples=["13800138000"],
    )
    email: str | None = Field(
        default=None,
        pattern=r"^[\w.+-]+@[\w-]+\.[\w.-]+$",  # 邮箱格式
        description="邮箱",
        examples=["user@example.com"],
    )

    # ---------- 密码(明文, 后端哈希) ----------
    password: str = Field(
        min_length=6, max_length=64,
        description="明文密码, 后端哈希成 hash 存库",
        examples=["abc123456"],
    )

    # ---------- 资料(可选) ----------
    nickname: str | None = Field(default=None, max_length=64, examples=["张三"])
    avatar_url: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def _check_account(self) -> "RegisterSchema":
        """手机号和邮箱至少传一个, 否则没法登录。"""
        if not self.phone and not self.email:
            raise ValueError("phone 和 email 至少传一个")
        return self


# ============================================================
# 登录入参
# ============================================================
class LoginSchema(SchemaBase):
    """登录请求体(account 接收手机号或邮箱 + 密码)。

    account 不校验手机号/邮箱格式, 因为:
        1. 格式错 → 数据库查不到 → 自然报"账号或密码错误"
        2. 统一错误提示更安全(不向攻击者泄露"这个账号格式对不对")
    只做轻校验: 防空、防明显瞎填(太短/太长)。
    真正的账号存在性 + 密码正确性交给数据库和业务层判断。

    ⚠️ 安全提醒: 登录失败时, 业务层应统一返回"账号或密码错误",
    不要分别提示"账号不存在"/"密码错误"(否则会泄露账号是否存在)。
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


# ============================================================
# 用户信息出参(登录成功后返回的用户对象)
# ============================================================
class UserOut(SchemaBase):
    """用户信息出参(给登录/个人信息接口复用)。

    ⚠️ 绝不出现 password_hash。id 用于接口交互, user_code 用于对外展示。
    """

    id: int
    user_code: str
    phone: str | None = None
    email: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    role: str = "user"
    created_at: datetime | None = None


# ============================================================
# 登录出参
# ============================================================
class LoginOut(SchemaBase):
    """登录成功后的出参(token + 用户信息)。

    注册成功不需要出参(只返回"注册成功"提示即可),
    登录成功才需要出参: 前端拿 token 进登录态, 拿用户信息渲染页面。

    ⚠️ 绝不能出现 password_hash, 否则严重安全漏洞。
    """

    token: str = Field(description="JWT, 前端存 localStorage, 后续请求放 Authorization 头")
    user: UserOut
