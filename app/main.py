"""FastAPI 应用入口。

启动: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
文档: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api import routers
from app.core.config import settings
from app.core.database import engine
from app.core.exception_handlers import register_exception_handlers

# ---------- 启动前准备: 确保上传目录存在 ----------
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期钩子。"""
    print(f"[JobHunter] 启动成功, 环境={settings.APP_ENV}")
    print(f"[JobHunter] MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    print(f"[JobHunter] ES:     {settings.ES_URL}")

    yield  # 之前启动逻辑，之后关闭逻辑。

    # 关闭时, 释放连接池
    await engine.dispose()
    print("[JobHunter] 已关闭, 连接池已释放")


app = FastAPI(
    title="JobHunter API",
    description="智能招聘平台后端",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------- 路由挂载 ----------
# 从 api 包统一收集所有 router, 循环挂载。
# 新增路由模块只改 app/api/__init__.py, 这里不用动。
for _router in routers:
    app.include_router(_router)

# ---------- 全局异常处理器 ----------
# 把 BizException / 参数校验错误 / 未预期异常 都转成统一 Result 格式。
# 必须在路由挂载之后注册。
register_exception_handlers(app)


@app.get("/health", tags=["系统"])
async def health():
    """健康检查接口。"""
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "service": "jobhunter-backend",
    }

