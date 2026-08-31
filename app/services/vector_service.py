"""ChromaDB 向量库封装: 建库脚本和推荐召回共用。

集合 job_jd: id=str(job_id), document=JD原文, embedding=2048维向量,
metadata={title, city, source}(支持过滤)。
"""
import asyncio

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.llm import embed_batch
from app.schemas.result import BizCode


_COLLECTION_NAME = "job_jd"


@lru_cache
def _get_collection():
    """ChromaDB 集合单例(惰性创建, 不用向量库时不报错)。"""
    try:
        import chromadb
    except ImportError as e:
        raise BizException(
            f"未安装 chromadb, 请执行: pip install chromadb (错误: {e})",
            code=BizCode.SYSTEM_ERROR,
        )

    settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # 余弦相似度
    )


def upsert_jobs(
    job_ids: list[int],
    texts: list[str],
    metadatas: list[dict[str, Any]],
) -> int:
    """批量向量化岗位 JD 并写入向量库(建库用), 同 id 覆盖。

    metadata 的 value 只能是 str/int/float/bool(ChromaDB 限制)。
    返回实际写入条数。
    """
    if not job_ids:
        return 0

    embeddings = embed_batch(texts)

    # 跳过空向量(对应空文本)
    valid_ids, valid_texts, valid_metas, valid_embs = [], [], [], []
    for jid, text, meta, emb in zip(job_ids, texts, metadatas, embeddings):
        if emb:
            valid_ids.append(str(jid))
            valid_texts.append(text)
            valid_metas.append(meta)
            valid_embs.append(emb)

    if not valid_ids:
        return 0

    _get_collection().upsert(
        ids=valid_ids,
        embeddings=valid_embs,
        documents=valid_texts,
        metadatas=valid_metas,
    )
    return len(valid_ids)


def get_existing_ids(job_ids: list[int]) -> set[int]:
    """查哪些 job_id 已在向量库里(增量建库省 embedding 费用)。"""
    if not job_ids:
        return set()
    str_ids = [str(j) for j in job_ids]
    result = _get_collection().get(ids=str_ids, include=[])
    return {int(i) for i in result["ids"]}


def search(
    query_vec: list[float],
    top_k: int = 20,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """向量相似度搜索, 返回 [{job_id, score, title, city}] 按相似度降序。

    cosine distance ∈ [0,2], 换算 score = 1 - distance/2 ∈ [0,1], 越大越像。
    """
    if not query_vec:
        raise BizException("查询向量不能为空", code=BizCode.PARAM_ERROR)

    kwargs: dict[str, Any] = {
        "query_embeddings": [query_vec],
        "n_results": top_k,
        "include": ["metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    raw = _get_collection().query(**kwargs)

    # 外层 list 对应查询次数(只查 1 次, 取 [0])
    ids = raw["ids"][0]
    distances = raw["distances"][0]
    metadatas = raw["metadatas"][0]

    results = []
    for jid, dist, meta in zip(ids, distances, metadatas):
        results.append(
            {
                "job_id": int(jid),
                "score": round(1 - dist / 2, 4),
                "title": meta.get("title"),
                "city": meta.get("city"),
            }
        )
    return results


async def asearch(
    query_vec: list[float],
    top_k: int = 20,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """search 的异步包装(ChromaDB 客户端是同步的, 直接调会阻塞事件循环)。"""
    return await asyncio.to_thread(search, query_vec, top_k, where)
