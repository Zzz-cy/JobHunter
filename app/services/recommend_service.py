"""岗位推荐服务(核心业务逻辑)

三段式: 召回(技能召回+向量召回) → 融合粗排 → LLM 精排落库。
每次推荐写 Recommendation 流水(strategy + 各路分数快照), 方便回溯对比。
"""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.llm import aembed
from app.models import Job, JobSkill, Recommendation, Resume, ResumeSkill
from app.schemas.jobs import JobOut
from app.schemas.recommend import RecommendItem, RecommendOut
from app.services.vector_service import asearch


# 召回条数(粗筛, 后面精排再挑)
_RECALL_TOP_N = 30
# 送 LLM 重排的条数(再多 prompt 太长, 慢且贵)
_RERANK_TOP_K = 15
# 最终返回条数
_RETURN_TOP_N = 10
# 技能命中数的归一化基数(超过按 5 算, 防"只要1个技能且命中"就满分虚高)
_MAX_SKILLS_FOR_NORMALIZE = 5


# ---- 召回 ----

async def get_resume_skills(resume_id: int, db: AsyncSession) -> list[int]:
    """取简历的技能 id 列表。"""
    result = await db.scalars(
        select(ResumeSkill.skill_id).where(ResumeSkill.resume_id == resume_id)
    )
    return result.all()


async def recall_by_skills(
    skill_ids: list[int],
    db: AsyncSession,
    top_n: int = _RECALL_TOP_N,
) -> list[tuple[Job, int]]:
    """技能交集召回: 数每个岗位命中了简历几个技能, 必须技能加权排序。

    返回 [(job, hit_count)], Job 带预加载的关联(JobCard 要用)。
    """
    if not skill_ids:
        return []

    # 每个岗位的命中数 + 加权分(必须技能 is_must=1 算 2 分)
    weighted = (
        select(
            JobSkill.job_id.label("job_id"),
            func.count(JobSkill.skill_id).label("hit_count"),
            func.sum(JobSkill.is_must + 1).label("weighted"),
        )
        .where(JobSkill.skill_id.in_(skill_ids))
        .group_by(JobSkill.job_id)
        .subquery()
    )

    stmt = (
        select(Job, weighted.c.hit_count)
        .join(weighted, weighted.c.job_id == Job.id)
        .where(Job.status == "active", Job.is_deleted == 0)
        .order_by(
            weighted.c.weighted.desc(),
            Job.publish_at.desc(),   # 同分看新鲜度
        )
        .limit(top_n)
    )

    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def recall_by_vector(
    resume: Resume,
    db: AsyncSession,
    top_n: int = _RECALL_TOP_N,
) -> list[tuple[Job, float]]:
    """语义召回: 简历文本转向量, 在 ChromaDB 查最相似的岗位。

    补技能召回的盲区("会Python"匹配不到"招后端")。
    返回 [(job, 相似度0~1)]。
    """
    query_text = _build_resume_query_text(resume)
    if not query_text.strip():
        return []

    query_vec = await aembed(query_text)
    raw_hits = await asearch(query_vec, top_k=top_n)
    if not raw_hits:
        return []

    # 回 SQL 批量取 Job 对象
    job_ids = [h["job_id"] for h in raw_hits]
    score_map = {h["job_id"]: h["score"] for h in raw_hits}

    stmt = (
        select(Job)
        .where(Job.id.in_(job_ids), Job.status == "active", Job.is_deleted == 0)
        .options(
            selectinload(Job.company),
            selectinload(Job.skills),
        )
    )
    jobs = (await db.execute(stmt)).scalars().all()

    # IN 查询不保证顺序, 按相似度重排
    job_by_id = {j.id: j for j in jobs}
    return [
        (job_by_id[jid], score_map[jid])
        for jid in job_ids
        if jid in job_by_id
    ]


def _build_resume_query_text(resume: Resume) -> str:
    """把简历拼成向量检索用的求职文本(意向 + 技能 + 经历)。

    拼法和建库时 JD 文本的结构对齐, 两边向量才在同一语系里可比。
    """
    parts = []
    if resume.expect_job:
        parts.append(resume.expect_job)
    elif resume.title:
        parts.append(resume.title)

    skill_names = [rs.skill.name for rs in resume.skills if rs.skill]
    if skill_names:
        parts.append("技能: " + ", ".join(skill_names))

    # 最多取 2 段经历, 防文本过长稀释信号
    for exp in resume.experiences[:2]:
        seg = exp.title or ""
        if exp.description:
            seg += " " + exp.description[:80]
        if seg.strip():
            parts.append(seg.strip())

    return " | ".join(parts)


# ---- 打分归一化 ----

def _normalize_skill_score(hit_count: int) -> Decimal:
    """命中技能数 → 0~100 分(命中5个即满分)。"""
    clamped = min(hit_count, _MAX_SKILLS_FOR_NORMALIZE)
    return Decimal(str(round(clamped / _MAX_SKILLS_FOR_NORMALIZE * 100, 2)))


# ---- LLM 重排 ----

async def rerank_with_llm(
    resume: Resume,
    candidates: list[dict],
) -> dict[int, dict]:
    """让 glm-4-flash 对候选岗位精排 + 生成推荐理由。

    LLM 挂了就回退融合分 + 默认理由, 推荐绝不能因此崩掉。

    返回 {job_id: {"score": 0~100, "reason": "..."}}
    """
    from app.core.llm import achat_json
    from app.core.exceptions import BizException

    if not candidates:
        return {}

    resume_brief = _build_resume_query_text(resume)

    job_lines = []
    for idx, info in enumerate(candidates, 1):
        job = info["job"]
        skills = [js.skill.name for js in job.skills if js.skill] if hasattr(job, "skills") else []
        job_lines.append(
            f"{idx}. 岗位编号:{job.id} 标题:{job.title} 城市:{job.city or '不限'} "
            f"技能:{','.join(skills) if skills else '未填写'} "
            f"要求:{(job.description_text or '')[:60]}"
        )
    jobs_text = "\n".join(job_lines)

    prompt = f"""你是一个资深技术招聘专家, 请根据候选人简历, 对下面这些候选岗位逐一评估匹配度。

【候选人简历摘要】
{resume_brief}

【候选岗位列表】
{jobs_text}

请对每个岗位输出 JSON, 格式为对象数组, 每项包含:
- job_id: 岗位编号(整数)
- score: 匹配度评分 0~100(整数, 越高越匹配, 考虑技能契合/方向一致/经验层级)
- reason: 一句话推荐理由(中文, 不超过30字, 说清"为什么这个岗位适合该候选人")

只返回 JSON 数组, 不要任何解释文字。示例:
[{{"job_id": 1, "score": 92, "reason": "技能高度契合, 5年后端经验完全胜任"}}]"""

    try:
        result = await achat_json(prompt)
    except BizException:
        # LLM 抖动: 回退融合分 + 默认理由
        return {
            info["job"].id: {
                "score": float(max(info["skill_score"], info["vector_score"])),
                "reason": "技能与经验较为匹配",
            }
            for info in candidates
        }

    reranked: dict[int, dict] = {}
    fallback_map = {info["job"].id: info for info in candidates}

    if isinstance(result, list):
        for item in result:
            try:
                jid = int(item.get("job_id"))
                score = float(item.get("score", 0))
                reason = str(item.get("reason", ""))[:60]  # 限长防撑爆 DB
                score = max(0.0, min(100.0, score))
                reranked[jid] = {"score": score, "reason": reason or "技能与经验较为匹配"}
            except (ValueError, TypeError, AttributeError):
                continue  # 单条坏数据跳过

    # LLM 漏掉的岗位用融合分补上
    for jid, info in fallback_map.items():
        if jid not in reranked:
            reranked[jid] = {
                "score": float(max(info["skill_score"], info["vector_score"])),
                "reason": "技能与经验较为匹配",
            }

    return reranked


# ---- 主入口 ----

async def recommend(
    resume_id: int,
    user_id: int,
    db: AsyncSession,
) -> RecommendOut:
    """根据简历推荐岗位。

    校验归属 → 技能/向量两路召回 → 融合粗排Top15 → LLM精排Top10 → 落库返回。
    """
    # 校验简历属于当前用户(防越权), selectinload 预加载后面拼文本要的关联
    resume = await db.scalar(
        select(Resume)
        .options(
            selectinload(Resume.skills).selectinload(ResumeSkill.skill),
            selectinload(Resume.experiences),
        )
        .where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.is_deleted == 0,
        )
    )
    if resume is None:
        raise NotFoundError("简历不存在或无权访问")

    # 两路召回
    skill_ids = await get_resume_skills(resume_id, db)
    skill_hits = await recall_by_skills(skill_ids, db) if skill_ids else []
    vector_hits = await recall_by_vector(resume, db)

    # 两路融合: 按 job_id 求并集, 分数量纲统一到 0~100
    candidate: dict[int, dict] = {}

    for job, hit_count in skill_hits:
        candidate[job.id] = {
            "job": job,
            "skill_score": _normalize_skill_score(hit_count),
            "vector_score": Decimal("0"),
            "hit_skill_count": hit_count,
        }

    for job, similarity in vector_hits:
        if job.id in candidate:
            candidate[job.id]["vector_score"] = Decimal(str(round(similarity * 100, 2)))
        else:
            # 只被向量召回: 技能分记 0(没命中不等于不匹配, 可能技能没标全)
            candidate[job.id] = {
                "job": job,
                "skill_score": Decimal("0"),
                "vector_score": Decimal(str(round(similarity * 100, 2))),
                "hit_skill_count": 0,
            }

    if not candidate:
        return RecommendOut(items=[], total=0, strategy="hybrid")

    # 融合分粗排, 取 Top K 送 LLM
    candidate_list = list(candidate.values())
    for info in candidate_list:
        info["fused_score"] = max(info["skill_score"], info["vector_score"])
    candidate_list.sort(key=lambda x: x["fused_score"], reverse=True)
    to_rerank = candidate_list[:_RERANK_TOP_K]

    rerank_result = await rerank_with_llm(resume, to_rerank)

    items: list[RecommendItem] = []
    for info in to_rerank:
        jid = info["job"].id
        llm = rerank_result.get(jid, {})
        final_score = Decimal(str(llm.get("score", float(info["fused_score"]))))
        reason = llm.get("reason")
        items.append(
            RecommendItem(
                job=JobOut.model_validate(info["job"]),
                score=final_score,
                reason=reason,
                strategy="rag",
            )
        )
    items.sort(key=lambda x: x.score, reverse=True)
    items = items[:_RETURN_TOP_N]

    # 落库, snapshot 留各路原始分数
    for item in items:
        info = candidate[item.job.id]
        db.add(
            Recommendation(
                user_id=user_id,
                resume_id=resume_id,
                job_id=item.job.id,
                score=item.score,
                reason=item.reason,
                strategy="rag",
                snapshot={
                    "skill_score": float(info["skill_score"]),
                    "vector_score": float(info["vector_score"]),
                    "fused_score": float(info["fused_score"]),
                    "llm_score": float(item.score),
                    "hit_skill_count": info["hit_skill_count"],
                },
            )
        )
    await db.commit()

    return RecommendOut(items=items, total=len(items), strategy="rag")
