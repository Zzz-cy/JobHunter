"""
爬虫数据管理接口: 预览数据文件 / 一键同步四库 / 查同步进度。
"""
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.config import settings
from app.schemas import Result
from app.services.sync_all_service import get_sync_status, run_sync_all
from app.utils.jwtUtil import require_admin

router = APIRouter(prefix="/crawl", tags=["爬虫数据管理"])

# 数据文件路径: backend/db/data/jobs_raw.json
_DATA_PATH = Path(settings.UPLOAD_DIR).parent / "db" / "data" / "jobs_raw.json"


@router.get("/preview", response_model=Result[dict], summary="预览爬虫数据文件状态")
async def preview_crawl_data(_=Depends(require_admin)):
    """预览待导入的数据文件(条数/字段填充率), 不入库。需管理员。"""
    if not _DATA_PATH.exists():
        return Result.success(data={
            "exists": False,
            "message": "数据文件不存在, 请先让爬虫把数据放到 db/data/jobs_raw.json",
        })

    with open(_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    ws_filled = sum(1 for j in jobs if j.get("company", {}).get("website"))
    ind_filled = sum(1 for j in jobs if j.get("company", {}).get("industry"))

    return Result.success(data={
        "exists": True,
        "file_name": _DATA_PATH.name,
        "crawl_batch": data.get("crawl_batch"),
        "total": len(jobs),
        "website_filled": ws_filled,
        "industry_filled": ind_filled,
        "file_size_mb": round(_DATA_PATH.stat().st_size / 1024 / 1024, 2),
        "last_modified": datetime.fromtimestamp(
            _DATA_PATH.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S"),
    }, message="数据文件就绪")


# ---------- 首次部署初始化(Bootstrap) ----------

@router.post("/bootstrap", response_model=Result[dict], summary="首次部署初始化(免登录)")
async def bootstrap_system():
    """
    空库专用: 建表 + 字典种子 + 默认账号。

    初始化成功后再调无任何效果, 免鉴权也不会被滥用。
    """
    import asyncio
    import os

    import pymysql

    def _has_admin() -> bool:
        """users 表存在且有 admin 账号 = 已初始化(表/库不存在视为未初始化)。"""
        try:
            conn = pymysql.connect(
                host=settings.MYSQL_HOST, port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER, password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE, charset="utf8mb4",
            )
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
                return cur.fetchone()[0] > 0
        except Exception:
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    if await asyncio.to_thread(_has_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统已初始化, 请直接登录",
        )

    # 注入 env(init_storage 用 os.getenv 读配置, .env 的值不在 os.environ)
    for key, val in (
        ("MYSQL_HOST", settings.MYSQL_HOST),
        ("MYSQL_PORT", str(settings.MYSQL_PORT)),
        ("MYSQL_USER", settings.MYSQL_USER),
        ("MYSQL_PASSWORD", settings.MYSQL_PASSWORD),
    ):
        os.environ.setdefault(key, val)

    from scripts.init_storage import init_mysql

    # 只跑 01+02: 表 + 字典 + 账号 + 求职者A演示简历(在 02 里)。
    # 不跑 03: 纯演示数据(mock 职位/投递), 会污染真实爬虫数据。
    await asyncio.to_thread(init_mysql, ["01_schema.sql", "02_seed.sql"])

    return Result.success(
        data={"initialized": True},
        message="初始化完成! 请用默认管理员账号登录",
    )


# ---------- 一键全库同步 ----------

@router.post("/sync-all", response_model=Result[dict], summary="一键同步所有库")
async def sync_all_stores(
    background_tasks: BackgroundTasks,
    _=Depends(require_admin),
):
    """
    一键同步四个库(MySQL→ES→ChromaDB→Neo4j), 后台执行立即返回。
    """
    if get_sync_status()["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同步任务正在进行中, 请等完成后再触发",
        )
    if not _DATA_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据文件不存在: {_DATA_PATH.name}, 请先让爬虫产出数据",
        )

    # 跑在主事件循环(BackgroundTasks), 无跨循环问题
    background_tasks.add_task(run_sync_all)
    return Result.success(
        data=get_sync_status(),
        message="全库同步已启动(约2-5分钟), 完成后所有库数据就绪",
    )


@router.get("/sync-status", response_model=Result[dict], summary="进度轮询")
async def sync_all_status(_=Depends(require_admin)):
    """查同步进度(前端每 5 秒轮询)。"""
    return Result.success(data=get_sync_status())
