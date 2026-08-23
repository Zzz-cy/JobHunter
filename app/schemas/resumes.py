"""
简历相关 Schema
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import model_validator

from app.schemas.base import ORMOut


# ============================================================
# 出参: 上传成功后返回(前端拿这个轮询状态)
# ============================================================
class ResumeUploadOut(ORMOut):
    """简历上传成功后的返回。

    上传阶段只返回 id / 状态 / 文件地址,
    """

    id: int
    resume_code: str
    source_type: str
    file_url: str | None = None
    parse_status: str = "pending"
    parse_error: str | None = None
    created_at: datetime | None = None


# 出参: 简历卡片里的单个技能
class SkillOut(ORMOut):
    id: int                            # 取自 Skill 字典表
    name: str                          # 取自 Skill 字典表

    @model_validator(mode="before")
    @classmethod
    def _flatten_resume_skill(cls, data: Any) -> Any:
        # 只处理 ORM 对象(dict 直接过, 兼容测试/手工构造)
        if isinstance(data, dict):
            return data
        # data 是 ResumeSkill ORM 对象: 把 .skill.id / .skill.name 提到顶层
        skill_obj = getattr(data, "skill", None)
        if skill_obj is not None:
            # 直接构造一个 dict, 让 pydantic 走标准路径
            return {
                "id": getattr(skill_obj, "id", None),
                "name": getattr(skill_obj, "name", None),
            }
        return data


# 出参: 用户的简历卡片数据列表
class OutList(ORMOut):
    """
    返回用户简历卡片数据
    """
    id: int
    title: str | None = None      # 用户自定义标题, 未填则前端回退显示 name
    name: str
    is_primary: int = 0           # 是否默认简历(0普通 1默认), 前端据此显示"默认"标签
    city: str | None = None
    work_years: int | None = None
    education: str | None = None
    expect_job: str | None = None
    overall_score: Decimal | None = None
    parse_status: str = "done"
    source_type: str
    created_at: datetime | None = None
    skills: list[SkillOut] = []
