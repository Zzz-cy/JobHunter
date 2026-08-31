"""
新兴技能候选记录

技能归一未命中字典时, 不再丢弃——记一笔到 emerging_skills,
新技能(字典外的词)由此可被发现和积累证据。
"""
from datetime import datetime

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmergingSkill


async def record_unknown_skills(db: AsyncSession, names: list[str]) -> int:
    """未匹配技能词批量落候选表(upsert: 已存在则计数+1并刷新最近出现)。

    Returns:
        实际记录的词数(去重后)
    """
    unique = list({n.strip() for n in names if n and n.strip()})
    if not unique:
        return 0

    now = datetime.now()
    stmt = mysql_insert(EmergingSkill).values([
        {"name": n, "hit_count": 1, "first_seen": now, "last_seen": now}
        for n in unique
    ]).on_duplicate_key_update(
        hit_count=EmergingSkill.hit_count + 1,
        last_seen=now,
    )
    await db.execute(stmt)
    return len(unique)
