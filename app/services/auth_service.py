from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ParamError, NotFoundError
from app.models import User
from app.schemas import RegisterSchema, LoginSchema, UserOut, LoginOut
from app.utils.jwtUtil import create_access_token
from app.utils.pwdUtil import hash_password, verify_password
from app.utils.codeUtil import generate_code


async def register(payload: RegisterSchema, db: AsyncSession):
    """
        - 入参 RegisterSchema 已校验: 手机号/邮箱格式、密码长度、至少传一个账号
        - 这里只校验"账号是否已存在"(数据库唯一性)
        - 注册成功只返回提示, 不返回用户信息(注册不等于登录)
    """
    conditions = []
    if payload.phone:
        conditions.append(User.phone == payload.phone)
    if payload.email:
        conditions.append(User.email == payload.email)

    existing = await db.scalar(select(User).where(or_(*conditions)))
    if existing:
        raise ConflictError("手机号或邮箱已注册")

    new_user = User(
        user_code=generate_code("U"),  # 统一用 codeUtil 生成(前缀 U + 日期 + 秒数 + 8位随机)
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),  # 存 hash, 不存明文
        nickname=payload.nickname,
        avatar_url=payload.avatar_url,
        role="user",  # 固定 user, 不让前端传 admin
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)  # 拿到自增 id 和数据库默认值


async def login(user: LoginSchema, db: AsyncSession):
    """
    接收邮箱和手机号登录，返回token和用户信息
    """
    # 1. 校验账号是否为空
    if not user.account:
        raise ParamError("请填写账号")
    # 检查用户是否存在
    conditions = []
    if user.account:
        conditions.append(User.phone == user.account)
        conditions.append(User.email == user.account)

    existing = await db.scalar(select(User).where(or_(*conditions)))
    if not existing:
        raise NotFoundError("用户名或密码错误")
    # 检查密码是否正确
    if not verify_password(user.password, existing.password_hash):
        raise NotFoundError("用户名或密码错误")
    user_out = UserOut.model_validate(existing)

    return LoginOut(
        # jwt,默认一天过期
        # sub 存数字 user.id(数据库主键), 便于跨服务统一用户标识
        # (LLM 服务也用数字 user_id, 两边类型一致才能正确识别用户)
        token=create_access_token(data={"sub": str(existing.id)}),
        user=user_out
    )
