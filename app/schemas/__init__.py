"""Schema 聚合包: import 本包即可拿到所有对外 schema。"""
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
