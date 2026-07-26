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


# ============================================================
# 求职进度出参(Application → Job → Company 嵌套结构)
# ============================================================
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
    """求职进度出参。

    时间字段用 datetime 类型(ORM 里就是 datetime),Pydantic 会自动序列化成 ISO 字符串。
    status 可空:纯收藏的记录 status=None;投递过的才有值(submitted/interviewed/...)。
    """
    job: jobApplication
    submitted_at: datetime | None = None
    note: str | None = None
    status: str | None = None

class applicationSchema(SchemaBase):
    """修改求职进度的入参。

    入参用 SchemaBase(extra=forbid),禁止前端传多余字段,早暴露问题。
    (之前误继承 ORMOut 是出参基类,语义不对)

    job_id 必填(告诉后端要改哪条记录),status/note 可选(传哪个改哪个)。
    job_id 用 int 跟数据库 BIGINT 对齐(str 在严格模式下会校验失败)。
    """
    job_id: int
    status: str | None = Field(default=None, max_length=16)
    note: str | None = None


