from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import Result, PageResult, JobSearchSchema, JobOut
from app.services.jobs_service import query
from app.utils.jwtUtil import get_current_user

# 加上属性所有API都要登录才能访问 dependencies=[Depends(get_current_user)]
router = APIRouter(prefix="/jobs", tags=["工作"])

@router.get("/page", response_model=Result[PageResult[JobOut]])
async def get_page(job: JobSearchSchema = Depends(), db: AsyncSession = Depends(get_db)):
    """
    职位搜索(分页)。
    service 返回 (jobs, total), 这里拆开包装成 PageResult。
    """
    jobs, total = await query(job, db)
    items = [JobOut.model_validate(j) for j in jobs]
    page_result = PageResult(items=items, total=total, page=job.page, page_size=job.page_size)
    return Result.success_page(page_result)
