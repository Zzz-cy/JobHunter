"""爬虫数据导入接口

用途: 给前端一个"同步爬虫数据"按钮, 手动触发数据导入。
      替代之前"定时读固定文件"的方案(定时读一个不变的文件没意义)。

接口:
    POST /crawl/import   读 jobs_raw.json 并入库(幂等: 已存在的跳过)
    GET  /crawl/preview  预览文件状态(条数/字段填充率), 不入库, 给前端展示用
"""
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas import Result
from app.utils.jwtUtil import require_admin
from app.utils.jsonToMysqlUtil import json_to_mysql

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


@router.post("/import", response_model=Result[dict], summary="手动触发爬虫数据导入")
async def import_crawl_data(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """读取 db/data/jobs_raw.json 并入库。需要管理员权限。

    特点:
        - 按 (source, source_id) 去重, 重复点按钮不会重复入库
        - 公司 upsert: 已存在的公司会自动补全空字段(industry/website 等)

    ⚠️ 注意: 数据导入要时间, 直接同步执行会让请求阻塞。
       用 BackgroundTasks 在后台跑, 接口立即返回"导入中"。

    """
    if not _DATA_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据文件不存在, 请先让爬虫把数据放到 db/data/jobs_raw.json",
        )

    # 后台执行真正的导入(不阻塞接口返回)
    # 用闭包封装, 避免 BackgroundTasks 直接持有 db(请求结束 db 会关)
    async def _do_import():
        # 注意: 后台任务必须用新的 session, 不能复用请求的 db
        from app.core.database import AsyncSessionLocal
        with open(_DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        async with AsyncSessionLocal() as task_db:
            await json_to_mysql(data, task_db)

    background_tasks.add_task(_do_import)

    return Result.success(
        data={"status": "importing", "file": _DATA_PATH.name},
        message="导入任务已启动, 后台执行中(约1分钟)",
    )
