"""构建岗位向量库(ChromaDB)。

把 MySQL 里的岗位 JD 文本, 通过 GLM embedding-3 转成向量, 存进 ChromaDB。
之后阶段④ 推荐召回时, 把简历也转成向量, 在这个库里找"语义最相似"的岗位。

用法:
    cd backend
    python -m scripts.build_job_vectors              # 增量建库(跳过已存在的)
    python -m scripts.build_job_vectors --rebuild     # 全量重建(先清空再建)
    python -m scripts.build_job_vectors --limit 5     # 只建前 5 条(调试用)

设计要点:
    1. JD 文本拼接 = 标题 + 技能名 + JD正文
       为什么拼技能名: embedding 模型理解"Python工程师"和"会Python的岗位"语义相近,
       关键是技能词要出现在文本里。只拼正文的话, 有些 JD 正文很泛,
       技能词埋在段落深处, 向量里技能特征就被稀释了。
    2. 增量建库: 已在向量库里的 job_id 跳过(省 API 调用费, embedding 不便宜)
    3. 批量调用: 一次 embed_batch 多条, 比逐条 embed 省 N-1 次网络往返
    4. 进度打印: 每批打印一次, 调用方能直观看到进展
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证从 backend/ 目录运行时, app 包能被正确导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import joinedload  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import Job, JobSkill, Skill  # noqa: E402
from app.services.vector_service import (  # noqa: E402
    get_existing_ids,
    upsert_jobs,
)
from app.services import vector_service  # noqa: E402

# 每批处理多少条。智谱单次 embedding 建议不超过 64 条, 这里保守取 20。
# 现在测试数据只有 15 条, 一次就够; 将来上千条时这个分批才真正发挥作用。
_BATCH_SIZE = 20


def _build_jd_text(job: Job, skill_names: list[str]) -> str:
    """把一条岗位的零散信息, 拼成一段适合 embedding 的自然文本。

    拼接顺序: 标题 + 技能 + 正文
    技能放在标题后面、正文前面, 是为了让技能词在文本前段(embedding 的
    注意力机制对前段文本通常更敏感)。

    Args:
        job:         Job ORM 对象
        skill_names: 该岗位要求的技能名列表(如 ["Python", "MySQL", "Redis"])

    Returns:
        拼好的 JD 文本, 例如:
        "资深Python后端工程师 | 技能: Python, MySQL, Redis | 岗位职责: ..."
    """
    parts = [job.title]
    if skill_names:
        parts.append("技能: " + ", ".join(skill_names))
    if job.description_text:
        parts.append(job.description_text)
    return " | ".join(parts)


async def fetch_active_jobs(limit: int | None) -> list[Job]:
    """从 MySQL 拉所有在招且有正文的岗位(含技能名)。

    用 joinedload 一次性把 JobSkill + Skill 关联查出, 避免 N+1 查询。
    (虽然 Job model 默认 lazy=selectin 会自动预加载, 但显式 joinedload 更清晰)
    """
    stmt = (
        select(Job)
        .options(joinedload(Job.skills).joinedload(JobSkill.skill))
        .where(
            Job.status == "active",
            Job.is_deleted == 0,
            Job.description_text.is_not(None),
        )
        .order_by(Job.id)
    )
    if limit:
        stmt = stmt.limit(limit)

    async with AsyncSessionLocal() as db:
        result = await db.execute(stmt)
        # unique() 因为 joinedload M:N 关系会产生重复父行, 需去重
        return result.unique().scalars().all()


async def run_build(rebuild: bool = False, limit: int | None = None) -> int:
    """主流程: 拉岗位 → (可选清空) → 增量过滤 → 向量化 → 入库。返回退出码。"""
    try:
        # 显式预热 collection(触发懒加载, 顺便确认 chromadb 装好了)
        collection = vector_service._get_collection()

        # ---------- 1. 拉岗位 ----------
        jobs = await fetch_active_jobs(limit)
        print(f"[1/4] 从 MySQL 拉到 {len(jobs)} 条在招岗位")
        if not jobs:
            print("[完成] 没有可建库的岗位")
            return 0

        # ---------- 2. 可选: 全量重建 ----------
        if rebuild:
            # 删旧集合 → 重新建空集合。ChromaDB 的 delete_collection 是惰性删除,
            # 删除后磁盘上的 <uuid>/*.bin 文件夹不会立即清掉(每个 ~833KB),
            # 反复 --rebuild 会让向量库文件夹越来越大。所以这里手动清理孤儿。
            import chromadb
            import shutil

            client = chromadb.PersistentClient(path=str(vector_service.settings.CHROMA_PATH))
            try:
                client.delete_collection(vector_service._COLLECTION_NAME)
                print("[重建] 已清空旧向量库")
            except Exception:
                pass  # 集合不存在就算了

            # 删除后, 重新查"现在还活跃的集合"(此时旧集合已不在列表里),
            # 磁盘上不在活跃列表里的 <uuid> 目录就是孤儿, 删掉。
            active_uuids = {str(c.id) for c in client.list_collections()}
            for sub in settings.CHROMA_PATH.iterdir():
                # 只删 UUID 命名的目录(chroma.sqlite3 等文件不动), 且不是活跃集合
                if sub.is_dir() and sub.name not in active_uuids:
                    shutil.rmtree(sub, ignore_errors=True)
                    print(f"[清理] 删除孤儿目录 {sub.name}")

            # 清掉单例缓存, 重新拿空集合
            vector_service._get_collection.cache_clear()
            collection = vector_service._get_collection()

        # ---------- 3. 增量过滤 ----------
        all_ids = [j.id for j in jobs]
        existing = get_existing_ids(all_ids) if not rebuild else set()
        todo = [j for j in jobs if j.id not in existing]
        skipped = len(jobs) - len(todo)
        print(f"[2/4] 增量过滤: 跳过已存在 {skipped} 条, 待建 {len(todo)} 条")
        if not todo:
            print("[完成] 向量库已是最新, 无需更新")
            return 0

        # ---------- 4. 分批向量化 + 入库 ----------
        print(f"[3/4] 开始向量化(每批 {_BATCH_SIZE} 条)...")
        total_done = 0
        for i in range(0, len(todo), _BATCH_SIZE):
            batch = todo[i : i + _BATCH_SIZE]
            # 拼文本 + 准备 metadata
            texts = [_build_jd_text(j, [js.skill.name for js in j.skills if js.skill]) for j in batch]
            metas = [
                {"title": j.title or "", "city": j.city or "", "source": j.source or ""}
                for j in batch
            ]
            ids = [j.id for j in batch]

            # 向量化 + 入库(都在 upsert_jobs 内完成)
            written = upsert_jobs(ids, texts, metas)
            total_done += written
            print(f"       批次 {i // _BATCH_SIZE + 1}: 写入 {written} 条 (累计 {total_done})")

        # ---------- 5. 收尾 ----------
        final_count = collection.count()
        print(f"[4/4] 完成。本次写入 {total_done} 条, 向量库当前共 {final_count} 条")
        print(f"       存储位置: {vector_service.settings.CHROMA_PATH}")
        return 0
    finally:
        # 无论走哪个分支(含增量跳过的早 return), 都要关闭连接池,
        # 否则 aiomysql 在脚本退出时报 "Event loop is closed"
        # (参考 scripts/import_jobs.py 的处理方式)
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="构建 JobHunter 岗位向量库(ChromaDB)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m scripts.build_job_vectors              # 增量建库
    python -m scripts.build_job_vectors --rebuild     # 全量重建
    python -m scripts.build_job_vectors --limit 5     # 只建前 5 条(调试)
        """,
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="全量重建: 先清空向量库再重新建(已存在的也会重算)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="只处理前 N 条岗位(调试用)",
    )
    args = parser.parse_args(argv)

    import asyncio
    return asyncio.run(run_build(rebuild=args.rebuild, limit=args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
