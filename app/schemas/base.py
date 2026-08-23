"""
Pydantic Schema 基类

所有对外(请求/响应)的 Schema 都继承这里的基类, 共享:
    - 统一的 model_config(禁止额外字段 / 从 ORM 取值)

本文件只放"基类", 具体的 schema 各自成文件:
    - 分页:     schemas/page.py
    - 统一返回:  schemas/result.py
    - 业务:     schemas/page.py 等

设计原则:
    1. Schema 只负责"数据长什么样", 不写业务逻辑。
    2. 入参用严格模式(extra=forbid), 防止前端传多余字段埋雷。
    3. 出参用宽松模式, 只返回字段声明了的, 隐藏 ORM 内部细节。
"""
from pydantic import BaseModel, ConfigDict


# ============================================================
# 基础配置
# ============================================================
class SchemaBase(BaseModel):
    """所有 Schema 的基类。

    默认行为:
        - 禁止客户端传未声明的字段(extra=forbid), 早暴露问题。
        - 读取 ORM 对象时按属性名取值(from_attributes=True)。
        - 允许从 ORM 模型直接构造: Schema.model_validate(orm_obj)。
    """

    model_config = ConfigDict(
        from_attributes=True,   # 允许从 ORM 对象构造(读 obj.attr)
        extra="forbid",         # 多余字段直接报错, 不静默丢弃
        populate_by_name=True,  # 允许 alias 和 字段名 都能赋值
    )


class ORMOut(SchemaBase):
    """出参基类(从 ORM 模型序列化)。

    和 SchemaBase 的唯一区别: 允许忽略前端传来的多余字段,
    适合用来接收 ORM 对象后只挑关心的字段返回。
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",         # 出参场景下, ORM 上多余字段忽略即可
        populate_by_name=True,
    )
