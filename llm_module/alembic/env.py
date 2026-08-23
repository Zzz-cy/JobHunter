"""
Alembic 环境配置 - 支持MySQL/SQLite自动切换

使用方式：
- 自动迁移: alembic upgrade head
- 生成迁移: alembic revision --autogenerate -m "description"
- 回滚: alembic downgrade -1
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 将项目根目录添加到sys.path，以便导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 动态设置数据库URL：优先使用环境变量，否则根据项目配置
database_url = os.getenv("DATABASE_URL", "")
if not database_url:
    try:
        from utils.config import MYSQL_CONFIG, SQLITE_PATH
        # 尝试MySQL
        try:
            import pymysql
            database_url = (
                f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
                f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
            )
        except ImportError:
            # 回退到SQLite
            database_url = f"sqlite:///{SQLITE_PATH}"
    except Exception:
        # 默认SQLite
        database_url = "sqlite:///data/job_competency.db"

config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
# for 'autogenerate' support
# 注意：由于本项目使用手动DDL（db_service.py），这里设为None
# 如需autogenerate，需定义SQLAlchemy模型并设置target_metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
