"""
通用分页 Schema

从 schemas/base.py 拆出来, 因为它俩不是"基类/混入", 而是拿来直接用的具体 schema,
单独成文件更符合本项目的组织方式(类比 models/base.py 只放 Base/mixin,
具体模型各自成文件)。

内容:
    - PageParams:   分页入参(?page=1&page_size=10), 内置 offset 算偏移量
    - PageResult[T]: 分页返回结构(items + total + page + page_size), 泛型
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

from app.schemas.base import SchemaBase

# 泛型类型变量, 供 PageResult[T] 使用
T = TypeVar("T")


# ============================================================
# 分页入参
# ============================================================
class PageParams(SchemaBase):
    """通用分页查询参数。

    所有列表接口(职位列表/简历列表/...)都接收它,
    在路由里展开成 page / page_size 即可。

    用法:
        @router.get("/jobs")
        async def list_jobs(params: PageParams = Depends()):
            ...
    """

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


# ============================================================
# 分页结果
# ============================================================
class PageResult(BaseModel, Generic[T]):
    """通用分页返回结构。

    任何需要分页的接口, 把列表数据塞进 items 即可,
    前端按 total 算总页数: math.ceil(total / page_size)。

    用法:
        jobs = await session.scalars(select(Job).limit(...).offset(...))
        return PageResult(items=jobs.all(), total=count, page=1, page_size=10)
    """

    items: list[T] = Field(description="当前页的数据列表")
    total: int = Field(default=0, ge=0, description="符合查询条件的总条数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=10, ge=1, description="每页条数")

    @computed_field
    @property
    def pages(self) -> int:
        """总页数(向上取整)。

        用 @computed_field 让它出现在返回前端的 JSON 里 + Swagger 文档里,
        前端不用自己算 Math.ceil(total / page_size)。
        """
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
