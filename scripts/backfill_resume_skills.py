# -*- coding: utf-8 -*-
"""字典扩充后回填简历技能。

场景: 02_seed.sql 补了新技能/别名后, 已解析的简历不会自动重算,
本脚本按"不区分大小写的 name+alias 匹配"重扫 parsed_raw.skills,
补齐 resume_skills, 并把已能命中字典的词从 emerging_skills 候选表清掉。

用法: python scripts/backfill_resume_skills.py [--only 真实-]
  --only 只处理标题前缀匹配的简历(默认全部)
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # app 包在项目根
from app.core.database import AsyncSessionLocal
from app.models import EmergingSkill, Resume, ResumeSkill, Skill


def build_lookup(skills) -> dict:
    """词(小写) -> skill_id, name 和 alias 都进索引"""
    lookup = {}
    for s in skills:
        lookup[s.name.lower()] = s.id
        for a in (s.alias or "").split(","):
            a = a.strip().lower()
            if a:
                lookup[a] = s.id
    return lookup


async def main(prefix: str | None):
    async with AsyncSessionLocal() as db:
        skills = (await db.scalars(select(Skill))).all()
        lookup = build_lookup(skills)
        print(f"字典 {len(skills)} 个技能, 索引 {len(lookup)} 个词形")

        stmt = select(Resume).where(Resume.parse_status == "done")
        if prefix:
            stmt = stmt.where(Resume.title.like(f"{prefix}%"))
        resumes = (await db.scalars(stmt)).all()

        matched_words = set()
        total_added = 0
        for r in resumes:
            words = ((r.parsed_raw or {}).get("skills")) or []
            if not words:
                continue
            existing = set((await db.scalars(
                select(ResumeSkill.skill_id).where(ResumeSkill.resume_id == r.id))).all())
            ids = {lookup[w.lower()] for w in words if w.lower() in lookup}
            matched_words |= {w for w in words if w.lower() in lookup}
            added = ids - existing
            for sid in added:
                db.add(ResumeSkill(resume_id=r.id, skill_id=sid))
            total_added += len(added)
            if added:
                names = [s.name for s in skills if s.id in added]
                print(f"  {r.title}: +{names}")

        # 已能命中字典的词不再是"候选", 从候选表清掉
        removed = 0
        for word in matched_words:
            res = await db.execute(
                delete(EmergingSkill).where(EmergingSkill.name == word))
            removed += res.rowcount

        await db.commit()
        print(f"\n处理 {len(resumes)} 份简历, 新增 {total_added} 条 resume_skills, "
              f"清理候选词 {removed} 个")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="只处理标题以该前缀开头的简历")
    args = parser.parse_args()
    asyncio.run(main(args.only))
