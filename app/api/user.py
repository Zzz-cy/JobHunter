from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models import User, Application, Job
from app.schemas import Result, UserOut, JobOut
from app.schemas.user import UserUpdateSchema, applicationOut, applicationSchema
from app.services.user_service import update_user, seek_favorites
from app.utils.jwtUtil import get_current_user

router = APIRouter(prefix="/user", tags=["用户接口"])


@router.put("/update", response_model=Result, summary="更新当前用户信息")
async def change_user(
        user: UserUpdateSchema,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_current_user)
):
    await update_user(user,db,current_user.id)
    return Result.success(message="资料更新成功")

@router.get("/me", response_model=Result[UserOut], summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return Result.success(data=UserOut.model_validate(current_user))

@router.get("/applications/favorites", response_model=Result[list[JobOut]], summary="获取当前用户收藏的职位")
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户收藏的职位列表。
    """
    jobs = await seek_favorites(current_user.id,db)
    out = [JobOut.model_validate(j) for j in jobs]
    return Result.success(data=out)

@router.get("/applications", response_model=Result[list[applicationOut]], summary="获取当前用户求职进度")
async def get_applications(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    """获取当前用户的求职进度(投递记录)。

    只返回真正投递过的职位(status 不为 None),
    纯收藏(status=None + is_favorited=1)在"我的收藏"接口展示。
    """
    stmt = select(Application).where(
        Application.user_id == current_user.id,
        Application.is_deleted == 0,                  # 过滤软删除
        Application.status.is_not(None),              # 只看投递过的(有 status)
    )
    result = await db.execute(stmt)
    applications = result.scalars().all()    # 列表(可能为空 [])
    out = [applicationOut.model_validate(a) for a in applications]
    return Result.success(data=out)

@router.put("/update_application", response_model=Result, summary="修改当前用户求职进度")
async def update_application(application: applicationSchema, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Application).where(
        Application.user_id == current_user.id,
        Application.job_id == application.job_id,
        Application.is_deleted == 0)
    result = await db.scalar(stmt)
    if not result:
        raise NotFoundError("不存在")
    if bool(application.status):
        result.status = application.status
    if bool(application.note):
        result.note = application.note
    else:
        result.note = None
    await db.commit()
    return Result.success()

@router.delete("/delete_application/{job_id}", response_model=Result, summary="删除对应求职进度")
async def delete_application(job_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Application).where(
        Application.user_id == current_user.id,
        Application.job_id == job_id,
        Application.is_deleted == 0)
    application = await db.scalar(stmt)
    if not application:
        raise NotFoundError("不存在")
    if application.is_favorited == 0:
        application.is_deleted = 1
    else:
        application.status = None
    await db.commit()
    return Result.success()



