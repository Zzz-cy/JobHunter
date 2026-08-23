"""
推荐相关 Schema

出参设计:
    RecommendItem = 一个推荐结果项 = 一个职位 + 匹配分 + 推荐理由 + 策略标记
    RecommendOut  = 列表包裹 + 简单统计

为什么 reason / strategy 单独抽出来:
    - reason: 阶段⑤ LLM 生成的"为什么推荐这个岗位"的一句话, 前端高亮展示
    - strategy: 标记这个分是用什么策略算的(skill纯技能 / hybrid技能+向量 / rag全链路),
      写进 Recommendation 流水表, 用于 A/B 对比不同策略的效果
"""
from decimal import Decimal

from app.schemas.base import ORMOut
from app.schemas.jobs import JobOut


class RecommendItem(ORMOut):
    """单个推荐结果。

    字段说明:
        job:      完整职位信息(复用 JobOut, 前端 JobCard 可直接渲染)
        score:    匹配分 0~100(归一化后, 越高越匹配)
        reason:   推荐理由(一句话中文)。阶段③纯 SQL 时为 None, 阶段⑤接 LLM 后填充
        strategy: 策略标记。skill=纯技能召回, hybrid=技能+向量, rag=全链路含LLM重排
    """

    job: JobOut
    score: Decimal
    reason: str | None = None
    strategy: str = "skill"


class RecommendOut(ORMOut):
    """推荐结果包裹(带统计, 方便前端展示"为你找到 N 个匹配岗位")。

    不直接返回 list[RecommendItem] 而是包一层, 是为了将来加字段(如总耗时、
    召回了多少、用了哪些策略)不用改前端协议。
    """

    items: list[RecommendItem]
    total: int
    strategy: str = "skill"  # 本次推荐整体用的策略(取多数项的策略)
