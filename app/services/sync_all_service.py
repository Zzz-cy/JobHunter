"""一键全库同步服务(MySQL → ES / ChromaDB / Neo4j)。

爬虫产出新 jobs_raw.json 后一键把四个库同步到位。
每步独立容错, 单库没启动只标记该步失败。全局状态 dict 供前端轮询。
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from app.core.config import settings

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_JOBS_RAW_PATH = _BACKEND_DIR / "db" / "data" / "jobs_raw.json"

# 全局状态(前端轮询读)
_sync_state: dict = {
    "running": False,
    "steps": [],          # [{"key","name","status","message"}, ...] pending/running/done/failed/skipped
    "started_at": None,
    "finished_at": None,
    "message": "",
}


def get_sync_status() -> dict:
    # 排除 _ 开头的内部标记(如 _fresh_import), 不给前端
    return {k: v for k, v in _sync_state.items() if not k.startswith("_")}


def _init_steps() -> None:
    """初始化四步的状态骨架。"""
    _sync_state["steps"] = [
        {"key": "mysql",  "name": "MySQL 导入",   "status": "pending", "message": ""},
        {"key": "es",     "name": "ES 同步",      "status": "pending", "message": ""},
        {"key": "chroma", "name": "向量库构建",   "status": "pending", "message": ""},
        {"key": "neo4j",  "name": "知识图谱构建", "status": "pending", "message": ""},
    ]


def _step(key: str, status: str, message: str = "") -> None:
    """更新某一步的状态。"""
    for s in _sync_state["steps"]:
        if s["key"] == key:
            s.update(status=status, message=message)
            break


# ---------- 四个同步步骤 ----------

async def _step_mysql() -> str:
    """第1步: 确保表结构/字典存在(幂等) + 导入 jobs_raw.json(幂等)。"""
    import asyncio
    import os

    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.utils.jsonToMysqlUtil import json_to_mysql

    # init_storage 用 os.getenv 读配置, .env 的值不在 os.environ 里, 先注入
    for env_key, setting in (
        ("MYSQL_HOST", settings.MYSQL_HOST),
        ("MYSQL_PORT", str(settings.MYSQL_PORT)),
        ("MYSQL_USER", settings.MYSQL_USER),
        ("MYSQL_PASSWORD", settings.MYSQL_PASSWORD),
    ):
        os.environ.setdefault(env_key, setting)

    # 建表+字典种子(全新库补齐, 已有库 IF NOT EXISTS/IGNORE 无感跳过)
    # 不含 03_mock: mock 不幂等, 重复跑数据翻倍
    from scripts.init_storage import init_mysql
    await asyncio.to_thread(
        init_mysql, ["01_schema.sql", "02_seed.sql"])

    with open(_JOBS_RAW_PATH, encoding="utf-8") as f:
        data = json.load(f)

    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        # 导入前职位数: 0 = 全新库(重置/首次), 供向量库判断全量重建
        before = await db.scalar(text("SELECT COUNT(*) FROM jobs WHERE is_deleted=0"))
        _sync_state["_fresh_import"] = (before == 0)

        await json_to_mysql(data, db)

        # 热门技能动态重算: 按 active 职位关联数 Top15 置 is_hot
        # (不再依赖种子手工标注, 前端 SkillTag 火焰图标随真实需求刷新)
        await db.execute(text("UPDATE skills SET is_hot = 0"))
        await db.execute(text("""
            UPDATE skills s SET s.is_hot = 1 WHERE s.id IN (
                SELECT skill_id FROM (
                    SELECT js.skill_id AS skill_id
                    FROM job_skills js
                    JOIN jobs j ON j.id = js.job_id
                    WHERE j.status = 'active' AND j.is_deleted = 0
                    GROUP BY js.skill_id
                    ORDER BY COUNT(*) DESC
                    LIMIT 15
                ) top
            )
        """))
    return f"导入 {len(data.get('jobs', []))} 条(已存在的自动跳过), 热门技能已重算"


async def _step_es() -> str:
    """第2步: MySQL 全量职位 → ES(以 MySQL 为准, 删索引重建)。"""
    from app.core.es import es_client, JOBS_INDEX
    from scripts.init_es_index import MAPPING
    from scripts.sync_jobs_to_es import sync

    # 删了重建: 增量写入会让 MySQL 已删/重置的职位残留在 ES(total 虚高/分页错乱)
    if es_client.indices.exists(index=JOBS_INDEX):
        es_client.indices.delete(index=JOBS_INDEX)
    es_client.indices.create(index=JOBS_INDEX, **MAPPING)
    await sync()
    return "ES 重建完成(与 MySQL 完全一致)"


async def _step_chroma() -> str:
    """第3步: MySQL 职位 → ChromaDB 向量。

    两个关键设计:
    1. 子进程执行: embedding 是同步阻塞计算, 跑在事件循环里会卡死
       整个后端(连进度轮询都没响应, 前端弹超时)。丢给子进程完全隔离。
    2. 智能全量/增量:
       - 全新库(重置/首次, _fresh_import) 或 向量数>MySQL数(残留异常) → 全量重建
         (重置库后主键复用, 旧向量内容与新职位对不上, 增量无法自愈)
       - 追加场景 → 增量(只建新职位, 存量向量不重算)
    """
    import sys

    from sqlalchemy import text

    from app.core.database import AsyncSessionLocal
    from app.services import vector_service

    col = vector_service._get_collection()
    chroma_count = col.count()
    async with AsyncSessionLocal() as db:
        mysql_count = await db.scalar(text("SELECT COUNT(*) FROM jobs WHERE is_deleted=0"))

    rebuild = _sync_state.get("_fresh_import", False) or chroma_count > mysql_count
    mode = "全量重建" if rebuild else "增量构建"

    args = [sys.executable, "-m", "scripts.build_job_vectors"] + (["--rebuild"] if rebuild else [])
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()   # 等子进程, 不阻塞事件循环
    if proc.returncode != 0:
        tail = (out or b"").decode(errors="replace")[-200:]
        raise RuntimeError(f"向量构建失败: {tail}")

    vector_service._get_collection.cache_clear()
    n = vector_service._get_collection().count()
    return f"向量库{mode}完成: {chroma_count} → {n} 条"


def _step_neo4j_sync() -> str:
    """第4步: 重建 Neo4j 知识图谱(同步代码, 由 to_thread 调用)。"""
    import os

    import scripts.init_neo4j as init_neo4j

    # 注入 Neo4j 密码到环境变量: 脚本优先读它, 避免后台无终端卡在 getpass 交互
    if settings.NEO4J_PASSWORD:
        os.environ["NEO4J_PASSWORD"] = settings.NEO4J_PASSWORD

    init_neo4j.main()
    return "知识图谱(岗位+就业分析)重建完成"


# ---------- 主流程 ----------

async def run_sync_all() -> None:
    """依次执行四步同步。每步独立 try, 失败不断流。"""
    _sync_state.update(
        running=True, started_at=datetime.now().isoformat(timespec="seconds"),
        finished_at=None, message="",
    )
    _init_steps()
    failed = []

    # ---- 前置: 数据文件必须存在 ----
    if not _JOBS_RAW_PATH.exists():
        _sync_state.update(
            running=False,
            finished_at=datetime.now().isoformat(timespec="seconds"),
            message=f"数据文件不存在: {_JOBS_RAW_PATH}",
        )
        return

    executors = [
        ("mysql",  "读取 jobs_raw.json 导入 MySQL",        _step_mysql),
        ("es",     "MySQL 职位全量同步到 ES",               _step_es),
        ("chroma", "构建职位向量(ChromaDB)",                _step_chroma),
        ("neo4j",  "重建知识图谱(Neo4j)",                   None),   # 同步函数特殊处理
    ]

    for key, desc, coro_fn in executors:
        _step(key, "running", desc)
        t0 = time.time()
        try:
            if key == "neo4j":
                # 同步脚本 → 线程池执行, 不阻塞事件循环
                msg = await asyncio.to_thread(_step_neo4j_sync)
            else:
                msg = await coro_fn()
            _step(key, "done", f"{msg} ({time.time() - t0:.1f}s)")
        except Exception as e:
            failed.append(key)
            _step(key, "failed", str(e)[:200])
            print(f"[sync_all] {key} 失败: {e}")

    _sync_state.update(
        running=False,
        finished_at=datetime.now().isoformat(timespec="seconds"),
        message=("全部完成 ✅" if not failed else f"完成, 但 {len(failed)} 步失败: {', '.join(failed)}(该库可能未启动)"),
    )
