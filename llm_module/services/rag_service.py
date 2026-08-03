"""
RAG检索增强服务 - 结合向量检索和大模型生成
"""
from typing import List, Dict, Optional, Any
from services.llm_service import get_llm_service
from services.vector_store import get_vector_store, VectorStore
from utils.logger import get_logger
logger = get_logger("services.rag_service")


class RAGService:
    """RAG检索增强服务 - 支持混合检索、重排序、行业分区"""

    def __init__(self):
        self.llm = get_llm_service()
        self.vector_store = get_vector_store()

    async def add_knowledge_base(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        industry: str = "",
    ) -> List[str]:
        """
        添加知识到知识库

        Args:
            documents: 文档列表
            metadatas: 文档元数据
            industry: 行业标签（用于行业分区）

        Returns:
            文档ID列表
        """
        logger.info(f"添加 {len(documents)} 个文档到知识库{f' (行业: {industry})' if industry else ''}")

        # 注入行业标签到元数据
        if metadatas is None:
            metadatas = [{} for _ in documents]
        for meta in metadatas:
            if industry and "industry" not in meta:
                meta["industry"] = industry

        return self.vector_store.add_documents(documents, metadatas)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索相关知识

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            检索结果
        """
        logger.info(f"检索查询: {query[:50]}...")
        return self.vector_store.search(query, top_k, filter_dict)

    async def generate_answer(
        self,
        question: str,
        context: str,
    ) -> str:
        """
        基于上下文生成答案

        Args:
            question: 问题
            context: 上下文信息

        Returns:
            生成的答案
        """
        prompt = f"""请根据以下上下文回答问题。如果上下文无法回答，请基于你的知识回答。

【上下文】
{context}

【问题】
{question}

请用中文回答，保持简洁专业。"""

        messages = [
            {"role": "system", "content": "你是一位专业的人力资源智能助手。"},
            {"role": "user", "content": prompt},
        ]

        return await self.llm.chat(messages)

    async def query(
        self,
        question: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        完整的RAG查询流程：检索 + 生成

        Args:
            question: 用户问题
            top_k: 检索数量
            filter_dict: 过滤条件

        Returns:
            包含答案和来源的结果
        """
        logger.info(f"RAG查询: {question[:50]}...")

        # 1. 检索相关知识
        retrieved_docs = await self.retrieve(question, top_k, filter_dict)

        if not retrieved_docs:
            logger.warning("未检索到相关知识")
            return {
                "answer": "抱歉，知识库中没有找到相关信息。",
                "sources": [],
                "retrieved_count": 0,
            }

        # 2. 构建上下文
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[{i}] {doc['text']}")

        context = "\n\n".join(context_parts)

        # 3. 生成答案
        answer = await self.generate_answer(question, context)

        # 4. 返回结果
        return {
            "answer": answer,
            "sources": [
                {
                    "id": doc["id"],
                    "text": doc["text"][:200],
                    "metadata": doc.get("metadata", {}),
                    "relevance": 1.0 / (doc.get("distance", 1) + 0.01),
                }
                for doc in retrieved_docs
            ],
            "retrieved_count": len(retrieved_docs),
        }

    async def add_job_descriptions(
        self,
        job_descriptions: List[Dict[str, Any]],
    ) -> List[str]:
        """
        批量添加岗位描述到知识库

        Args:
            job_descriptions: 岗位描述列表
                [{"title": "岗位名", "requirements": "要求", "responsibilities": "职责"}]

        Returns:
            文档ID列表
        """
        documents = []
        metadatas = []

        for jd in job_descriptions:
            # 构建文档文本
            text_parts = []
            if "title" in jd:
                text_parts.append(f"岗位名称: {jd['title']}")
            if "requirements" in jd:
                text_parts.append(f"岗位要求: {jd['requirements']}")
            if "responsibilities" in jd:
                text_parts.append(f"岗位职责: {jd['responsibilities']}")

            if text_parts:
                documents.append("\n".join(text_parts))
                metadatas.append({
                    "type": "job_description",
                    "title": jd.get("title", ""),
                    "source": jd.get("source", "unknown"),
                })

        if documents:
            return await self.add_knowledge_base(documents, metadatas)
        return []

    async def add_skill_definitions(
        self,
        skills: List[Dict[str, Any]],
    ) -> List[str]:
        """
        批量添加技能定义到知识库

        Args:
            skills: 技能定义列表
                [{"name": "技能名", "description": "描述", "category": "类别"}]

        Returns:
            文档ID列表
        """
        documents = []
        metadatas = []

        for skill in skills:
            text_parts = []
            if "name" in skill:
                text_parts.append(f"技能名称: {skill['name']}")
            if "description" in skill:
                text_parts.append(f"技能描述: {skill['description']}")
            if "category" in skill:
                text_parts.append(f"技能类别: {skill['category']}")

            if text_parts:
                documents.append("\n".join(text_parts))
                metadatas.append({
                    "type": "skill_definition",
                    "name": skill.get("name", ""),
                    "category": skill.get("category", ""),
                })

        if documents:
            return await self.add_knowledge_base(documents, metadatas)
        return []

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计"""
        return self.vector_store.get_stats()

    # ========== 混合检索 ==========

    async def hybrid_retrieve(self, query: str, top_k: int = 5,
                               industry: str = "") -> List[Dict[str, Any]]:
        """
        混合检索：向量检索 + 关键词检索 + 图谱检索融合

        Args:
            query: 查询文本
            top_k: 返回结果数量
            industry: 行业过滤

        Returns:
            融合后的检索结果
        """
        results = []

        # 1. 向量检索
        filter_dict = {"industry": industry} if industry else None
        vector_results = await self.retrieve(query, top_k=top_k * 2, filter_dict=filter_dict)
        for r in vector_results:
            r["_source"] = "vector"
            r["_score"] = 1.0 / (r.get("distance", 1) + 0.01)
        results.extend(vector_results)

        # 2. 关键词检索（数据库）
        try:
            from services.db_service import get_db_service
            db = get_db_service()
            # 从技能库中关键词搜索
            keywords = query.split()[:3]  # 简单分词
            for kw in keywords:
                if len(kw) >= 2:
                    skills = db.search_skills(keyword=kw, limit=3)
                    for skill in skills:
                        results.append({
                            "id": f"skill_{skill.get('id', '')}",
                            "text": f"{skill.get('name', '')}: {skill.get('description', '')}",
                            "metadata": {
                                "type": "skill",
                                "category": skill.get("category", ""),
                            },
                            "_source": "keyword",
                            "_score": 0.5,  # 关键词检索默认中等分数
                        })
        except Exception as e:
            logger.debug(f"关键词检索跳过: {e}")

        # 3. 图谱检索
        try:
            from services.neo4j_service import get_neo4j_service
            neo4j = get_neo4j_service()
            if neo4j.is_connected():
                # 提取查询中的实体名（简单启发式）
                entity_results = neo4j.find_neighbors(query, depth=1)
                if isinstance(entity_results, dict):
                    neighbors = entity_results.get("neighbors", [])
                    if isinstance(neighbors, list):
                        for neighbor in neighbors[:3]:
                            if isinstance(neighbor, dict):
                                results.append({
                                    "id": f"graph_{neighbor.get('name', '')}",
                                    "text": f"{neighbor.get('name', '')} ({neighbor.get('type', '')}): {neighbor.get('description', '')}",
                                    "metadata": {"type": "graph", "source": "neo4j"},
                                    "_source": "graph",
                                    "_score": 0.7,
                                })
        except Exception as e:
            logger.debug(f"图谱检索跳过: {e}")

        # 去重（按文本相似度）
        seen_texts = set()
        unique_results = []
        for r in results:
            text_key = r.get("text", "")[:50]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_results.append(r)

        return unique_results[:top_k]

    # ========== 重排序 ==========

    async def rerank(self, query: str, documents: List[Dict[str, Any]],
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """
        LLM重排序 - 用LLM对检索结果重排序，提升相关性

        Args:
            query: 查询文本
            documents: 待排序文档列表
            top_k: 返回Top-K结果

        Returns:
            重排序后的文档列表
        """
        if not documents or len(documents) <= 1:
            return documents[:top_k]

        # 构建重排序prompt
        doc_list = "\n".join(
            f"[{i+1}] {doc.get('text', '')[:100]}"
            for i, doc in enumerate(documents[:10])  # 最多重排序10条
        )

        prompt = f"""请根据与查询的相关性，对以下文档重新排序。最相关的排最前。

查询: {query}

文档列表:
{doc_list}

请以JSON格式回复排序结果，只包含文档编号:
{{"ranking": [最相关文档编号, 次相关文档编号, ...]}}"""

        try:
            result = await self.llm.extract_json(
                prompt,
                task_type="intent_classification",
            )
            ranking = result.get("ranking", [])

            # 按LLM排序重排
            reordered = []
            for idx in ranking:
                idx_int = int(idx) - 1
                if 0 <= idx_int < len(documents):
                    doc = documents[idx_int].copy()
                    doc["reranked"] = True
                    reordered.append(doc)

            # 添加未排到的文档
            ranked_indices = set(int(idx) - 1 for idx in ranking)
            for i, doc in enumerate(documents):
                if i not in ranked_indices:
                    reordered.append(doc)

            return reordered[:top_k]

        except Exception as e:
            logger.warning(f"重排序失败，使用原始排序: {e}")
            return documents[:top_k]

    # ========== 检索质量评估 ==========

    def assess_retrieval_quality(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估检索质量

        Returns:
            {avg_relevance, score_distribution, quality_level, suggestion}
        """
        if not results:
            return {
                "avg_relevance": 0.0,
                "score_distribution": {},
                "quality_level": "empty",
                "suggestion": "无检索结果，可能需要扩充知识库",
            }

        scores = [r.get("_score", r.get("relevance", 0.5)) for r in results]
        avg = sum(scores) / len(scores) if scores else 0

        # 分数分布
        high = sum(1 for s in scores if s >= 0.7)
        medium = sum(1 for s in scores if 0.3 <= s < 0.7)
        low = sum(1 for s in scores if s < 0.3)

        quality_level = "high" if avg >= 0.7 else ("medium" if avg >= 0.4 else "low")
        suggestion = {
            "high": "检索质量良好",
            "medium": "检索质量中等，可尝试混合检索或重排序",
            "low": "检索质量较差，建议扩充知识库或优化查询",
        }.get(quality_level, "")

        return {
            "avg_relevance": round(avg, 3),
            "result_count": len(results),
            "score_distribution": {"high": high, "medium": medium, "low": low},
            "quality_level": quality_level,
            "suggestion": suggestion,
        }

    # ========== 增量更新 ==========

    async def incremental_update(self, documents: List[str],
                                 metadatas: Optional[List[Dict[str, Any]]] = None,
                                 industry: str = "") -> Dict[str, Any]:
        """
        增量更新知识库 - 添加新文档而不重建索引

        Returns:
            {added_count, total_count}
        """
        ids = await self.add_knowledge_base(documents, metadatas, industry=industry)
        stats = self.get_stats()

        return {
            "added_count": len(ids),
            "total_count": stats.get("document_count", 0),
            "using_chromadb": stats.get("using_chromadb", False),
        }

    # ========== 优化查询流程 ==========

    async def enhanced_query(self, question: str, top_k: int = 5,
                             industry: str = "", use_rerank: bool = True) -> Dict[str, Any]:
        """
        增强RAG查询流程：混合检索 + 重排序 + 质量评估

        Args:
            question: 用户问题
            top_k: 返回结果数量
            industry: 行业过滤
            use_rerank: 是否使用重排序

        Returns:
            {answer, sources, retrieval_quality, retrieved_count}
        """
        logger.info(f"增强RAG查询: {question[:50]}...")

        # 1. 混合检索
        retrieved_docs = await self.hybrid_retrieve(question, top_k=top_k * 2, industry=industry)

        if not retrieved_docs:
            return {
                "answer": "抱歉，知识库中没有找到相关信息。",
                "sources": [],
                "retrieval_quality": self.assess_retrieval_quality(question, []),
                "retrieved_count": 0,
            }

        # 2. 重排序（可选）
        if use_rerank and len(retrieved_docs) > 1:
            retrieved_docs = await self.rerank(question, retrieved_docs, top_k=top_k)

        # 3. 检索质量评估
        quality = self.assess_retrieval_quality(question, retrieved_docs)

        # 4. 构建上下文
        context_parts = []
        for i, doc in enumerate(retrieved_docs[:top_k], 1):
            context_parts.append(f"[{i}] {doc.get('text', '')}")

        context = "\n\n".join(context_parts)

        # 5. 生成答案
        answer = await self.generate_answer(question, context)

        return {
            "answer": answer,
            "sources": [
                {
                    "id": doc.get("id", ""),
                    "text": doc.get("text", "")[:200],
                    "metadata": doc.get("metadata", {}),
                    "relevance": doc.get("_score", doc.get("relevance", 0.5)),
                    "source_type": doc.get("_source", "vector"),
                }
                for doc in retrieved_docs[:top_k]
            ],
            "retrieval_quality": quality,
            "retrieved_count": len(retrieved_docs),
        }


# 单例
_rag_service: Any = None


def get_rag_service() -> RAGService:
    """获取RAG服务单例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
