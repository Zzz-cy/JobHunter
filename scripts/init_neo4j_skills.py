"""
Neo4j 图谱补充: 岗位方向 → 核心技能关系(DEMANDS)
"""
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j import GraphDatabase  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import Job, JobSkill, Skill  # noqa: E402

TOP_N = 8          # 每个方向写入的核心技能上限(前端展示再截断)
MIN_JOB_COUNT = 3  # 岗位数低于此值的技能不写入(小样本噪音)

# 图是从这份 JSON 建的(与 init_neo4j_jobs/analysis 同源)。
# 图里的 job_code 和 MySQL 的不是同一次生成的(直接 JOIN 交集为 0),
# 用这份 JSON 把图里的 job_code 翻译成 (source, source_id) 再对 MySQL。
JOBS_JSON = Path(__file__).resolve().parents[1] / "db" / "neo4j" / "jobs.json"


def _load_json_code_map() -> dict[str, tuple[str, str]]:
    """jobs.json: {job_code: (source, source_id)}"""
    with open(JOBS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {
        j["job_code"]: (j.get("source") or "", str(j.get("source_id") or ""))
        for j in data if j.get("job_code")
    }


async def _fetch_job_skills() -> dict[tuple[str, str], list[str]]:
    """MySQL: {(source, source_id): [技能名, ...]}, 只统计在招岗位。"""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Job.source, Job.source_id, Skill.name)
            .join(JobSkill, JobSkill.job_id == Job.id)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(Job.is_deleted == 0)
        )).all()
    result: dict[tuple[str, str], list[str]] = defaultdict(list)
    for source, source_id, skill_name in rows:
        if source and source_id and skill_name:
            result[(source, str(source_id))].append(skill_name)
    return result


def _fetch_direction_membership(driver) -> dict[str, list[str]]:
    """Neo4j: {方向名: [job_code, ...]}, 直接读图里已建好的方向归属。"""
    with driver.session(database="neo4j") as session:
        records = session.run(
            """
            MATCH (j:Job)-[:IN_DIRECTION]->(d:JobDirection)
            RETURN d.name AS direction, j.job_code AS job_code
            """
        )
        result: dict[str, list[str]] = defaultdict(list)
        for r in records:
            if r["job_code"]:
                result[r["direction"]].append(r["job_code"])
    return result


async def main_async() -> None:
    password = (
        os.getenv("NEO4J_PASSWORD") or settings.NEO4J_PASSWORD
        or getpass("请输入Neo4j密码：")
    )
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", settings.NEO4J_URI),
        auth=("neo4j", password),
    )

    job_skills = await _fetch_job_skills()
    membership = _fetch_direction_membership(driver)
    code_map = _load_json_code_map()
    await engine.dispose()

    if not membership:
        print("[跳过] 图里没有 IN_DIRECTION 归属, 请先跑 init_neo4j_jobs/analysis")
        driver.close()
        return

    with driver.session(database="neo4j") as session:
        # 幂等: 清旧关系再重建(Skill 节点本身由 MERGE 收敛, 无需删)
        session.run("MATCH (:JobDirection)-[r:DEMANDS]->() DELETE r").consume()
        session.run(
            """
            CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
            FOR (s:Skill) REQUIRE s.name IS UNIQUE
            """
        ).consume()

        written = 0
        for direction, job_codes in membership.items():
            counter: Counter = Counter()
            matched = 0
            for jc in job_codes:
                key = code_map.get(jc)   # 图里的 job_code → (source, source_id)
                if not key:
                    continue
                skills = job_skills.get(key)
                if skills is None:
                    continue
                matched += 1
                for name in set(skills):   # 同岗位同技能只计一次
                    counter[name] += 1

            total = matched or 1   # 分母: 匹配到技能数据的岗位数(覆盖率口径)
            for name, cnt in [(n, c) for n, c in counter.most_common(TOP_N)
                              if c >= MIN_JOB_COUNT]:
                session.run(
                    """
                    MERGE (s:Skill {name: $name})
                    WITH s
                    MATCH (d:JobDirection {name: $direction})
                    MERGE (d)-[r:DEMANDS]->(s)
                    SET r.pct = $pct, r.job_count = $cnt
                    """,
                    name=name,
                    direction=direction,
                    pct=round(cnt / total * 100, 2) if total else 0,
                    cnt=cnt,
                ).consume()
                written += 1

    driver.close()
    print(f"[完成] 方向-核心技能关系(DEMANDS)写入 {written} 条")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
