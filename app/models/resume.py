"""
Resume 简历相关模型

对应数据库表:
    - resumes              简历主表
    - resume_skills        简历-技能关联(M:N)
    - resume_experiences   工作经历(1:N)
    - resume_educations    教育经历(1:N)

⚠️ 注意: JSON 类型用 SQLAlchemy 的 JSON, MySQL 8 自动用原生 JSON 类型。
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DECIMAL,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, SoftDeleteMixin, TimestampMixin


# ============================================================
# 简历主表
# ============================================================
class Resume(Base, TimestampMixin, SoftDeleteMixin):
    """简历主表, 元信息 + parsed_raw 原始解析结果。"""

    __tablename__ = "resumes"

    id: Mapped[int] = BigIntPk()
    resume_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # ---------- 关联用户 ----------
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ---------- 基本信息 ----------
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[int | None] = mapped_column(Integer)  # 0男 1女
    age: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(128))

    # ---------- 简历来源 ----------
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    file_url: Mapped[str | None] = mapped_column(String(512))

    # ---------- 解析状态机 ----------
    parse_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True,
    )
    parse_error: Mapped[str | None] = mapped_column(String(512))

    # ---------- 求职意向 ----------
    work_years: Mapped[int | None] = mapped_column(Integer)
    education: Mapped[str | None] = mapped_column(String(16))
    expect_salary_min: Mapped[int | None] = mapped_column(Integer)
    expect_salary_max: Mapped[int | None] = mapped_column(Integer)
    expect_city: Mapped[str | None] = mapped_column(String(64))
    expect_job: Mapped[str | None] = mapped_column(String(128))

    # ---------- 评分 ----------
    overall_score: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 2))

    # ---------- 原始解析结果 ----------
    parsed_raw: Mapped[dict | None] = mapped_column(JSON)

    # ---------- 关系 ----------
    user: Mapped["User"] = relationship(back_populates="resumes")  # noqa: F821
    skills: Mapped[list["ResumeSkill"]] = relationship(
        back_populates="resume", lazy="selectin", cascade="all, delete-orphan",
    )
    experiences: Mapped[list["ResumeExperience"]] = relationship(
        back_populates="resume", lazy="selectin", cascade="all, delete-orphan",
    )
    educations: Mapped[list["ResumeEducation"]] = relationship(
        back_populates="resume", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, name={self.name!r}, status={self.parse_status!r})>"


# ============================================================
# 简历-技能关联 (M:N)
# ============================================================
class ResumeSkill(Base):
    """简历与技能的多对多关联表, 带熟练度/年限属性。"""

    __tablename__ = "resume_skills"
    __table_args__ = (
        UniqueConstraint("resume_id", "skill_id", name="uk_resume_skill"),
    )

    id: Mapped[int] = BigIntPk()
    resume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resumes.id"), nullable=False, index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False, index=True,
    )
    proficiency: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    years: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))

    resume: Mapped[Resume] = relationship(back_populates="skills")

    def __repr__(self) -> str:
        return f"<ResumeSkill(resume_id={self.resume_id}, skill_id={self.skill_id}, prof={self.proficiency})>"


# ============================================================
# 工作经历 (1:N)
# ============================================================
class ResumeExperience(Base):
    """简历工作经历明细。"""

    __tablename__ = "resume_experiences"

    id: Mapped[int] = BigIntPk()
    resume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resumes.id"), nullable=False, index=True,
    )
    company_name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(String(128))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    resume: Mapped[Resume] = relationship(back_populates="experiences")


# ============================================================
# 教育经历 (1:N)
# ============================================================
class ResumeEducation(Base):
    """简历教育经历明细。"""

    __tablename__ = "resume_educations"

    id: Mapped[int] = BigIntPk()
    resume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resumes.id"), nullable=False, index=True,
    )
    school: Mapped[str] = mapped_column(String(128), nullable=False)
    major: Mapped[str | None] = mapped_column(String(128))
    degree: Mapped[str | None] = mapped_column(String(32))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    resume: Mapped[Resume] = relationship(back_populates="educations")
