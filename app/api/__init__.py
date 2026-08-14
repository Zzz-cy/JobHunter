"""
API 路由聚合包

每个业务模块(职位/用户/简历/...)各自定义一个 APIRouter,
这里统一收集到 routers 列表, main.py 循环挂载。

新增路由模块时, 只需要:
    1. 新建 app/api/xxx.py, 里面定义 router = APIRouter(...)
    2. 在本文件 import 它, 加进 routers 列表
    3. main.py 不用动!

类比 models/__init__.py 聚合所有 ORM 模型给 alembic 用。
"""
from app.api.auth import router as auth_router
from app.api.crawl import router as crawl_router
from app.api.jobs import router as jobs_router
from app.api.resumes import router as resumes_router
from app.api.user import router as user_router
from app.api.stats import router as stats_router
from app.api.knowledge_graph import router as knowledge_graph_router

# 所有需要挂载的 router 统一放这, 顺序就是 /docs 文档里的展示顺序
routers = [
    auth_router,
    jobs_router,
    resumes_router,
    user_router,
    crawl_router,
    stats_router,
    knowledge_graph_router,
]
__all__ = ["routers"]
