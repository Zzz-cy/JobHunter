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
    return dict(_sync_state)


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
    """第1步: jobs_raw.json → MySQL(幂等)。"""
    from app.core.database import AsyncSessionLocal
    from app.utils.jsonToMysqlUtil import json_to_mysql

    with open(_JOBS_RAW_PATH, encoding="utf-8") as f:
        data = json.load(f)
    async with AsyncSessionLocal() as db:
        await json_to_mysql(data, db)
    return f"导入 {len(data.get('jobs', []))} 条(已存在的自动跳过)"


async def _step_es() -> str:
    """第2步: MySQL 全量职位 → ES。"""
    from scripts.sync_jobs_to_es import sync

    await sync()   # 函数内部会打印成功条数
    return "ES 全量同步完成(_id=主键, 幂等)"


async def _step_chroma() -> str:
    """第3步: MySQL 职位 → ChromaDB 向量(推荐用)。"""
    from scripts.build_job_vectors import run_build

    count = await run_build()   # 增量构建, 已有向量不重建
    return f"向量库构建完成, 本次处理 {count} 条"


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
