"""
Elasticsearch 客户端初始化

类比 app/core/database.py(MySQL 的连接), 这是 ES 的连接。
- 全局唯一客户端(连接池), 各 service 直接 import 用
- 同步库(elasticsearch-py 本身线程安全), FastAPI 异步路由里可直接调
  (ES 查询毫秒级, 若以后量大再换 AsyncElasticsearch)

用法:
    from app.core.es import es_client, JOBS_INDEX
    es_client.search(index=JOBS_INDEX, body={...})
"""
from elasticsearch import Elasticsearch

from app.core.config import settings

# 职位索引名(所有操作都用这个常量, 改名只改一处)
JOBS_INDEX = "jobs"

# 本地开发已关闭 xpack 安全认证, 免密直连
# 生产环境要填 .env 的 ES_USERNAME / ES_PASSWORD
# 注意: 8.15 客户端连 9.x 服务端偶发"请求成功但等响应超时", timeout 给大点
es_client = Elasticsearch(
    settings.ES_URL,
    request_timeout=60,
    retry_on_timeout=True,      # 超时自动重试
    max_retries=3,
)
