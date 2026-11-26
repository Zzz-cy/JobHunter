"""User 用户模型。"""
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPk, SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """系统用户表(求职者/管理员)。"""

    __tablename__ = "users"

    # 主键
    id: Mapped[int] = BigIntPk()

    # 对外编码
    user_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # 联系方式(明文存储)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(128), unique=True)

    # 注销留档: 注销时把原联系方式拷到这里, phone/email 置 NULL 释放唯一键
    # 仅审计用(查"该手机号是否曾注销/重新注册"), 不参与登录/搜索/唯一约束
    deleted_phone: Mapped[str | None] = mapped_column(String(20))
    deleted_email: Mapped[str | None] = mapped_column(String(128))

    # 凭据
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # 资料
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    # 求职期望(首登引导建档收集)
    expected_city: Mapped[str | None] = mapped_column(String(20))
    expected_job: Mapped[str | None] = mapped_column(String(50))
    expected_salary: Mapped[str | None] = mapped_column(String(10))

    # 是否已完成首登引导建档(0=否, 1=是)
    onboarded: Mapped[int] = mapped_column(nullable=False, default=0)

    # 角色
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")

    # 账号状态(normal=正常, banned=已封禁; 封禁后不能登录, 在线会话下一次请求即失效)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")

    # 活跃度
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    # 关系(1:N 简历)
    # lazy="selectin" 表示查询 user 时自动把 resumes 一起查出来(避免 N+1)
    # 如果担心性能, 可以改为 lazy="raise" 强制显式 eager load
    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, nickname={self.nickname!r}, role={self.role!r})>"
