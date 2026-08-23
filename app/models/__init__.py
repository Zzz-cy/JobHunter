"""
模型聚合包

import 本包即可触发所有模型注册到 Base.metadata,
便于 alembic 迁移和 create_all 建表。

用法:
    from app.models import User, Resume
    # 或
    from app.models import Base
"""
from app.models.base import Base
from app.models.behavior import Application, ChatHistory, Recommendation
from app.models.company import Company
from app.models.crawl import CrawlSource, CrawlTask
from app.models.dict import Industry, Skill
from app.models.job import Job, JobSkill
from app.models.resume import (
    Resume,
    ResumeEducation,
    ResumeExperience,
    ResumeSkill,
)
from app.models.user import User

__all__ = [
    "Base",
    # ---- 字典层 ----
    "Skill",
    "Industry",
    # ---- 用户 & 简历 ----
    "User",
    "Resume",
    "ResumeSkill",
    "ResumeExperience",
    "ResumeEducation",
    # ---- 公司 & 职位 ----
    "Company",
    "Job",
    "JobSkill",
    # ---- 行为 & 业务 ----
    "Application",
    "Recommendation",
    "ChatHistory",
    # ---- 爬虫 ----
    "CrawlSource",
    "CrawlTask",
]
