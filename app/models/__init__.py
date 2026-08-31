"""模型聚合包: import 本包即注册所有模型到 Base.metadata。"""
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
