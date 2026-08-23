"""爬虫 JSON 数据导入 MySQL

    1. 公司 upsert: 有则关联 id, 无则新建(优先按 website 查, 否则按 name+source)
    2. 职位每个都新建(按 source_id 去重由数据库唯一索引保证)
    3. 技能精确匹配: raw_skills 的词去 skills 表按 name 匹配, 命中才写 job_skills
    4. code 防撞码: generate_code 生成后 flush 触发唯一约束检查, 撞了重试
    5. 一个事务保护: 中途任一步失败全部回滚, 不留半截数据
"""
import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Job, JobSkill, Skill
from app.utils.codeUtil import generate_code


# 行业归一化: 把爬虫给的中文细字符串映射到 industries 表的大类 code
# 为啥要归一化: 爬虫 industry 有 141 种写法("互联网/短视频"、"电子商务"...),
# ⚠️ 规则顺序敏感: 先匹配具体的, 后匹配宽泛的(否则容易误归类)
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
    """把爬虫给的中文行业字符串映射到 industries 表的大类 code。

    Args:
        raw: 爬虫给的 industry, 如 "互联网/短视频" / "电子商务"

    Returns:
        大类 code, 如 "IT" / "FIN"; raw 为空返回 None; 匹配不上返回 "OTHER"
    """
    if not raw:
        return None
    for code, keywords in _INDUSTRY_RULES:
        if any(kw in raw for kw in keywords):
            return code
    return "OTHER"


# 工具: 插入带 code 的对象, 撞唯一索引就换 code 重试
async def _safe_flush(
    db: AsyncSession,
    obj: Any,
    code_field: str,     # "job_code" / "company_code"
    prefix: str,         # "J" / "C"
):
    """flush 触发唯一约束检查, 万一 code 撞了就重新生成 code 重试。

    注意: flush 只是把对象推到数据库执行 SQL(能拿到自增 id), 并不会落盘。
    真正落盘要靠外层最后的 db.commit()。

    ⚠️ 关键: 用 savepoint(begin_nested) 隔离失败, 不能用 db.rollback()!
        因为 rollback 会清空整个 session 已 add 的所有对象,
        导致批量导入时前面几百条全丢、状态错乱。
    """
    for _ in range(3):
        try:
            async with db.begin_nested():    # savepoint: 失败只回滚这一段
                db.add(obj)
                await db.flush()
            return obj
        except IntegrityError:
            # savepoint 失败已自动回滚, 这里只需换 code 重试
            setattr(obj, code_field, generate_code(prefix))
            # 注意: 不需要重新 db.add, obj 之前已经 add 过,
            #      换属性后 flush 时会自动 UPDATE(因为已有主键 id 会重新分配)
    raise RuntimeError(
        f"{code_field} 重试3次仍撞码, 请检查随机算法 "
        f"(也可能撞的不是 {code_field}, 而是其他唯一索引, 如 uk_job_source)"
    )


# 公司 upsert: 有则补空字段+拿 id, 无则新建
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
    """增量补全: 公司已存在, 但某些字段之前是空的, 用新数据补上。

    只补空字段, 不覆盖已有值(避免新数据更差时把好数据改坏)。
    用 changed 标记是否实际改过, 改过才 flush, 省一次 SQL。
    """
    changed = False
    for db_field, src_field in _COMPANY_FIELDS.items():
        # 库里字段为空 且 新数据有值 → 补上
        if getattr(company, db_field) in (None, "", []) and company_data.get(src_field):
            setattr(company, db_field, company_data[src_field])
            changed = True
    # industry 单独处理:
    # 优先用源数据的标准 industry_code(如 IT-DATA),没有再退回用中文 industry 映射
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
    """返回 company_id。

        1. 先按 (name, source) 查(主力, 覆盖 ~95% 的公司, 因为 BOSS 不显示官网)
        2. 再按 website 查(辅助, 少数有官网的公司能跨平台合并)
        3. 都没有 → 新建
    """
    name = company_data.get("name")
    source = company_data.get("source") or "boss"   # source 是 NOT NULL, 兜底 boss
    website = company_data.get("website")

    existing = None
    # 1. 主力: 按 (name, source) 查
    existing = await db.scalar(
        select(Company).where(
            Company.name == name,
            Company.source == source,
        )
    )
    # 2. 辅助: 按 website 查(如果有官网, 能把不同 source 的同公司合并)
    if not existing and website:
        existing = await db.scalar(
            select(Company).where(Company.website == website)
        )

    if existing:
        # 已存在 → 补空字段(增量更新)
        # 后续爬虫补了数据, 这里自动把空字段补上, 不用全删重导
        _fill_missing_fields(existing, company_data)
        return existing.id

    # 3. 新建
    new_company = Company(
        company_code=generate_code("C"),
        name=name,
        short_name=company_data.get("short_name"),
        # industry_code:源数据已经是标准 code(如 IT-DATA),直接用,不过 normalize_industry
        # (normalize_industry 是给"中文行业名"用的,对标准 code 会误判成 OTHER)
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


# 技能关联: raw_skills 的词去 skills 表精确匹配 name
async def _link_skills(
    db: AsyncSession,
    job_id: int,
    raw_skills: list,
):
    """把 raw_skills(字符串列表)映射到 skills 字典表, 命中才写 job_skills。

    raw_skills 例: ["Python", "MySQL", "Docker"]
    匹配策略: 精确匹配 name
    匹配不上的词直接跳过(不新建垃圾技能)。
    """
    if not raw_skills:
        return

    # 一次查出所有能命中的 skill(用 in_ 避免 N+1 查询)
    skills = (await db.scalars(
        select(Skill).where(Skill.name.in_(raw_skills))
    )).all()

    for skill in skills:
        db.add(JobSkill(
            job_id=job_id,
            skill_id=skill.id,
            # is_must / weight 用默认值, 后续推荐算法再细化
        ))


# 主流程: 读 JSON → 入库
async def json_to_mysql(data: dict, db: AsyncSession):
    """把整批爬虫 JSON 数据导入数据库。

    Args:
        data: 解析后的 dict, 结构见 db/CRAWL_REQUIREMENTS.md 的交付格式
              {
                "crawl_batch": "20260728_ALL",
                "source": "multi",          # 批级来源, 不入库
                "jobs": [ { ... }, ... ]
              }
        db:   数据库会话

    用法:
        import json
        with open("jobs_raw.json", encoding="utf-8") as f:
            data = json.load(f)
        async with AsyncSessionLocal() as db:
            await json_to_mysql(data, db)
    """
    crawl_batch = data.get("crawl_batch")
    crawl_at = datetime.datetime.now()
    jobs = data.get("jobs", [])
    total = len(jobs)

    try:
        for idx, job_data in enumerate(jobs):
            company_data = job_data.get("company", {})

            # 1. 公司 upsert → 拿 company_id (顺便补全空字段, 即使职位已存在也要更新公司)
            company_id = await _get_or_create_company(db, company_data)

            # 2. 新建职位
            source_id = job_data.get("source_id") or ""
            source = source_id.split("_")[0] or "boss"

            # ★ 去重预检: 如果 (source, source_id) 已存在, 直接跳过这条职位
            existed = await db.scalar(
                select(Job).where(
                    Job.source == source,
                    Job.source_id == source_id,
                )
            )
            if existed:
                continue   # 职位已导入过, 跳过(但上面的公司补全已经执行了)

            new_job = Job(
                company_id=company_id,
                job_code=generate_code("J"),
                title=job_data.get("title"),
                department=job_data.get("department"),
                city=job_data.get("city"),
                # 空字符串统一转 None, 避免数据库存一堆 ""
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
                # source 从 source_id 前缀推断 ("boss_0" → "boss"), 不能用批级的 "multi"
                source=source_id.split("_")[0] or "boss",
                source_url=job_data.get("source_url"),
                source_id=source_id or None,
                crawl_batch=crawl_batch,
                status="active",   # TODO 暂时全部 active, 后续可按 publish_at 判断
                publish_at=job_data.get("publish_at"),
                crawl_at=crawl_at,
            )
            db.add(new_job)
            await _safe_flush(db, new_job, "job_code", "J")

            # 3. 技能关联(flush 后 new_job.id 已拿到)
            raw_skills = job_data.get("raw_skills", [])
            await _link_skills(db, new_job.id, raw_skills)

            # 进度日志(每 500 条打一次)
            if (idx + 1) % 500 == 0:
                print(f"[导入进度] {idx + 1}/{total}")

        # 4. 全部成功, 统一提交(只 commit 一次, 快)
        await db.commit()
        print(f"[导入完成] 共 {total} 条职位")

    except Exception as e:
        # 中途任一步失败, 全部回滚, 不留半截数据
        await db.rollback()
        print(f"[导入失败] 已回滚, 错误: {e}")
        raise
