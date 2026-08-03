"""
大模型服务 - 智能模型路由与多提供商兼容

架构设计：
- 智谱 GLM-4 系列为主力模型
- 智能路由：根据任务类型自动选择最适合的模型
- 健康监控：实时跟踪模型可用性，自动降级/恢复
- 成本追踪：记录各模型调用成本
"""
import httpx
import json as json_mod
import os
import time
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from utils.config import (
    ZHIPU_CONFIG, FALLBACK_CONFIGS, XFYUN_CONFIG,
    ZHIPU_MODELS, MODEL_ROUTER, FALLBACK_STRATEGY,
    LLM_CONFIG as _LLM_CONFIG,  # 兼容旧版
    COST_BUDGET_CONFIG,
)
from utils.logger import get_logger
logger = get_logger("services.llm_service")


@dataclass
class ModelHealth:
    """模型健康状态"""
    model_name: str
    status: str = "unknown"  # healthy, degraded, unhealthy
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    avg_latency: float = 0.0
    # 降级相关
    fallback_active: bool = False
    fallback_until: Optional[datetime] = None
    fallback_reason: str = ""


@dataclass
class ModelCallRecord:
    """模型调用记录"""
    model_name: str
    task_type: str
    timestamp: datetime
    latency: float
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None


class ModelRouter:
    """
    智能模型路由器
    - 根据任务类型选择最适合的模型
    - 监控模型健康状态
    - 自动降级和恢复
    - 追踪调用成本
    """

    def __init__(self):
        # 初始化模型健康状态
        self._health: Dict[str, ModelHealth] = {}
        self._call_history: List[ModelCallRecord] = []
        self._history_limit = 1000

        # 初始化智谱模型健康状态
        for model_name in ZHIPU_MODELS.keys():
            self._health[model_name] = ModelHealth(model_name=model_name)

        # 当前活跃的模型配置
        self._active_model = ZHIPU_CONFIG["model"]

        # 成本预算追踪
        self._daily_cost: float = 0.0
        self._monthly_cost: float = 0.0
        self._current_date: str = datetime.now().strftime("%Y-%m-%d")
        self._current_month: str = datetime.now().strftime("%Y-%m")
        self._budget_degraded: bool = False  # 是否因预算限制已降级

    def get_model_config(self, task_type: str = "default") -> Dict[str, Any]:
        """
        根据任务类型获取模型配置（含成本预算检查和动态路由）

        Args:
            task_type: 任务类型，如 "intent_classification", "report_generation" 等

        Returns:
            模型配置字典
        """
        # 刷新日期（跨日重置日成本）
        self._check_date_rollover()

        # 成本预算检查：如果接近/超过预算，自动降级到便宜模型
        if COST_BUDGET_CONFIG.get("enabled", True) and COST_BUDGET_CONFIG.get("auto_degrade", True):
            daily_budget = COST_BUDGET_CONFIG.get("daily_budget", 10.0)
            warning_threshold = COST_BUDGET_CONFIG.get("warning_threshold", 0.8)
            if self._daily_cost >= daily_budget:
                # 超预算：强制使用最便宜模型
                self._budget_degraded = True
                return {
                    "model": "glm-4-flash",
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "json_mode": False,
                    "tier": "light",
                    "description": "成本预算已达上限，自动降级",
                }
            elif self._daily_cost >= daily_budget * warning_threshold:
                # 接近预算：降级到便宜模型
                self._budget_degraded = True
                router_config = MODEL_ROUTER.get(task_type, MODEL_ROUTER["default"])
                # 始终使用fallback模型
                model = router_config.get("fallback", "glm-4-flash")
                model_info = ZHIPU_MODELS.get(model, {})
                return {
                    "model": model,
                    "temperature": router_config.get("temperature", 0.3),
                    "max_tokens": min(router_config.get("max_tokens", 4096), 2048),
                    "json_mode": router_config.get("json_mode", False),
                    "tier": model_info.get("tier", "standard"),
                    "description": f"成本预算接近上限({self._daily_cost:.2f}/{daily_budget:.2f})，降级使用",
                }
            else:
                self._budget_degraded = False

        # 获取路由配置
        router_config = MODEL_ROUTER.get(task_type, MODEL_ROUTER["default"])

        # 检查主模型是否可用
        primary_model = router_config["primary"]
        if self._is_model_available(primary_model):
            model = primary_model
        else:
            # 降级到备选模型
            model = router_config.get("fallback", "glm-4-flash")
            logger.warning(f"模型降级: {task_type} 从 {primary_model} 降级到 {model}")

        # 获取模型详细信息
        model_info = ZHIPU_MODELS.get(model, {})

        return {
            "model": model,
            "temperature": router_config.get("temperature", 0.3),
            "max_tokens": router_config.get("max_tokens", 4096),
            "json_mode": router_config.get("json_mode", False),
            "tier": model_info.get("tier", "standard"),
            "description": router_config.get("description", ""),
        }

    def _is_model_available(self, model_name: str) -> bool:
        """检查模型是否可用"""
        health = self._health.get(model_name)
        if not health:
            return True  # 未知模型，默认可用

        # 检查是否处于降级状态
        if health.fallback_active and health.fallback_until:
            if datetime.now() < health.fallback_until:
                return False
            else:
                # 降级时间已过，自动恢复
                health.fallback_active = False
                health.fallback_until = None
                health.fallback_reason = ""
                logger.info(f"模型 {model_name} 自动恢复")

        # 检查失败次数
        if health.failure_count >= FALLBACK_STRATEGY["max_fallback_count"]:
            return False

        return health.status != "unhealthy"

    def record_call(self, record: ModelCallRecord):
        """记录模型调用（含成本累计）"""
        self._call_history.append(record)

        # 限制历史记录大小
        if len(self._call_history) > self._history_limit:
            self._call_history = self._call_history[-self._history_limit:]

        # 累计成本
        if record.cost > 0:
            self._daily_cost += record.cost
            self._monthly_cost += record.cost

        # 更新健康状态
        health = self._health.get(record.model_name)
        if health:
            if record.success:
                health.success_count += 1
                health.last_success = record.timestamp
                health.status = "healthy"
                # 成功时重置失败计数
                health.failure_count = max(0, health.failure_count - 1)
            else:
                health.failure_count += 1
                health.last_failure = record.timestamp
                if health.failure_count >= FALLBACK_STRATEGY["max_fallback_count"]:
                    health.status = "unhealthy"

    def activate_fallback(self, model_name: str, reason: str = ""):
        """激活降级"""
        health = self._health.get(model_name)
        if health:
            health.fallback_active = True
            health.fallback_until = datetime.now() + timedelta(
                seconds=FALLBACK_STRATEGY["recovery_time"]
            )
            health.fallback_reason = reason
            logger.warning(f"模型 {model_name} 降级: {reason}")

    def get_health_status(self) -> Dict[str, Any]:
        """获取所有模型健康状态"""
        return {
            model: {
                "status": h.status,
                "fallback_active": h.fallback_active,
                "failure_count": h.failure_count,
                "success_count": h.success_count,
            }
            for model, h in self._health.items()
        }

    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本汇总"""
        total_cost = sum(r.cost for r in self._call_history)
        total_calls = len(self._call_history)
        successful_calls = sum(1 for r in self._call_history if r.success)

        # 按模型统计
        model_stats = {}
        for record in self._call_history:
            if record.model_name not in model_stats:
                model_stats[record.model_name] = {"calls": 0, "cost": 0.0}
            model_stats[record.model_name]["calls"] += 1
            model_stats[record.model_name]["cost"] += record.cost

        return {
            "total_cost": round(total_cost, 4),
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "model_stats": model_stats,
            "daily_cost": round(self._daily_cost, 4),
            "monthly_cost": round(self._monthly_cost, 4),
            "daily_budget": COST_BUDGET_CONFIG.get("daily_budget", 10.0),
            "monthly_budget": COST_BUDGET_CONFIG.get("monthly_budget", 200.0),
            "budget_degraded": self._budget_degraded,
        }

    def _check_date_rollover(self):
        """检查日期变更，重置日成本"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")
        if today != self._current_date:
            self._daily_cost = 0.0
            self._current_date = today
            self._budget_degraded = False
        if current_month != self._current_month:
            self._monthly_cost = 0.0
            self._current_month = current_month

    def get_budget_status(self) -> Dict[str, Any]:
        """获取成本预算状态"""
        self._check_date_rollover()
        daily_budget = COST_BUDGET_CONFIG.get("daily_budget", 10.0)
        monthly_budget = COST_BUDGET_CONFIG.get("monthly_budget", 200.0)
        warning_threshold = COST_BUDGET_CONFIG.get("warning_threshold", 0.8)

        daily_pct = self._daily_cost / daily_budget if daily_budget > 0 else 0
        monthly_pct = self._monthly_cost / monthly_budget if monthly_budget > 0 else 0

        return {
            "daily": {
                "cost": round(self._daily_cost, 4),
                "budget": daily_budget,
                "percentage": round(daily_pct * 100, 1),
                "remaining": round(max(0, daily_budget - self._daily_cost), 4),
                "warning": daily_pct >= warning_threshold,
                "exceeded": self._daily_cost >= daily_budget,
            },
            "monthly": {
                "cost": round(self._monthly_cost, 4),
                "budget": monthly_budget,
                "percentage": round(monthly_pct * 100, 1),
                "remaining": round(max(0, monthly_budget - self._monthly_cost), 4),
                "warning": monthly_pct >= warning_threshold,
                "exceeded": self._monthly_cost >= monthly_budget,
            },
            "budget_degraded": self._budget_degraded,
        }


class LLMService:
    """
    大模型调用服务
    - 支持智谱GLM-4系列为主力
    - 智能路由自动选择模型
    - 自动降级和恢复
    """

    def __init__(self):
        # 初始化模型路由器
        self.router = ModelRouter()

        # 智谱配置
        self.api_key = ZHIPU_CONFIG["api_key"]
        self.api_base = ZHIPU_CONFIG["api_base"]
        self.model = ZHIPU_CONFIG["model"]
        self.temperature = ZHIPU_CONFIG["temperature"]
        self.max_tokens = ZHIPU_CONFIG["max_tokens"]

        # 讯飞配置
        self.xfyun_appid = XFYUN_CONFIG["appid"]
        self.xfyun_apikey = XFYUN_CONFIG["apikey"]
        self.xfyun_apisecret = XFYUN_CONFIG["apisecret"]

        # 备选模型配置
        self.fallback_configs = FALLBACK_CONFIGS

    def _get_model_config(self, task_type: str = "default") -> Dict[str, Any]:
        """获取任务对应的模型配置"""
        return self.router.get_model_config(task_type)

    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """获取请求头"""
        key = api_key or self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        model_config: Dict[str, Any],
        stream: bool = False,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """构建请求体"""
        payload = {
            "model": model_config["model"],
            "messages": messages,
            "temperature": model_config.get("temperature", self.temperature),
            "max_tokens": model_config.get("max_tokens", self.max_tokens),
            "stream": stream,
        }

        # JSON模式：只有当 response_format 参数未明确传入时才根据 model_config 设置
        if response_format is not None:
            if response_format:
                payload["response_format"] = response_format
        elif model_config.get("json_mode"):
            payload["response_format"] = {"type": "json_object"}

        return payload

    async def chat(
        self,
        messages: List[Dict[str, str]],
        task_type: str = "default",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        非流式对话 - 支持智能路由

        Args:
            messages: 消息列表
            task_type: 任务类型，用于模型路由
            temperature: 温度参数（可选，覆盖路由配置）
            max_tokens: 最大token数（可选，覆盖路由配置）
            stream: 是否流式输出
            response_format: 响应格式配置

        Returns:
            模型回复文本
        """
        # 获取模型配置
        model_config = self._get_model_config(task_type)

        # 应用覆盖参数
        if temperature is not None:
            model_config["temperature"] = temperature
        if max_tokens is not None:
            model_config["max_tokens"] = max_tokens

        model_name = model_config["model"]
        start_time = time.time()

        logger.debug(f"LLM请求: model={model_name}, task={task_type}, messages={len(messages)}条, temperature={model_config.get('temperature')}")

        try:
            headers = self._get_headers()
            payload = self._build_payload(messages, model_config, stream, response_format)

            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # 解析响应
                content = data["choices"][0]["message"]["content"]

                # 提取token用量
                usage = data.get("usage", {})
                tokens_input = usage.get("prompt_tokens", 0)
                tokens_output = usage.get("completion_tokens", 0)

                # 计算成本
                model_info = ZHIPU_MODELS.get(model_name, {})
                cost_per_1k = model_info.get("cost_per_1k", 0.0)
                cost = (tokens_input + tokens_output) / 1000 * cost_per_1k

                # 记录调用
                latency = time.time() - start_time
                logger.debug(f"LLM响应: model={model_name}, latency={latency:.2f}s, tokens_in={tokens_input}, tokens_out={tokens_output}, cost={cost:.4f}")
                self.router.record_call(ModelCallRecord(
                    model_name=model_name,
                    task_type=task_type,
                    timestamp=datetime.now(),
                    latency=latency,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost=cost,
                    success=True,
                ))
                from services.metrics_service import get_metrics_collector
                get_metrics_collector().record_llm_call(
                    model_name, tokens_input, tokens_output, cost, latency, True
                )

                return content

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"API调用失败: {e.response.status_code} - {error_text}")

            # 记录失败
            latency = time.time() - start_time
            self.router.record_call(ModelCallRecord(
                model_name=model_name,
                task_type=task_type,
                timestamp=datetime.now(),
                latency=latency,
                success=False,
                error=f"{e.response.status_code}: {error_text[:200]}",
            ))
            from services.metrics_service import get_metrics_collector
            get_metrics_collector().record_llm_call(model_name, 0, 0, 0.0, latency, False)

            # 检查是否需要降级
            if self._should_fallback(e.response.status_code, error_text):
                self.router.activate_fallback(
                    model_name,
                    f"HTTP {e.response.status_code}"
                )

            return self._handle_error(e.response.status_code, error_text)

        except Exception as e:
            logger.error(f"调用异常: {str(e)}")
            latency = time.time() - start_time
            from services.metrics_service import get_metrics_collector
            get_metrics_collector().record_llm_call(model_name, 0, 0, 0.0, latency, False)
            return f"调用异常: {str(e)}"

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        task_type: str = "default",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话 - 支持智能路由
        """
        model_config = self._get_model_config(task_type)
        if temperature is not None:
            model_config["temperature"] = temperature
        if max_tokens is not None:
            model_config["max_tokens"] = max_tokens

        headers = self._get_headers()
        payload = self._build_payload(messages, model_config, stream=True)

        logger.debug(f"LLM流式请求: model={model_config['model']}, task={task_type}")

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json_mod.loads(data)
                                delta = chunk["choices"][0]["delta"]
                                if delta.get("content"):
                                    yield delta["content"]
                            except (json_mod.JSONDecodeError, KeyError, IndexError):
                                continue
        except Exception as e:
            logger.error(f"流式调用异常: {str(e)}")
            yield f"调用异常: {str(e)}"

    async def extract_json(
        self,
        prompt: str,
        task_type: str = "skill_extraction",
    ) -> Dict[str, Any]:
        """
        从Prompt中提取JSON格式的结构化数据

        Args:
            prompt: 包含抽取指令的Prompt
            task_type: 任务类型

        Returns:
            解析后的JSON数据
        """
        messages = [
            {"role": "system", "content": "你是一个专业的数据抽取助手，只输出JSON格式数据。"},
            {"role": "user", "content": prompt},
        ]

        response = await self.chat(
            messages,
            task_type=task_type,
            response_format={"type": "json_object"},
        )

        try:
            result = json_mod.loads(response)
            logger.debug(f"JSON抽取完成, keys={list(result.keys()) if isinstance(result, dict) else 'non-dict'}")
            return result
        except json_mod.JSONDecodeError:
            # 尝试从文本中提取JSON块
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json_mod.loads(json_match.group())
                except:
                    pass
            logger.warning(f"无法解析JSON: {response[:200]}")
            return {"error": "解析失败", "raw": response}

    def _should_fallback(self, status_code: int, error_text: str) -> bool:
        """判断是否应触发降级"""
        # 检查错误码
        if status_code in FALLBACK_STRATEGY["trigger_codes"]:
            return True

        # 检查错误关键词
        error_lower = error_text.lower()
        for keyword in FALLBACK_STRATEGY["trigger_keywords"]:
            if keyword.lower() in error_lower:
                return True

        return False

    def _handle_error(self, status_code: int, error_text: str) -> str:
        """处理API错误"""
        if status_code == 401:
            return "API认证失败: 请检查API Key是否正确"
        elif status_code == 429:
            return "API请求过多: 已达到速率限制，请稍后再试"
        elif status_code in (500, 502):
            return f"API服务器错误({status_code}): 请稍后重试"
        else:
            return f"API调用失败: {status_code} - {error_text[:200]}"

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "provider": "zhipu",
            "model": self.model,
            "health": self.router.get_health_status(),
            "cost": self.router.get_cost_summary(),
        }


# 单例模式
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取LLM服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
