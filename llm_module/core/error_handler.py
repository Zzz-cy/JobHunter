"""
错误兜底模块 - 重试/降级/熔断/超时

提供：
- retry_with_backoff(): 指数退避重试
- CircuitBreaker: 熔断器
- AgentTimeout: 超时控制
- FallbackHandler: 降级处理
- ModelFallback: 重试时模型降级
- PromptSimplifier: 重试时prompt简化
"""
import asyncio
import time
from typing import Any, Callable, Optional, Dict, Set
from datetime import datetime, timedelta

from utils.logger import get_logger
logger = get_logger("core.error_handler")


# ==================== 可重试错误判定 ====================

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
RETRYABLE_KEYWORDS = {"timeout", "rate limit", "server error", "bad gateway", "service unavailable", "超时", "限流"}


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试"""
    error_str = str(error).lower()

    # 检查HTTP状态码
    for code in RETRYABLE_STATUS_CODES:
        if str(code) in error_str:
            return True

    # 检查关键词
    for keyword in RETRYABLE_KEYWORDS:
        if keyword.lower() in error_str:
            return True

    # 检查是否是超时异常
    if isinstance(error, asyncio.TimeoutError):
        return True

    return False


# ==================== 指数退避重试 ====================

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
    task_type: str = "",
) -> Any:
    """
    带指数退避的重试

    Args:
        func: 要重试的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        task_type: 任务类型（用于日志）

    Returns:
        函数执行结果

    Raises:
        最后一次重试的异常
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            if attempt > 0:
                logger.info(f"重试成功 [task={task_type}, attempt={attempt}]")
            return result
        except Exception as e:
            last_error = e

            if not is_retryable_error(e):
                logger.warning(f"不可重试错误 [task={task_type}]: {str(e)[:200]}")
                raise

            if attempt >= max_retries:
                logger.error(f"重试耗尽 [task={task_type}, attempts={max_retries + 1}]: {str(e)[:200]}")
                raise

            # 计算退避延迟
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"重试中 [task={task_type}, attempt={attempt + 1}/{max_retries}, "
                f"delay={delay:.1f}s]: {str(e)[:100]}"
            )
            await asyncio.sleep(delay)

    raise last_error  # 不应到达这里，但作为安全兜底


# ==================== 熔断器 ====================

class CircuitBreaker:
    """
    熔断器 - 连续失败后暂停调用，定时探测恢复

    状态：
    - closed: 正常（允许调用）
    - open: 熔断（拒绝调用）
    - half_open: 探测（允许一次调用测试恢复）
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._state = "closed"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.time()

    @property
    def state(self) -> str:
        """获取当前状态"""
        if self._state == "open":
            # 检查是否到了探测时间
            if self._last_failure_time and (
                time.time() - self._last_failure_time > self.recovery_timeout
            ):
                self._state = "half_open"
                logger.info(f"熔断器 [{self.name}] 进入探测状态")
        return self._state

    def record_success(self):
        """记录成功"""
        self._success_count += 1
        if self._state == "half_open":
            self._state = "closed"
            self._failure_count = 0
            logger.info(f"熔断器 [{self.name}] 恢复正常")
        elif self._state == "closed":
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            if self._state != "open":
                self._state = "open"
                logger.warning(
                    f"熔断器 [{self.name}] 触发熔断 "
                    f"(failures={self._failure_count}, threshold={self.failure_threshold})"
                )

    def is_available(self) -> bool:
        """检查是否可用"""
        return self.state in ("closed", "half_open")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }


# ==================== 熔断器注册表 ====================

_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """获取或创建熔断器"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name)
    return _circuit_breakers[name]


# ==================== 降级处理 ====================

class FallbackHandler:
    """
    降级处理器 - Agent失败后降级为通用问答
    """

    def __init__(self, llm_service=None):
        self._llm = llm_service

    async def fallback_to_general_qa(self, user_input: str, error: str = "") -> str:
        """降级为通用问答"""
        logger.info(f"降级为通用问答: {error[:100]}")

        if self._llm is None:
            from services.llm_service import get_llm_service
            self._llm = get_llm_service()

        try:
            response = await self._llm.chat(
                [{"role": "user", "content": user_input}],
                task_type="general_qa",
            )
            return f"{response}\n\n（注：由于专业分析暂时不可用，以上为通用回答。错误信息：{error[:50]}）"
        except Exception as e:
            logger.error(f"降级通用问答也失败: {str(e)}")
            return f"抱歉，服务暂时不可用，请稍后重试。"


# ==================== 超时控制 ====================

class AgentTimeout:
    """Agent超时控制"""

    DEFAULT_TIMEOUT = 30.0  # 默认30秒

    @staticmethod
    async def execute_with_timeout(
        coro,
        timeout: float = 30.0,
        task_type: str = "",
    ) -> Any:
        """
        带超时的异步执行

        Args:
            coro: 协程
            timeout: 超时时间（秒）
            task_type: 任务类型（用于日志）

        Returns:
            协程结果

        Raises:
            asyncio.TimeoutError: 超时
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Agent执行超时 [task={task_type}, timeout={timeout}s]")
            raise


# ==================== 重试时模型降级 ====================

class ModelFallback:
    """
    重试时模型降级 - 主模型失败后尝试备选模型

    降级链路：
    premium (glm-4-plus) → standard (glm-4-air) → light (glm-4-flash)

    用法：
        fallback = ModelFallback(llm_service)
        result = await fallback.call_with_fallback(messages, task_type="job_analysis")
    """

    # 模型降级链路：按tier从高到低
    TIER_FALLBACK_ORDER = ["premium", "standard", "light"]

    def __init__(self, llm_service=None):
        self._llm = llm_service

    def _get_llm(self):
        """延迟获取LLM服务"""
        if self._llm is None:
            from services.llm_service import get_llm_service
            self._llm = get_llm_service()
        return self._llm

    def _get_fallback_model(self, current_model: str) -> Optional[str]:
        """
        获取当前模型的降级备选模型

        Args:
            current_model: 当前模型名称

        Returns:
            降级模型名称，如果已是最轻量模型则返回None
        """
        from utils.config import ZHIPU_MODELS, MODEL_ROUTER

        # 获取当前模型的tier
        current_info = ZHIPU_MODELS.get(current_model, {})
        current_tier = current_info.get("tier", "standard")

        # 找到当前tier在降级链路中的位置
        try:
            current_idx = self.TIER_FALLBACK_ORDER.index(current_tier)
        except ValueError:
            current_idx = 1  # 默认standard

        # 选择下一个更低tier的模型
        for next_idx in range(current_idx + 1, len(self.TIER_FALLBACK_ORDER)):
            next_tier = self.TIER_FALLBACK_ORDER[next_idx]
            # 找到该tier的第一个可用模型
            for model_name, model_info in ZHIPU_MODELS.items():
                if model_info.get("tier") == next_tier:
                    return model_name

        return None  # 已是最轻量模型

    async def call_with_fallback(
        self,
        messages: list,
        task_type: str = "default",
        response_format: Optional[Dict] = None,
        attempt: int = 0,
    ) -> str:
        """
        带模型降级的LLM调用

        Args:
            messages: 消息列表
            task_type: 任务类型
            response_format: 响应格式
            attempt: 当前重试次数（用于决定是否降级）

        Returns:
            LLM回复文本
        """
        llm = self._get_llm()

        # 第一次尝试使用正常路由
        if attempt == 0:
            return await llm.chat(
                messages,
                task_type=task_type,
                response_format=response_format,
            )

        # 重试时尝试降级模型
        model_config = llm._get_model_config(task_type)
        current_model = model_config["model"]
        fallback_model = self._get_fallback_model(current_model)

        if fallback_model:
            logger.info(
                f"模型降级重试 [attempt={attempt}]: "
                f"{current_model} → {fallback_model}"
            )
            try:
                # 使用降级模型直接调用
                from utils.config import ZHIPU_MODELS
                fallback_config = {
                    "model": fallback_model,
                    "temperature": model_config.get("temperature", 0.3),
                    "max_tokens": min(model_config.get("max_tokens", 4096), 2048),  # 降级时减少token
                }
                headers = llm._get_headers()
                payload = llm._build_payload(messages, fallback_config, response_format=response_format)

                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{llm.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

            except Exception as e:
                logger.warning(f"降级模型调用也失败 [{fallback_model}]: {str(e)[:100]}")
                # 降级模型也失败，回退到正常调用
                return await llm.chat(
                    messages,
                    task_type=task_type,
                    response_format=response_format,
                )
        else:
            # 已是最轻量模型，正常重试
            return await llm.chat(
                messages,
                task_type=task_type,
                response_format=response_format,
            )


# ==================== 重试时Prompt简化 ====================

class PromptSimplifier:
    """
    重试时Prompt简化 - 缩短prompt减少token消耗

    简化策略：
    1. 移除示例（Few-shot examples）
    2. 缩短系统提示词
    3. 移除冗余的格式说明
    4. 压缩用户输入（保留核心信息）
    """

    # 简化级别对应的保留比例
    SIMPLIFY_LEVELS = {
        0: 1.0,    # 不简化
        1: 0.7,    # 保留70%
        2: 0.5,    # 保留50%
        3: 0.3,    # 保留30%（最简短指令）
    }

    @staticmethod
    def simplify_prompt(prompt: str, attempt: int = 0) -> str:
        """
        根据重试次数简化prompt

        Args:
            prompt: 原始prompt
            attempt: 重试次数（0=首次，1=第一次重试...）

        Returns:
            简化后的prompt
        """
        if attempt == 0:
            return prompt

        # 确定简化级别
        level = min(attempt, 3)
        ratio = PromptSimplifier.SIMPLIFY_LEVELS.get(level, 0.5)

        # 策略1：移除"要求"部分（通常在prompt末尾）
        simplified = prompt

        # 移除"要求："或"要求："后面的内容
        for marker in ["要求：", "要求:", "重要提示：", "重要提示:"]:
            if marker in simplified and attempt >= 2:
                simplified = simplified.split(marker)[0]

        # 策略2：移除示例段落
        if attempt >= 1:
            lines = simplified.split("\n")
            filtered = []
            skip = False
            for line in lines:
                if "示例" in line or "例子" in line or "例如" in line:
                    skip = True
                    continue
                if skip and line.strip().startswith(("-", "•", "1.", "2.", "3.")):
                    continue
                if skip and not line.strip():
                    skip = False
                    continue
                if not skip:
                    filtered.append(line)
            simplified = "\n".join(filtered)

        # 策略3：如果仍然太长，截断到目标长度
        target_length = int(len(prompt) * ratio)
        if len(simplified) > target_length and target_length > 100:
            # 保留开头和结尾
            head_length = int(target_length * 0.7)
            tail_length = target_length - head_length
            simplified = (
                simplified[:head_length]
                + "\n...\n[内容已简化]\n...\n"
                + simplified[-tail_length:]
            )

        if simplified != prompt:
            logger.info(
                f"Prompt简化 [attempt={attempt}, "
                f"original={len(prompt)}chars, simplified={len(simplified)}chars]"
            )

        return simplified

    @staticmethod
    def simplify_messages(messages: list, attempt: int = 0) -> list:
        """
        简化消息列表（用于重试时）

        Args:
            messages: 消息列表
            attempt: 重试次数

        Returns:
            简化后的消息列表
        """
        if attempt == 0 or not messages:
            return messages

        simplified = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                # 系统消息：重试时缩短
                if attempt >= 2:
                    # 保留第一句
                    first_sentence = content.split("。")[0] + "。"
                    if len(first_sentence) < len(content) * 0.5:
                        simplified.append({"role": role, "content": first_sentence})
                        continue
                simplified.append(msg)
            elif role == "user":
                # 用户消息：简化prompt
                simplified_content = PromptSimplifier.simplify_prompt(content, attempt)
                simplified.append({"role": role, "content": simplified_content})
            else:
                simplified.append(msg)

        return simplified
