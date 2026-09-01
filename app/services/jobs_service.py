from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.es import es_client, JOBS_INDEX
from app.core.exceptions import NotFoundError
from app.models import Job, Skill, Company, JobSkill, Application
from app.schemas import JobSearchSchema


def _parse_salary_range(salary_range: str | None) -> tuple[int | None, int | None]:
    """解析薪资区间 "10-20" / "50-"(单位K) → (元下限, 元上限), None 表示不限。"""
    if not salary_range:
        return None, None
    parts = salary_range.split("-")
    lo = int(parts[0]) * 1000 if parts[0] else None  # 下限(元)
    hi = int(parts[1]) * 1000 if len(parts) > 1 and parts[1] else None  # 上限(元)
    return lo, hi


# 排序方式映射表: sort 值 → 排序字段(倒序)
_SORT_MAP = {
    "latest": Job.publish_at.desc(),  # 最新: 纯按发布时间
    "salary": Job.salary_max.desc(),  # 薪资: 纯按薪资上限
}


async def query(job: JobSearchSchema, db: AsyncSession):
    """按条件分页查询职位, 返回 (当前页列表, 总数)。"""
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

    # 排序: 按 sort 值选字段, 未知值回退最新
    stmt = stmt.order_by(_SORT_MAP.get(job.sort, _SORT_MAP["latest"]))

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


async def favorite_job(job_id: int, db: AsyncSession, user_id: int):
    """收藏职位。只动 is_favorited, 收藏和投递是两个独立维度。"""
    stmt = select(Application).where(
        Application.user_id == user_id,
        Application.job_id == job_id,
    )
    application = await db.scalar(stmt)
    if application:
        application.is_deleted = 0
        application.is_favorited = 1
    else:
        application = Application(
            user_id=user_id,
            job_id=job_id,
            is_favorited=1,
        )
        db.add(application)
    await db.commit()
    await db.refresh(application)


async def submit_application(job_id: int, db: AsyncSession, user_id: int):
    """投递职位。收藏过就改 status, 没记录就新建(收藏状态不动)。"""
    stmt = select(Application).where(
        Application.user_id == user_id,
        Application.job_id == job_id,
    )
    application = await db.scalar(stmt)
    if application:
        application.is_deleted = 0
        application.status = "submitted"  # 只更新投递状态,不动 is_favorited
        application.submitted_at = datetime.now()
    else:
        application = Application(
            user_id=user_id,
            job_id=job_id,
            status="submitted",
            is_favorited=0,  # 默认没收藏
            submitted_at=datetime.now(),
        )
        db.add(application)
    await db.commit()
    await db.refresh(application)


async def unfavorite_job(job_id: int, db: AsyncSession, user_id: int):
    """取消收藏。不删记录(用户可能在投递中), 只有没收藏又没投递的才软删。"""
    stmt = select(Application).where(
        Application.user_id == user_id,
        Application.job_id == job_id,
        Application.is_deleted == 0,
    )
    application = await db.scalar(stmt)
    if not application:
        raise NotFoundError("记录不存在")

    application.is_favorited = 0
    # 如果用户也没投递(还在 clicked 初始态), 这条记录没价值了, 软删除
    if application.status == "clicked":
        application.is_deleted = 1
    await db.commit()


async def find_similar_jobs(db: AsyncSession, job_id: int):
    """找相似职位: 技能重叠数排序, 排除自己只看在招, 取前5。"""
    skill_ids_result = await db.scalars(
        select(JobSkill.skill_id).where(JobSkill.job_id == job_id)
    )
    skill_ids = skill_ids_result.all()
    if not skill_ids:
        return []
    stmt = (
        select(Job)
        .join(JobSkill, JobSkill.job_id == Job.id)
        .where(
            JobSkill.skill_id.in_(skill_ids),  # 技能重叠
            Job.id != job_id,  # 排除自己
            Job.status == "active",  # 只看在招的
            Job.is_deleted == 0,
        )
        .group_by(Job.id)  # 按职位分组(一个职位多技能会重复)
        .order_by(
            func.count(JobSkill.skill_id).desc(),  # 按重叠技能数排(相似度)
            Job.publish_at.desc(),  # 重叠数同则看新鲜度
        )
        .limit(5)
    )
    result = await db.scalars(stmt)
    return result.unique().all()  # unique() 去重(selectin 会产生重复父行)


# ES 版职位搜索(ES 查 id + 排序, MySQL 取详情)
def _build_es_query(params: JobSearchSchema) -> dict:
    """搜索入参 → ES DSL。keyword 放 must 算相关度, 筛选放 filter 不算分。"""
    must = []
    # 基础过滤: 只搜在招职位(等价原 MySQL 的 status=='active')
    filter = [{"term": {"job_status": "active"}}]

    # ---- keyword: 多字段匹配, 标题权重×3(标题命中排最前, LIKE 做不到) ----
    if params.keyword:
        must.append({
            "multi_match": {
                "query": params.keyword,
                "fields": ["title^3", "skills", "company_name", "description_text"],
            }
        })

    # ---- 精确筛选(对应原 MySQL 的等值条件) ----
    if params.city:
        filter.append({"term": {"city": params.city}})
    if params.experience:
        filter.append({"term": {"experience_req": params.experience}})
    if params.education:
        filter.append({"term": {"education_req": params.education}})
    if params.industry:
        filter.append({"term": {"industry_code": params.industry}})
    if params.source:
        filter.append({"term": {"source": params.source}})

    # ---- 薪资区间(复用 MySQL 版的解析逻辑, 两边口径一致) ----
    sal_lo, sal_hi = _parse_salary_range(params.salary_range)
    if sal_lo is not None:
        filter.append({"range": {"salary_max": {"gte": sal_lo}}})
    if sal_hi is not None:
        filter.append({"range": {"salary_min": {"lte": sal_hi}}})

    # ---- 排序 ----
    if params.keyword:
        # 有搜索词: 相关度优先, 同分看新鲜度
        sort = [{"_score": "desc"}, {"publish_at": "desc"}]
    elif params.sort == "salary":
        sort = [{"salary_max": "desc"}]
    else:  # latest
        sort = [{"publish_at": "desc"}]

    return {
        "query": {"bool": {"must": must, "filter": filter}},
        "sort": sort,
        "from": params.offset,       # ES 的偏移量叫 from(等价 MySQL 的 offset)
        "size": params.page_size,
    }


async def search_jobs_es(params: JobSearchSchema, db: AsyncSession) -> tuple[list[Job], int]:
    """ES 版搜索: 查询/排序/分页在 ES 完成, 回 MySQL 取详情。

    返回结构和 query() 一致, API 层无感。
    """
    body = _build_es_query(params)
    resp = es_client.search(index=JOBS_INDEX, body=body)

    total = resp["hits"]["total"]["value"]
    # ES 文档的 _id 就是 MySQL 主键(同步时指定的)
    ids = [int(h["_id"]) for h in resp["hits"]["hits"]]
    if not ids:
        return [], 0

    # 回 MySQL 批量取完整 ORM 对象(skills/company 走 selectin 预加载)
    jobs_raw = (await db.scalars(
        select(Job).where(Job.id.in_(ids))
    )).unique().all()

    # in_() 查回来的顺序是乱的, 必须按 ES 返回的顺序重排
    # (ES 是按相关度/排序字段排好的, 不重排前端列表顺序就乱了)
    job_map = {j.id: j for j in jobs_raw}
    jobs = [job_map[i] for i in ids if i in job_map]
    return jobs, total
