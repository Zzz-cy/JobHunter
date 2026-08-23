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
    """职位列表搜索入参。

    继承 PageParams 自动拥有分页字段(page / page_size, 带默认值和校验),
    本类只声明业务筛选条件。

    对应前端 JobList.vue 的所有筛选条件。
    keyword 是模糊跨表搜索(职位名/技能/公司), 其余都是精确匹配。
    """

    # ---------- 业务筛选条件 ----------
    keyword: str | None = Field(default=None, description="关键词: 职位名/技能/公司")
    city: str | None = None
    experience: str | None = None  # 经验
    education: str | None = None
    industry: str | None = Field(default=None, description="行业 code, 如 IT / IT-RD")
    salary_range: str | None = Field(default=None, description="薪资区间(K), 如 '10-20' / '50-'")
    source: str | None = None
    sort: str = Field(default="default", description="排序: default/latest/salary")


# 出参: 公司信息(嵌套在 JobOut 里)
class CompanyBrief(ORMOut):
    """职位卡片上展示的公司简要信息。

    industry_name 来自 ORM 模型上的 @property(桥接 Company.industry.name),
    CompanyDetail 继承本类时自动拥有该字段。
    """

    id: int
    name: str
    short_name: str | None = None
    industry_code: str | None = None
    size: str | None = None
    logo_url: str | None = None
    industry_name: str | None = None


# 出参: 技能(嵌套在 JobOut 里)
class JobSkillOut(ORMOut):
    """职位要求的单个技能。

    skill_name / category / is_hot 都来自 ORM 模型上的 @property
    (桥接 JobSkill.skill 字典表), Pydantic 的 from_attributes 模式能直接取到。

    proficiency / years 是简历技能的字段, 职位没有, 故不声明
    (SkillTag 组件用 v-if 判断, 缺失就不显示)。
    """

    skill_id: int
    is_must: int = 0
    weight: Decimal | None = None
    skill_name: str | None = None
    skill_code: str | None = None
    category: str | None = None  # 分类(语言/框架/工具), 影响 SkillTag 颜色
    is_hot: int = 0  # 是否热门, 影响 SkillTag 是否显示火焰图标


# 出参: 职位详情(列表项)
class JobOut(ORMOut):
    """职位列表项出参。

    前端 JobCard 组件渲染需要的字段。
    """

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
    """公司完整(详情页用)。

    继承 CompanyBrief, 自动拥有 industry_code + industry_name(computed_field),
    """
    full_name: str | None = None
    stage: str | None = None
    city: str | None = None
    address: str | None = None
    website: str | None = None
    welfare: list[str] | None = None
    description: str | None = None


class JobDetailOut(JobOut):
    """职位详情(重量)。

    继承 JobOut, 在其基础上加详情字段。
    """

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
