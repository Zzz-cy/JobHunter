"""
岗位推荐服务(核心业务逻辑)

三段式管线设计(业界经典「召回 → 打分 → 落库」):
    recall  : 从全量岗位里粗筛出候选集(阶段③=技能召回, ④会加向量召回)
    score   : 把候选岗位打分归一化到 0~100(便于前端统一展示)
    persist : 写 Recommendation 流水表(strategy 标记策略, 做 A/B 回溯)

为什么这么分:
    - 三段可独立替换: ④加向量召回不用改 score/persist; ⑤加 LLM 重排也只在 recall
      和 score 之间插一层。每加一层能力, 改动都局部化。
    - 流水落库: 每次推荐都记录"用了什么策略 + 打了多少分", 将来能对比
      "纯技能推荐 vs 向量+技能 vs 加 LLM 重排"哪个效果好(点击率)。

阶段③ MVP: 只实现 recall_by_skills + 归一化 + 落库, 不依赖 GLM/向量库。
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


# ============================================================
# 派生常量
# ============================================================
# 召回阶段拉多少候选。召回要多, 后续精排(阶段⑤ LLM)才有东西可挑。
_RECALL_TOP_N = 30
# 送 LLM 重排的候选数。召回 30 → 先用融合分粗排取前 15 → 送 LLM 精排。
# 为什么不全送: prompt 太长 LLM 会忽略后段 + 慢 + 贵; 取 top 15 够 LLM 挑了。
_RERANK_TOP_K = 15
# 最终返回给前端的条数。LLM 重排 15 条 → 展示前 10 条。
_RETURN_TOP_N = 10
# 技能匹配的归一化基数: 假设一个岗位最多要求 5 个技能(超过按 5 算),
# 命中率 = 命中数/5, 这样分数上限天然 100。
# 用 min() 防止"岗位只要 1 个技能且命中"时算出 100 分虚高。
_MAX_SKILLS_FOR_NORMALIZE = 5


# ============================================================
# 1. 召回(RECALL)
# ============================================================
async def get_resume_skills(resume_id: int, db: AsyncSession) -> list[int]:
    """取简历关联的技能 id 列表。

    走 ResumeSkill 关联表(不是 Resume.skills 的 ORM 关系),
    因为这里只要 id 列表, 不需要技能名等额外字段, 查询更轻。
    """
    result = await db.scalars(
        select(ResumeSkill.skill_id).where(ResumeSkill.resume_id == resume_id)
    )
    return result.all()


async def recall_by_skills(
    skill_ids: list[int],
    db: AsyncSession,
    top_n: int = _RECALL_TOP_N,
) -> list[tuple[Job, int]]:
    """按技能重叠召回岗位(阶段③核心)。

    算法(通用的"技能集合交集"召回):
        输入「简历的技能集」→ 找 JobSkill 表里 skill_id 在该集合的行 →
        按 job_id 分组, 数每组几条 = 这个岗位命中了简历几个技能

    SQL 思路:
        1. 子查询: JobSkill 按 job_id 分组, 算命中数 + 加权分(必须技能权重高)
        2. 主查询: JOIN 回 Job 表, 过滤"在招", 按加权分排序, 限量

    加权排序(不在分数里体现, 只影响顺序):
        is_must=1 的命中算 2 分, 普通命中算 1 分 → 命中核心技能的岗位排前面
        对外暴露的 hit_count 仍是"命中技能个数"(直观), 加权只用于排序

    Args:
        skill_ids: 简历的技能 id 列表
        db:        异步会话
        top_n:     召回条数

    Returns:
        [(job, hit_count), ...] —— Job 是 ORM 对象(含 company/skills 关系,
        因 Job model 配了 lazy=selectin 自动预加载, 前端 JobCard 要用),
        hit_count 是这个岗位命中了简历几个技能
    """
    if not skill_ids:
        return []

    # 子查询: 每个岗位命中了几个简历技能 + 命中"必须技能"的加权分
    weighted = (
        select(
            JobSkill.job_id.label("job_id"),
            func.count(JobSkill.skill_id).label("hit_count"),
            # is_must=1 → 2 分, is_must=0 → 1 分; 命中必须技能含金量更高
            func.sum(JobSkill.is_must + 1).label("weighted"),
        )
        .where(JobSkill.skill_id.in_(skill_ids))
        .group_by(JobSkill.job_id)
        .subquery()
    )

    # 主查询: JOIN 回 Job 表拿完整对象 + 过滤"在招" + 排序 + 限量
    stmt = (
        select(Job, weighted.c.hit_count)
        .join(weighted, weighted.c.job_id == Job.id)
        .where(Job.status == "active", Job.is_deleted == 0)
        .order_by(
            weighted.c.weighted.desc(),   # 先按加权分(必须技能优先)
            Job.publish_at.desc(),         # 同分看新鲜度
        )
        .limit(top_n)
    )

    result = await db.execute(stmt)
    # result.all() 返回 list[Row], 每个 Row 解包成 (Job, hit_count)
    return [(row[0], row[1]) for row in result.all()]


async def recall_by_vector(
    resume: Resume,
    db: AsyncSession,
    top_n: int = _RECALL_TOP_N,
) -> list[tuple[Job, float]]:
    """按语义相似度召回岗位(阶段④核心)。

    流程:
        1. 把简历拼成"求职文本"(expect_job + 技能名 + 经历摘要)
        2. 调 GLM embed 把求职文本转向量
        3. 在 ChromaDB 里查最相似的 top_n 个岗位(向量召回)
        4. 回 SQL 把 job_id 批量转成 Job ORM 对象(前端 JobCard 要用)

    为什么需要它(和技能召回互补):
        技能召回只能找"技能 id 完全相同"的岗位 —— 简历写"Python"匹配不到
        要求"后端开发"的岗位(字面不同)。向量召回懂语义, 能把"会Python的人"
        和"招后端开发的岗位"关联起来, 扩大推荐覆盖面。

    Args:
        resume:  简历 ORM 对象(已预加载 skills/experiences, 拼文本要用)
        db:      异步会话
        top_n:   召回条数

    Returns:
        [(job, similarity), ...] —— similarity 是向量相似度 0~1(越大越像)
    """
    # 1. 拼求职文本
    query_text = _build_resume_query_text(resume)
    if not query_text.strip():
        return []

    # 2. 向量化 + 3. 向量库召回(都在 vector_service 内)
    query_vec = await aembed(query_text)
    raw_hits = await asearch(query_vec, top_k=top_n)
    if not raw_hits:
        return []

    # 4. 回 SQL 批量查 Job 对象(只查召回出来的那几个 id, 配 selectin 预加载关联)
    job_ids = [h["job_id"] for h in raw_hits]
    score_map = {h["job_id"]: h["score"] for h in raw_hits}  # job_id → 相似度

    stmt = (
        select(Job)
        .where(Job.id.in_(job_ids), Job.status == "active", Job.is_deleted == 0)
        # selectinload 预加载 company/skills, JobCard 要用; 避免 N+1
        .options(
            selectinload(Job.company),
            selectinload(Job.skills),
        )
    )
    jobs = (await db.execute(stmt)).scalars().all()

    # 按 ChromaDB 返回的相似度排序(不是按 job_id), 保留 score
    # 注意: jobs 查询结果顺序不保证, 要按 score_map 的原始顺序重排
    job_by_id = {j.id: j for j in jobs}
    return [
        (job_by_id[jid], score_map[jid])
        for jid in job_ids
        if jid in job_by_id  # 防御: 万一召回的 job 在 SQL 里被过滤掉了(如已下架)
    ]


def _build_resume_query_text(resume: Resume) -> str:
    """把简历拼成适合向量检索的"求职文本"。

    拼接策略(和建库时的 _build_jd_text 风格对齐, 让两者在同一向量空间可比):
        求职意向 + 技能名 + 工作经历摘要

    为什么这么拼:
        - expect_job(求职意向): 最强信号, 用户明确想做什么 → 放最前
        - 技能名: 和 JD 的技能段对应, 模型能匹配"会Python ↔ 招Python"
        - 经历摘要: 提供"做过什么"的语义(如"高并发""微服务"),
          让向量捕捉到经验维度, 而不只是技能词

    对齐的重要性: 建库时 JD 文本是"标题+技能+正文", 这里简历文本也是
    "意向+技能+经历", 两边结构相似, embedding 出来的向量才在同一"语系"里,
    相似度才有意义。如果一边只放技能词, 另一边放长正文, 向量空间会错位。
    """
    parts = []
    if resume.expect_job:
        parts.append(resume.expect_job)
    elif resume.title:
        parts.append(resume.title)  # 没填意向就用简历标题兜底

    skill_names = [rs.skill.name for rs in resume.skills if rs.skill]
    if skill_names:
        parts.append("技能: " + ", ".join(skill_names))

    # 经历摘要: 每段经历的"公司/职位/描述"拼一下, 控制总长度避免 query 过长
    for exp in resume.experiences[:2]:  # 最多取 2 段, 防止文本过长稀释信号
        seg = exp.title or ""
        if exp.description:
            seg += " " + exp.description[:80]  # 描述截断到 80 字
        if seg.strip():
            parts.append(seg.strip())

    return " | ".join(parts)


# ============================================================
# 2. 打分归一化(SCORE)
# ============================================================
def _normalize_skill_score(hit_count: int) -> Decimal:
    """把"命中技能数"归一化到 0~100 分。

    公式: score = min(hit_count, _MAX_SKILLS_FOR_NORMALIZE) / _MAX * 100

    举例(假设 _MAX=5):
        命中 1 个 → 20 分
        命中 3 个 → 60 分
        命中 5 个 → 100 分
        命中 8 个 → 100 分(封顶, 防止"命中多就虚高")

    为什么要归一化:
        - 阶段⑤ LLM 也是打 0~100 分, 统一量纲才能和向量分/LLM 分融合
        - 前端展示分数有统一参照(用户看 85 分就懂是"比较匹配")
    """
    clamped = min(hit_count, _MAX_SKILLS_FOR_NORMALIZE)
    return Decimal(str(round(clamped / _MAX_SKILLS_FOR_NORMALIZE * 100, 2)))


# ============================================================
# 2.5 LLM 重排(阶段⑤)
# ============================================================
async def rerank_with_llm(
    resume: Resume,
    candidates: list[dict],
) -> dict[int, dict]:
    """让 glm-4-flash 对候选岗位精排 + 生成推荐理由(阶段⑤核心)。

    输入: 两路召回融合后的候选岗位(阶段④的产物)
    输出: {job_id: {"score": float, "reason": str}}

    为什么需要 LLM 重排(在向量召回之上再做一层):
        向量召回是"表示相似度"——简历和 JD 文本在向量空间里近。
        但"近"≠"合适": 比如简历要北京, 岗位在深圳, 文本再像也不该推。
        LLM 能理解这种"硬约束"(城市/薪资/经验层级), 做更聪明的判断,
        还能用一句话写出"为什么推荐", 这是向量给不出的可解释性。

    容错策略(关键):
        LLM 可能: 返回非法 JSON / 超时 / 漏掉部分岗位。
        处理: 任何失败都 catch, 回退到候选的原始融合分, reason 给默认文案。
        原则: "用户看到推荐结果"比"LLM 完美工作"更重要, 绝不让推荐因 LLM 抖动而崩。

    Args:
        resume:      简历 ORM 对象(拼给 LLM 当背景)
        candidates:  候选列表, 每项 {job, skill_score, vector_score, ...}

    Returns:
        {job_id: {"score": 0~100, "reason": "..."}}, 缺失的 job_id 用融合分兜底
    """
    from app.core.llm import achat_json
    from app.core.exceptions import BizException

    if not candidates:
        return {}

    # ---------- 1. 拼 prompt ----------
    # 给 LLM 的信息要"足够它判断, 但不冗长":
    #   - 简历摘要: 意向 + 技能 + 年限(让它知道候选人画像)
    #   - 候选岗位: 编号 + 标题 + 城市 + 技能 + 要求摘要(让它逐个判断匹配度)
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

    # ---------- 2. 调 LLM + 容错 ----------
    try:
        result = await achat_json(prompt)
    except BizException:
        # LLM 抖动(JSON 解析失败/超时/限流): 回退融合分, 给默认理由
        return {
            info["job"].id: {
                "score": float(max(info["skill_score"], info["vector_score"])),
                "reason": "技能与经验较为匹配",
            }
            for info in candidates
        }

    # ---------- 3. 解析 LLM 返回, 容错缺失项 ----------
    # LLM 可能漏掉部分岗位或返回非预期结构, 逐个兜底
    reranked: dict[int, dict] = {}
    # 先建 job_id → 候选信息 的索引, 方便兜底
    fallback_map = {info["job"].id: info for info in candidates}

    if isinstance(result, list):
        for item in result:
            try:
                jid = int(item.get("job_id"))
                score = float(item.get("score", 0))
                reason = str(item.get("reason", ""))[:60]  # 限长, 防止 LLM 写太长撑爆 DB
                # score 范围校验
                score = max(0.0, min(100.0, score))
                reranked[jid] = {"score": score, "reason": reason or "技能与经验较为匹配"}
            except (ValueError, TypeError, AttributeError):
                continue  # 单条解析失败跳过, 不影响其他岗位

    # 补全 LLM 漏掉的岗位(用融合分兜底)
    for jid, info in fallback_map.items():
        if jid not in reranked:
            reranked[jid] = {
                "score": float(max(info["skill_score"], info["vector_score"])),
                "reason": "技能与经验较为匹配",
            }

    return reranked


# ============================================================
# 3. 主入口: recommend
# ============================================================
async def recommend(
    resume_id: int,
    user_id: int,
    db: AsyncSession,
) -> RecommendOut:
    """根据简历推荐岗位(阶段③ MVP 版)。

    流程:
        1. 校验简历存在 + 属于当前用户(防越权)
        2. 取简历技能 → recall_by_skills 召回候选
        3. 归一化打分 → 排序 → 取 top _RETURN_TOP_N
        4. 写 Recommendation 流水(strategy="skill")
        5. 返回 RecommendOut(items, total, strategy)

    阶段④⑤ 会扩展本函数:
        - ④: 在 recall 后加 recall_by_vector, 两路召回合并
        - ⑤: 在 score 后插入 LLM 重排, 用 GLM 分覆盖归一化分, 填 reason

    Args:
        resume_id: 简历 id
        user_id:   当前登录用户 id(用于越权校验 + 流水归属)
        db:        异步会话

    Raises:
        NotFoundError: 简历不存在或不属于该用户
    """
    # ---- 1. 校验简历归属(防越权: 不能用别人的简历推) ----
    # selectinload 预加载 skills + experiences: 阶段④ recall_by_vector 拼查询文本要用
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

    # ---- 2. 召回(两路并行, 求并集) ----
    # 技能召回: 精确匹配, 字面命中
    skill_ids = await get_resume_skills(resume_id, db)
    skill_hits = await recall_by_skills(skill_ids, db) if skill_ids else []

    # 向量召回: 语义匹配, 能找字面不同但意思相近的岗位
    vector_hits = await recall_by_vector(resume, db)

    # ---- 3. 两路融合(按 job_id 求并集, 分数取 max) ----
    # 为什么取 max 而不是 sum/avg:
    #   召回阶段求"全" —— 一个岗位只要在某一路表现好就该进候选。
    #   技能命中强但向量分低(如技能全中但 JD 文本没写清), 或反之, 都该保留。
    #   sum 会让"两路都中等"的岗位反超"一路极强"的, 不符合召回语义。
    # 量纲对齐: 技能分归一化到 0~100, 向量分(similarity 0~1)也 ×100 映射到 0~100。
    candidate: dict[int, dict] = {}  # job_id → {job, skill_score, vector_score, hit_count}

    for job, hit_count in skill_hits:
        candidate[job.id] = {
            "job": job,
            "skill_score": _normalize_skill_score(hit_count),
            "vector_score": Decimal("0"),
            "hit_skill_count": hit_count,
        }

    for job, similarity in vector_hits:
        if job.id in candidate:
            # 两路都召回的岗位: 补上向量分
            candidate[job.id]["vector_score"] = Decimal(str(round(similarity * 100, 2)))
        else:
            # 只向量召回的岗位: 技能分记 0(没命中技能不等于不匹配, 可能技能没填全)
            candidate[job.id] = {
                "job": job,
                "skill_score": Decimal("0"),
                "vector_score": Decimal(str(round(similarity * 100, 2))),
                "hit_skill_count": 0,
            }

    if not candidate:
        # 简历没技能 + 向量库为空/无匹配, 返回空
        return RecommendOut(items=[], total=0, strategy="hybrid")

    # ---- 4. 计算融合分 + 粗排 + LLM 精排 ----
    # 先算融合分(skill/vector 取 max), 粗排, 取 top K 送 LLM
    candidate_list = list(candidate.values())
    for info in candidate_list:
        info["fused_score"] = max(info["skill_score"], info["vector_score"])
    candidate_list.sort(key=lambda x: x["fused_score"], reverse=True)
    to_rerank = candidate_list[:_RERANK_TOP_K]

    # LLM 重排: 让 glm-4-flash 对 top K 逐个打分 + 写理由
    # 容错在内: LLM 抖动时回退融合分, reason 给默认, 不阻断流程
    rerank_result = await rerank_with_llm(resume, to_rerank)

    # 用 LLM 分覆盖融合分(若 LLM 失败已在上一步回退为融合分), 重新排序
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
    # 按 LLM 分降序, 取前 N
    items.sort(key=lambda x: x.score, reverse=True)
    items = items[:_RETURN_TOP_N]

    # ---- 5. 写推荐流水 ----
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
                # snapshot 记三路原始信号, 完整保留分数推导链路
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

    # ---- 6. 返回 ----
    return RecommendOut(items=items, total=len(items), strategy="rag")
