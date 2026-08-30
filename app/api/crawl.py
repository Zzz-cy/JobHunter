"""爬虫数据管理接口

接口:
    GET  /crawl/preview      预览数据文件状态(条数/字段填充率), 给前端展示用
    POST /crawl/sync-all     一键同步四个库(MySQL→ES→ChromaDB→Neo4j, 后台执行)
    GET  /crawl/sync-status  查一键同步进度(前端轮询)
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
    """预览待导入的数据文件, 不入库。给前端按钮旁边显示"待导入 X 条"用。

    需要管理员权限。
    """
    if not _DATA_PATH.exists():
        return Result.success(data={
            "exists": False,
            "message": "数据文件不存在, 请先让爬虫把数据放到 db/data/jobs_raw.json",
        })

    # 读文件统计(不读全量, 只取必要信息, 大文件也不卡)
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


# ---------- 一键全库同步 ----------

@router.post("/sync-all", response_model=Result[dict], summary="一键同步所有库")
async def sync_all_stores(
    background_tasks: BackgroundTasks,
    _=Depends(require_admin),
):
    """一键同步四个库(后台执行, 立即返回):

    1. MySQL     导入 jobs_raw.json(幂等)
    2. ES        职位全量同步(搜索立即可用)
    3. ChromaDB  职位向量构建(推荐用)
    4. Neo4j     知识图谱重建

    每步独立容错: 某个库没启动(如 Neo4j)只标记该步失败, 不影响其他库。
    用 GET /crawl/sync-status 轮询进度。
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


@router.get("/sync-status", response_model=Result[dict], summary="一键同步进度(轮询)")
async def sync_all_status(_=Depends(require_admin)):
    """查四步同步的当前状态(前端每 5 秒轮询)。"""
    return Result.success(data=get_sync_status())
