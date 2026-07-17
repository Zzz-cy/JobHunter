"""
职位相关 Schema
"""
from datetime import datetime
from decimal import Decimal

from pydantic import Field, computed_field

from app.schemas.base import ORMOut
from app.schemas.page import PageParams


# ============================================================
# 职位搜索入参
# ============================================================
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


# ============================================================
# 出参: 公司简要(嵌套在 JobOut 里)
# ============================================================
class CompanyBrief(ORMOut):
    """职位卡片上展示的公司简要信息。"""

    id: int
    name: str
    short_name: str | None = None
    industry_code: str | None = None
    size: str | None = None
    logo_url: str | None = None


# ============================================================
# 出参: 技能(嵌套在 JobOut 里)
# ============================================================
class JobSkillOut(ORMOut):
    """职位要求的单个技能。

    数据来源: job_skills 关联表 + skills 字典表(通过 relationship 取 name)。
    ORM 对象 job_skill 上没有 skill_name 属性, 用 computed_property
    从 job_skill.skill.name 取值。
    """

    skill_id: int
    is_must: int = 0
    weight: Decimal | None = None

    @computed_field
    @property
    def skill_name(self) -> str | None:
        """技能标准名, 从关联的 Skill 字典表取。"""
        # ORM 对象通过 JobSkill.skill relationship 访问 Skill.name
        # from_attributes 模式下, Pydantic 会把 self 当 ORM 对象,
        # 这里用 getattr 兜底, 防止 skill 关系未加载时报错。
        skill = getattr(self, "skill", None)
        return getattr(skill, "name", None) if skill else None


# ============================================================
# 出参: 职位详情(列表项)
# ============================================================
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
    company: CompanyBrief | None = None       # 来自 Job.company relationship
    skills: list[JobSkillOut] = []            # 来自 Job.skills relationship
