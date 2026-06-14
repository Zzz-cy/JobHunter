"""
应用配置中心

通过 pydantic-settings 从 .env 文件读取环境变量，
代码中不出现任何明文密码/密钥。

用法:
    from app.core.config import settings
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 根目录(无论从哪里运行都能找到 .env)
# __file__ 是 config.py 自己, 向上 3 层: config.py -> core -> app -> backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """全局配置，所有字段从 .env 自动加载。"""

    # ---------- Pydantic 配置 ----------
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),     # 用绝对路径, 不受 CWD 影响
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- App ----------
    APP_ENV: str = Field(default="dev", description="运行环境: dev/prod")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    APP_DEBUG: bool = Field(default=True)

    JWT_SECRET_KEY: str = Field(default="dev-secret-change-me")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=10080, description="Token 过期时间(分钟), 默认 7 天")

    # ---------- MySQL ----------
    MYSQL_HOST: str = Field(default="127.0.0.1")
    MYSQL_PORT: int = Field(default=3306)
    MYSQL_USER: str = Field(default="root")
    MYSQL_PASSWORD: str = Field(default="")
    MYSQL_DATABASE: str = Field(default="jobhunter")
    MYSQL_POOL_SIZE: int = Field(default=10)
    MYSQL_POOL_RECYCLE: int = Field(default=3600, description="连接回收时间(秒), 防 MySQL 8h 超时")
    MYSQL_ECHO: bool = Field(default=False, description="是否打印 SQL(开发期可开启)")

    # ---------- Elasticsearch ----------
    ES_URL: str = Field(default="http://127.0.0.1:9200")
    ES_USERNAME: str = Field(default="elastic")
    ES_PASSWORD: str = Field(default="")
    ES_VERIFY_CERTS: bool = Field(default=False)

    # ---------- Neo4j ----------
    NEO4J_URI: str = Field(default="bolt://127.0.0.1:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="")

    # ---------- 讯飞星火 ----------
    SPARK_APP_ID: str = Field(default="")
    SPARK_API_KEY: str = Field(default="")
    SPARK_API_SECRET: str = Field(default="")

    # ---------- 派生属性 ----------
    @property
    def MYSQL_DSN_ASYNC(self) -> str:
        """aiomysql 异步连接串。"""
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    @property
    def MYSQL_DSN_SYNC(self) -> str:
        """PyMySQL 同步连接串(脚本用)。"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """单例缓存，避免每次访问都重新读 .env。"""
    return Settings()


# 全局可直接导入的配置实例
settings = get_settings()
