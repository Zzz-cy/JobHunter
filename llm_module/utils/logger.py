"""
统一日志管理模块
- 支持按模块分层日志器 (llm_module.api, llm_module.services.llm_service, ...)
- 支持日志轮转 (RotatingFileHandler)
- 支持环境变量配置日志级别
- 支持请求ID追踪 (contextvars + RequestIdFilter)
- 支持结构化JSON日志输出 (LOG_FORMAT=json 切换)
- 支持全链路Trace ID (trace_id_ctx)
- 支持慢请求告警标记
- 保持向后兼容: from utils.logger import logger
"""
import json
import logging
import os
import sys
import traceback
import contextvars
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# 日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 配置常量（从环境变量读取，提供默认值）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT_ENV = os.getenv("LOG_FORMAT", "text").lower()  # "text" 或 "json"
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
LOG_FILE = LOG_DIR / "llm_module.log"

# 慢请求阈值（秒），超过此值的请求自动记录WARNING
SLOW_REQUEST_THRESHOLD = float(os.getenv("SLOW_REQUEST_THRESHOLD", "10.0"))

# 请求ID上下文变量（asyncio安全，每个协程独立）
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

# Trace ID上下文变量（全链路追踪）
trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default="-"
)

# 模块级别的标志，确保只配置一次
_configured = False


class RequestIdFilter(logging.Filter):
    """将当前请求ID和Trace ID注入日志记录"""
    def filter(self, record):
        record.request_id = request_id_ctx.get("-")
        record.trace_id = trace_id_ctx.get("-")
        return True


class JsonFormatter(logging.Formatter):
    """
    结构化JSON日志格式器

    输出格式：
    {
        "timestamp": "2024-01-01T12:00:00.000",
        "level": "INFO",
        "logger": "llm_module.api",
        "message": "...",
        "request_id": "abc123",
        "trace_id": "def456",
        "module": "routes",
        "func": "health_check",
        "line": 42
    }
    """

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加额外字段（通过 logger.info("msg", extra={...}) 传入）
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields and isinstance(extra_fields, dict):
            log_entry.update(extra_fields)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """文本格式日志格式器（默认）"""

    TEXT_FORMAT = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[req:%(request_id)s] [trace:%(trace_id)s] - %(message)s"
    )

    def __init__(self):
        super().__init__(fmt=self.TEXT_FORMAT)

    def format(self, record):
        # 确保上下文字段存在
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return super().format(record)


def _get_formatter():
    """根据环境变量选择日志格式器"""
    if LOG_FORMAT_ENV == "json":
        return JsonFormatter()
    return TextFormatter()


def _ensure_configured():
    """确保根日志器已配置（仅执行一次）"""
    global _configured
    if _configured:
        return
    _configured = True

    root_logger = logging.getLogger("llm_module")
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # 防止日志传播到根日志器（避免 basicConfig 冲突和重复输出）
    root_logger.propagate = False

    # 如果已有处理器则不重复添加（防御性检查）
    if root_logger.handlers:
        return

    formatter = _get_formatter()
    request_id_filter = RequestIdFilter()

    # 控制台处理器（Windows兼容：处理中文编码）
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_id_filter)
    root_logger.addHandler(console_handler)

    # 文件处理器（轮转）
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(request_id_filter)
    root_logger.addHandler(file_handler)

    # JSON模式下额外输出一份JSON日志文件
    if LOG_FORMAT_ENV == "json":
        json_log_file = LOG_DIR / "llm_module.json.log"
        json_file_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        json_file_handler.setFormatter(JsonFormatter())
        json_file_handler.addFilter(request_id_filter)
        root_logger.addHandler(json_file_handler)

    logger_instance = logging.getLogger("llm_module")
    logger_instance.info(
        f"日志系统初始化完成 [format={LOG_FORMAT_ENV}, level={LOG_LEVEL}]"
    )


def get_logger(name: str = "") -> logging.Logger:
    """
    获取分层日志器

    Args:
        name: 模块名称，如 "api", "services.llm_service"
              会自动加上 "llm_module." 前缀

    Returns:
        配置好的 Logger 实例

    Usage:
        logger = get_logger("api")            # -> llm_module.api
        logger = get_logger("services.llm")   # -> llm_module.services.llm
    """
    _ensure_configured()

    if name:
        logger_name = f"llm_module.{name}"
    else:
        logger_name = "llm_module"

    return logging.getLogger(logger_name)


def log_with_extra(logger_instance: logging.Logger, level: str, message: str,
                   **extra_fields):
    """
    带额外字段的结构化日志

    Args:
        logger_instance: 日志器实例
        level: 日志级别 (debug/info/warning/error)
        message: 日志消息
        **extra_fields: 额外字段，会合并到JSON日志中

    Usage:
        log_with_extra(logger, "info", "Agent执行完成",
                       agent="job_analysis", latency_ms=150, success=True)
    """
    getattr(logger_instance, level)(
        message,
        extra={"extra_fields": extra_fields},
    )


def check_slow_request(duration_seconds: float, request_id: str = "",
                       path: str = "", trace_id: str = ""):
    """
    慢请求告警检查

    Args:
        duration_seconds: 请求耗时（秒）
        request_id: 请求ID
        path: 请求路径
        trace_id: 追踪ID
    """
    if duration_seconds > SLOW_REQUEST_THRESHOLD:
        logger_instance = get_logger("slow_request")
        log_with_extra(
            logger_instance, "warning",
            f"慢请求检测 [duration={duration_seconds:.2f}s, "
            f"threshold={SLOW_REQUEST_THRESHOLD}s]",
            duration_seconds=round(duration_seconds, 3),
            threshold=SLOW_REQUEST_THRESHOLD,
            request_id=request_id or request_id_ctx.get("-"),
            trace_id=trace_id or trace_id_ctx.get("-"),
            path=path,
        )


# 向后兼容：模块级 logger，现有代码 from utils.logger import logger 不需修改
_ensure_configured()
logger = logging.getLogger("llm_module")
