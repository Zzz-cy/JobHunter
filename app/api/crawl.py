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

# 数据文件目录: backend/db/data/
_DATA_DIR = Path(settings.UPLOAD_DIR).parent / "db" / "data"
_DEFAULT_DATA_FILE = "jobs_raw.json"


def _resolve_data_file(name: str | None) -> Path:
    """文件名白名单校验: 只允许 db/data 下的 .json, 防路径穿越。"""
    name = (name or _DEFAULT_DATA_FILE).strip()
    if not name.endswith(".json") or Path(name).name != name:
        raise HTTPException(status_code=400, detail="只能选 db/data 目录下的 .json 文件")
    path = _DATA_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"数据文件不存在: {name}")
    return path


@router.get("/data-files", response_model=Result[dict], summary="列出可导入的数据文件")
async def list_data_files(_=Depends(require_admin)):
    """列出 db/data 下所有 json 文件(前端下拉选择导入源)。"""
    files = []
    if _DATA_DIR.exists():
        for p in sorted(_DATA_DIR.glob("*.json"),
                        key=lambda x: x.stat().st_mtime, reverse=True):
            st = p.stat()
            files.append({
                "name": p.name,
                "size_mb": round(st.st_size / 1024 / 1024, 2),
                "last_modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    return Result.success(data={"files": files, "default": _DEFAULT_DATA_FILE})


@router.get("/preview", response_model=Result[dict], summary="预览爬虫数据文件状态")
async def preview_crawl_data(file: str | None = None, _=Depends(require_admin)):
    """预览待导入的数据文件(条数/字段填充率), 不入库。需管理员。"""
    data_path = _DATA_DIR / (file or _DEFAULT_DATA_FILE)
    if not data_path.exists():
        return Result.success(data={
            "exists": False,
            "message": f"数据文件不存在, 请先让爬虫把数据放到 db/data/{file or _DEFAULT_DATA_FILE}",
        })

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    ws_filled = sum(1 for j in jobs if j.get("company", {}).get("website"))
    ind_filled = sum(1 for j in jobs if j.get("company", {}).get("industry"))

    return Result.success(data={
        "exists": True,
        "file_name": data_path.name,
        "crawl_batch": data.get("crawl_batch"),
        "total": len(jobs),
        "website_filled": ws_filled,
        "industry_filled": ind_filled,
        "file_size_mb": round(data_path.stat().st_size / 1024 / 1024, 2),
        "last_modified": datetime.fromtimestamp(
            data_path.stat().st_mtime
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
    await asyncio.to_thread(init_mysql, ["01_schema.sql", "02_seed.sql", "04_llm_module.sql"])

    return Result.success(
        data={"initialized": True},
        message="初始化完成! 请用默认管理员账号登录",
    )


# ---------- 一键全库同步 ----------

@router.post("/sync-all", response_model=Result[dict], summary="一键同步所有库")
async def sync_all_stores(
    background_tasks: BackgroundTasks,
    payload: dict | None = None,
    _=Depends(require_admin),
):
    """
    一键同步四个库(MySQL→ES→ChromaDB→Neo4j), 后台执行立即返回。

    body 可选: {"data_file": "jobs_raw_2.json"} 指定导入源(默认 jobs_raw.json)
    """
    if get_sync_status()["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同步任务正在进行中, 请等完成后再触发",
        )
    data_file = (payload or {}).get("data_file") or None
    _resolve_data_file(data_file)   # 白名单校验(不存在直接 404)

    # 跑在主事件循环(BackgroundTasks), 无跨循环问题
    background_tasks.add_task(run_sync_all, data_file)
    return Result.success(
        data=get_sync_status(),
        message=f"全库同步已启动(数据源: {data_file or _DEFAULT_DATA_FILE}, 约2-5分钟)",
    )


@router.get("/sync-status", response_model=Result[dict], summary="进度轮询")
async def sync_all_status(_=Depends(require_admin)):
    """查同步进度(前端每 5 秒轮询)。"""
    return Result.success(data=get_sync_status())
