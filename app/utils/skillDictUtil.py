"""
技能字典归一化工具
"""
import difflib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Skill


def alias_tokens(alias: str | None) -> set[str]:
    """alias 字段("py,python3")拆成小写词集合(精确匹配用, 不用 LIKE 防误中)。"""
    if not alias:
        return set()
    return {t.strip().lower() for t in alias.split(",") if t.strip()}


def match_skill_in_list(name: str, skills: list[Skill]) -> Skill | None:
    """纯函数: 在给定技能列表里规则归一。优先级: 标准名 > 别名, 均忽略大小写。"""
    key = (name or "").strip().lower()
    if not key:
        return None
    for s in skills:
        if s.name and s.name.strip().lower() == key:
            return s
    for s in skills:
        if key in alias_tokens(s.alias):
            return s
    return None


async def load_all_skills(db: AsyncSession) -> list[Skill]:
    """一次拉出全字典(字典量级小, 全量进内存比逐词查库快)。"""
    return list((await db.scalars(select(Skill))).all())


async def find_skill(db: AsyncSession, name: str) -> Skill | None:
    """查字典(别名感知)。未命中返回 None, 由调用方决定记候选还是新建。"""
    if not name or not name.strip():
        return None
    return match_skill_in_list(name, await load_all_skills(db))


async def find_skills(db: AsyncSession, names: list[str]) -> dict[str, Skill]:
    """批量版: 一次查全表, 内存里逐词归一, 返回 {原始词(去空白): Skill}。"""
    skills = await load_all_skills(db)
    hits: dict[str, Skill] = {}
    for n in names:
        key = (n or "").strip()
        if not key or key in hits:
            continue
        s = match_skill_in_list(key, skills)
        if s:
            hits[key] = s
    return hits


def recall_similar_skills(
    name: str, skills: list[Skill], top_k: int = 5, min_score: float = 0.3
) -> list[Skill]:
    """字符串相似度召回 TopK 候选(标准名与别名都参与打分), 供 LLM 精判。

    打分规则:
      - difflib 序列相似度为基础分
      - 存在包含关系("Vue.js" vs "Vue")保底 0.8, 版本号/后缀类变体不被漏掉
      - 低于 min_score 的候选不上送(全不像就说明是真新词, 省一次 LLM 调用)
    """
    key = (name or "").strip().lower()
    if not key:
        return []

    scored: list[tuple[float, Skill]] = []
    for s in skills:
        variants = [s.name.strip().lower()] if s.name else []
        variants += list(alias_tokens(s.alias))
        if not variants:
            continue
        best = max(difflib.SequenceMatcher(None, key, v).ratio() for v in variants)
        if any(key in v or v in key for v in variants):
            best = max(best, 0.8)
        scored.append((best, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for score, s in scored[:top_k] if score >= min_score]
