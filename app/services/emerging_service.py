"""
新兴技能转正服务

转正三段式判定:
  1. 规则层: 标准名/别名精确匹配(零开销)
  2. 召回层: 字符串相似度捞 TopK 候选(零开销)
  3. 精判层: LLM 判断是否某候选技能的别名, 输出强制落候选集(幻觉校验)
判定为别名 → 归并进老技能(补 alias + 回溯关联); 判定为新词 → 进字典,
同步es的技能，在对应工作里加上技能。

"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.es import es_client, JOBS_INDEX
from app.models import EmergingSkill, Job, JobSkill, Resume, ResumeSkill, Skill
from app.utils.codeUtil import generate_code
from app.utils.skillDictUtil import (
    alias_tokens,
    load_all_skills,
    match_skill_in_list,
    recall_similar_skills,
)


async def _retro_jobs(db: AsyncSession, skill: Skill, name: str) -> int:
    """回溯职位: ES 搜 JD 提到该词的职位, 补 job_skills + 更新 ES 文档。"""
    # match_phrase 短语匹配: 词序相邻才算命中, 避免拆词泛匹配。
    # 查询侧显式 ik_max_word 与索引分词对齐(两种 ik 切词位置不一致时短语会 miss)
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
        "_source": ["skills"],
        "size": 500,
    })
    hits = resp["hits"]["hits"]
    if not hits:
        return 0

    hit_ids = [int(h["_id"]) for h in hits]

    existing = set((await db.scalars(
        select(JobSkill.job_id).where(
            JobSkill.skill_id == skill.id, JobSkill.job_id.in_(hit_ids)
        ))).all())
    for job_id in hit_ids:
        if job_id not in existing:
            db.add(JobSkill(job_id=job_id, skill_id=skill.id, is_must=0))

    # ES 文档的 skills 数组追加该词(下次搜索/筛选立即生效)
    for h in hits:
        skills = h["_source"].get("skills") or []
        if name not in skills:
            skills.append(name)
            es_client.update(index=JOBS_INDEX, id=h["_id"],
                             doc={"skills": skills})

    return len(hit_ids) - len(existing & set(hit_ids))


async def _retro_resumes(db: AsyncSession, skill: Skill, name: str) -> int:
    """回溯简历: parsed_raw 原始技能词里含该词的, 补 resume_skills。"""
    resumes = (await db.scalars(
        select(Resume).where(Resume.parse_status == "done")
    )).all()
    if not resumes:
        return 0

    hit_ids = [
        r.id for r in resumes
        if name in ((r.parsed_raw or {}).get("skills") or [])
    ]
    if not hit_ids:
        return 0

    existing = set((await db.scalars(
        select(ResumeSkill.resume_id).where(
            ResumeSkill.skill_id == skill.id, ResumeSkill.resume_id.in_(hit_ids)
        ))).all())
    for rid in hit_ids:
        if rid not in existing:
            db.add(ResumeSkill(resume_id=rid, skill_id=skill.id))

    return len(hit_ids) - len(existing & set(hit_ids))


async def _llm_judge_alias(name: str, candidates: list[Skill]) -> Skill | None:
    """LLM 精判: 新词是否某个候选技能的别名/同一技术的不同写法。

    幻觉校验: 返回的技能名必须落在候选集内, 越界一律按新技能处理。
    LLM 调用失败同样按新技能处理, 保底。
    """
    from app.core.llm import achat_json

    options = [c.name for c in candidates]
    prompt = f"""判断技能词 "{name}" 是否是下列候选技能中某一个的别名(同一技术的不同写法)。

候选技能: {json.dumps(options, ensure_ascii=False)}

判断标准:
- 指向同一种技术才算别名, 如 K8s = Kubernetes、sklearn = scikit-learn、Vue.js = Vue
- 只是相关但不是同一技术的不算, 如 Vue 和 Vuex、Java 和 JavaScript、MySQL 和 SQL

只输出 JSON, 不要其他内容: {{"match": "候选技能名"}} 或 {{"match": null}}"""

    try:
        data = await achat_json(prompt)
    except Exception:
        return None   # LLM 挂了: 降级按新技能处理

    hit = data.get("match") if isinstance(data, dict) else None
    if not hit:
        return None
    for c in candidates:   # 输出校验: 必须落在候选集内
        if c.name == hit:
            return c
    return None


def _append_alias(skill: Skill, name: str) -> None:
    """把新词补进老技能的 alias(若未收录), 字典越转越厚。"""
    key = name.strip().lower()
    if key == (skill.name or "").strip().lower():
        return
    tokens = alias_tokens(skill.alias)
    if key in tokens:
        return
    skill.alias = f"{skill.alias},{name.strip()}" if skill.alias else name.strip()


async def adopt_emerging_skills(db: AsyncSession, names: list[str]) -> dict:
    """批量转正候选技能。

    每个词先走"规则 → 召回 → LLM精判"三段式:
    判定为老技能别名的归并进老技能(不新建, 回溯关联挂到老技能上);
    判定为真新词的才新建技能。

    Returns:
        {"results": [{"name", "jobs_linked", "resumes_linked", "note"?}, ...]}
    """
    all_skills = await load_all_skills(db)   # 全字典只查一次, 循环内复用

    results = []
    for name in names:
        name = name.strip()
        if not name:
            continue

        # 第 1 层: 规则匹配(标准名/别名精确, 零开销)
        skill = match_skill_in_list(name, all_skills)
        merged = False

        # 第 2+3 层: 规则未命中 → 相似度召回 TopK → LLM 精判是否别名
        if skill is None:
            candidates = recall_similar_skills(name, all_skills)
            if candidates:
                judged = await _llm_judge_alias(name, candidates)
                if judged:
                    skill = judged
                    merged = True

        if skill:
            _append_alias(skill, name)
            await db.flush()
            # 回溯挂到老技能: JD/简历里提到这个词的, 关联到老技能
            jobs_n = await _retro_jobs(db, skill, name)
            resumes_n = await _retro_resumes(db, skill, name)
            await _mark_adopted(db, name)
            note = (f"归并为「{skill.name}」的别名" if merged
                    else "字典已存在(或命中别名), 已归并")
            results.append({"name": name, "jobs_linked": jobs_n,
                            "resumes_linked": resumes_n, "note": note})
            continue

        # 真新词: 进字典
        skill = Skill(skill_code=generate_code("SK"), name=name)
        db.add(skill)
        await db.flush()   # 拿自增 id
        all_skills.append(skill)   # 同批次后面的词也能匹配到它

        # 回溯职位/简历
        jobs_n = await _retro_jobs(db, skill, name)
        resumes_n = await _retro_resumes(db, skill, name)

        await _mark_adopted(db, name)
        results.append({"name": name, "jobs_linked": jobs_n, "resumes_linked": resumes_n})

    await db.commit()
    return {"results": results}


async def _mark_adopted(db: AsyncSession, name: str) -> None:
    row = await db.scalar(select(EmergingSkill).where(EmergingSkill.name == name))
    if row:
        row.status = "adopted"
