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


# ============================================================
# 职位主表
# ============================================================
class Job(Base, TimestampMixin, SoftDeleteMixin):
    """职位主表(爬虫核心产物, MySQL 存元信息, ES 存全文检索)。"""

    __tablename__ = "jobs"

    id: Mapped[int] = BigIntPk()
    job_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id"), index=True,
    )

    # ---------- 基本信息 ----------
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    district: Mapped[str | None] = mapped_column(String(64))

    # ---------- 要求 ----------
    experience_req: Mapped[str | None] = mapped_column(String(32))
    education_req: Mapped[str | None] = mapped_column(String(32))

    # ---------- 薪资 ----------
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="month")
    salary_months: Mapped[int | None] = mapped_column(Integer)

    # ---------- 类型 ----------
    job_type: Mapped[str] = mapped_column(String(16), nullable=False, default="full")

    # ---------- JD 内容 ----------
    description: Mapped[str | None] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text)
    highlights: Mapped[list | None] = mapped_column(JSON)
    advantage: Mapped[str | None] = mapped_column(Text)
    work_address: Mapped[str | None] = mapped_column(String(255))

    # ---------- 地理位置 ----------
    longitude: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 7))
    latitude: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 7))

    # ---------- 来源追溯 ----------
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="boss")
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64))
    crawl_batch: Mapped[str | None] = mapped_column(String(32))

    # ---------- 状态 ----------
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", index=True,
    )
    publish_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    crawl_at: Mapped[datetime | None] = mapped_column(DateTime)
    quality_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 2))

    # ---------- 关系 ----------
    company: Mapped["Company"] = relationship(back_populates="jobs")  # noqa: F821
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, title={self.title!r}, "
            f"source={self.source!r}, status={self.status!r})>"
        )


# ============================================================
# 职位-技能关联 (M:N)
# ============================================================
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

    job: Mapped[Job] = relationship(back_populates="skills")

    def __repr__(self) -> str:
        return f"<JobSkill(job_id={self.job_id}, skill_id={self.skill_id}, must={self.is_must})>"
