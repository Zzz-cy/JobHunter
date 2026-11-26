from sqlalchemy import update, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ParamError
from app.models import User, Application, Job
from app.schemas.user import UserUpdateSchema, OnboardingSchema, AdminUserQuery
from app.utils.pwdUtil import hash_password, verify_password


async def complete_onboarding(
        data: OnboardingSchema,
        db: AsyncSession,
        user_id: int
) -> User:
    """首登引导建档: 写入期望三项并置 onboarded 标记(每账号仅一次)。"""
    user_obj = await db.get(User, user_id)
    if not user_obj:
        raise ParamError("用户不存在")
    if user_obj.onboarded:
        raise ParamError("已完成建档, 不能重复提交")

    user_obj.expected_city = data.expected_city
    user_obj.expected_job = data.expected_job
    user_obj.expected_salary = data.expected_salary
    user_obj.onboarded = 1
    await db.commit()
    await db.refresh(user_obj)
    return user_obj


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


# ============================================================
# 账号管理(管理员)
# ============================================================
async def query_admin_users(
        params: AdminUserQuery,
        db: AsyncSession,
) -> tuple[list[User], int]:
    """按昵称/手机号模糊搜索的用户分页列表(排除软删除), 返回 (当前页, 总数)。"""
    conditions = [User.is_deleted == 0]
    if params.keyword:
        kw = f"%{params.keyword.strip()}%"
        conditions.append(or_(User.nickname.like(kw), User.phone.like(kw)))

    total = await db.scalar(select(func.count()).select_from(User).where(*conditions))
    result = await db.execute(
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc(), User.id.desc())
        .limit(params.page_size)
        .offset(params.offset)
    )
    return list(result.scalars().all()), total or 0


async def _get_active_user(user_id: int, db: AsyncSession) -> User:
    """取未被软删除的目标用户, 不存在则 404。"""
    user_obj = await db.scalar(
        select(User).where(User.id == user_id, User.is_deleted == 0)
    )
    if not user_obj:
        raise NotFoundError("用户不存在")
    return user_obj


async def set_user_role(
        user_id: int,
        role: str,
        db: AsyncSession,
        operator_id: int,
) -> None:
    """设为/收回管理员。不能操作自己(防止自降权限把自己锁在管理端外)。"""
    if user_id == operator_id:
        raise ParamError("不能操作自己的账号")
    user_obj = await _get_active_user(user_id, db)
    user_obj.role = role
    await db.commit()


async def set_user_status(
        user_id: int,
        status: str,
        db: AsyncSession,
        operator_id: int,
) -> None:
    """封禁/解封账号。不能操作自己。"""
    if user_id == operator_id:
        raise ParamError("不能操作自己的账号")
    user_obj = await _get_active_user(user_id, db)
    user_obj.status = status
    await db.commit()
