"""
岗位推荐 API 路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.schemas import Result
from app.schemas.recommend import RecommendOut
from app.services.recommend_service import recommend as recommend_service
from app.utils.jwtUtil import get_current_user

router = APIRouter(prefix="/recommend", tags=["推荐"])


@router.get("", response_model=Result[RecommendOut], summary="根据简历推荐岗位")
async def get_recommend(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    根据指定简历推荐匹配岗位，必须登录。
    """
    result = await recommend_service(
        resume_id=resume_id,
        user_id=current_user.id,
        db=db,
    )
    return Result.success(data=result)
