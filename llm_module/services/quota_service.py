"""
资源配额服务 - 每用户每日调用次数/Token用量限制
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional
from datetime import datetime

from utils.config import QUOTA_CONFIG
from utils.logger import get_logger
logger = get_logger("services.quota_service")


class QuotaService:
    """资源配额服务 - 内存缓存 + 数据库持久化"""

    def __init__(self):
        self._enabled = QUOTA_CONFIG["enabled"]
        self._default_daily_calls = QUOTA_CONFIG["default_daily_calls"]
        self._default_daily_tokens = QUOTA_CONFIG["default_daily_tokens"]
        self._admin_daily_calls = QUOTA_CONFIG["admin_daily_calls"]
        self._admin_daily_tokens = QUOTA_CONFIG["admin_daily_tokens"]
        self._db = None  # 懒加载
        # 内存缓存: (user_id, date) -> {daily_calls, daily_tokens, timestamp}
        self._usage_cache: Dict[tuple, Dict[str, Any]] = {}
        self._cache_ttl = 60  # 缓存有效期（秒）

    def _get_db(self):
        """懒加载数据库服务"""
        if self._db is None:
            from services.db_service import get_db_service
            self._db = get_db_service()
        return self._db

    def _today(self) -> str:
        """获取今日日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_call_limit(self, role: str = "") -> int:
        """获取调用次数限额"""
        if role == "manager":
            return self._admin_daily_calls
        return self._default_daily_calls

    def _get_token_limit(self, role: str = "") -> int:
        """获取Token用量限额"""
        if role == "manager":
            return self._admin_daily_tokens
        return self._default_daily_tokens

    def _is_cache_valid(self, user_id: int, date: str) -> bool:
        """检查缓存是否有效"""
        key = (user_id, date)
        entry = self._usage_cache.get(key)
        if not entry:
            return False
        return (time.time() - entry["timestamp"]) < self._cache_ttl

    def _get_or_create_usage(self, user_id: int, date: str) -> Dict[str, Any]:
        """获取或创建用户每日使用量"""
        key = (user_id, date)

        # 先检查缓存
        if self._is_cache_valid(user_id, date):
            return self._usage_cache[key]

        # 从数据库读取
        db = self._get_db()
        usage = db.get_user_daily_usage(user_id, date)

        if usage:
            result = {
                "daily_calls": usage.get("daily_calls", 0),
                "daily_tokens": usage.get("daily_tokens", 0),
                "timestamp": time.time(),
            }
        else:
            result = {
                "daily_calls": 0,
                "daily_tokens": 0,
                "timestamp": time.time(),
            }

        self._usage_cache[key] = result
        return result

    def check_quota(self, user_id: int, tokens_estimate: int = 0,
                    role: str = "") -> bool:
        """
        检查用户是否在配额内
        返回True表示允许，False表示超限
        """
        if not self._enabled:
            return True

        if user_id == 0:
            return True  # 匿名用户不限配额（由限流器控制）

        date = self._today()
        usage = self._get_or_create_usage(user_id, date)

        call_limit = self._get_call_limit(role)
        token_limit = self._get_token_limit(role)

        if usage["daily_calls"] >= call_limit:
            logger.info(f"用户{user_id}调用次数超限: {usage['daily_calls']}/{call_limit}")
            return False

        if tokens_estimate > 0 and usage["daily_tokens"] + tokens_estimate > token_limit:
            logger.info(f"用户{user_id}Token用量超限: {usage['daily_tokens']}/{token_limit}")
            return False

        return True

    def record_usage(self, user_id: int, tokens_used: int = 0) -> None:
        """记录用户使用量"""
        if not self._enabled or user_id == 0:
            return

        date = self._today()
        key = (user_id, date)
        usage = self._get_or_create_usage(user_id, date)

        # 更新内存缓存
        usage["daily_calls"] += 1
        usage["daily_tokens"] += tokens_used
        usage["timestamp"] = time.time()
        self._usage_cache[key] = usage

        # 异步持久化到数据库（fire-and-forget）
        try:
            db = self._get_db()
            db.upsert_user_usage(
                user_id, date,
                daily_calls=usage["daily_calls"],
                daily_tokens=usage["daily_tokens"],
            )
        except Exception as e:
            logger.warning(f"配额持久化失败: {e}")

    def get_usage(self, user_id: int, role: str = "") -> Dict[str, Any]:
        """获取用户使用情况"""
        date = self._today()
        usage = self._get_or_create_usage(user_id, date)

        call_limit = self._get_call_limit(role)
        token_limit = self._get_token_limit(role)

        return {
            "daily_calls": usage["daily_calls"],
            "daily_tokens": usage["daily_tokens"],
            "call_limit": call_limit,
            "token_limit": token_limit,
            "remaining_calls": max(0, call_limit - usage["daily_calls"]),
            "remaining_tokens": max(0, token_limit - usage["daily_tokens"]),
            "quota_date": date,
        }

    def reset_daily_usage(self) -> int:
        """重置所有用户的每日使用量（通常在日期变更时调用）"""
        # 清除所有缓存
        count = len(self._usage_cache)
        self._usage_cache.clear()
        logger.info(f"已清除{count}条配额缓存")
        return count


# 单例
_quota_service: Any = None


def get_quota_service() -> QuotaService:
    """获取配额服务单例"""
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
    return _quota_service
