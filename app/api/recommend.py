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
    """根据指定简历推荐匹配岗位。

    阶段③: 纯 SQL 技能匹配(strategy="skill")
    阶段④⑤ 会逐步接入向量召回 + LLM 重排, 但本路由签名不变, 前端无感升级。

    Query 参数:
        resume_id: 用哪份简历做推荐(必填)

    鉴权:
        必须登录(token 解析出 current_user);
        service 层会校验该简历是否属于 current_user, 防越权用别人简历推。
    """
    result = await recommend_service(
        resume_id=resume_id,
        user_id=current_user.id,
        db=db,
    )
    return Result.success(data=result)
