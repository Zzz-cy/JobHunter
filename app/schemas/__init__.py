"""
Schema 聚合包

import 本包即可拿到所有对外 schema, 写法更短:
    from app.schemas import Result, BizCode, PageParams, PageResult, SchemaBase

组织方式(对齐 models 包):
    - base.py:     基类 SchemaBase / ORMOut
    - 后续新增的用户/简历等 schema 在这里追加 __all__ 即可
"""
from app.schemas.base import ORMOut, SchemaBase
from app.schemas.page import PageParams, PageResult
from app.schemas.result import BizCode, Result
from app.schemas.auth import RegisterSchema, LoginSchema, LoginOut, UserOut
from app.schemas.jobs import JobSearchSchema, CompanyBrief, JobSkillOut, JobOut
from app.schemas.stats import OverviewOut

__all__ = [
    # ---- 基类 ----
    "SchemaBase",
    "ORMOut",
    # ---- 通用 ----
    "Result",
    "BizCode",
    "PageParams",
    "PageResult",
    # ---- 登录注册 ----
    "RegisterSchema",
    "LoginSchema",
    "LoginOut",
    # ---- 获取用户信息 ----
    "UserOut",
    # ---- 获取工作信息 ----
    "JobSearchSchema",
    "CompanyBrief",
    "JobSkillOut",
    "JobOut",
    # ---- 统计数据 ----
    "OverviewOut",
]
