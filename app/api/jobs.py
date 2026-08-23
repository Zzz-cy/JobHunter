from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models import Job, Industry, Skill, Application, JobSkill
from app.schemas import Result, PageResult, JobSearchSchema, JobOut
from app.schemas.jobs import JobDetailOut, IndustryOut
from app.services.jobs_service import query, favorite_job, unfavorite_job, submit_application, find_similar_jobs
from app.utils.jwtUtil import get_current_user

# 加上属性所有API都要登录才能访问 dependencies=[Depends(get_current_user)]
router = APIRouter(prefix="/jobs", tags=["工作"])


@router.get("/page", response_model=Result[PageResult[JobOut]], summary="工作的分页查询")
async def get_page(job: JobSearchSchema = Depends(), db: AsyncSession = Depends(get_db)):
    """
    职位搜索(分页)。
    """
    jobs, total = await query(job, db)
    items = [JobOut.model_validate(j) for j in jobs]
    page_result = PageResult(items=items, total=total, page=job.page, page_size=job.page_size)
    return Result.success_page(page_result)


@router.get("/industries", response_model=Result[List[IndustryOut]], summary="行业字典")
async def get_industries(db: AsyncSession = Depends(get_db)):
    stmt = select(Industry)
    industries = (await db.scalars(stmt)).all()
    if not industries:
        raise NotFoundError("没有行业")
    out = [IndustryOut.model_validate(i) for i in industries]
    return Result.success(data=out)


@router.get("/hot-keywords", response_model=Result[List[str]], summary="热门搜索词")
async def get_hot_keywords(db: AsyncSession = Depends(get_db)):
    """热门搜索词(来自 skills 字典表的 is_hot 字段)。"""
    stmt = select(Skill.name).where(Skill.is_hot == 1).limit(10)
    result = await db.scalars(stmt)
    keywords = result.all()
    return Result.success(data=keywords)


@router.get("/hot", response_model=Result[List[JobOut]], summary="热门职位(首页用)")
async def get_hot_jobs(db: AsyncSession = Depends(get_db)):
    """首页"热门职位"数据。

    用"最新发布 + 薪资较高"近似热门:
    """
    stmt = (
        select(Job)
        .where(
            Job.status == "active",
            Job.is_deleted == 0,
            Job.publish_at.is_not(None),
        )
        .order_by(Job.publish_at.desc())
        .limit(6)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().unique().all()
    out = [JobOut.model_validate(j) for j in jobs]
    return Result.success(data=out)


@router.get("/{job_id}", response_model=Result[JobDetailOut], summary="通过job_id职位详情")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """职位详情。

    查不到抛 NotFoundError。
    """
    stmt = select(Job).where(Job.id == job_id)
    job = await db.scalar(stmt)
    if job is None:
        raise NotFoundError(f"职位不存在: id={id}")
    out = JobDetailOut.model_validate(job)
    return Result.success(data=out)


@router.post("/applications/{job_id}/favorite", response_model=Result, summary="收藏职位")
async def favorite_job_api(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await favorite_job(job_id, db, current_user.id)
    return Result.success(message="已收藏")


@router.delete("/applications/{job_id}/favorite", response_model=Result, summary="取消收藏")
async def unfavorite_job_api(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await unfavorite_job(job_id, db, current_user.id)
    return Result.success(message="已取消收藏")


@router.post("/applications/{job_id}/submit", response_model=Result, summary="已投递")
async def submit_application_api(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """
    把这个职位的 status 设为 submitted,记录进求职进度。
    """
    await submit_application(job_id, db, current_user.id)
    return Result.success(message="已记录投递")


@router.get("/applications/favorite-ids", response_model=Result[List[int]], summary="我收藏的职位id列表")
async def get_favorite_ids(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """查当前用户收藏的职位 id 列表(只返回 id)。

    供前端进详情页时判断"这个职位我收没收藏"。
    """
    stmt = select(Application.job_id).where(
        Application.user_id == current_user.id,
        Application.is_favorited == 1,      # 改用独立的收藏维度字段
        Application.is_deleted == 0,
    )
    # 注意:AsyncSession 没有 await db.scalars(),要用 db.execute() + .scalars()
    result = await db.execute(stmt)
    ids = result.scalars().all()
    return Result.success(data=ids)


@router.get("/applications/applied-ids", response_model=Result[List[int]], summary="我已投递的职位id列表")
async def get_applied_ids(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """查当前用户已投递的职位 id 列表(只返回 id)。

    供前端进详情页时判断"这个职位我投没投过"。
    投递的判定:status 不为 None(纯收藏 status=None 不算投递)。
    """
    stmt = select(Application.job_id).where(
        Application.user_id == current_user.id,
        Application.status.is_not(None),    # 只看真正投递过的
        Application.is_deleted == 0,
    )
    result = await db.execute(stmt)
    ids = result.scalars().all()
    return Result.success(data=ids)


@router.get("/{job_id}/similar", response_model=Result[List[JobOut]], summary="相似职位推荐")
async def similar_jobs(job_id: int, db: AsyncSession = Depends(get_db)):
    """找和当前职位技能最相似的职位(按技能重叠数排序)。"""
    result = await find_similar_jobs(db, job_id)
    out = [JobOut.model_validate(j) for j in result]
    return Result.success(data=out)

