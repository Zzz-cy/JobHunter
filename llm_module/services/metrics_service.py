"""
监控指标采集服务 - 内存指标存储与查询

提供：
- 请求级指标（总量/成功率/延迟分布）
- Agent级指标（调用次数/成功率/耗时/重试率）
- LLM级指标（Token消耗/成本/延迟/错误率）
- 意图分布指标
- 业务指标（会话数/活跃用户/对话轮数）
"""
import json
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import get_logger
logger = get_logger("services.metrics_service")

# 直方图类指标名称：恢复数据库数据时按观测值还原，而非累加
HISTOGRAM_METRICS = {
    "request_latency_seconds",
    "agent_latency_seconds",
    "agent_retry_count",
    "llm_latency_seconds",
    "llm_tokens_input",
    "llm_tokens_output",
    "llm_cost",
    "intent_confidence",
}


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    监控指标采集器 - 内存存储

    支持三种指标类型：
    - Counter: 单调递增计数器（请求数、错误数）
    - Histogram: 分布统计（延迟、Token数）
    - Gauge: 当前值（活跃会话数、内存使用）
    """

    def __init__(self, max_points: int = 10000):
        self._max_points = max_points

        # 计数器
        self._counters: Dict[str, float] = defaultdict(float)

        # 直方图 - 存储最近的值用于计算P50/P90/P99
        self._histograms: Dict[str, List[float]] = defaultdict(list)

        # 仪表盘
        self._gauges: Dict[str, float] = {}

        # 时间窗口（最近1小时的详细数据）
        self._time_series: List[MetricPoint] = []

        # 意图分布
        self._intent_counts: Dict[str, int] = defaultdict(int)

        # 是否已从数据库恢复历史指标
        self._restored = False

    # ========== 计数器操作 ==========

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """递增计数器"""
        key = self._make_key(name, labels)
        self._counters[key] += value
        self._add_time_point(name, value, labels or {})

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    # ========== 直方图操作 ==========

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图观测值"""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

        # 限制历史长度
        if len(self._histograms[key]) > self._max_points:
            self._histograms[key] = self._histograms[key][-self._max_points:]

        self._add_time_point(name, value, labels or {})

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """获取直方图统计（count/avg/min/max/P50/P90/P99）"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p90": 0, "p99": 0}

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "avg": round(sum(sorted_values) / count, 2),
            "min": round(sorted_values[0], 2),
            "max": round(sorted_values[-1], 2),
            "p50": round(sorted_values[int(count * 0.5)], 2),
            "p90": round(sorted_values[int(count * 0.9)], 2),
            "p99": round(sorted_values[int(count * 0.99)], 2),
        }

    # ========== 仪表盘操作 ==========

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        self._add_time_point(f"gauge:{name}", value, labels or {})

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """获取仪表盘值"""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0)

    # ========== 便捷记录方法 ==========

    def record_request(self, status_code: int, latency: float, path: str = ""):
        """记录请求级指标"""
        self.increment("requests_total")
        self.increment(f"requests_status_{status_code}")
        self.observe("request_latency_seconds", latency)

        if status_code >= 400:
            self.increment("requests_errors")

    def record_agent_call(self, agent_name: str, success: bool, latency: float, retry_count: int = 0):
        """记录Agent级指标"""
        self.increment(f"agent_calls_total", labels={"agent": agent_name})
        self.observe("agent_latency_seconds", latency, labels={"agent": agent_name})

        if success:
            self.increment(f"agent_calls_success", labels={"agent": agent_name})
        else:
            self.increment(f"agent_calls_failed", labels={"agent": agent_name})

        if retry_count > 0:
            self.increment("agent_retries_total", labels={"agent": agent_name})
            self.observe("agent_retry_count", retry_count, labels={"agent": agent_name})

    def record_llm_call(self, model: str, tokens_input: int, tokens_output: int,
                        cost: float, latency: float, success: bool):
        """记录LLM级指标"""
        self.increment("llm_calls_total", labels={"model": model})
        self.observe("llm_latency_seconds", latency, labels={"model": model})
        self.observe("llm_tokens_input", tokens_input, labels={"model": model})
        self.observe("llm_tokens_output", tokens_output, labels={"model": model})
        self.observe("llm_cost", cost, labels={"model": model})

        if success:
            self.increment("llm_calls_success", labels={"model": model})
        else:
            self.increment("llm_calls_failed", labels={"model": model})

    def record_intent(self, intent: str, confidence: float):
        """记录意图分布"""
        self._intent_counts[intent] += 1
        self.increment("intent_count", labels={"intent": intent})
        self.observe("intent_confidence", confidence, labels={"intent": intent})

        if confidence < 0.6:
            self.increment("intent_low_confidence", labels={"intent": intent})

    def record_quota_check(self, user_id: int, allowed: bool):
        """记录配额检查结果"""
        self.increment("quota_checks_total", labels={"user_id": str(user_id)})
        if not allowed:
            self.increment("quota_exceeded_total", labels={"user_id": str(user_id)})

    # ========== 查询方法 ==========

    def get_summary(self) -> Dict[str, Any]:
        """获取所有指标汇总"""
        # 请求指标
        requests_total = self.get_counter("requests_total")
        requests_errors = self.get_counter("requests_errors")
        request_latency = self.get_histogram_stats("request_latency_seconds")

        # Agent指标
        agent_stats = {}
        agent_names = set()
        for key in self._counters:
            base_name, key_labels = self._parse_key(key)
            if base_name == "agent_calls_total":
                agent_name = key_labels.get("agent", "")
                if agent_name:
                    agent_names.add(agent_name)

        for agent_name in agent_names:
            total = self.get_counter("agent_calls_total", labels={"agent": agent_name})
            success = self.get_counter("agent_calls_success", labels={"agent": agent_name})
            failed = self.get_counter("agent_calls_failed", labels={"agent": agent_name})
            latency = self.get_histogram_stats("agent_latency_seconds", labels={"agent": agent_name})
            retries = self.get_counter("agent_retries_total", labels={"agent": agent_name})

            agent_stats[agent_name] = {
                "total_calls": total,
                "success": success,
                "failed": failed,
                "success_rate": round(success / total, 3) if total > 0 else 0,
                "latency": latency,
                "retries": retries,
            }

        # LLM指标
        llm_stats = {}
        model_names = set()
        for key in self._counters:
            base_name, key_labels = self._parse_key(key)
            if base_name == "llm_calls_total":
                model_name = key_labels.get("model", "")
                if model_name:
                    model_names.add(model_name)

        for model_name in model_names:
            total = self.get_counter("llm_calls_total", labels={"model": model_name})
            success = self.get_counter("llm_calls_success", labels={"model": model_name})
            failed = self.get_counter("llm_calls_failed", labels={"model": model_name})
            latency = self.get_histogram_stats("llm_latency_seconds", labels={"model": model_name})
            tokens_in = self.get_histogram_stats("llm_tokens_input", labels={"model": model_name})
            tokens_out = self.get_histogram_stats("llm_tokens_output", labels={"model": model_name})
            cost = self.get_histogram_stats("llm_cost", labels={"model": model_name})

            llm_stats[model_name] = {
                "total_calls": total,
                "success": success,
                "failed": failed,
                "success_rate": round(success / total, 3) if total > 0 else 0,
                "latency": latency,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "cost": cost,
            }

        # 意图分布
        intent_total = sum(self._intent_counts.values())
        intent_distribution = {
            intent: {
                "count": count,
                "percentage": round(count / intent_total, 3) if intent_total > 0 else 0,
            }
            for intent, count in self._intent_counts.items()
        }

        # 错误明细
        agent_failed_total = sum(
            self.get_counter("agent_calls_failed", labels={"agent": a})
            for a in agent_names
        )
        llm_failed_total = sum(
            self.get_counter("llm_calls_failed", labels={"model": m})
            for m in model_names
        )
        timeout_errors = self.get_counter("requests_errors", labels={"type": "timeout"})
        error_breakdown = {
            "total": requests_errors + timeout_errors + llm_failed_total + agent_failed_total,
            "timeout": timeout_errors,
            "llm": llm_failed_total,
            "agent": agent_failed_total,
            "validation": 0,
        }

        # intent_low_confidence 按 intent 标签记录，需要汇总所有标签值
        intent_low_conf_total = sum(
            v for k, v in self._counters.items()
            if k == "intent_low_confidence" or k.startswith("intent_low_confidence{")
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "requests": {
                "total": requests_total,
                "errors": requests_errors,
                "error_rate": round(requests_errors / requests_total, 3) if requests_total > 0 else 0,
                "latency": request_latency,
            },
            "agents": agent_stats,
            "llm": llm_stats,
            "intents": {
                "total": intent_total,
                "distribution": intent_distribution,
                "low_confidence_rate": round(
                    intent_low_conf_total / intent_total, 3
                ) if intent_total > 0 else 0,
            },
            "request_trend": self.get_hourly_trend("requests_total", 24),
            "latency_buckets": self.get_histogram_buckets("request_latency_seconds"),
            "intent_confidence_buckets": self.get_intent_confidence_buckets(),
            "errors": error_breakdown,
        }

    def get_prometheus_format(self) -> str:
        """导出Prometheus格式指标"""
        lines = []

        for key, value in self._counters.items():
            clean_key = key.replace(":", "_").replace("{", "").replace("}", "")
            lines.append(f"# TYPE {clean_key} counter")
            lines.append(f"{clean_key} {value}")

        for key, value in self._gauges.items():
            clean_key = key.replace(":", "_").replace("{", "").replace("}", "")
            lines.append(f"# TYPE {clean_key} gauge")
            lines.append(f"{clean_key} {value}")

        return "\n".join(lines)

    # ========== 统计辅助方法 ==========

    def get_hourly_trend(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标的小时趋势（默认近24小时）"""
        from datetime import datetime as dt, timedelta

        now = time.time()
        window_start = now - hours * 3600
        points = [
            p for p in self._time_series
            if p.name == metric_name and p.timestamp >= window_start
        ]
        buckets: Dict[str, float] = defaultdict(float)
        for p in points:
            key = dt.fromtimestamp(p.timestamp).strftime("%Y-%m-%d %H:00")
            buckets[key] += p.value

        result = []
        current = dt.now().replace(minute=0, second=0, microsecond=0)
        for offset in range(hours - 1, -1, -1):
            ts = current - timedelta(hours=offset)
            key = ts.strftime("%Y-%m-%d %H:00")
            result.append({
                "label": ts.strftime("%H:00"),
                "count": round(buckets.get(key, 0)),
            })
        return result

    def get_histogram_buckets(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        definitions=None,
    ) -> List[Dict[str, Any]]:
        """将直方图数据划分为固定区间"""
        if definitions is None:
            definitions = [
                ("<1s", 0, 1),
                ("1-3s", 1, 3),
                ("3-5s", 3, 5),
                ("5-10s", 5, 10),
                (">10s", 10, float("inf")),
            ]
        values = self._histograms.get(self._make_key(name, labels), [])
        return [
            {"label": label, "count": sum(1 for v in values if low <= v < high)}
            for label, low, high in definitions
        ]

    def get_intent_confidence_buckets(self) -> List[Dict[str, Any]]:
        """意图置信度分布区间"""
        definitions = [
            ("<0.3", 0, 0.3),
            ("0.3-0.5", 0.3, 0.5),
            ("0.5-0.6", 0.5, 0.6),
            ("0.6-0.8", 0.6, 0.8),
            ("0.8-1.0", 0.8, 1.01),
        ]
        return self.get_histogram_buckets("intent_confidence", definitions=definitions)

    def restore_from_db(self):
        """从数据库恢复历史指标，进程重启后管理页数据仍然保留"""
        if self._restored:
            return
        try:
            from services.db_service import get_db_service
            db = get_db_service()
            rows = db.query_metrics(metric_name="", limit=self._max_points * 10)
        except Exception as e:
            logger.warning(f"指标从数据库恢复失败: {e}")
            return

        time_series = []
        restored_counters = defaultdict(float)
        restored_histograms = defaultdict(list)
        restored_gauges = {}
        restored_intents = defaultdict(int)

        for row in rows:
            name = row.get("metric_name", "")
            if not name:
                continue
            try:
                labels = json.loads(row.get("labels_json") or "{}") or {}
            except Exception:
                labels = {}
            value = row.get("metric_value", 0) or 0
            ts = row.get("timestamp")
            timestamp = time.time()
            if ts:
                try:
                    from datetime import datetime as dt
                    timestamp = dt.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S").timestamp()
                except Exception:
                    timestamp = time.time()

            time_series.append(MetricPoint(
                name=name,
                value=value,
                timestamp=timestamp,
                labels=labels,
            ))

            key = self._make_key(name, labels)
            if name.startswith("gauge:"):
                restored_gauges[self._make_key(name[len("gauge:"):], labels)] = value
            elif name == "intent_count":
                restored_intents[labels.get("intent", "unknown")] += int(value)
            elif name in HISTOGRAM_METRICS:
                restored_histograms[self._make_key(name, labels)].append(value)
            else:
                restored_counters[self._make_key(name, labels)] += value

        time_series.sort(key=lambda p: p.timestamp)
        self._time_series = time_series[-self._max_points:]
        self._counters = restored_counters
        self._histograms = defaultdict(list, {
            k: v[-self._max_points:]
            for k, v in restored_histograms.items()
        })
        self._gauges = restored_gauges
        self._intent_counts = restored_intents
        self._restored = True

        if rows:
            logger.info(f"指标已从数据库恢复: {len(rows)} 条记录")

    # ========== 内部方法 ==========

    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """生成带标签的指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}:{v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str):
        """将带标签的指标键解析为 (名称, 标签字典)"""
        if "{" in key:
            name, label_part = key.split("{", 1)
            label_part = label_part.rstrip("}")
            labels = {}
            for pair in label_part.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    labels[k] = v
            return name, labels
        return key, {}

    def _add_time_point(self, name: str, value: float, labels: Dict[str, str]):
        """添加时间序列数据点，并持久化到数据库"""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels,
        )
        self._time_series.append(point)

        # 限制时间序列长度
        if len(self._time_series) > self._max_points:
            self._time_series = self._time_series[-self._max_points:]

        # 持久化到metrics表（异步不阻塞，失败静默）
        self._persist_metric(name, value, labels)

    def _persist_metric(self, name: str, value: float, labels: Dict[str, str]):
        """将指标持久化到数据库metrics表"""
        try:
            from services.db_service import get_db_service
            db = get_db_service()
            db.create_metric(name, value, labels=labels)
        except Exception:
            pass  # 持久化失败不影响指标采集


# 单例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取指标采集器单例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        _metrics_collector.restore_from_db()
    return _metrics_collector


# ==================== 告警引擎 ====================

@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    condition: str  # 条件描述
    severity: str  # critical / warning / info
    enabled: bool = True
    threshold: float = 0.0  # 触发阈值
    check_fn: Optional[Any] = None  # 检查函数


@dataclass
class AlertEvent:
    """告警事件"""
    rule_name: str
    severity: str
    title: str
    message: str
    timestamp: str
    resolved: bool = False


class AlertEngine:
    """
    告警引擎 - 基于指标的实时告警

    内置规则：
    1. 错误率 > 5% → critical
    2. P99延迟 > 30s → warning
    3. Agent连续失败 > 3次 → critical
    4. LLM日成本 > 预算80% → warning
    5. 意图识别低置信度比例 > 30% → info
    """

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self._rules: List[AlertRule] = []
        self._active_alerts: List[AlertEvent] = []
        self._alert_history: List[AlertEvent] = []
        self._max_history = 100

        # Agent连续失败计数器
        self._agent_consecutive_failures: Dict[str, int] = defaultdict(int)

        # 注册内置规则
        self._register_builtin_rules()

    def _register_builtin_rules(self):
        """注册内置告警规则"""
        self._rules = [
            AlertRule(
                name="error_rate_high",
                description="请求错误率超过5%",
                condition="error_rate > 0.05",
                severity="critical",
                threshold=0.05,
                check_fn=self._check_error_rate,
            ),
            AlertRule(
                name="p99_latency_high",
                description="P99延迟超过30秒",
                condition="p99_latency > 30s",
                severity="warning",
                threshold=30.0,
                check_fn=self._check_p99_latency,
            ),
            AlertRule(
                name="agent_consecutive_failures",
                description="同一Agent连续失败超过3次",
                condition="agent_consecutive_failures > 3",
                severity="critical",
                threshold=3,
                check_fn=self._check_agent_failures,
            ),
            AlertRule(
                name="llm_cost_budget",
                description="LLM日成本超过预算80%",
                condition="daily_cost > budget * 0.8",
                severity="warning",
                threshold=0.8,
                check_fn=self._check_llm_cost,
            ),
            AlertRule(
                name="low_confidence_rate",
                description="意图识别低置信度比例超过30%",
                condition="low_confidence_rate > 0.3",
                severity="info",
                threshold=0.3,
                check_fn=self._check_low_confidence,
            ),
        ]

    def record_agent_failure(self, agent_name: str):
        """记录Agent失败（用于连续失败检测）"""
        self._agent_consecutive_failures[agent_name] += 1

    def record_agent_success(self, agent_name: str):
        """记录Agent成功（重置连续失败计数）"""
        self._agent_consecutive_failures[agent_name] = 0

    def check_all_rules(self) -> List[AlertEvent]:
        """
        检查所有告警规则

        Returns:
            触发的告警事件列表
        """
        new_alerts = []

        for rule in self._rules:
            if not rule.enabled or not rule.check_fn:
                continue

            try:
                result = rule.check_fn()
                if result:
                    alert = AlertEvent(
                        rule_name=rule.name,
                        severity=rule.severity,
                        title=rule.description,
                        message=result,
                        timestamp=datetime.now().isoformat(),
                    )
                    new_alerts.append(alert)

                    # 添加到活跃告警和历史
                    self._active_alerts.append(alert)
                    self._alert_history.append(alert)

                    # 限制历史长度
                    if len(self._alert_history) > self._max_history:
                        self._alert_history = self._alert_history[-self._max_history:]

                    logger.warning(f"告警触发: [{rule.severity}] {rule.description} - {result}")

            except Exception as e:
                logger.error(f"告警规则检查失败 [{rule.name}]: {e}")

        return new_alerts

    def get_active_alerts(self) -> List[AlertEvent]:
        """获取当前活跃告警"""
        return [a for a in self._active_alerts if not a.resolved]

    def get_alert_history(self, limit: int = 50) -> List[AlertEvent]:
        """获取告警历史"""
        return self._alert_history[-limit:]

    def resolve_alert(self, rule_name: str):
        """解决告警"""
        for alert in self._active_alerts:
            if alert.rule_name == rule_name and not alert.resolved:
                alert.resolved = True

    def get_rules(self) -> List[Dict[str, Any]]:
        """获取所有告警规则"""
        return [
            {
                "name": r.name,
                "description": r.description,
                "condition": r.condition,
                "severity": r.severity,
                "enabled": r.enabled,
                "threshold": r.threshold,
            }
            for r in self._rules
        ]

    # ========== 检查函数 ==========

    def _check_error_rate(self) -> Optional[str]:
        """检查错误率"""
        total = self.metrics.get_counter("requests_total")
        errors = self.metrics.get_counter("requests_errors")

        if total < 10:  # 样本太少不检查
            return None

        error_rate = errors / total
        if error_rate > self._get_rule_threshold("error_rate_high"):
            return f"当前错误率 {error_rate:.1%}，超过阈值 {self._get_rule_threshold('error_rate_high'):.1%}（总请求: {int(total)}，错误: {int(errors)}）"
        return None

    def _check_p99_latency(self) -> Optional[str]:
        """检查P99延迟"""
        stats = self.metrics.get_histogram_stats("request_latency_seconds")
        p99 = stats.get("p99", 0)

        if p99 > self._get_rule_threshold("p99_latency_high"):
            return f"当前P99延迟 {p99:.2f}s，超过阈值 {self._get_rule_threshold('p99_latency_high'):.1f}s"
        return None

    def _check_agent_failures(self) -> Optional[str]:
        """检查Agent连续失败"""
        threshold = int(self._get_rule_threshold("agent_consecutive_failures"))
        failing_agents = {
            name: count for name, count in self._agent_consecutive_failures.items()
            if count > threshold
        }

        if failing_agents:
            details = ", ".join(f"{name}({count}次)" for name, count in failing_agents.items())
            return f"以下Agent连续失败超过{threshold}次: {details}"
        return None

    def _check_llm_cost(self) -> Optional[str]:
        """检查LLM成本"""
        from utils.config import COST_BUDGET_CONFIG

        if not COST_BUDGET_CONFIG.get("enabled"):
            return None

        # 获取今日总成本
        daily_budget = COST_BUDGET_CONFIG.get("daily_budget", 10.0)
        warning_threshold = COST_BUDGET_CONFIG.get("warning_threshold", 0.8)

        # 从直方图获取总成本
        cost_stats = self.metrics.get_histogram_stats("llm_cost")
        total_cost = cost_stats.get("count", 0) * cost_stats.get("avg", 0)

        if daily_budget > 0 and total_cost > daily_budget * warning_threshold:
            usage_pct = total_cost / daily_budget
            return f"今日LLM成本 ¥{total_cost:.2f}，已达日预算 ¥{daily_budget:.2f} 的 {usage_pct:.1%}"
        return None

    def _check_low_confidence(self) -> Optional[str]:
        """检查意图识别低置信度比例"""
        summary = self.metrics.get_summary()
        low_rate = summary.get("intents", {}).get("low_confidence_rate", 0)
        total_intents = summary.get("intents", {}).get("total", 0)

        if total_intents < 5:  # 样本太少不检查
            return None

        if low_rate > self._get_rule_threshold("low_confidence_rate"):
            return f"意图识别低置信度比例 {low_rate:.1%}，超过阈值 {self._get_rule_threshold('low_confidence_rate'):.1%}"
        return None

    def _get_rule_threshold(self, rule_name: str) -> float:
        """获取规则阈值"""
        for rule in self._rules:
            if rule.name == rule_name:
                return rule.threshold
        return 0.0


# 告警引擎单例
_alert_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    """获取告警引擎单例"""
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertEngine(get_metrics_collector())
    return _alert_engine
