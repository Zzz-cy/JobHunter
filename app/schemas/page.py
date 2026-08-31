"""通用分页 Schema: PageParams(入参) + PageResult[T](出参)。"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

from app.schemas.base import SchemaBase

# 泛型类型变量, 供 PageResult[T] 使用
T = TypeVar("T")


# 分页入参
class PageParams(SchemaBase):
    """通用分页入参(?page=1&page_size=10), offset 属性算偏移量。"""

    page: int = Field(
        default=1, ge=1,
        description="页码, 从 1 开始",
        examples=[1],
    )
    page_size: int = Field(
        default=10, ge=1, le=100,
        description="每页条数, 上限 100(防止一次拉爆)",
        examples=[10],
    )

    @property
    def offset(self) -> int:
        """SQLAlchemy limit/offset 用的偏移量。"""
        return (self.page - 1) * self.page_size


# 分页结果
class PageResult(BaseModel, Generic[T]):
    """通用分页返回结构(items + total + page + page_size)。"""

    items: list[T] = Field(description="当前页的数据列表")
    total: int = Field(default=0, ge=0, description="符合查询条件的总条数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=10, ge=1, description="每页条数")

    @computed_field
    @property
    def pages(self) -> int:
        """总页数(computed_field 会带进返回 JSON 和 Swagger 文档)。"""
        return (self.total + self.page_size - 1) // self.page_size

    @classmethod
    def from_query(
        cls,
        items: list[T],
        total: int,
        params: "PageParams",
    ) -> "PageResult[T]":
        """便捷工厂: 由查询结果 + 分页参数直接构造。"""
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )
