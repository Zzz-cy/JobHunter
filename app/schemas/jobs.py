"""
职位相关 Schema
"""
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import ORMOut
from app.schemas.page import PageParams


# 职位搜索入参
class JobSearchSchema(PageParams, ORMOut):
    """职位列表搜索入参(继承 PageParams 自带分页字段)。

    keyword 是模糊跨表搜索(职位名/技能/公司), 其余精确匹配。
    """

    # ---------- 业务筛选条件 ----------
    keyword: str | None = Field(default=None, description="关键词: 职位名/技能/公司")
    city: str | None = None
    experience: str | None = None  # 经验
    education: str | None = None
    industry: str | None = Field(default=None, description="行业 code, 如 IT / IT-RD")
    salary_range: str | None = Field(default=None, description="薪资区间(K), 如 '10-20' / '50-'")
    source: str | None = None
    sort: str = Field(default="latest", description="排序: latest/salary")


# 出参: 公司信息(嵌套在 JobOut 里)
class CompanyBrief(ORMOut):
    """职位卡片展示的公司简要信息。industry_name 桥接自 ORM 的 @property。"""

    id: int
    name: str
    short_name: str | None = None
    industry_code: str | None = None
    size: str | None = None
    logo_url: str | None = None
    industry_name: str | None = None


# 出参: 技能(嵌套在 JobOut 里)
class JobSkillOut(ORMOut):
    """职位要求的单个技能。skill_name 等字段桥接自 ORM 的 @property。"""

    skill_id: int
    is_must: int = 0
    weight: Decimal | None = None
    skill_name: str | None = None
    skill_code: str | None = None
    category: str | None = None  # 分类(语言/框架/工具), 影响 SkillTag 颜色
    is_hot: int = 0  # 是否热门, 影响 SkillTag 是否显示火焰图标


# 出参: 职位详情(列表项)
class JobOut(ORMOut):
    """职位列表项出参(前端 JobCard 渲染用)。"""

    id: int
    job_code: str
    title: str
    city: str | None = None
    district: str | None = None
    experience_req: str | None = None
    education_req: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_unit: str = "month"
    job_type: str = "full"
    highlights: list | None = None
    source: str = "boss"
    source_url: str
    publish_at: datetime | None = None

    # ---------- 嵌套关联 ----------
    company: CompanyBrief | None = None  # 来自 Job.company relationship
    skills: list[JobSkillOut] = []  # 来自 Job.skills relationship


class CompanyDetail(CompanyBrief):
    """公司完整信息(详情页用), 继承 Brief 自动带 industry_name。"""
    full_name: str | None = None
    stage: str | None = None
    city: str | None = None
    address: str | None = None
    website: str | None = None
    welfare: list[str] | None = None
    description: str | None = None


class JobDetailOut(JobOut):
    """职位详情, 在 JobOut 上加 JD 正文等字段。"""

    # 详情页才需要的字段
    description: str | None = None  # JD HTML 正文
    description_text: str | None = None  # JD 纯文本
    advantage: str | None = None  # 职位亮点
    job_type: str = "full"
    highlights: list | None = None
    address: str | None = None

    # 详情页公司信息更全
    company: CompanyDetail | None = None  # 覆盖父类的 Brief


class IndustryOut(ORMOut):
    id: int
    code: str
    name: str
    parent_id: int | None = None
    level: int
