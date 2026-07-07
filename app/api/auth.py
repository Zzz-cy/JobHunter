"""
认证相关路由(注册/登录)

"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError, ParamError
from app.models import User
from app.schemas import RegisterSchema, Result, LoginSchema, LoginOut, UserOut
from app.utils.pwdUtil import hash_password, verify_password
from app.utils.jwtUtil import create_access_token

router = APIRouter(prefix="/auth", tags=["认证"])


def generate_user_code() -> str:
    """生成用户编码。

    规律: U + 年月日(8位) + 当日秒数(5位补零)
        例: U20260628 + 45213 → "U2026062845213"

    为啥不用自增 id:
        - 自增 id 会泄露业务量(能猜出注册了多少人)
        - user_code 对外展示, 无规律、不可猜测更安全
    为啥不用纯随机:
        - 纯随机(如 uuid)对人不友好, 没有可读性
        - 带日期前缀方便肉眼识别 + 排序
    并发风险:
        - 同一秒注册会有极小概率撞码(实际几乎不可能)
        - 真要绝对唯一, 可以加 user.id 做后缀, 或在 DB 层加唯一索引兜底
        (User.user_code 已经是 unique=True, 撞了会抛 IntegrityError)
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")  # 20260628
    second_part = f"{now.hour * 3600 + now.minute * 60 + now.second:05d}"  # 00000~86399
    return f"U{date_part}{second_part}"


@router.post("/register", response_model=Result, summary="用户注册")
async def register_user(payload: RegisterSchema, db: AsyncSession = Depends(get_db)):
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
        user_code=generate_user_code(),  # 自动生成, 不信任前端
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

    return Result.success(message="注册成功")


@router.post("/login", response_model=Result[LoginOut],summary="用户登录")
async def login_user(user: LoginSchema, db: AsyncSession = Depends(get_db)):
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
    if  not verify_password(user.password,existing.password_hash):
        raise NotFoundError("用户名或密码错误")
    user_out = UserOut.model_validate(existing)

    return Result.success(data=LoginOut(
        # jwt,默认一天过期
        token=create_access_token(data={"sub": existing.user_code}),
        user=user_out
    ))
