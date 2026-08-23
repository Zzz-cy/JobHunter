"""
SQLAlchemy 2.0 异步数据库引擎与会话管理

核心组件:
    - engine: 全局唯一的异步引擎(连接池)
    - AsyncSessionLocal: 会话工厂, 每个请求开一个会话
    - get_db: FastAPI 依赖注入函数

用法(FastAPI 路由):
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.get("/users/{user_id}")
    async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
        user = await db.get(User, user_id)
        return user
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ---------- 1. 异步引擎 ----------
# pool_size: 连接池大小
# pool_recycle: 防 MySQL wait_timeout 默认 8h 自动断连
# echo: 是否打印 SQL(开发期调试用)
engine = create_async_engine(
    settings.MYSQL_DSN_ASYNC,
    pool_size=settings.MYSQL_POOL_SIZE,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    echo=settings.MYSQL_ECHO,
    pool_pre_ping=True,  # 每次取连接前 ping 一下, 避免拿到失效连接
)

# ---------- 2. 会话工厂 ----------
# expire_on_commit=False: commit 后对象仍可访问属性(避免 lazy load 报错)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------- 3. FastAPI 依赖注入 ----------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每个请求获取一个独立 Session, 请求结束自动关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # 路由内未显式 commit 时, 由调用方决定; 默认不自动 commit
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
