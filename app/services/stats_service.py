from sqlalchemy import select, func, distinct, desc, case, text
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


async def count_skill_trend(db: AsyncSession, skills: list[str], months: int = 6):
    """技能需求月度趋势。skills 传空自动取热门前5, 月份按数据里实际存在的取。"""
    month_expr = func.date_format(Job.publish_at, "%Y-%m")

    # 没指定技能就取热门前5
    if not skills:
        hot_stmt = (
            select(Skill.name)
            .join(JobSkill, JobSkill.skill_id == Skill.id)
            .group_by(Skill.id)
            .order_by(desc(func.count()))
            .limit(5)
        )
        skills = [row[0] for row in (await db.execute(hot_stmt)).all()]

    # 横轴: 数据里存在的最近 N 个月
    month_stmt = (
        select(month_expr.label("month"))
        .where(Job.publish_at.isnot(None))
        .group_by("month")
        .order_by(desc("month"))
        .limit(months)
    )
    month_rows = list(reversed((await db.execute(month_stmt)).all()))
    month_list = [row.month for row in month_rows]

    # 逐月逐技能统计
    stmt = (
        select(
            month_expr.label("month"),
            Skill.name.label("skill"),
            func.count().label("cnt"),
        )
        .join(JobSkill, JobSkill.job_id == Job.id)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(
            Job.publish_at.isnot(None),
            Skill.name.in_(skills),
        )
        .group_by("month", "skill")
    )
    rows = (await db.execute(stmt)).all()

    # 缺失月份补0
    count_map = {(row.month, row.skill): row.cnt for row in rows}

    series = {
        skill: [count_map.get((month, skill), 0) for month in month_list]
        for skill in skills
    }

    return {
        "month": month_list,
        "skills": skills,
        "series": series,
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
    """经验要求 × 平均薪资(单位K, 雷达图用, 数据已归一化到 5 档)。"""
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


async def count_emerging_skills(db: AsyncSession, recent_months: int = 3,
                                min_early: int = 5, top: int = 10) -> dict:
    """新兴技能: 近N个月 vs 前N个月的需求增速榜。

    growth = 近期需求量 / 早期需求量
    过滤: 早期 < min_early 次的扔掉(小样本虚高), 增速 < 2 倍不上榜
    """
    recent_since = func.date_format(
        func.date_sub(func.now(), text(f"INTERVAL {recent_months} MONTH")), "%Y-%m-01")
    early_since = func.date_format(
        func.date_sub(func.now(), text(f"INTERVAL {recent_months * 2} MONTH")), "%Y-%m-01")

    stmt = (
        select(
            Skill.name,
            Skill.category,
            func.sum(case((Job.publish_at >= recent_since, 1), else_=0)).label("recent_cnt"),
            func.sum(case((Job.publish_at >= early_since, 1), else_=0)).label("window_cnt"),
            func.count(Job.id).label("total_cnt"),
        )
        .select_from(JobSkill)
        .join(Job, Job.id == JobSkill.job_id)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(
            Job.publish_at.isnot(None),
            Job.status == "active",
            Job.is_deleted == 0,
            Job.publish_at >= early_since,
        )
        .group_by(Skill.id, Skill.name, Skill.category)
    )
    rows = (await db.execute(stmt)).all()

    results = []
    for name, category, recent_cnt, window_cnt, total_cnt in rows:
        early_cnt = window_cnt - recent_cnt
        if early_cnt < min_early:
            continue
        growth = recent_cnt / early_cnt
        if growth < 2.0:
            continue
        results.append({
            "name": name,
            "category": category,
            "recent_count": int(recent_cnt),
            "early_count": int(early_cnt),
            "growth": round(growth, 2),
            "total_count": int(total_cnt),
        })

    results.sort(key=lambda x: x["growth"], reverse=True)
    return {
        "window": f"近{recent_months}个月 vs 之前{recent_months}个月",
        "skills": results[:top],
    }
