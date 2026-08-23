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

    # ---------- 文件上传 ----------
    UPLOAD_DIR: str = Field(default="uploads", description="文件上传根目录(相对 backend/)")
    RESUME_MAX_SIZE_MB: int = Field(default=10, description="简历文件大小上限(MB)")

    # ---------- LLM 简历解析服务 ----------
    # 同机部署, 直接传本地文件路径给 LLM, LLM 读文件解析返回 JSON
    LLM_SERVICE_URL: str = Field(
        default="http://localhost:8001",
        description="LLM 简历解析服务地址(队友的端口, 联调时确认)",
    )
    LLM_PARSE_TIMEOUT: int = Field(
        default=120,
        description="LLM 解析超时(秒), AI 解析慢要给足",
    )

    # ---------- 智谱 GLM(岗位推荐功能专用) ----------
    # 直连智谱 GLM: embedding-3 向量化(建库+召回) + glm-4-flash 对话(LLM重排/推荐理由)
    ZHIPU_API_KEY: str = Field(default="", description="智谱开放平台 API Key")
    ZHIPU_BASE_URL: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/",
        description="智谱 API 基址(默认官方, 可换私有化部署地址)",
    )
    ZHIPU_CHAT_MODEL: str = Field(default="glm-4-flash", description="对话模型(flash 免费且快)")
    ZHIPU_EMBED_MODEL: str = Field(default="embedding-3", description="向量模型")
    ZHIPU_EMBED_DIM: int = Field(default=2048, description="embedding-3 默认输出维度")
    ZHIPU_TIMEOUT: int = Field(default=60, description="GLM API 超时(秒)")

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

    @property
    def CHROMA_PATH(self) -> Path:
        """ChromaDB 文件型向量库的持久化目录(相对 backend/)。

        用 Path 而非 str: 方便调用方直接 .mkdir(parents=True) 建目录。
        不写绝对路径: 跟着 BASE_DIR 走, 项目移动后自动适配。
        """
        return BASE_DIR / "storage" / "chroma"


@lru_cache
def get_settings() -> Settings:
    """单例缓存，避免每次访问都重新读 .env。"""
    return Settings()


# 全局可直接导入的配置实例
settings = get_settings()
