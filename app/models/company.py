"""
Company 公司模型

对应数据库表: companies
"""
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, SoftDeleteMixin, TimestampMixin


class Company(Base, TimestampMixin, SoftDeleteMixin):
    """公司信息表(多源聚合, (name, source) 联合唯一)。"""

    __tablename__ = "companies"

    id: Mapped[int] = BigIntPk()
    company_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # ---------- 基本信息 ----------
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(64))
    industry_code: Mapped[str | None] = mapped_column(String(32), index=True)
    size: Mapped[str | None] = mapped_column(String(32))
    stage: Mapped[str | None] = mapped_column(String(32))

    # ---------- 地址 ----------
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    district: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(String(255))

    # ---------- 资产 ----------
    logo_url: Mapped[str | None] = mapped_column(String(512))
    website: Mapped[str | None] = mapped_column(String(255))

    # ---------- 详情 ----------
    welfare: Mapped[list | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)

    # ---------- 来源追溯 ----------
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="boss")
    source_url: Mapped[str | None] = mapped_column(String(512))

    # ---------- 关系(1:N 职位) ----------
    jobs: Mapped[list["Job"]] = relationship(  # noqa: F821
        back_populates="company", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name!r}, source={self.source!r})>"
