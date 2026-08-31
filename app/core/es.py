"""
Elasticsearch 客户端
"""
from elasticsearch import Elasticsearch

from app.core.config import settings

JOBS_INDEX = "jobs"

# 本地开发免密直连，生产填.env的ES_USERNAME和ES_PASSWORD
es_client = Elasticsearch(
    settings.ES_URL,
    request_timeout=60,
    retry_on_timeout=True,
    max_retries=3,
)
