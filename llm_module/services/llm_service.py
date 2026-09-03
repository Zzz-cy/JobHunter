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
    ZHIPU_MODELS, ALL_MODELS, EXTRA_MODELS, resolve_model_endpoint,
    MODEL_ROUTER, FALLBACK_STRATEGY,
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

    def get_model_config(self, task_type: str = "default",
                         override: Optional[str] = None) -> Dict[str, Any]:
        """
        根据任务类型获取模型配置（含成本预算检查和动态路由）

        Args:
            task_type: 任务类型，如 "intent_classification", "report_generation" 等
            override: 管理员后台设定的平台默认模型名(在 ZHIPU_MODELS 内才生效)。
                      只覆盖生成/分析类任务; intent_classification 等轻任务仍走廉价路由省钱。

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
        # 管理员后台设定的平台默认模型: 覆盖生成/分析类任务(意图/工具选择等轻任务仍走廉价路由省钱)
        # 覆盖值可为智谱 glm-* 或已配 key 的跨厂商模型(deepseek-chat / moonshot-v1-8k / ...)
        if override and task_type != "intent_classification" and override in ALL_MODELS:
            primary_model = override
        if self._is_model_available(primary_model):
            model = primary_model
        else:
            # 降级到备选模型(仍是智谱名, 保证兜底永远可用)
            model = router_config.get("fallback", "glm-4-flash")
            logger.warning(f"模型降级: {task_type} 从 {primary_model} 降级到 {model}")

        # 获取模型详细信息(跨厂商模型信息也在全量目录里)
        model_info = ALL_MODELS.get(model, {})

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

        # 管理员后台设定的平台默认模型(llm 运行时配置, 如 admin_default_model)
        self._admin_default_model: Optional[str] = self._load_admin_default_model()

    def _load_admin_default_model(self) -> Optional[str]:
        """启动/切换时从 model_config 读回管理员默认模型。表不存在或值非法返回 None。"""
        try:
            from services.db_service import get_db_service
            v = get_db_service().get_runtime_setting("admin_default_model")
            return v if v and v in ALL_MODELS else None
        except Exception as e:
            logger.debug(f"读取平台默认模型失败(降级为环境变量默认): {e}")
            return None

    def get_admin_default_model(self) -> str:
        """当前生效的平台默认模型: 管理员设定优先, 否则 env LLM_MODEL。"""
        return self._admin_default_model or self.model

    def set_admin_default_model(self, model: str) -> str:
        """设置平台默认模型(管理员后台调用)。校验后持久化到 model_config 并即时生效。

        值可为智谱 glm-* 或任意已配 key 的跨厂商模型名(见 utils.config.ALL_MODELS)。
        """
        model = (model or "").strip()
        if model not in ALL_MODELS:
            raise ValueError(f"未知模型: {model}, 可选: {', '.join(list(ALL_MODELS.keys())[:40])}")
        from services.db_service import get_db_service
        if not get_db_service().set_runtime_setting("admin_default_model", model):
            raise RuntimeError("持久化平台默认模型失败")
        self._admin_default_model = model
        logger.info(f"平台默认模型已切换为: {model}")
        return model

    def _get_model_config(self, task_type: str = "default") -> Dict[str, Any]:
        """获取任务对应的模型配置(带管理员默认模型覆盖)"""
        return self.router.get_model_config(task_type, override=self._admin_default_model)

    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """获取请求头"""
        key = api_key or self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _build_provider_headers(self, endpoint: Dict[str, Any]) -> Dict[str, str]:
        """按厂商构建请求头。

        - 讯飞星火: HMAC-SHA256 签名(api_key/api_secret + Date/Host 参与签名);
        - 其余(智谱/DeepSeek/Kimi/通义等): 标准 Bearer Token。
        """
        if (endpoint or {}).get("provider") == "xfyun":
            import base64
            import hashlib
            import hmac as _hmac
            from urllib.parse import urlparse

            base = endpoint.get("api_base") or "https://spark-api-open.xf-yun.com/v1"
            host = urlparse(base).netloc
            date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
            signature_origin = f"host: {host}\ndate: {date}\nPOST /v1/chat/completions HTTP/1.1"
            signature = base64.b64encode(
                _hmac.new(
                    (endpoint.get("api_secret") or "").encode('utf-8'),
                    signature_origin.encode('utf-8'),
                    digestmod=hashlib.sha256,
                ).digest()
            ).decode('utf-8')
            authorization = (
                f'api_key="{(endpoint.get("api_key") or "")}", '
                f'algorithm="hmac-sha256", headers="host date request-line", '
                f'signature="{signature}"'
            )
            return {
                "Authorization": authorization,
                "Content-Type": "application/json",
                "Date": date,
                "Host": host,
            }
        return self._get_headers((endpoint or {}).get("api_key"))

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

        # ⭐ 跨厂商: 按所选模型解析到对应厂商端点(智谱模型→智谱; deepseek/kimi/通义/星火→各自底座)。
        # 非智谱厂商失败时自动回落到智谱默认路由重试一次, 保证切了厂商也不至于让对话崩掉。
        endpoint = resolve_model_endpoint(model_name)
        candidates = [(endpoint, model_config, model_name)]
        if endpoint.get("provider") != "zhipu":
            fb_cfg = self.router.get_model_config(task_type, override=None)  # 不带默认覆盖 → 智谱路由
            fb_model = fb_cfg.get("model") or "glm-4-flash"
            candidates.append((resolve_model_endpoint(fb_model), fb_cfg, fb_model))

        last_status = None
        last_text = ""
        for attempt_no, (ep, cfg, label) in enumerate(candidates):
            try:
                if attempt_no > 0:
                    logger.warning(
                        f"模型 {model_name}({endpoint.get('provider')}) 调用失败, 回落到智谱重试"
                    )
                headers = self._build_provider_headers(ep)
                payload = self._build_payload(messages, cfg, stream, response_format)
                # 实际 remote 模型名(跨厂商端点可能同名不同底座, 显式覆盖一次)
                payload["model"] = ep.get("model") or cfg.get("model") or model_name
                base = ep.get("api_base") or self.api_base

                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]

                # 提取token用量 + 成本(全量目录里查单价比)
                usage = data.get("usage", {})
                tokens_input = usage.get("prompt_tokens", 0)
                tokens_output = usage.get("completion_tokens", 0)
                model_info = ALL_MODELS.get(label, {})
                cost = (tokens_input + tokens_output) / 1000 * model_info.get("cost_per_1k", 0.0)

                # 记录调用
                latency = time.time() - start_time
                logger.debug(f"LLM响应: model={label}, provider={ep.get('provider')}, latency={latency:.2f}s, tokens_in={tokens_input}, tokens_out={tokens_output}, cost={cost:.4f}")
                self.router.record_call(ModelCallRecord(
                    model_name=label,
                    task_type=task_type,
                    timestamp=datetime.now(),
                    latency=latency,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost=cost,
                    success=True,
                ))
                try:
                    from services.metrics_service import get_metrics_collector
                    get_metrics_collector().record_llm_call(
                        label, tokens_input, tokens_output, cost, latency, True
                    )
                except Exception:
                    pass

                return content

            except httpx.HTTPStatusError as e:
                last_status = e.response.status_code
                last_text = e.response.text
                logger.error(f"API调用失败: {last_status} - {last_text[:200]}")
            except Exception as e:
                last_status = None
                last_text = str(e)
                logger.error(f"调用异常: {str(e)}")

        # 所有候选都失败: 记录一条失败指标(以首选模型名义)并返回可读错误
        latency = time.time() - start_time
        self.router.record_call(ModelCallRecord(
            model_name=model_name,
            task_type=task_type,
            timestamp=datetime.now(),
            latency=latency,
            success=False,
            error=(f"{last_status}: {last_text[:200]}" if last_status is not None else last_text[:200]),
        ))
        try:
            from services.metrics_service import get_metrics_collector
            get_metrics_collector().record_llm_call(model_name, 0, 0, 0.0, latency, False)
        except Exception:
            pass

        if last_status is not None:
            # 检查是否需要降级(智谱模型失败走原有激活降级; 跨厂商失败下次仍走回落逻辑)
            if self._should_fallback(last_status, last_text):
                self.router.activate_fallback(model_name, f"HTTP {last_status}")
            return self._handle_error(last_status, last_text)
        return f"调用异常: {last_text[:200]}"

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

        # ⭐ 跨厂商: 按模型解析端点与鉴权(默认智谱)
        ep = resolve_model_endpoint(model_config["model"])
        headers = self._build_provider_headers(ep)
        payload = self._build_payload(messages, model_config, stream=True)
        payload["model"] = ep.get("model") or model_config["model"]
        base = ep.get("api_base") or self.api_base

        logger.debug(f"LLM流式请求: model={model_config['model']}, provider={ep.get('provider')}, task={task_type}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{base}/chat/completions",
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
        """获取服务状态(provider 反映当前生效默认模型所属厂商)"""
        default_model = self.get_admin_default_model()
        ep = resolve_model_endpoint(default_model)
        return {
            "provider": ep.get("provider") or "zhipu",
            "model": default_model,
            "default_model": default_model,
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
