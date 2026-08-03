from sqlalchemy import select, func, distinct, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, Company, Skill, Industry, JobSkill
from app.schemas import OverviewOut


async def count_overview(db: AsyncSession):
    stmt_job = select(func.count(Job.id))
    stmt_company = select(func.count(Company.id))
    stmt_skill = select(func.count(Skill.id))
    stmd_industry = select(func.count(Industry.id))
    stmt_city = select(func.count(distinct(Job.city)))

    jobs = await db.scalar(stmt_job)
    companies = await db.scalar(stmt_company)
    skills = await db.scalar(stmt_skill)
    industry = await db.scalar(stmd_industry)
    city = await db.scalar(stmt_city)
    overviewOut = OverviewOut(
        job_count=jobs,
        company_count=companies,
        skill_count=skills,
        industry_count=industry,
        city_count=city,
    )
    return overviewOut


async def count_salary_distribution(db: AsyncSession):
    stmt_1 = select(func.count(Job.id)).where(Job.salary_max <= 5000)
    stmt_2 = select(func.count(Job.id)).where(Job.salary_min >= 5000, Job.salary_max <= 10000)
    stmt_3 = select(func.count(Job.id)).where(Job.salary_min >= 10000, Job.salary_max <= 15000)
    stmt_4 = select(func.count(Job.id)).where(Job.salary_min >= 15000, Job.salary_max <= 20000)
    stmt_5 = select(func.count(Job.id)).where(Job.salary_min >= 20000, Job.salary_max <= 30000)
    stmt_6 = select(func.count(Job.id)).where(Job.salary_min >= 30000, Job.salary_max <= 50000)
    stmt_7 = select(func.count(Job.id)).where(Job.salary_max >= 50000)

    salary1 = await db.scalar(stmt_1)
    salary2 = await db.scalar(stmt_2)
    salary3 = await db.scalar(stmt_3)
    salary4 = await db.scalar(stmt_4)
    salary5 = await db.scalar(stmt_5)
    salary6 = await db.scalar(stmt_6)
    salary7 = await db.scalar(stmt_7)
    return [salary1, salary2, salary3, salary4, salary5, salary6, salary7]


async def count_city_distribution(db: AsyncSession):
    stmt = (
        select(Job.city, func.count().label("cnt"))
        .where(Job.city.isnot(None))  # ← 过滤掉没填城市的
        .group_by(Job.city)
        .order_by(desc(func.count()))
        .limit(10)
    )
    result = await db.execute(stmt)
    data = result.all()
    cities = {
        "city": [],
        "count": []
    }
    for city, cnt in data:
        cities["city"].append(city)
        cities["count"].append(cnt)
    return cities


async def count_skills_hot(db: AsyncSession):
    stmt = (
        select(Skill.name, func.count().label("cnt"))
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .group_by(Skill.name)
        .order_by(desc(func.count()))
        .limit(15)
    )
    result = await db.execute(stmt)
    data = result.all()
    skills = {
        "name": [],
        "count": []
    }
    for name, cnt in data:
        skills["name"].append(name)
        skills["count"].append(cnt)
    return skills


async def count_job_trend(db: AsyncSession):
    """
    按月统计职位发布量(近 8 个月, 用于趋势图)。
    """
    # func.date_format 是 MySQL 的日期格式化函数
    stmt = (
        select(
            func.date_format(Job.publish_at, "%Y-%m").label("month"),
            func.count().label("cnt"),
        )
        .where(Job.publish_at.isnot(None))
        .group_by("month")
        .order_by(desc("month"))   # 倒序取最近 8 个月
        .limit(8)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 反转: 从旧到新(折线图左→右是时间递增)
    rows = list(reversed(rows))

    return {
        "month": [row.month for row in rows],
        "count": [row.cnt for row in rows],
    }


async def count_industry_distribution(db: AsyncSession):
    """
    行业职位占比(按一级行业聚合, 二级自动归到父级)。
    """
    # 取一级 code(二级 IT-RD → IT)
    first_level_code = func.substring_index(Company.industry_code, '-', 1)

    stmt = (
        select(
            Industry.name.label("industry"),
            func.count(Job.id).label("cnt"),
        )
        .select_from(Job)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(
            Industry, (Industry.code == first_level_code) & (Industry.parent_id.is_(None)),
        )
        .where(Company.industry_code.isnot(None))  # 过滤没填行业的
        .group_by(Industry.name)
        .order_by(desc(func.count(Job.id)))
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {"name": row.industry or "其他", "value": row.cnt}
        for row in rows
    ]


async def count_education_distribution(db: AsyncSession):
    stmt = (
        select(Job.education_req, func.count().label("cnt"))
        .group_by(Job.education_req)
    )
    result = await db.execute(stmt)
    rows = result.all()

    order = ["不限", "大专", "本科", "硕士", "博士"]
    count_map = {row[0]: row[1] for row in rows if row[0]}
    return [{"name": edu, "value": count_map.get(edu, 0)} for edu in order]


async def count_experience_salary(db: AsyncSession):
    """经验要求 × 平均薪资(数据已由 @validates 归一化到标准 5 档)。

    Returns:
        {"labels": ["应届","1-3年",...], "values": [10, 26, 35, 37, 52]}
        values 是平均薪资, 单位 K(千元), 方便雷达图显示
    """
    # 平均薪资 = (salary_min + salary_max) / 2, 再除以1000转成K
    avg_salary_k = (func.avg((Job.salary_min + Job.salary_max) / 2) / 1000).label("avg_k")

    stmt = (
        select(Job.experience_req, avg_salary_k)
        .where(
            Job.experience_req.isnot(None),
            Job.salary_min.isnot(None),
            Job.salary_max.isnot(None),
        )
        .group_by(Job.experience_req)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 固定顺序返回(雷达图轴顺序), "不限"代表经验不限/应届可投
    order = ["不限", "1-3年", "3-5年", "5-10年", "10年+"]
    salary_map = {row[0]: round(float(row[1]), 1) for row in rows}
    return {
        "labels": order,
        "values": [salary_map.get(exp, 0) for exp in order],
    }


source_map = {
    "boss": 'Boss直聘',
    "liepin": '猎聘',
    "official": '官方',
    "NCSS": '大学生就业网',
    "51job": '前程无忧',
    "cultural": '文化创意'
}


async def count_source_distribution(db: AsyncSession):
    stmt = (select(Job.source, func.count().label("cnt"))
            .where(Job.source.isnot(None))
            .group_by(Job.source)
            )
    result = await db.execute(stmt)
    data = result.all()
    sources = []
    for source, cnt in data:
        sources.append({"name": source_map[source], "value": cnt})
    return sources
