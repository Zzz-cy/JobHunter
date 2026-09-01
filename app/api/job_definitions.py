"""新岗位发现与定义接口。"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import Result
from app.services import job_definition_service as svc
from app.utils.jwtUtil import require_admin

router = APIRouter(prefix="/job-definitions", tags=["新岗位发现"])


@router.get("", response_model=Result[dict], summary="岗位定义列表+发现进度")
async def list_job_definitions(db: AsyncSession = Depends(get_db)):
    """列表 + 发现任务进度(运行中前端每 5 秒轮询本接口)。"""
    state = svc.get_discover_status()
    items = await svc.list_definitions(db)
    return Result.success(data={
        "running": state["running"],
        "message": state["message"],
        "total": state["total"],
        "done": state["done"],
        "failed": state["failed"],
        "items": items,
    })


@router.post("/discover", response_model=Result[dict], summary="触发新岗位发现(管理员)")
async def discover_jobs(
    background_tasks: BackgroundTasks,
    _=Depends(require_admin),
):
    """LLM 后台执行立即返回: 归纳岗位名 → 逐个生成画像。"""
    if svc.get_discover_status()["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="发现任务正在进行中, 请等完成后再触发",
        )
    background_tasks.add_task(svc.run_discovery)
    return Result.success(
        data=svc.get_discover_status(),
        message="新岗位发现已启动(约1-2分钟)",
    )


@router.put("/{def_id}", response_model=Result[dict], summary="人工修改岗位定义(管理员)")
async def update_job_definition(
    def_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """人工修改后标 manual, 之后的重新发现不覆盖该条。

    body: {"definition": {"core_duties": [...], "must_skills": [...],
                          "plus_skills": [...], "industries": [...]}}
    """
    definition = payload.get("definition")
    if not isinstance(definition, dict):
        raise HTTPException(status_code=400, detail="definition 不能为空")
    out = await svc.update_definition(db, def_id, definition)
    return Result.success(data=out, message="已保存为人工定义, 重新发现不会覆盖")
