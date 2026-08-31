"""
Job 职位相关模型

对应数据库表:
    - jobs         职位主表(爬虫核心产物)
    - job_skills   职位-技能关联(M:N)
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DECIMAL,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, SoftDeleteMixin, TimestampMixin


# 职位主表
class Job(Base, TimestampMixin, SoftDeleteMixin):
    """职位主表(爬虫核心产物, MySQL 存元信息, ES 存全文检索)。"""

    __tablename__ = "jobs"

    id: Mapped[int] = BigIntPk()
    job_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id"), index=True,
    )

    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    district: Mapped[str | None] = mapped_column(String(64))

    # 要求
    experience_req: Mapped[str | None] = mapped_column(String(32))
    education_req: Mapped[str | None] = mapped_column(String(32))

    # 字段验证器: 学历归一化(入库时自动清洗)
    from sqlalchemy.orm import validates

    @validates("education_req")
    def _normalize_education(self, key, value):
        """写入时把脏学历('统招本科'等)归一到 博士/硕士/本科/大专/不限。"""
        if not value:
            return None
        v = str(value)
        if "博士" in v: return "博士"
        if "硕士" in v: return "硕士"
        if "本科" in v or "统招" in v: return "本科"
        if "大专" in v or "专科" in v: return "大专"
        return "不限"   # 学历不限/中专等

    @validates("experience_req")
    def _normalize_experience(self, key, value):
        """
        写入时把脏经验要求归一到 5 档。
        """
        if not value:
            return None
        v = str(value)
        # 先判断"不限"(优先级最高, 经验不限=不限)
        if "不限" in v: return "不限"
        # 从高到低判断年限(避免"10年"被"1年"误匹配)
        if "10" in v: return "10年+"
        if "5" in v or "6" in v or "7" in v or "8" in v or "9" in v: return "5-10年"
        if "3" in v or "4" in v: return "3-5年"
        if "1" in v or "2" in v: return "1-3年"
        return "应届"   # 应届/1年以内/无经验要求 等

    # 薪资
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="month")
    salary_months: Mapped[int | None] = mapped_column(Integer)

    # 类型
    job_type: Mapped[str] = mapped_column(String(16), nullable=False, default="full")

    # JD 内容
    description: Mapped[str | None] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text)
    highlights: Mapped[list | None] = mapped_column(JSON)
    advantage: Mapped[str | None] = mapped_column(Text)
    work_address: Mapped[str | None] = mapped_column(String(255))

    # 地理位置
    longitude: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 7))
    latitude: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 7))

    # 来源追溯
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="boss")
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64))
    crawl_batch: Mapped[str | None] = mapped_column(String(32))

    # 状态
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", index=True,
    )
    publish_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    crawl_at: Mapped[datetime | None] = mapped_column(DateTime)
    quality_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 2))

    # 关系-
    # lazy="selectin": 预加载, 避免 async 模式下访问 company 时触发同步懒加载(MissingGreenlet)
    company: Mapped["Company"] = relationship(back_populates="jobs", lazy="selectin")  # noqa: F821
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, title={self.title!r}, "
            f"source={self.source!r}, status={self.status!r})>"
        )


# 职位-技能关联 (M:N)
class JobSkill(Base):
    """职位与技能的多对多关联表, 带权重/必须性。"""

    __tablename__ = "job_skills"
    __table_args__ = (
        UniqueConstraint("job_id", "skill_id", name="uk_job_skill"),
    )

    id: Mapped[int] = BigIntPk()
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id"), nullable=False, index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False, index=True,
    )
    is_must: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weight: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 2))

    # 关系
    # 双向关系: JobSkill 一端连 Job, 一端连 Skill
    # 拿技能名: job_skill.skill.name
    job: Mapped[Job] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(  # noqa: F821
        back_populates="job_skills", lazy="selectin",
    )

    # 派生属性(给 schema 用)
    # Pydantic v2 的 from_attributes 模式不能跨 relationship 取值,
    # 在 ORM 上加 @property 桥接, schema 用普通字段就能取到 skill 字典表的字段。
    @property
    def skill_name(self) -> str | None:
        """技能标准名, 从关联的 Skill 字典表取。"""
        return self.skill.name if self.skill else None

    @property
    def skill_code(self) -> str | None:
        """技能编码, 用于前端按技能搜索。"""
        return self.skill.skill_code if self.skill else None

    @property
    def category(self) -> str | None:
        """技能分类(语言/框架/工具/方向/软技能), 影响 SkillTag 颜色。"""
        return self.skill.category if self.skill else None

    @property
    def is_hot(self) -> int:
        """是否热门技能, 影响 SkillTag 是否显示火焰图标。"""
        return self.skill.is_hot if self.skill else 0

    def __repr__(self) -> str:
        return f"<JobSkill(job_id={self.job_id}, skill_id={self.skill_id}, must={self.is_must})>"
