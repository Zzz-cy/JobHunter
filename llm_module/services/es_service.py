"""
Elasticsearch服务 - 全文搜索引擎
支持岗位、技能等数据的快速检索
"""
from typing import List, Dict, Optional, Any

from utils.config import ES_CONFIG
from utils.logger import get_logger
logger = get_logger("services.es_service")

# 尝试导入Elasticsearch
try:
    from elasticsearch import Elasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    logger.warning("elasticsearch未安装，搜索功能将使用内存索引")


class ElasticSearchService:
    """Elasticsearch搜索服务"""

    def __init__(self):
        self.client = None
        self.index_name = ES_CONFIG["index_name"]

        if ES_AVAILABLE:
            try:
                self.client = Elasticsearch(ES_CONFIG["hosts"])
                if self.client.ping():
                    logger.info(f"Elasticsearch连接成功: {ES_CONFIG['hosts']}")
                    self._create_index()
                else:
                    logger.warning("Elasticsearch连接失败")
                    self.client = None
            except Exception as e:
                logger.warning(f"Elasticsearch初始化失败: {e}")
                self.client = None

        # 内存索引（ES不可用时使用）
        self.memory_index: Dict[str, Dict] = {}

    def _create_index(self):
        """创建索引"""
        if not self.client:
            return

        try:
            # 检查索引是否存在
            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(
                    index=self.index_name,
                    body={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "analysis": {
                                "analyzer": {
                                    "ik_max_word": {
                                        "type": "custom",
                                        "tokenizer": "ik_max_word"
                                    }
                                }
                            }
                        },
                        "mappings": {
                            "properties": {
                                "title": {"type": "text", "analyzer": "ik_max_word"},
                                "content": {"type": "text", "analyzer": "ik_max_word"},
                                "category": {"type": "keyword"},
                                "tags": {"type": "keyword"},
                                "source": {"type": "keyword"},
                                "created_at": {"type": "date"},
                            }
                        }
                    }
                )
                logger.info(f"索引创建成功: {self.index_name}")
        except Exception as e:
            logger.warning(f"索引创建失败: {e}")

    def index_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """
        索引文档

        Args:
            doc_id: 文档ID
            document: 文档内容

        Returns:
            是否成功
        """
        if self.client:
            try:
                self.client.index(index=self.index_name, id=doc_id, body=document)
                return True
            except Exception as e:
                logger.warning(f"ES索引失败: {e}")

        # 回退到内存索引
        self.memory_index[doc_id] = document
        return True

    def search(self, query: str, filters: Optional[Dict] = None,
               size: int = 10) -> List[Dict]:
        """
        搜索文档

        Args:
            query: 搜索关键词
            filters: 过滤条件
            size: 返回数量

        Returns:
            搜索结果列表
        """
        if self.client:
            try:
                body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "content", "tags"],
                        }
                    },
                    "size": size,
                }

                if filters:
                    body["query"] = {
                        "bool": {
                            "must": body["query"],
                            "filter": [
                                {"term": {k: v}} for k, v in filters.items()
                            ]
                        }
                    }

                result = self.client.search(index=self.index_name, body=body)
                return [hit["_source"] for hit in result["hits"]["hits"]]
            except Exception as e:
                logger.warning(f"ES搜索失败: {e}")

        # 回退到内存搜索
        results = []
        query_lower = query.lower()
        for doc_id, doc in self.memory_index.items():
            title = doc.get("title", "")
            content = doc.get("content", "")
            if query_lower in title.lower() or query_lower in content.lower():
                results.append(doc)

        return results[:size]

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """获取文档"""
        if self.client:
            try:
                result = self.client.get(index=self.index_name, id=doc_id)
                return result["_source"]
            except Exception as e:
                logger.warning(f"ES获取文档失败: {e}")

        return self.memory_index.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if self.client:
            try:
                self.client.delete(index=self.index_name, id=doc_id)
                return True
            except Exception as e:
                logger.warning(f"ES删除文档失败: {e}")

        if doc_id in self.memory_index:
            del self.memory_index[doc_id]
            return True

        return False


# 单例
_es_service: Any = None


def get_es_service() -> ElasticSearchService:
    """获取ES服务单例"""
    global _es_service
    if _es_service is None:
        _es_service = ElasticSearchService()
    return _es_service
