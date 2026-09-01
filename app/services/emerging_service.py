"""
新兴技能转正服务

转正：把技能加入技能字典，同步es的技能，在对应工作里加上技能。

"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.es import es_client, JOBS_INDEX
from app.models import EmergingSkill, Job, JobSkill, Resume, ResumeSkill, Skill
from app.utils.codeUtil import generate_code


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


async def adopt_emerging_skills(db: AsyncSession, names: list[str]) -> dict:
    """批量转正候选技能。

    Returns:
        {"results": [{"name", "jobs_linked", "resumes_linked"}], ...}
    """
    results = []
    for name in names:
        name = name.strip()
        if not name:
            continue

        skill = await db.scalar(select(Skill).where(Skill.name == name))
        if skill:
            await _mark_adopted(db, name)
            results.append({"name": name, "jobs_linked": 0, "resumes_linked": 0,
                            "note": "字典已存在, 仅标记"})
            continue

        # 进字典
        skill = Skill(skill_code=generate_code("SK"), name=name)
        db.add(skill)
        await db.flush()   # 拿自增 id

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
