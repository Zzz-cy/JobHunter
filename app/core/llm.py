"""智谱 GLM 客户端封装。

同步实现 + to_thread 异步包装(zhipuai SDK 没有官方协程版, 直接调会阻塞事件循环)。
懒加载单例, 没配 key 不影响其他功能启动。SDK 异常统一转成 BizException。
"""
import asyncio
import json
import re

from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import BizException
from app.schemas.result import BizCode


@lru_cache
def _get_client():
    """ZhipuAI 同步客户端单例(懒加载, 没调过 GLM 就不会触发)。"""
    try:
        from zhipuai import ZhipuAI
    except ImportError as e:
        raise BizException(
            f"未安装 zhipuai SDK, 请执行: pip install zhipuai (错误: {e})",
            code=BizCode.SYSTEM_ERROR,
        )

    if not settings.ZHIPU_API_KEY:
        raise BizException(
            "未配置 ZHIPU_API_KEY, 请在 backend/.env 中填入智谱 API Key",
            code=BizCode.SYSTEM_ERROR,
        )

    return ZhipuAI(
        api_key=settings.ZHIPU_API_KEY,
        base_url=settings.ZHIPU_BASE_URL,
        timeout=settings.ZHIPU_TIMEOUT,
        max_retries=2,  # SDK 内置重试, 够用
    )


def _wrap_sdk_error(e: Exception) -> BizException:
    """SDK 异常 → BizException(让全局处理器统一兜底)。"""
    from zhipuai import (
        APIAuthenticationError,
        APIReachLimitError,
        APITimeoutError,
        APIConnectionError,
    )

    if isinstance(e, APIAuthenticationError):
        return BizException(
            "智谱 API Key 无效, 请检查 backend/.env 的 ZHIPU_API_KEY",
            code=BizCode.SYSTEM_ERROR,
        )
    if isinstance(e, APIReachLimitError):
        # 智谱的 429 要区分"余额不足(1113)"和"真限流", 看响应体的 error.code
        hint = _parse_glm_error_body(e)
        if "1113" in hint or "余额" in hint or "资源包" in hint:
            return BizException(
                f"智谱账户余额不足或无 embedding 资源包, 请到 open.bigmodel.cn 充值"
                f"或领取资源包。详情: {hint}",
                code=BizCode.SYSTEM_ERROR,
            )
        return BizException(
            f"智谱 API 触发限流, 请稍后重试或降低调用频率。详情: {hint}",
            code=BizCode.SYSTEM_ERROR,
        )
    if isinstance(e, (APITimeoutError, APIConnectionError)):
        return BizException(
            f"智谱 API 连接失败/超时: {e}",
            code=BizCode.SYSTEM_ERROR,
        )
    return BizException(
        f"智谱 API 调用失败: {e}",
        code=BizCode.SYSTEM_ERROR,
    )


def _parse_glm_error_body(e: Exception) -> str:
    """从异常 .response 里抠出 GLM 的真实错误信息(str(e) 只有 "Error code: 429")。"""
    import json as _json

    resp = getattr(e, "response", None)
    if resp is None:
        return str(e)
    try:
        body = resp.json()
        err = body.get("error", body)
        code = err.get("code", "")
        msg = err.get("message", "")
        return f"[code={code}] {msg}" if code else msg
    except Exception:
        text = getattr(resp, "text", "")
        return text[:200] if text else str(e)


# ---- 同步接口(建库脚本用) ----

def chat(prompt: str, system: str | None = None) -> str:
    """单轮对话, 返回纯文本。一次性调用, 不维护对话历史。"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = _get_client().chat.completions.create(
            model=settings.ZHIPU_CHAT_MODEL,
            messages=messages,
            temperature=0.1,  # 推荐场景要稳定输出
        )
        return resp.choices[0].message.content
    except BizException:
        raise
    except Exception as e:
        raise _wrap_sdk_error(e)


def chat_json(prompt: str, system: str | None = None) -> dict | list:
    """对话并要求返回 JSON, 自动解析为 dict/list。

    容错: 先直接 json.loads, 失败再正则抠第一个 {}/[] 块, 还不行抛 BizException 让调用方降级。
    """
    raw = chat(prompt, system)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 模型有时前后带解释文字, 抠出 JSON 块
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise BizException(
        f"GLM 未返回合法 JSON, 原始回答: {raw[:200]}...",
        code=BizCode.SYSTEM_ERROR,
    )


def embed(text: str) -> list[float]:
    """单条文本转向量(默认 2048 维)。批量场景用 embed_batch 省网络往返。"""
    if not text or not text.strip():
        raise BizException("待向量化的文本不能为空", code=BizCode.PARAM_ERROR)

    try:
        resp = _get_client().embeddings.create(
            model=settings.ZHIPU_EMBED_MODEL,
            input=text,
            dimensions=settings.ZHIPU_EMBED_DIM,
        )
        return resp.data[0].embedding
    except BizException:
        raise
    except Exception as e:
        raise _wrap_sdk_error(e)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """批量文本转向量(建库用, 一次请求多条)。

    智谱单次建议 ≤64 条, 分片由调用方自己切。空串会过滤, 位置用空向量占位。
    """
    if not texts:
        return []

    non_empty_idx = [i for i, t in enumerate(texts) if t and t.strip()]
    if not non_empty_idx:
        raise BizException("待向量化的文本列表全为空", code=BizCode.PARAM_ERROR)

    clean_texts = [texts[i] for i in non_empty_idx]
    try:
        resp = _get_client().embeddings.create(
            model=settings.ZHIPU_EMBED_MODEL,
            input=clean_texts,
            dimensions=settings.ZHIPU_EMBED_DIM,
        )
        resp.data.sort(key=lambda x: x.index if x.index is not None else 0)
        clean_vecs = [d.embedding for d in resp.data]
    except BizException:
        raise
    except Exception as e:
        raise _wrap_sdk_error(e)

    # 过滤掉的位置填回空列表, 保持返回长度对齐
    result: list[list[float]] = [[] for _ in texts]
    for idx, vec in zip(non_empty_idx, clean_vecs):
        result[idx] = vec
    return result


# ---- 异步包装(FastAPI service 用) ----
# to_thread 把同步调用丢到默认线程池, 不阻塞事件循环

async def achat(prompt: str, system: str | None = None) -> str:
    return await asyncio.to_thread(chat, prompt, system)


async def achat_json(prompt: str, system: str | None = None) -> dict | list:
    return await asyncio.to_thread(chat_json, prompt, system)


async def aembed(text: str) -> list[float]:
    return await asyncio.to_thread(embed, text)


async def aembed_batch(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(embed_batch, texts)
