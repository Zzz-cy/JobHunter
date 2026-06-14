"""
启动脚本

用法:
    到backend目录下 python run.py
"""
import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,  # 开发期 true, 生产 false
        log_level="debug" if settings.APP_DEBUG else "info",
    )
