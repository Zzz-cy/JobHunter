from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas import ORMOut, SchemaBase
from app.schemas.page import PageParams


class UserUpdateSchema(ORMOut):
    """更新用户资料的入参(昵称/手机号/邮箱/密码)。"""
    nickname: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$")
    email: str | None = Field(default=None, pattern=r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
    old_password: str | None = Field(default=None, min_length=6, max_length=64)
    new_password: str | None = Field(default=None, min_length=6, max_length=64)


class OnboardingSchema(SchemaBase):
    """首登引导建档入参(期望城市/职位/薪资三项必填)。"""
    expected_city: str = Field(min_length=1, max_length=20, description="期望城市")
    expected_job: str = Field(min_length=1, max_length=50, description="期望职位")
    expected_salary: Literal["0-10", "10-20", "20-30", "30-50", "50-"] = Field(
        description="期望薪资档位"
    )


class DeleteAccountSchema(SchemaBase):
    """注销账号入参(需输入登录密码确认, 防误触/防他人借登录态恶意注销)。"""

    password: str = Field(min_length=1, max_length=64, description="登录密码")


# ============================================================
# 账号管理(管理员)
# ============================================================
class AdminUserQuery(PageParams, ORMOut):
    """账号管理用户列表查询入参(keyword 匹配昵称或手机号)。"""

    keyword: str | None = Field(default=None, max_length=64, description="昵称或手机号(模糊)")


class AdminUserOut(ORMOut):
    """账号管理用户列表出参(只含列表需要的字段, 不含密码/邮箱)。"""

    id: int
    nickname: str | None = None
    phone: str | None = None
    role: str
    status: str
    created_at: datetime | None = None
    last_login_at: datetime | None = None
    onboarded: bool = False


class AdminUserRoleSchema(SchemaBase):
    """设为/收回管理员入参。"""

    role: Literal["admin", "user"] = Field(description="目标角色")


class AdminUserStatusSchema(SchemaBase):
    """封禁/解封入参。"""

    status: Literal["normal", "banned"] = Field(description="目标状态")


# 求职进度出参(Application → Job → Company 嵌套结构)
class companyApplication(ORMOut):
    name: str


class jobApplication(ORMOut):
    id: int                       # 职位 id(前端调"修改/删除求职进度"接口时需要)
    title: str
    city: str
    salary_min: int
    salary_max: int
    source_url: str
    company: companyApplication   # 嵌套:Job 关联的 Company


class applicationOut(ORMOut):
    """求职进度出参。纯收藏的记录 status=None, 投递过才有值。"""
    job: jobApplication
    submitted_at: datetime | None = None
    note: str | None = None
    status: str | None = None

class applicationSchema(SchemaBase):
    """修改求职进度的入参。job_id 必填, status/note 传哪个改哪个。"""
    job_id: int
    status: str | None = Field(default=None, max_length=16)
    note: str | None = None


