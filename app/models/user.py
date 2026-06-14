"""
User 用户模型

对应数据库表: users

⚠️ 重要: 字段名/类型必须和数据库一致, 否则 ORM 查询会报错。
对照参考: backend/db/mysql/01_schema.sql 第 47-65 行
"""
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """系统用户表(求职者/管理员)。"""

    __tablename__ = "users"

    # ---------- 主键 ----------
    id: Mapped[int] = BigIntPk()

    # ---------- 对外编码 ----------
    user_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # ---------- 联系方式(加密存储) ----------
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(128), unique=True)

    # ---------- 凭据 ----------
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # ---------- 资料 ----------
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    # ---------- 角色 ----------
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")

    # ---------- 活跃度 ----------
    last_login_at: Mapped[str | None] = mapped_column(DateTime)

    # ---------- 关系(1:N 简历) ----------
    # lazy="selectin" 表示查询 user 时自动把 resumes 一起查出来(避免 N+1)
    # 如果担心性能, 可以改为 lazy="raise" 强制显式 eager load
    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, nickname={self.nickname!r}, role={self.role!r})>"
