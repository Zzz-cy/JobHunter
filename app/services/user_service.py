from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ParamError
from app.models import User, Application, Job
from app.schemas.user import UserUpdateSchema
from app.utils.pwdUtil import hash_password, verify_password


async def update_user(
        user: UserUpdateSchema,
        db: AsyncSession,
        user_id: int
):
    has_profile = any([user.nickname, user.phone, user.email])
    has_password = bool(user.old_password) or bool(user.new_password)

    if not has_profile and not has_password:
        return

    if bool(user.old_password) != bool(user.new_password):
        raise ParamError("修改密码时,原密码和新密码必须同时填写")

    user_obj = await db.get(User, user_id)
    if not user_obj:
        raise ParamError("用户不存在")

    if user.old_password and user.new_password:
        if not verify_password(user.old_password, user_obj.password_hash):
            raise ParamError("原密码不正确")
        user_obj.password_hash = hash_password(user.new_password)

    if user.nickname is not None:
        user_obj.nickname = user.nickname

    if user.phone is not None:
        existed = await db.execute(
            select(User).where(User.phone == user.phone, User.id != user_id)
        )
        if existed.scalar_one_or_none():
            raise ParamError("该手机号已被其他账号使用")
        user_obj.phone = user.phone

    if user.email is not None:
        existed = await db.execute(
            select(User).where(User.email == user.email, User.id != user_id)
        )
        if existed.scalar_one_or_none():
            raise ParamError("该邮箱已被其他账号使用")
        user_obj.email = user.email

    await db.commit()

async def seek_favorites(
    user_id: int,
    db: AsyncSession,
):
    fav_stmt = select(Application.job_id).where(
        Application.user_id == user_id,
        Application.is_favorited == 1,
    )
    fav_result = await db.execute(fav_stmt)
    job_ids = fav_result.scalars().all()

    if not job_ids:
        return []
    job_stmt = select(Job).where(
        Job.id.in_(job_ids),
        Job.is_deleted == 0,  # 过滤掉软删除的职位
    )
    job_result = await db.execute(job_stmt)
    return job_result.scalars().all()
