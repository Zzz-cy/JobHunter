from datetime import datetime

from pydantic import Field

from app.schemas import ORMOut, SchemaBase


class UserUpdateSchema(ORMOut):
    """更新用户资料的入参(昵称/手机号/邮箱/密码)。"""
    nickname: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$")
    email: str | None = Field(default=None, pattern=r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
    old_password: str | None = Field(default=None, min_length=6, max_length=64)
    new_password: str | None = Field(default=None, min_length=6, max_length=64)


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


