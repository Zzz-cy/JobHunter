"""SQLAlchemy 2.0 异步数据库引擎与会话管理。

engine 全局唯一(连接池), AsyncSessionLocal 会话工厂, get_db 供路由依赖注入。
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
    pool_pre_ping=True,
)

# 2. 会话工厂
# expire_on_commit=False: commit 后对象仍可访问属性(避免 lazy load 报错)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# astAPI 依赖注入
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每个请求获取一个独立 Session, 请求结束自动关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
