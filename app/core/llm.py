"""
智谱 GLM 客户端封装

本模块统一封装对智谱 GLM 的调用, 提供:
    - chat / chat_json:  对话(glm-4-flash), 阶段⑤ LLM 重排用
    - embed / embed_batch: 向量化(embedding-3), 阶段②建库 + 阶段④向量召回用
    - achat / aembed / ...: 上述函数的 async 包装(供 FastAPI 异步 service 调用)

设计要点(为什么这么写):

1. **同步实现 + to_thread 异步包装**
   zhipuai SDK 只有同步的 ZhipuAI 客户端(没有官方 async 版本;
   注意 api_resource.AsyncCompletions 是"异步任务"轮询接口, 不是协程)。
   而本项目是 FastAPI 全异步(AsyncSession), 在 async 函数里直接调同步 SDK 会
   阻塞整个事件循环。所以:
       - 同步函数(供建库脚本等同步场景用)
       - async 包装(内部 asyncio.to_thread 把同步调用丢到线程池)

2. **懒加载 + 单例**
   _get_client() 用 lru_cache 缓存一个 ZhipuAI 实例。
   不在模块顶层构造: 否则 import 本模块时就会连一次智谱, 没配 key 时其他功能也起不来。

3. **异常转译**
   SDK 抛的是 APIReachLimitError/APITimeoutError 等, 本模块统一 catch 后
   转成本项目的 BizException(SYSTEM_ERROR/ParamError), 让全局异常处理器
   转成统一 Result 格式。调用方(service/api 层)只认 BizException, 不用关心 SDK 细节。

用法(同步, 建库脚本):
    from app.core.llm import embed, chat
    vec = embed("3年Python后端经验")

用法(异步, FastAPI service):
    from app.core.llm import aembed, achat
    vec = await aembed("3年Python后端经验")
    text = await achat("帮我把这段简历总结成一句话: ...")
"""
import asyncio
import json
import re

from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import BizException
from app.schemas.result import BizCode


# ============================================================
# 客户端单例
# ============================================================
@lru_cache
def _get_client():
    """获取 ZhipuAI 同步客户端(单例)。

    lru_cache 保证全进程只构造一次, 复用底层 HTTP 连接池。
    懒加载: 没调过 GLM 就不会触发, 即使没配 key 也不影响其他功能启动。
    """
    # 懒导入: 没装 zhipuai 时给清晰的报错指引, 而不是 ImportError 堆栈
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
        max_retries=2,  # SDK 内置重试(网络抖动/限流), 不用自己加 tenacity
    )


def _wrap_sdk_error(e: Exception) -> BizException:
    """把 zhipuai SDK 的异常转成 BizException, 方便全局处理器统一兜底。

    SDK 异常体系(都继承自 APIStatusError, 带 .response: httpx.Response):
        APIAuthenticationError  → key 错误(配置问题, 指向 .env)
        APIReachLimitError      → 429, 但智谱用同一个码表达两种情况:
                                  - code=1113 余额不足/无资源包(要充值)
                                  - 其他      真的触发限流(稍后重试)
                                  区分要靠解析 response 体的 error.code 字段
        APITimeoutError         → 超时(网络或服务端慢)
        APIConnectionError      → 连不上(网络/代理)
        其他                    → 兜底按系统错误处理
    """
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
        # 智谱的 429 可能是"余额不足"也可能是"真限流", 要看响应体里的 error.code
        # 余额不足时: {"error":{"code":"1113","message":"余额不足..."}}
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
    """从 SDK 异常的 .response 里抠出 GLM 返回的 error.message, 给用户看真相。

    智谱报错时响应体形如 {"error":{"code":"1113","message":"余额不足..."}},
    但 SDK 默认的 str(e) 只给了 "Error code: 429", 真正原因被吞了。
    这里手动解析, 失败就退回原始 str(e)。
    """
    import json as _json

    resp = getattr(e, "response", None)
    if resp is None:
        return str(e)
    try:
        body = resp.json()
        err = body.get("error", body)
        # 拼上 code + message, 方便日志和判断
        code = err.get("code", "")
        msg = err.get("message", "")
        return f"[code={code}] {msg}" if code else msg
    except Exception:
        # json 解析失败, 退回原始文本
        text = getattr(resp, "text", "")
        return text[:200] if text else str(e)


# ============================================================
# 同步接口(建库脚本等同步场景用)
# ============================================================
def chat(prompt: str, system: str | None = None) -> str:
    """单轮对话, 返回纯文本回答。

    Args:
        prompt:  用户消息(必填)
        system:  系统人设(可选), 放在 messages 最前面约束模型行为

    Returns:
        模型回答的纯文本(resp.choices[0].message.content)

    单轮而非多轮: 本功能的调用都是"一次性"的(总结简历/重排打分),
    不需要维护对话历史, 所以不暴露 messages 参数, 保持接口极简。
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = _get_client().chat.completions.create(
            model=settings.ZHIPU_CHAT_MODEL,
            messages=messages,
            temperature=0.1,  # 推荐场景要稳定, 不希望模型每次答得不一样
        )
        return resp.choices[0].message.content
    except BizException:
        raise  # _get_client 已经转过的, 直接放行
    except Exception as e:
        raise _wrap_sdk_error(e)


def chat_json(prompt: str, system: str | None = None) -> dict | list:
    """对话并要求模型返回 JSON, 自动解析为 dict/list。

    给 LLM 重排阶段用: 让模型输出 [{job_id, score, reason}, ...] 结构。

    容错策略(LLM 不保证 100% 返回合法 JSON):
        1. 先尝试直接 json.loads(整个回答)
        2. 失败则用正则抠出第一个 {...} 或 [...] 块再解析
        3. 还失败就抛 BizException, 让调用方决定降级(如回退粗排分数)

    注意: 不依赖 SDK 的 response_format={"type":"json_object"},
          因为 GLM 对中文 prompt 的 JSON 约束不稳定, 自己容错更可靠。
    """
    raw = chat(prompt, system)

    # 1. 直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. 正则抠 JSON 块(模型有时会前后带解释文字, 如 "结果如下: {...}")
    #    非贪婪匹配到最外层 {}/[], DOTALL 让 . 跨行
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 解析不了, 抛异常(调用方应 catch 后降级, 不要让整个推荐流程崩)
    raise BizException(
        f"GLM 未返回合法 JSON, 原始回答: {raw[:200]}...",
        code=BizCode.SYSTEM_ERROR,
    )


def embed(text: str) -> list[float]:
    """单条文本转向量, 返回 float 列表(默认 2048 维)。

    Args:
        text: 要向量化的文本

    Returns:
        embedding-3 的输出向量 list[float]

    单条接口, 适合"查询向量"场景(每次推荐只有一份简历)。
    批量场景(建库)请用 embed_batch, 一次请求多条, 省网络往返。
    """
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
    """批量文本转向量(建库专用, 一次请求多条省网络往返)。

    Args:
        texts: 文本列表

    Returns:
        与输入顺序一一对应的向量列表 [[f1,f2,...], ...]

    注意:
        - 智谱单次 embedding 请求有数量上限(官方建议 ≤ 64 条),
          本函数不做分片, 由调用方(build_job_vectors.py)按 batch 切好再传。
        - 空字符串会导致 API 报错, 这里先过滤并保持顺序。
    """
    if not texts:
        return []

    # 过滤空串(位置用空向量占位, 保持长度对齐, 避免下标错乱)
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
        # API 返回的 data 按 input 顺序排列, 但官方建议按 index 字段对齐更稳
        resp.data.sort(key=lambda x: x.index if x.index is not None else 0)
        clean_vecs = [d.embedding for d in resp.data]
    except BizException:
        raise
    except Exception as e:
        raise _wrap_sdk_error(e)

    # 把过滤掉的位置填回空列表, 保持返回长度 == len(texts)
    result: list[list[float]] = [[] for _ in texts]
    for idx, vec in zip(non_empty_idx, clean_vecs):
        result[idx] = vec
    return result


# ============================================================
# 异步包装(FastAPI service 层用)
# ============================================================
# asyncio.to_thread 把同步函数丢到默认线程池执行, 不阻塞事件循环。
# 为什么不自己起 ThreadPoolExecutor:
#   FastAPI/anyio 默认就有线程池, to_thread 直接复用, 无需额外管理生命周期。
async def achat(prompt: str, system: str | None = None) -> str:
    """chat 的异步版本。"""
    return await asyncio.to_thread(chat, prompt, system)


async def achat_json(prompt: str, system: str | None = None) -> dict | list:
    """chat_json 的异步版本。"""
    return await asyncio.to_thread(chat_json, prompt, system)


async def aembed(text: str) -> list[float]:
    """embed 的异步版本。"""
    return await asyncio.to_thread(embed, text)


async def aembed_batch(texts: list[str]) -> list[list[float]]:
    """embed_batch 的异步版本。"""
    return await asyncio.to_thread(embed_batch, texts)
