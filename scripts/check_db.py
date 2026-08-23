"""
连接测试脚本

验证:
    1. .env 配置能正确加载
    2. SQLAlchemy 模型与数据库 schema 匹配
    3. 能成功查询 users 表

运行:
    cd backend
    python -m scripts.check_db
"""
import asyncio
import sys
from pathlib import Path

# 把 backend 目录加入 sys.path, 让 import app.* 能找到
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402


async def main() -> None:
    print("==> 1. 测试数据库连接...")
    async with AsyncSessionLocal() as db:
        # 原生 SQL 探活
        result = await db.execute(text("SELECT VERSION(), DATABASE()"))
        row = result.first()
        print(f"   ✓ MySQL 版本: {row[0]}")
        print(f"   ✓ 当前数据库: {row[1]}")

        print("\n==> 2. 测试 ORM 查询 users 表...")
        stmt = select(User).where(User.is_deleted == 0)
        result = await db.execute(stmt)
        users = result.scalars().all()
        print(f"   ✓ 查到 {len(users)} 个用户:")
        for u in users:
            print(f"     - id={u.id} nickname={u.nickname} role={u.role} email={u.email}")

        print("\n==> 3. 测试取一个用户的关联简历(验证 relationship)...")
        if users:
            u = users[0]
            print(f"   用户 {u.nickname!r} 的简历: {len(u.resumes)} 份")
            for r in u.resumes:
                print(f"     - {r.name} (status={r.parse_status})")

    print("\n✅ 全部通过")


async def run() -> None:
    try:
        await main()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
