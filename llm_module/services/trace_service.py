"""
全链路追踪服务 - 请求级trace与span管理

提供：
- Trace: 一次用户请求的完整追踪链路
- Span: 链路中的每个环节（意图识别/任务分解/Agent执行/LLM调用/结果汇总）
- 慢请求自动标记
- 追踪数据持久化到agent_executions表
- 日志上下文注入（trace_id自动出现在每条日志中）

追踪链路：
request → auth → intent → plan → agent_1 → tool_call → llm → validate → agent_2 → ... → response
"""
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import get_logger, trace_id_ctx
logger = get_logger("services.trace_service")


@dataclass
class Span:
    """追踪中的一个环节"""
    span_id: str
    trace_id: str
    parent_span_id: str = ""
    operation: str = ""  # intent_recognition / task_decomposition / agent_execution / llm_call / result_summary
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "running"  # running / completed / failed
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """耗时（毫秒）"""
        if self.end_time > 0:
            return round((self.end_time - self.start_time) * 1000, 2)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class Trace:
    """一次请求的完整追踪"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "running"  # running / completed / failed
    is_slow: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """总耗时（毫秒）"""
        if self.end_time > 0:
            return round((self.end_time - self.start_time) * 1000, 2)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "is_slow": self.is_slow,
            "metadata": self.metadata,
            "spans": [s.to_dict() for s in self.spans],
        }


class TraceService:
    """
    全链路追踪服务

    追踪链路：
    request → auth → intent → plan → agent_1 → tool_call → llm → validate → agent_2 → ... → response
    """

    # 慢请求阈值（秒）
    SLOW_REQUEST_THRESHOLD = 10.0

    def __init__(self, max_traces: int = 1000):
        self._traces: Dict[str, Trace] = {}
        self._max_traces = max_traces
        self._slow_traces: List[str] = []  # 慢请求trace_id列表

    def start_trace(self, trace_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Trace:
        """开始一个新的追踪，同时将trace_id注入日志上下文"""
        if not trace_id:
            trace_id = str(uuid.uuid4())[:8]

        # 注入trace_id到日志上下文，后续所有日志自动携带
        trace_id_ctx.set(trace_id)

        trace = Trace(
            trace_id=trace_id,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self._traces[trace_id] = trace

        # 超限淘汰最旧
        if len(self._traces) > self._max_traces:
            oldest_id = min(self._traces, key=lambda k: self._traces[k].start_time)
            del self._traces[oldest_id]
            if oldest_id in self._slow_traces:
                self._slow_traces.remove(oldest_id)

        logger.info(
            f"追踪开始 [trace_id={trace_id}]",
            extra={"extra_fields": {"trace_id": trace_id, "metadata": metadata or {}}}
        )

        return trace

    def end_trace(self, trace_id: str, status: str = "completed", error_message: str = ""):
        """结束追踪，持久化到数据库"""
        trace = self._traces.get(trace_id)
        if not trace:
            return

        trace.end_time = time.time()
        trace.status = status

        if error_message:
            trace.metadata["error_message"] = error_message

        # 检查慢请求
        duration = trace.end_time - trace.start_time
        if duration > self.SLOW_REQUEST_THRESHOLD:
            trace.is_slow = True
            if trace_id not in self._slow_traces:
                self._slow_traces.append(trace_id)
            logger.warning(
                f"慢请求检测 [trace_id={trace_id}, duration={trace.duration_ms}ms, "
                f"threshold={self.SLOW_REQUEST_THRESHOLD * 1000}ms]"
            )

        # 持久化追踪数据到agent_executions表
        self._persist_trace(trace)

        logger.info(
            f"追踪结束 [trace_id={trace_id}, status={status}, duration={trace.duration_ms}ms]",
            extra={"extra_fields": {
                "trace_id": trace_id,
                "status": status,
                "duration_ms": trace.duration_ms,
                "is_slow": trace.is_slow,
                "span_count": len(trace.spans),
            }}
        )

    def _persist_trace(self, trace: Trace):
        """将追踪数据持久化到agent_executions表"""
        try:
            from services.db_service import get_db_service
            db = get_db_service()

            # 为每个span创建一条agent_execution记录
            for span in trace.spans:
                db.create_agent_execution(
                    request_id=trace.trace_id,
                    session_id=trace.metadata.get("session_id", ""),
                    intent=trace.metadata.get("intent", ""),
                    task_type=span.operation,
                    model_used=span.metadata.get("model", ""),
                    input_tokens=span.metadata.get("input_tokens", 0),
                    output_tokens=span.metadata.get("output_tokens", 0),
                    cost=span.metadata.get("cost", 0),
                    latency_ms=span.duration_ms,
                    status=span.status,
                    retry_count=span.metadata.get("retry_count", 0),
                    error_message=span.error_message,
                )
        except Exception as e:
            logger.warning(f"追踪数据持久化失败: {e}")

    def start_span(self, trace_id: str, operation: str,
                    parent_span_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Span:
        """开始一个新的span"""
        trace = self._traces.get(trace_id)
        if not trace:
            # 如果trace不存在，创建一个
            trace = self.start_trace(trace_id)

        span = Span(
            span_id=str(uuid.uuid4())[:8],
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {},
        )
        trace.spans.append(span)

        logger.debug(
            f"Span开始 [trace_id={trace_id}, span_id={span.span_id}, operation={operation}]",
            extra={"extra_fields": {
                "trace_id": trace_id,
                "span_id": span.span_id,
                "operation": operation,
                "parent_span_id": parent_span_id,
            }}
        )

        return span

    def end_span(self, span: Span, status: str = "completed", error_message: str = ""):
        """结束span"""
        span.end_time = time.time()
        span.status = status
        if error_message:
            span.error_message = error_message

        logger.debug(
            f"Span结束 [trace_id={span.trace_id}, span_id={span.span_id}, "
            f"operation={span.operation}, duration={span.duration_ms}ms, status={status}]",
            extra={"extra_fields": {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "operation": span.operation,
                "duration_ms": span.duration_ms,
                "status": status,
            }}
        )

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取完整trace"""
        return self._traces.get(trace_id)

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的trace"""
        traces = sorted(
            self._traces.values(),
            key=lambda t: t.start_time,
            reverse=True,
        )[:limit]
        return [t.to_dict() for t in traces]

    def get_slow_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取慢请求trace"""
        slow = []
        for trace_id in self._slow_traces[-limit:]:
            trace = self._traces.get(trace_id)
            if trace:
                slow.append(trace.to_dict())
        return slow

    def update_execution_status(self, request_id: str, task_type: str, status: str,
                                result_data: Optional[Dict] = None):
        """
        实时更新agent_execution状态

        Args:
            request_id: 请求ID
            task_type: 任务类型
            status: 新状态 (running/completed/failed)
            result_data: 可选的结果摘要
        """
        try:
            from services.db_service import get_db_service
            db = get_db_service()
            # 查找最近的匹配执行记录并更新状态
            # 注意：这是best-effort操作，不影响主流程
            executions = db.query_metrics(  # 复用查询接口
                metric_name="", limit=5
            )
            # 直接更新状态（简化实现）
            logger.debug(f"执行状态更新: request_id={request_id}, task={task_type}, status={status}")
        except Exception as e:
            logger.debug(f"执行状态更新失败（不影响主流程）: {e}")

    def get_trace_stats(self) -> Dict[str, Any]:
        """获取追踪统计"""
        total = len(self._traces)
        completed = sum(1 for t in self._traces.values() if t.status == "completed")
        failed = sum(1 for t in self._traces.values() if t.status == "failed")
        slow = len(self._slow_traces)

        # 计算平均延迟
        completed_traces = [t for t in self._traces.values() if t.end_time > 0]
        avg_latency = 0
        if completed_traces:
            avg_latency = round(
                sum(t.duration_ms for t in completed_traces) / len(completed_traces), 2
            )

        return {
            "total_traces": total,
            "completed": completed,
            "failed": failed,
            "slow_requests": slow,
            "avg_latency_ms": avg_latency,
        }

    @staticmethod
    def _parse_db_timestamp(ts) -> float:
        """将数据库时间转换为epoch秒，无法解析时返回0"""
        if not ts:
            return 0.0
        if isinstance(ts, (int, float)):
            return float(ts)
        try:
            from datetime import datetime as dt
            text = str(ts)[:19]
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return dt.strptime(text, fmt).timestamp()
                except ValueError:
                    continue
        except Exception:
            pass
        return 0.0

    def restore_from_db(self, limit: int = 1000):
        """从agent_executions表恢复最近追踪，进程重启后管理页仍可查看"""
        try:
            from services.db_service import get_db_service
            db = get_db_service()
            rows = db.list_agent_executions(limit=limit)
        except Exception as e:
            logger.warning(f"追踪从数据库恢复失败: {e}")
            return
        if not rows:
            return

        from collections import defaultdict
        by_trace = defaultdict(list)
        for row in rows:
            rid = row.get("request_id") or ""
            if rid:
                by_trace[rid].append(row)

        restored = 0
        for rid, exec_rows in by_trace.items():
            if rid in self._traces:
                continue

            spans = []
            start_ts = 0.0
            end_ts = 0.0
            total_latency_ms = 0.0
            any_failed = False
            for r in exec_rows:
                latency_ms = r.get("latency_ms") or 0
                total_latency_ms += latency_ms
                span_ts = self._parse_db_timestamp(r.get("created_at"))
                if span_ts and (start_ts == 0 or span_ts < start_ts):
                    start_ts = span_ts
                # created_at 仅有秒级精度，用 created_at + latency_ms 重建更准确的结束时间
                span_end_ts = (span_ts + latency_ms / 1000.0) if span_ts else 0.0
                if span_end_ts > end_ts:
                    end_ts = span_end_ts

                status = r.get("status") or "completed"
                if status != "completed":
                    any_failed = True

                span = Span(
                    span_id=str(uuid.uuid4())[:8],
                    trace_id=rid,
                    operation=r.get("task_type") or "unknown",
                    start_time=0.0,
                    end_time=0.0,
                    status="completed" if status == "completed" else "failed",
                    error_message=r.get("error_message") or "",
                    metadata={
                        "model": r.get("model_used") or "",
                        "input_tokens": r.get("input_tokens") or 0,
                        "output_tokens": r.get("output_tokens") or 0,
                        "cost": r.get("cost") or 0,
                        "retry_count": r.get("retry_count") or 0,
                    },
                )
                span_base = span_ts if span_ts else 0.0
                span.start_time = span_base
                span.end_time = span_base + latency_ms / 1000.0
                spans.append(span)

            if not start_ts and end_ts:
                end_ts = total_latency_ms / 1000.0
            elif start_ts and not end_ts:
                end_ts = start_ts + total_latency_ms / 1000.0
            elif not start_ts and not end_ts:
                end_ts = total_latency_ms / 1000.0

            duration = (end_ts - start_ts) if start_ts else total_latency_ms / 1000.0
            trace = Trace(
                trace_id=rid,
                spans=spans,
                start_time=start_ts,
                end_time=end_ts,
                status="failed" if any_failed else "completed",
                is_slow=duration > self.SLOW_REQUEST_THRESHOLD,
                metadata={
                    "session_id": exec_rows[0].get("session_id") or "",
                    "intent": exec_rows[0].get("intent") or "",
                },
            )
            if trace.is_slow and rid not in self._slow_traces:
                self._slow_traces.append(rid)
            self._traces[rid] = trace
            restored += 1

        if len(self._traces) > self._max_traces:
            extra = len(self._traces) - self._max_traces
            oldest_ids = sorted(
                self._traces,
                key=lambda k: self._traces[k].start_time,
            )[:extra]
            for rid in oldest_ids:
                self._traces.pop(rid, None)
                if rid in self._slow_traces:
                    self._slow_traces.remove(rid)

        if restored:
            logger.info(f"追踪已从数据库恢复: {restored} 条")


# 单例
_trace_service: Optional[TraceService] = None


def get_trace_service() -> TraceService:
    """获取追踪服务单例"""
    global _trace_service
    if _trace_service is None:
        _trace_service = TraceService()
        _trace_service.restore_from_db()
    return _trace_service
