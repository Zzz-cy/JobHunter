from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, Skill, Company, JobSkill
from app.schemas import JobSearchSchema


def _parse_salary_range(salary_range: str | None) -> tuple[int | None, int | None]:
    """解析前端传来的薪资区间字符串。

    前端格式: "10-20" / "0-10" / "50-"
    单位是 K, 转成元(salary_min/max 存的是元/月)。
    返回 (min_k, max_k), None 表示该端不限。

    例:
        "10-20" → (10000, 20000)
        "0-10"  → (0, 10000)
        "50-"   → (50000, None)   # 上限不限
    """
    if not salary_range:
        return None, None
    parts = salary_range.split("-")
    lo = int(parts[0]) * 1000 if parts[0] else None  # 下限(元)
    hi = int(parts[1]) * 1000 if len(parts) > 1 and parts[1] else None  # 上限(元)
    return lo, hi


# 排序方式映射表: sort 值 → 排序字段(倒序)
# default/latest 按发布时间, salary 按薪资上限
_SORT_MAP = {
    "default": Job.publish_at.desc(),
    "latest": Job.publish_at.desc(),
    "salary": Job.salary_max.desc(),
}


async def query(job: JobSearchSchema, db: AsyncSession):
    """
    根据条件查询工作
    :param job: 入参
    :param db: 数据库
    """
    conditions = [Job.is_deleted == 0, Job.status == "active"]

    need_join_skill = bool(job.keyword)  # 有 keyword 才连技能表
    need_join_company = bool(job.keyword) or bool(job.industry)  # 连接公司表

    # keyword 跨表 LIKE: 同时命中职位名/技能/公司
    if job.keyword:
        kw = f"%{job.keyword}%"
        conditions.append(or_(
            Job.title.ilike(kw),
            Job.description_text.ilike(kw),
            Skill.name.ilike(kw),  # ← 需要 JOIN Skill
            Company.name.ilike(kw),  # ← 需要 JOIN Company
        ))

    if job.city:
        conditions.append(Job.city == job.city)
    if job.experience:
        conditions.append(Job.experience_req == job.experience)
    if job.education:
        conditions.append(Job.education_req == job.education)
    # 行业: 挂在公司表上, 用 Company.industry_code 匹配
    if job.industry:
        conditions.append(Company.industry_code == job.industry)

    # 薪资区间: 用户区间 [lo, hi] 与职位区间 [salary_min, salary_max] 求相交
    # 相交充要条件: salary_max >= lo AND salary_min <= hi
    sal_lo, sal_hi = _parse_salary_range(job.salary_range)
    if sal_lo is not None:
        conditions.append(Job.salary_max >= sal_lo)
    if sal_hi is not None:
        conditions.append(Job.salary_min <= sal_hi)

    if job.source:
        conditions.append(Job.source == job.source)

    stmt = select(Job).where(*conditions)

    if need_join_skill:
        stmt = stmt.outerjoin(JobSkill, JobSkill.job_id == Job.id)
        stmt = stmt.outerjoin(Skill, Skill.id == JobSkill.skill_id)

    if need_join_company:
        stmt = stmt.outerjoin(Company, Company.id == Job.company_id)

    # 多表 JOIN 会让一个职位出现多行, 去重
    if need_join_skill or need_join_company:
        stmt = stmt.distinct()

    # 排序: 按 sort 值选字段, 默认按发布时间倒序
    stmt = stmt.order_by(_SORT_MAP.get(job.sort, _SORT_MAP["default"]))

    # 总数: 单独 count 一次(必须在加 limit/offset 之前, 不然数的是当前页条数)
    # 用 subquery() 包一层, 规避 DISTINCT + JOIN 对 count 的干扰
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # 分页: offset 决定从第几条开始, limit 决定取几条, 两者缺一不可
    stmt = stmt.offset(job.offset).limit(job.page_size)

    # unique(): 因为 Job.skills 配了 selectin 关系, 会产生重复父行, 必须去重
    result = await db.scalars(stmt)
    jobs = result.unique().all()

    return jobs, total
