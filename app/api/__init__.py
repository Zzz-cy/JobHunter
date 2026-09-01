"""API 路由聚合包: 各模块的 router 统一收集到 routers, main.py 循环挂载。"""
from app.api.auth import router as auth_router
from app.api.crawl import router as crawl_router
from app.api.jobs import router as jobs_router
from app.api.recommend import router as recommend_router
from app.api.resumes import router as resumes_router
from app.api.user import router as user_router
from app.api.stats import router as stats_router
from app.api.job_definitions import router as job_definitions_router
from app.api.knowledge_graph import router as knowledge_graph_router

# 所有需要挂载的 router 统一放这, 顺序就是 /docs 文档里的展示顺序
routers = [
    auth_router,
    jobs_router,
    resumes_router,
    user_router,
    crawl_router,
    stats_router,
    job_definitions_router,
    knowledge_graph_router,
    recommend_router,
]
__all__ = ["routers"]
