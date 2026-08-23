"""
向量库(ChromaDB)操作封装

职责: 管理 ChromaDB 集合的读写, 给上层(建库脚本 + 推荐召回)一个干净接口。

为什么单独抽一个 service:
    - 阶段②(建库脚本)和阶段④(推荐召回)都要操作 ChromaDB, 共用这里避免重复
    - 把 ChromaDB 的细节(集合名、距离换算、metadata 限制)藏在这里,
      上层只管"存岗位 / 查相似", 不关心向量库怎么实现

ChromaDB 核心概念(类比 MySQL 帮你理解):
    PersistentClient  ≈ 数据库连接(指向一个本地文件夹)
    Collection        ≈ 一张表(这里叫 job_jd, 存所有岗位 JD 的向量)
    collection.upsert ≈ INSERT ... ON DUPLICATE KEY(按 id 覆盖写入)
    collection.query  ≈ ORDER BY 向量距离 LIMIT N(语义相似度搜索)

集合设计(本项目的 job_jd 集合):
    id         = str(job_id)          # 主键, 和 MySQL jobs.id 对应
    document   = JD 文本               # 原文, 便于调试时查看
    embedding  = GLM embedding-3 向量  # 2048 维, 用于相似度计算
    metadata   = {title, city, source} # 标量字段, 支持过滤(如只查某城市)
"""
import asyncio

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.llm import embed_batch
from app.schemas.result import BizCode


# 集合名抽成常量, 避免散落字符串写错
_COLLECTION_NAME = "job_jd"


# ============================================================
# 客户端 & 集合单例
# ============================================================
@lru_cache
def _get_collection():
    """获取 ChromaDB 集合单例(惰性创建)。

    懒导入 + lru_cache 的理由同 llm.py:
        - 没装 chromadb 时, 只在真正用向量库时才报错, 不拖累其他功能启动
        - 全进程复用一个 client + collection, 避免重复打开文件
    """
    try:
        import chromadb
    except ImportError as e:
        raise BizException(
            f"未安装 chromadb, 请执行: pip install chromadb (错误: {e})",
            code=BizCode.SYSTEM_ERROR,
        )

    # 确保持久化目录存在(PersistentClient 不会自动建目录)
    settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
    # get_or_create: 首次运行时建集合, 之后复用
    # metadata={"hnsw:space": "cosine"}: 用余弦相似度(语义匹配的标准选择)
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ============================================================
# 写入: 建库脚本用
# ============================================================
def upsert_jobs(
    job_ids: list[int],
    texts: list[str],
    metadatas: list[dict[str, Any]],
) -> int:
    """批量把岗位 JD 向量化并写入向量库(建库脚本调用)。

    流程:
        1. 调 GLM embed_batch 把 JD 文本转向量
        2. 调 ChromaDB upsert 写入(id 相同的会覆盖, 实现增量更新)

    Args:
        job_ids:   岗位 id 列表(会转成 str 当 Chroma 的主键)
        texts:     对应的 JD 文本(已拼好 title+技能+正文)
        metadatas: 对应的元数据[{title, city, source}, ...]

    Returns:
        实际写入的条数(跳过空文本后)

    注意:
        - Chroma 的 id 必须 str, 所以 job_id 要转成字符串
        - metadata 的 value 只能是 str/int/float/bool, 不能是 list
          (ChromaDB 的硬性限制, 这里调用方要保证)
        - 同步函数: 建库脚本本来就是同步流程, 没必要包 async
    """
    if not job_ids:
        return 0

    # 1. 向量化(复用 llm.py 的批量接口, 内部已处理空串过滤)
    embeddings = embed_batch(texts)

    # 2. 过滤掉空向量(对应原文为空的项), 准备 upsert 的四个并行列表
    valid_ids, valid_texts, valid_metas, valid_embs = [], [], [], []
    for jid, text, meta, emb in zip(job_ids, texts, metadatas, embeddings):
        if emb:  # 空串位置的 emb 是 [], 跳过
            valid_ids.append(str(jid))
            valid_texts.append(text)
            valid_metas.append(meta)
            valid_embs.append(emb)

    if not valid_ids:
        return 0

    # 3. 写入向量库
    _get_collection().upsert(
        ids=valid_ids,
        embeddings=valid_embs,
        documents=valid_texts,
        metadatas=valid_metas,
    )
    return len(valid_ids)


def get_existing_ids(job_ids: list[int]) -> set[int]:
    """查询哪些 job_id 已经在向量库里了(增量建库用)。

    建库脚本跑第二次时, 已存在的岗位不必重新算 embedding(省 API 调用费)。
    用法:
        existing = get_existing_ids(all_job_ids)
        to_build = [j for j in all_job_ids if j not in existing]

    Args:
        job_ids: 要检查的 job_id 列表

    Returns:
        已存在于向量库的 job_id 集合
    """
    if not job_ids:
        return set()
    # Chroma 的 id 是 str, 这里转一下
    str_ids = [str(j) for j in job_ids]
    result = _get_collection().get(ids=str_ids, include=[])  # include=[] 不取数据, 只要 id 列表
    # 把返回的 str id 转回 int
    return {int(i) for i in result["ids"]}


# ============================================================
# 查询: 推荐召回用
# ============================================================
def search(
    query_vec: list[float],
    top_k: int = 20,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """用向量在岗位库里找最相似的 top_k 个(阶段④推荐召回用)。

    Args:
        query_vec: 查询向量(简历转向量后的结果)
        top_k:     返回条数
        where:     metadata 过滤条件(如 {"city": "北京"}), 可选

    Returns:
        [{job_id, score, title, city}, ...] 按相似度降序
        score 是 0~1 的相似度(由 distance 换算而来, 越大越像)

    关于 distance → score 的换算:
        ChromaDB cosine 模式下, distance ∈ [0, 2]:
            0  = 完全相同(夹角 0°)
            1  = 正交(无关)
            2  = 完全相反
        相似度 score = 1 - distance/2, 映射到 [0, 1]:
            distance 0 → score 1.0(最像)
            distance 1 → score 0.5(无关)
            distance 2 → score 0.0(最不像)
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

    # Chroma 返回结构: {ids:[[...]], distances:[[...]], metadatas:[[...]]}
    # 外层 list 对应"查询次数"(我们只查 1 次, 所以取 [0])
    ids = raw["ids"][0]
    distances = raw["distances"][0]
    metadatas = raw["metadatas"][0]

    results = []
    for jid, dist, meta in zip(ids, distances, metadatas):
        results.append(
            {
                "job_id": int(jid),
                "score": round(1 - dist / 2, 4),  # distance → 相似度
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
    """search 的异步包装(FastAPI service 层用)。

    ChromaDB 的客户端是同步的(本地文件 IO + numpy 计算),
    在 async 函数里直接调会阻塞事件循环, 所以包一层 to_thread。
    理由同 llm.py 的 achat/aembed。
    """
    return await asyncio.to_thread(search, query_vec, top_k, where)
