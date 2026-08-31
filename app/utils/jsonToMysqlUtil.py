"""爬虫 JSON 数据导入 MySQL。

公司 upsert(有则补空字段, 无则新建) → 职位按 (source, source_id) 去重新建 →
技能按 name 精确匹配关联 → 单事务提交, 中途失败全回滚。
"""
import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Job, JobSkill, Skill
from app.utils.codeUtil import generate_code


# 行业归一化: 爬虫的中文细字符串 → industries 表大类 code
_INDUSTRY_RULES = [
    ("FIN",    ["银行", "保险", "证券", "基金", "期货", "投资", "消费金融", "金融", "理财", "P2P"]),
    ("EDU",    ["教育", "培训", "学前", "院校", "学术"]),
    ("MED",    ["制药", "生物工程", "生物", "医疗", "医药", "保健", "器械", "美容卫生"]),
    ("LOGI",   ["快递", "物流", "货运", "配送", "即时配送", "交通运输", "出行", "交通", "共享出行", "旅游", "酒店", "旅行", "餐饮"]),
    ("REALEST", ["房产", "房地产", "建筑", "建材", "装潢", "装饰", "物业", "商业地产"]),
    ("ENERGY", ["能源", "环保", "电力", "石化", "化工", "石油", "水利", "新能源", "农", "林", "牧", "渔"]),
    ("RETAIL", ["零售", "电商", "电子商务", "便利店", "服装", "食品", "饮料", "日化", "生鲜", "百货", "批发", "时尚", "奢侈品", "烟酒", "化妆品"]),
    ("CULTURE", ["游戏", "传媒", "直播", "短视频", "视频", "媒体", "社交", "文娱", "出版", "新闻", "音频", "阅读", "娱乐", "体育", "无人机", "影像"]),
    ("IT",     ["互联网", "软件", "计算机", "信息技术", "人工智能", "大数据", "云计算", "数据", "通信", "电子", "半导体", "集成电路", "硬件", "网络", "O2O", "企业服务", "开发者", "IT服务", "系统集成", "社区", "招聘", "本地生活", "生活服务", "内容平台", "解决方案", "人力资源", "外包", "咨询", "审计", "财会", "法律", "翻译", "贸易", "进出口", "租赁", "办公"]),
    ("MFG",    ["制造", "机械", "机电", "重工", "工业", "自动化", "工程机械", "家电", "家具", "仪器", "仪表", "印刷", "包装", "造纸", "原材料", "加工", "安防", "视频监控", "检测", "认证", "汽车", "摩托车"]),
]


def normalize_industry(raw: str | None) -> str | None:
    """中文行业字符串 → 大类 code, 空返回 None, 匹配不上返回 OTHER。"""
    if not raw:
        return None
    for code, keywords in _INDUSTRY_RULES:
        if any(kw in raw for kw in keywords):
            return code
    return "OTHER"


# 插入带 code 的对象, 撞唯一索引就换 code 重试
async def _safe_flush(
    db: AsyncSession,
    obj: Any,
    code_field: str,     # "job_code" / "company_code"
    prefix: str,         # "J" / "C"
):
    """flush 撞唯一约束就换 code 重试(最多3次)。

    必须用 savepoint(begin_nested) 隔离, 不能 rollback——
    rollback 会把 session 里已 add 的前面几百条全清掉。
    """
    for _ in range(3):
        try:
            async with db.begin_nested():
                db.add(obj)
                await db.flush()
            return obj
        except IntegrityError:
            # savepoint 已自动回滚, 换 code 重试(不用重新 add, 换属性即可)
            setattr(obj, code_field, generate_code(prefix))
    raise RuntimeError(
        f"{code_field} 重试3次仍撞码, 请检查随机算法 "
        f"(也可能撞的不是 {code_field}, 而是其他唯一索引, 如 uk_job_source)"
    )


_COMPANY_FIELDS = {
    "short_name": "short_name",
    "size": "size",
    "stage": "stage",
    "city": "city",
    "district": "district",
    "logo_url": "logo_url",
    "website": "website",
    "source_url": "source_url",
    "welfare": "welfare",
}


def _fill_missing_fields(company: Company, company_data: dict):
    """公司已存在时增量补空字段(不覆盖已有值)。改过才返回 True。"""
    changed = False
    for db_field, src_field in _COMPANY_FIELDS.items():
        if getattr(company, db_field) in (None, "", []) and company_data.get(src_field):
            setattr(company, db_field, company_data[src_field])
            changed = True
    # industry 单独处理: 源数据自带标准 code 直接用, 没有再拿中文行业名映射
    if not company.industry_code:
        src_code = company_data.get("industry_code")
        if src_code:
            company.industry_code = src_code
            changed = True
        elif company_data.get("industry"):
            company.industry_code = normalize_industry(company_data.get("industry"))
            changed = True
    return changed


async def _get_or_create_company(
    db: AsyncSession,
    company_data: dict,
) -> int:
    """公司 upsert: 先按 (name, source) 查, 再按 website 查, 都没有就新建。"""
    name = company_data.get("name")
    source = company_data.get("source") or "boss"   # source NOT NULL, 兜底 boss
    website = company_data.get("website")

    existing = await db.scalar(
        select(Company).where(
            Company.name == name,
            Company.source == source,
        )
    )
    # 有官网的话能跨 source 合并同一家公司
    if not existing and website:
        existing = await db.scalar(
            select(Company).where(Company.website == website)
        )

    if existing:
        _fill_missing_fields(existing, company_data)
        return existing.id

    new_company = Company(
        company_code=generate_code("C"),
        name=name,
        short_name=company_data.get("short_name"),
        # 源数据的标准 code 直接用(中文行业名才走 normalize_industry, 对 code 会误判 OTHER)
        industry_code=company_data.get("industry_code") or normalize_industry(company_data.get("industry")),
        size=company_data.get("size"),
        stage=company_data.get("stage"),
        city=company_data.get("city"),
        district=company_data.get("district"),
        logo_url=company_data.get("logo_url"),
        website=website,
        source=source,
        source_url=company_data.get("source_url"),
        welfare=company_data.get("welfare"),
    )
    db.add(new_company)
    await _safe_flush(db, new_company, "company_code", "C")
    return new_company.id


async def _link_skills(
    db: AsyncSession,
    job_id: int,
    raw_skills: list,
):
    """raw_skills 按 name 精确匹配 skills 表, 命中才写 job_skills, 没命中跳过。"""
    if not raw_skills:
        return

    # 一次查出所有命中, 避免 N+1
    skills = (await db.scalars(
        select(Skill).where(Skill.name.in_(raw_skills))
    )).all()

    for skill in skills:
        db.add(JobSkill(
            job_id=job_id,
            skill_id=skill.id,
        ))


async def json_to_mysql(data: dict, db: AsyncSession):
    """整批爬虫 JSON 入库(结构见 db/CRAWL_REQUIREMENTS.md), 单事务。"""
    crawl_batch = data.get("crawl_batch")
    crawl_at = datetime.datetime.now()
    jobs = data.get("jobs", [])
    total = len(jobs)

    try:
        for idx, job_data in enumerate(jobs):
            company_data = job_data.get("company", {})

            # 1. 公司 upsert(即使职位已存在也要顺便补全公司空字段)
            company_id = await _get_or_create_company(db, company_data)

            # 2. 职位按 (source, source_id) 去重, 已存在跳过
            source_id = job_data.get("source_id") or ""
            source = source_id.split("_")[0] or "boss"

            existed = await db.scalar(
                select(Job).where(
                    Job.source == source,
                    Job.source_id == source_id,
                )
            )
            if existed:
                continue

            new_job = Job(
                company_id=company_id,
                job_code=generate_code("J"),
                title=job_data.get("title"),
                department=job_data.get("department"),
                city=job_data.get("city"),
                # 空串统一转 None
                district=job_data.get("district") or None,
                experience_req=job_data.get("experience_req"),
                education_req=job_data.get("education_req"),
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                salary_unit=job_data.get("salary_unit") or "month",
                salary_months=job_data.get("salary_months"),
                job_type=job_data.get("job_type") or "full",
                description=job_data.get("description"),
                description_text=job_data.get("description_text"),
                highlights=job_data.get("highlights"),
                # source 从 source_id 前缀推断("boss_0" → "boss"), 批级 "multi" 不能入
                source=source_id.split("_")[0] or "boss",
                source_url=job_data.get("source_url"),
                source_id=source_id or None,
                crawl_batch=crawl_batch,
                status="active",
                publish_at=job_data.get("publish_at"),
                crawl_at=crawl_at,
            )
            db.add(new_job)
            await _safe_flush(db, new_job, "job_code", "J")

            # 3. 技能关联(flush 后 new_job.id 已拿到)
            raw_skills = job_data.get("raw_skills", [])
            await _link_skills(db, new_job.id, raw_skills)

            if (idx + 1) % 500 == 0:
                print(f"[导入进度] {idx + 1}/{total}")

        await db.commit()
        print(f"[导入完成] 共 {total} 条职位")

    except Exception as e:
        await db.rollback()
        print(f"[导入失败] 已回滚, 错误: {e}")
        raise
