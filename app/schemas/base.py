"""Pydantic Schema 基类: 入参严格(extra=forbid), 出参宽松(extra=ignore)。"""
from pydantic import BaseModel, ConfigDict


# ============================================================
# 基础配置
# ============================================================
class SchemaBase(BaseModel):
    """所有 Schema 的基类(禁多余字段, 可直接从 ORM 构造)。"""

    model_config = ConfigDict(
        from_attributes=True,   # 允许从 ORM 对象构造(读 obj.attr)
        extra="forbid",         # 多余字段直接报错, 不静默丢弃
        populate_by_name=True,  # 允许 alias 和 字段名 都能赋值
    )


class ORMOut(SchemaBase):
    """出参基类: 忽略 ORM 上多余的字段, 只挑声明了的返回。"""

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",         # 出参场景下, ORM 上多余字段忽略即可
        populate_by_name=True,
    )
