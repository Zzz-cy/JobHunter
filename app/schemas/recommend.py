"""推荐相关 Schema(推荐项 = 职位 + 匹配分 + 理由 + 策略标记)。"""
from decimal import Decimal

from app.schemas.base import ORMOut
from app.schemas.jobs import JobOut


class RecommendItem(ORMOut):
    """单个推荐结果(职位 + 匹配分 + 推荐理由 + 策略标记)。"""

    job: JobOut
    score: Decimal
    reason: str | None = None
    strategy: str = "skill"


class RecommendOut(ORMOut):
    """推荐结果包裹(items + total + strategy), 包一层方便以后加统计字段。"""

    items: list[RecommendItem]
    total: int
    strategy: str = "skill"  # 本次推荐整体用的策略(取多数项的策略)
