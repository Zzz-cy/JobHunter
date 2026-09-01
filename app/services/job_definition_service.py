"""
新岗位发现与定义服务

两步 LLM:
  第1步: 飙升技能 + 近期职位标题 → 3~5 个候选新岗位名
  第2步: 逐个岗位 ES 搜真实 JD → 画像四要素(core_duties/must_skills/plus_skills/industries)

逐条独立落库, 单条失败不影响其他; 人工改过的(source=manual)重新发现时跳过。
全局状态 dict 供前端轮询。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.es import es_client, JOBS_INDEX
from app.core.exceptions import NotFoundError
from app.core.llm import achat_json
from app.models import Job, JobDefinition, Skill
from app.services.stats_service import count_emerging_skills

_discover_state: dict = {
    "running": False,
    "message": "",
    "total": 0,
    "done": 0,
    "failed": 0,
}


def get_discover_status() -> dict:
    return dict(_discover_state)


# 证据采集
async def _evidence_skills(db: AsyncSession) -> list[str]:
    """发现依据: 飙升技能榜 Top10, 榜单为空退回热门技能。"""
    trending = await count_emerging_skills(db, top=10)
    names = [s["name"] for s in trending["skills"]]
    if names:
        return names
    stmt = select(Skill.name).where(Skill.is_hot == 1).limit(10)
    return list((await db.scalars(stmt)).all())


async def _recent_titles(db: AsyncSession, limit: int = 60) -> list[str]:
    """近期职位标题(去重)"""
    stmt = (
        select(Job.title)
        .where(
            Job.status == "active",
            Job.is_deleted == 0,
            Job.publish_at.isnot(None),
        )
        .order_by(Job.publish_at.desc())
        .limit(limit * 3)   # 抽样池放大, 去重后再截断
    )
    seen, titles = set(), []
    for t in (await db.scalars(stmt)).all():
        t = (t or "").strip()
        if t and t not in seen:
            seen.add(t)
            titles.append(t)
    return titles[:limit]


def _search_jd(name: str, size: int = 20):
    """
    ES 短语匹配搜该岗位的真实 JD, 返回 (摘要列表, 命中数)。
    """
    resp = es_client.search(index=JOBS_INDEX, body={
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"title": {
                        "query": name, "analyzer": "ik_max_word", "boost": 3}}},
                    {"match_phrase": {"description_text": {
                        "query": name, "analyzer": "ik_max_word"}}},
                ],
                "minimum_should_match": 1,
            }
        },
        "_source": ["title", "description_text"],
        "size": size,
    })
    hits = resp["hits"]["hits"]
    snippets = []
    for h in hits:
        src = h["_source"]
        desc = (src.get("description_text") or "")[:200]
        snippets.append(f"- {src.get('title', '')}: {desc}")
    return snippets, len(hits)


# 两步 LLM

_NAME_SYSTEM = "你是劳动力市场的岗位分析师, 擅长从招聘数据里识别新兴岗位。"
_PROFILE_SYSTEM = "你是资深招聘行业分析师, 擅长基于真实 JD 归纳岗位画像。"


async def _discover_names(skills: list[str], titles: list[str]) -> list[str]:
    """起名。要求复用标题原词, 不凭空造词。"""
    prompt = (
        f"近期需求增速最快的技能:\n{', '.join(skills)}\n\n"
        f"近期发布的职位标题抽样:\n" + "\n".join(titles) + "\n\n"
        "请从这些标题中归纳 3~5 个新兴岗位(技能组合或业务方向新、与传统岗位名称有区分度), "
        "岗位名尽量复用标题中的原始用词, 保证能在职位列表里搜到。\n"
        '只返回 JSON: {"jobs": [{"name": "岗位名"}, {"name": "..."}]}'
    )
    data = await achat_json(prompt, _NAME_SYSTEM)
    jobs = data.get("jobs") if isinstance(data, dict) else data
    names = []
    for item in jobs or []:
        name = (item.get("name") if isinstance(item, dict) else str(item) if item else "").strip()
        if name and 1 < len(name) <= 60:
            names.append(name)
    # 去重保序
    return list(dict.fromkeys(names))[:5]


async def _profile_definition(name: str, snippets: list[str]) -> dict:
    """画像。只允许基于 JD 原文归纳, 技能尽量用原词。"""
    prompt = (
        f"岗位名: {name}\n\n该岗位的真实 JD 摘录(来自招聘平台近期职位):\n"
        + "\n".join(snippets) + "\n\n"
        "请基于以上 JD 归纳该岗位画像:\n"
        "- core_duties: 核心职责 3~5 条\n"
        "- must_skills: 必备技能 3~6 个(用 JD 原词)\n"
        "- plus_skills: 加分技能 2~4 个\n"
        "- industries: 主要行业方向 2~3 个\n"
        '只返回 JSON: {"core_duties": [...], "must_skills": [...], '
        '"plus_skills": [...], "industries": [...]}'
    )
    data = await achat_json(prompt, _PROFILE_SYSTEM)
    if not isinstance(data, dict):
        raise ValueError(f"画像返回格式异常: {str(data)[:100]}")
    return data


# 入库
async def _upsert_pending(db: AsyncSession, name: str, evidence: list[str]) -> bool:
    """建/更新占位行(generating)。人工编辑过的跳过, 返回 False。"""
    row = await db.scalar(select(JobDefinition).where(JobDefinition.name == name))
    if row is None:
        db.add(JobDefinition(name=name, evidence_skills=evidence, status="generating"))
    elif row.source == "manual":
        return False
    else:
        row.status = "generating"
        row.error_msg = None
        row.evidence_skills = evidence
        row.version += 1
    return True


async def run_discovery() -> None:
    """
    后台任务入口: 起名 → 建占位行 → 逐个画像落库。
    """
    from app.core.database import AsyncSessionLocal
    from app.core.exceptions import BizException

    _discover_state.update(running=True, message="正在准备证据数据", total=0, done=0, failed=0)
    try:
        async with AsyncSessionLocal() as db:
            skills = await _evidence_skills(db)
            titles = await _recent_titles(db)
            if not titles:
                raise BizException("库里没有可用职位数据, 请先导入")

            _discover_state["message"] = "LLM 正在归纳新岗位"
            names = await _discover_names(skills, titles)
            if not names:
                raise BizException("LLM 未归纳出候选岗位, 请稍后重试")

            # 建占位行, 前端轮询列表立即能看到候选名单
            targets = []
            for name in names:
                if await _upsert_pending(db, name, skills):
                    targets.append(name)
            await db.commit()

        # 逐个画像, 每条独立事务
        _discover_state.update(total=len(targets), message="LLM 正在生成岗位画像")
        for name in targets:
            try:
                snippets, hit = _search_jd(name)
                if hit == 0:
                    raise ValueError("ES 未搜到相关职位, 无法生成画像")
                definition = await _profile_definition(name, snippets)
                async with AsyncSessionLocal() as db:
                    row = await db.scalar(
                        select(JobDefinition).where(JobDefinition.name == name))
                    if row is None or row.source == "manual":
                        continue
                    row.definition = definition
                    row.job_count = hit
                    row.status = "done"
                    await db.commit()
                _discover_state["done"] += 1
            except Exception as e:
                _discover_state["failed"] += 1
                await _mark_failed(name, str(e))
        _discover_state["message"] = (
            f"完成: 成功 {_discover_state['done']} / 失败 {_discover_state['failed']}")
    except Exception as e:
        _discover_state["message"] = f"发现失败: {str(e)[:200]}"
    finally:
        _discover_state["running"] = False


async def _mark_failed(name: str, err: str) -> None:
    """单条失败只标该行, 不影响其他岗位。"""
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            row = await db.scalar(select(JobDefinition).where(JobDefinition.name == name))
            if row and row.source != "manual":
                row.status = "failed"
                row.error_msg = err[:500]
                await db.commit()
    except Exception:
        pass


# 查询和人工修改
async def list_definitions(db: AsyncSession) -> list[dict]:
    """全部岗位定义, 最近更新的在前。"""
    stmt = select(JobDefinition).order_by(JobDefinition.updated_at.desc())
    rows = (await db.scalars(stmt)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "definition": r.definition or {},
            "evidence_skills": r.evidence_skills or [],
            "job_count": r.job_count,
            "source": r.source,
            "status": r.status,
            "error_msg": r.error_msg,
            "version": r.version,
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else None,
        }
        for r in rows
    ]


async def update_definition(db: AsyncSession, def_id: int, definition: dict) -> dict:
    """人工修改画像: 标 source=manual, 之后的重新发现不再覆盖。"""
    row = await db.get(JobDefinition, def_id)
    if row is None:
        raise NotFoundError("岗位定义不存在")

    # 只收四个要素, 脏字段不进库
    cleaned = {
        k: [str(x).strip() for x in definition.get(k, []) if str(x).strip()]
        for k in ("core_duties", "must_skills", "plus_skills", "industries")
    }
    if not any(cleaned.values()):
        raise NotFoundError("画像内容不能为空")

    row.definition = cleaned
    row.source = "manual"
    row.status = "done"
    row.error_msg = None
    await db.commit()
    return {"id": row.id, "name": row.name, "source": row.source}
