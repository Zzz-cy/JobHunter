"""
用户行为 & 业务模型

对应数据库表:
    - applications       用户-职位关系(点击/收藏/外站投递反馈)
    - recommendations    推荐结果流水
    - chat_history       AI对话历史

注意:
    - applications 用完整 TimestampMixin + SoftDeleteMixin
    - recommendations / chat_history 只有 created_at(只增不改), 不用 mixin, 单独定义
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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, SoftDeleteMixin, TimestampMixin


# ============================================================
# 用户-职位关系
# ============================================================
class Application(Base, TimestampMixin, SoftDeleteMixin):
    """用户-职位关系表(点击/收藏/外站投递反馈)。

    本平台不代投, 仅提供 jobs.source_url 跳转;
    applied 之后状态依赖用户手动反馈。
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uk_user_job"),
    )

    id: Mapped[int] = BigIntPk()
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True,
    )
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id"), nullable=False, index=True,
    )
    resume_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("resumes.id"),
    )

    # ---------- 状态机 ----------
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="clicked", index=True,
    )
    match_score: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 2))

    # ---------- 时间点 ----------
    redirected_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime)

    # ---------- 统计 ----------
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ---------- 扩展 ----------
    external_source: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(String(512))

    # ---------- 关系 ----------
    user: Mapped["User"] = relationship()  # noqa: F821
    job: Mapped["Job"] = relationship()  # noqa: F821
    resume: Mapped["Resume"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Application(user_id={self.user_id}, job_id={self.job_id}, "
            f"status={self.status!r})>"
        )


# ============================================================
# 推荐流水
# ============================================================
class Recommendation(Base):
    """推荐结果流水, 每次(用户, 岗位)推荐一条, 用于A/B与效果回溯。"""

    __tablename__ = "recommendations"

    id: Mapped[int] = BigIntPk()
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True,
    )
    resume_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("resumes.id"),
    )
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id"), nullable=False,
    )

    score: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    strategy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="rag", index=True,
    )
    snapshot: Mapped[dict | None] = mapped_column(JSON)
    clicked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Recommendation(user_id={self.user_id}, job_id={self.job_id}, "
            f"score={self.score}, strategy={self.strategy!r})>"
        )


# ============================================================
# AI 对话历史
# ============================================================
class ChatHistory(Base):
    """AI对话历史, 按session聚合。"""

    __tablename__ = "chat_history"

    id: Mapped[int] = BigIntPk()
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSON)
    tokens: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ChatHistory(session={self.session_id!r}, role={self.role!r})>"
