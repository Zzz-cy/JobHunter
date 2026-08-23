"""
爬虫管理模型

对应数据库表:
    - crawl_sources  数据源配置
    - crawl_tasks    任务执行记录
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk


# ============================================================
# 数据源配置
# ============================================================
class CrawlSource(Base):
    """爬虫数据源配置(boss/liepin/qcc 等)。

    主键 INT(非 BIGINT); 纯配置表, 不带软删除。
    """

    __tablename__ = "crawl_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="job")
    base_url: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    config: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # ---------- 关系(1:N 任务) ----------
    tasks: Mapped[list["CrawlTask"]] = relationship(
        back_populates="source", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CrawlSource(id={self.id}, name={self.name!r}, type={self.type!r})>"


# ============================================================
# 任务执行记录
# ============================================================
class CrawlTask(Base):
    """爬虫任务执行记录。"""

    __tablename__ = "crawl_tasks"

    id: Mapped[int] = BigIntPk()
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crawl_sources.id"), nullable=False, index=True,
    )
    task_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    keyword: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(64))

    # ---------- 状态机 ----------
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True,
    )

    # ---------- 统计 ----------
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error_msg: Mapped[str | None] = mapped_column(String(512))
    start_at: Mapped[datetime | None] = mapped_column(DateTime)
    end_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    # ---------- 关系 ----------
    source: Mapped[CrawlSource] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        return f"<CrawlTask(id={self.id}, code={self.task_code!r}, status={self.status!r})>"
