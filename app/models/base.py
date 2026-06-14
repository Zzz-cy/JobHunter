"""
SQLAlchemy 模型基类

所有模型继承 Base, 共享:
    - 同一个 DeclarativeBase 元数据(metadata)
    - 命名约定(便于 alembic 迁移)
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


class TimestampMixin:
    """时间戳混入, 业务表通用。

    提供两个字段:
        - created_at: 创建时间(由 MySQL 默认值填充)
        - updated_at: 更新时间(由 MySQL ON UPDATE 自动维护)

    注意: 这两个字段是数据库层维护的, Python 代码不需要手动赋值。
    """

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class SoftDeleteMixin:
    """软删除混入, 业务表通用。

    使用 is_deleted=1 标记删除, 不物理删除, 保留数据用于审计。
    查询时需要手动过滤 WHERE is_deleted = 0。
    """

    is_deleted: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="软删除标记 0=正常 1=已删除",
    )


# 公共主键工厂(每次调用返回新的 column 对象, 不能直接共享实例)
def big_int_pk():
    """返回一个 BIGINT 自增主键列。"""
    return mapped_column(BigInteger, primary_key=True, autoincrement=True)


# 兼容旧用法(返回 column 工厂而非实例)
BigIntPk = big_int_pk
