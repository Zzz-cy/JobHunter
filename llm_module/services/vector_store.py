"""
向量数据库服务 - 基于ChromaDB的RAG检索增强
"""
import os
import hashlib
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from utils.logger import get_logger
logger = get_logger("services.vector_store")

# 尝试导入ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB未安装，将使用模拟实现")

from utils.config import VECTOR_DB_CONFIG


@dataclass
class Document:
    """文档数据类"""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class VectorStore:
    """向量数据库服务"""

    def __init__(self):
        self.collection_name = VECTOR_DB_CONFIG["collection_name"]
        self.db_path = VECTOR_DB_CONFIG["path"]
        self.client = None
        self.collection = None
        self._in_memory_store: List[Document] = []  # 内存存储（ChromaDB不可用时使用）

        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(
                    path=self.db_path,
                    settings=Settings(anonymized_telemetry=False),
                )
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "岗位能力知识库"},
                )
                logger.info(f"向量数据库初始化完成: {self.db_path}")
            except Exception as e:
                logger.error(f"ChromaDB初始化失败: {e}，将使用内存存储")
                self.client = None
                self.collection = None
        else:
            logger.warning("ChromaDB不可用，使用内存存储")

    def _generate_id(self, text: str) -> str:
        """为文本生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        添加文档到向量数据库

        Args:
            documents: 文档文本列表
            metadatas: 文档元数据列表
            ids: 文档ID列表

        Returns:
            文档ID列表
        """
        if not documents:
            return []

        # 生成ID
        if ids is None:
            ids = [self._generate_id(doc) for doc in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        # 使用ChromaDB
        if self.collection is not None:
            try:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                )
                logger.info(f"成功添加 {len(documents)} 个文档到向量数据库")
                return ids
            except Exception as e:
                logger.error(f"ChromaDB添加文档失败: {e}")
                # 回退到内存存储
                pass

        # 使用内存存储
        for i, doc_text in enumerate(documents):
            doc = Document(
                id=ids[i],
                text=doc_text,
                metadata=metadatas[i] if i < len(metadatas) else {},
            )
            self._in_memory_store.append(doc)

        logger.info(f"成功添加 {len(documents)} 个文档到内存存储")
        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            检索结果列表
        """
        # 使用ChromaDB
        if self.collection is not None:
            try:
                where_clause = filter_dict if filter_dict else None
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where_clause,
                )

                # 整理结果
                formatted_results = []
                if results and results["ids"]:
                    for i in range(len(results["ids"][0])):
                        formatted_results.append({
                            "id": results["ids"][0][i],
                            "text": results["documents"][0][i] if results["documents"] else "",
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "distance": results["distances"][0][i] if results["distances"] else 0,
                        })
                logger.debug(f"向量检索: query='{query[:50]}', top_k={top_k}, results={len(formatted_results)}")
                return formatted_results
            except Exception as e:
                logger.error(f"ChromaDB查询失败: {e}")
                # 回退到内存存储
                pass

        # 使用内存存储（简单关键词匹配）
        logger.info("使用内存存储进行检索")
        results = []
        query_lower = query.lower()

        for doc in self._in_memory_store:
            # 简单关键词匹配
            score = sum(1 for word in query_lower.split() if word in doc.text.lower())
            if score > 0:
                results.append({
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "distance": 1.0 / (score + 1),
                })

        # 按相关度排序
        results.sort(key=lambda x: x["distance"])
        return results[:top_k]

    def delete_documents(self, ids: List[str]) -> bool:
        """
        删除文档

        Args:
            ids: 要删除的文档ID列表

        Returns:
            是否成功
        """
        if self.collection is not None:
            try:
                self.collection.delete(ids=ids)
                logger.info(f"成功删除 {len(ids)} 个文档")
                return True
            except Exception as e:
                logger.error(f"ChromaDB删除失败: {e}")

        # 从内存中删除
        self._in_memory_store = [
            doc for doc in self._in_memory_store if doc.id not in ids
        ]
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "collection_name": self.collection_name,
            "using_chromadb": self.collection is not None,
        }

        if self.collection is not None:
            try:
                count = self.collection.count()
                stats["document_count"] = count
            except:
                stats["document_count"] = len(self._in_memory_store)
        else:
            stats["document_count"] = len(self._in_memory_store)

        return stats


# 单例
_vector_store: Any = None


def get_vector_store() -> VectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
