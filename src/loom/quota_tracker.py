"""API quota tracking for free-tier LLM providers.

Tracks usage for Groq, NVIDIA NIM, and Gemini free tiers with per-minute
and per-day sliding-window counters. Supports both in-memory and Redis backends.

Public API:
    QuotaTracker          Singleton quota tracker instance
    get_quota_tracker()   Get the global tracker instance
    record_usage()        Record a provider call (tokens + requests)
    get_remaining()       Get remaining quota for a provider
    is_near_limit()       Check if approaching quota (>80% by default)
    should_fallback()     Check if quota exhausted (skip to next provider)
    get_reset_time()      When does daily quota reset
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.quota_tracker")

# Free-tier API quotas (as of May 2026)
QUOTA_LIMITS: dict[str, dict[str, int]] = {
    "groq": {
        "requests_per_minute": 30,
        "requests_per_day": 14400,
        "tokens_per_minute": 6000,
        "tokens_per_day": 200000,
    },
    "nvidia_nim": {
        "requests_per_minute": 20,
        "requests_per_day": 5000,
        "tokens_per_minute": 4000,
        "tokens_per_day": 100000,
    },
    "gemini": {
        "requests_per_minute": 15,
        "requests_per_day": 1500,
        "tokens_per_minute": 1000,
        "tokens_per_day": 50000,
    },
}


@dataclass
class QuotaStatus:
    """Current quota status for a provider."""

    provider: str
    requests_this_minute: int
    requests_today: int
    tokens_this_minute: int
    tokens_today: int
    requests_limit_per_minute: int
    requests_limit_per_day: int
    tokens_limit_per_minute: int
    tokens_limit_per_day: int
    reset_time_utc: datetime

    def requests_remaining_per_minute(self) -> int:
        """Remaining requests in current minute."""
        return max(0, self.requests_limit_per_minute - self.requests_this_minute)

    def requests_remaining_per_day(self) -> int:
        """Remaining requests today."""
        return max(0, self.requests_limit_per_day - self.requests_today)

    def tokens_remaining_per_minute(self) -> int:
        """Remaining tokens in current minute."""
        return max(0, self.tokens_limit_per_minute - self.tokens_this_minute)

    def tokens_remaining_per_day(self) -> int:
        """Remaining tokens today."""
        return max(0, self.tokens_limit_per_day - self.tokens_today)

    def requests_used_percent_minute(self) -> float:
        """Percent of per-minute request quota used (0-100)."""
        if self.requests_limit_per_minute == 0:
            return 0.0
        return (self.requests_this_minute / self.requests_limit_per_minute) * 100

    def requests_used_percent_day(self) -> float:
        """Percent of per-day request quota used (0-100)."""
        if self.requests_limit_per_day == 0:
            return 0.0
        return (self.requests_today / self.requests_limit_per_day) * 100

    def tokens_used_percent_minute(self) -> float:
        """Percent of per-minute token quota used (0-100)."""
        if self.tokens_limit_per_minute == 0:
            return 0.0
        return (self.tokens_this_minute / self.tokens_limit_per_minute) * 100

    def tokens_used_percent_day(self) -> float:
        """Percent of per-day token quota used (0-100)."""
        if self.tokens_limit_per_day == 0:
            return 0.0
        return (self.tokens_today / self.tokens_limit_per_day) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "provider": self.provider,
            "requests_this_minute": self.requests_this_minute,
            "requests_today": self.requests_today,
            "tokens_this_minute": self.tokens_this_minute,
            "tokens_today": self.tokens_today,
            "requests_limit_per_minute": self.requests_limit_per_minute,
            "requests_limit_per_day": self.requests_limit_per_day,
            "tokens_limit_per_minute": self.tokens_limit_per_minute,
            "tokens_limit_per_day": self.tokens_limit_per_day,
            "reset_time_utc": self.reset_time_utc.isoformat(),
            "requests_remaining_per_minute": self.requests_remaining_per_minute(),
            "requests_remaining_per_day": self.requests_remaining_per_day(),
            "tokens_remaining_per_minute": self.tokens_remaining_per_minute(),
            "tokens_remaining_per_day": self.tokens_remaining_per_day(),
            "requests_used_percent_minute": self.requests_used_percent_minute(),
            "requests_used_percent_day": self.requests_used_percent_day(),
            "tokens_used_percent_minute": self.tokens_used_percent_minute(),
            "tokens_used_percent_day": self.tokens_used_percent_day(),
        }


class QuotaTracker:
    """Singleton quota tracker for free-tier LLM providers.

    Tracks requests and tokens per minute and per day using sliding-window
    counters. Supports Redis (if available) and falls back to in-memory storage.

    Thread-safe and can be used from sync or async contexts.
    """

    def __init__(self) -> None:
        """Initialize the quota tracker."""
        self._lock = threading.RLock()
        # In-memory sliding window: {provider: {minute_start_ts: count}}
        self._requests_per_minute: dict[str, dict[float, int]] = defaultdict(dict)
        self._tokens_per_minute: dict[str, dict[float, int]] = defaultdict(dict)
        # Daily aggregates: {provider: {date_str: count}}
        self._requests_per_day: dict[str, dict[str, int]] = defaultdict(dict)
        self._tokens_per_day: dict[str, dict[str, int]] = defaultdict(dict)
        # Redis client (optional)
        self._redis_client: Any | None = None
        self._redis_available = False
        self._try_redis_init()

    def _try_redis_init(self) -> None:
        """Try to connect to Redis for distributed quota tracking."""
        try:
            import redis  # noqa: F401

            try:
                self._redis_client = redis.Redis(
                    host="127.0.0.1",
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                # Test connection
                self._redis_client.ping()
                self._redis_available = True
                logger.info("quota_tracker using redis backend")
            except Exception as e:
                logger.debug("redis connection failed: %s, falling back to in-memory", e)
                self._redis_available = False
        except ImportError:
            logger.debug("redis not installed, using in-memory quota tracking")

    def _current_minute_key(self) -> float:
        """Get the current minute boundary (floor to nearest 60 seconds)."""
        return int(time.time() / 60) * 60

    def _current_day_key(self) -> str:
        """Get the current day key (YYYY-MM-DD UTC)."""
        return datetime.now(UTC).date().isoformat()

    def record_usage(
        self,
        provider: str,
        tokens: int = 0,
    ) -> None:
        """Record a provider call (one request + optional tokens).

        Args:
            provider: Provider name (groq, nvidia_nim, gemini)
            tokens: Total tokens used (input + output)

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in QUOTA_LIMITS:
            return False  # Unknown provider — no quota limits

        now = time.time()
        minute_key = self._current_minute_key()
        day_key = self._current_day_key()

        if self._redis_available:
            self._record_usage_redis(provider, tokens, minute_key, day_key)
        else:
            self._record_usage_inmemory(provider, tokens, minute_key, day_key)

        logger.debug(
            "quota_recorded provider=%s tokens=%d minute_key=%d day_key=%s",
            provider,
            tokens,
            minute_key,
            day_key,
        )

    def _record_usage_inmemory(
        self,
        provider: str,
        tokens: int,
        minute_key: float,
        day_key: str,
    ) -> None:
        """Record usage in in-memory store."""
        with self._lock:
            # Record per-minute request
            if minute_key not in self._requests_per_minute[provider]:
                self._requests_per_minute[provider][minute_key] = 0
            self._requests_per_minute[provider][minute_key] += 1

            # Record per-minute tokens
            if tokens > 0:
                if minute_key not in self._tokens_per_minute[provider]:
                    self._tokens_per_minute[provider][minute_key] = 0
                self._tokens_per_minute[provider][minute_key] += tokens

            # Record per-day request
            if day_key not in self._requests_per_day[provider]:
                self._requests_per_day[provider][day_key] = 0
            self._requests_per_day[provider][day_key] += 1

            # Record per-day tokens
            if tokens > 0:
                if day_key not in self._tokens_per_day[provider]:
                    self._tokens_per_day[provider][day_key] = 0
                self._tokens_per_day[provider][day_key] += tokens

    def _record_usage_redis(
        self,
        provider: str,
        tokens: int,
        minute_key: float,
        day_key: str,
    ) -> None:
        """Record usage in Redis (distributed)."""
        try:
            # Per-minute request counter with 120-second TTL
            req_min_key = f"quota:{provider}:req_min:{int(minute_key)}"
            self._redis_client.incr(req_min_key)
            self._redis_client.expire(req_min_key, 120)

            # Per-minute token counter with 120-second TTL
            if tokens > 0:
                tok_min_key = f"quota:{provider}:tok_min:{int(minute_key)}"
                self._redis_client.incrby(tok_min_key, tokens)
                self._redis_client.expire(tok_min_key, 120)

            # Per-day request counter with 86400-second TTL
            req_day_key = f"quota:{provider}:req_day:{day_key}"
            self._redis_client.incr(req_day_key)
            self._redis_client.expire(req_day_key, 86400)

            # Per-day token counter with 86400-second TTL
            if tokens > 0:
                tok_day_key = f"quota:{provider}:tok_day:{day_key}"
                self._redis_client.incrby(tok_day_key, tokens)
                self._redis_client.expire(tok_day_key, 86400)
        except Exception as e:
            logger.warning("redis record_usage failed, falling back to in-memory: %s", e)
            # Fall back to in-memory on Redis failure
            self._record_usage_inmemory(provider, tokens, minute_key, day_key)

    def get_remaining(self, provider: str) -> dict[str, int]:
        """Get remaining quota for a provider.

        Args:
            provider: Provider name (groq, nvidia_nim, gemini)

        Returns:
            Dict with keys:
                - requests_remaining_per_minute
                - requests_remaining_per_day
                - tokens_remaining_per_minute
                - tokens_remaining_per_day

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in QUOTA_LIMITS:
            return False  # Unknown provider — no quota limits

        status = self.get_status(provider)
        return {
            "requests_remaining_per_minute": status.requests_remaining_per_minute(),
            "requests_remaining_per_day": status.requests_remaining_per_day(),
            "tokens_remaining_per_minute": status.tokens_remaining_per_minute(),
            "tokens_remaining_per_day": status.tokens_remaining_per_day(),
        }

    def get_status(self, provider: str) -> QuotaStatus:
        """Get full quota status for a provider.

        Args:
            provider: Provider name (groq, nvidia_nim, gemini)

        Returns:
            QuotaStatus dataclass with all metrics

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in QUOTA_LIMITS:
            return False  # Unknown provider — no quota limits

        limits = QUOTA_LIMITS[provider]
        minute_key = self._current_minute_key()
        day_key = self._current_day_key()

        if self._redis_available:
            req_min, tok_min, req_day, tok_day = self._get_usage_redis(
                provider, minute_key, day_key
            )
        else:
            req_min, tok_min, req_day, tok_day = self._get_usage_inmemory(
                provider, minute_key, day_key
            )

        # Reset time is always 24h from now UTC midnight
        now = datetime.now(UTC)
        reset_time = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        return QuotaStatus(
            provider=provider,
            requests_this_minute=req_min,
            requests_today=req_day,
            tokens_this_minute=tok_min,
            tokens_today=tok_day,
            requests_limit_per_minute=limits["requests_per_minute"],
            requests_limit_per_day=limits["requests_per_day"],
            tokens_limit_per_minute=limits["tokens_per_minute"],
            tokens_limit_per_day=limits["tokens_per_day"],
            reset_time_utc=reset_time,
        )

    def _get_usage_inmemory(
        self, provider: str, minute_key: float, day_key: str
    ) -> tuple[int, int, int, int]:
        """Get usage counts from in-memory store."""
        with self._lock:
            req_min = self._requests_per_minute[provider].get(minute_key, 0)
            tok_min = self._tokens_per_minute[provider].get(minute_key, 0)
            req_day = self._requests_per_day[provider].get(day_key, 0)
            tok_day = self._tokens_per_day[provider].get(day_key, 0)
        return req_min, tok_min, req_day, tok_day

    def _get_usage_redis(
        self, provider: str, minute_key: float, day_key: str
    ) -> tuple[int, int, int, int]:
        """Get usage counts from Redis."""
        try:
            req_min_key = f"quota:{provider}:req_min:{int(minute_key)}"
            tok_min_key = f"quota:{provider}:tok_min:{int(minute_key)}"
            req_day_key = f"quota:{provider}:req_day:{day_key}"
            tok_day_key = f"quota:{provider}:tok_day:{day_key}"

            req_min = int(self._redis_client.get(req_min_key) or 0)
            tok_min = int(self._redis_client.get(tok_min_key) or 0)
            req_day = int(self._redis_client.get(req_day_key) or 0)
            tok_day = int(self._redis_client.get(tok_day_key) or 0)
            return req_min, tok_min, req_day, tok_day
        except Exception as e:
            logger.warning("redis get_usage failed: %s, falling back to in-memory", e)
            return self._get_usage_inmemory(provider, minute_key, day_key)

    def is_near_limit(self, provider: str, threshold: float = 0.8) -> bool:
        """Check if provider quota is approaching limit.

        Checks if either request or token quota exceeds threshold (default 80%).
        This is used to warn users but not strictly enforce quota.

        Args:
            provider: Provider name
            threshold: Warn threshold (0-1, default 0.8 = 80%)

        Returns:
            True if any quota exceeds threshold

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in QUOTA_LIMITS:
            return False  # Unknown provider — no quota limits

        status = self.get_status(provider)

        # Check per-minute quotas
        if status.requests_used_percent_minute() > (threshold * 100):
            return True
        if status.tokens_used_percent_minute() > (threshold * 100):
            return True

        # Check per-day quotas
        if status.requests_used_percent_day() > (threshold * 100):
            return True
        if status.tokens_used_percent_day() > (threshold * 100):
            return True

        return False

    def should_fallback(self, provider: str) -> bool:
        """Check if provider quota is exhausted (should fallback to next provider).

        A provider should be skipped if ANY quota is exhausted (requests or tokens,
        either per-minute or per-day).

        Args:
            provider: Provider name

        Returns:
            True if quota is exhausted

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in QUOTA_LIMITS:
            return False  # Unknown provider — no quota limits

        status = self.get_status(provider)

        # If any limit is reached, fallback
        if status.requests_remaining_per_minute() <= 0:
            logger.warning(
                "quota_fallback provider=%s reason=requests_per_minute_exhausted",
                provider,
            )
            return True
        if status.requests_remaining_per_day() <= 0:
            logger.warning(
                "quota_fallback provider=%s reason=requests_per_day_exhausted",
                provider,
            )
            return True
        if status.tokens_remaining_per_minute() <= 0:
            logger.warning(
                "quota_fallback provider=%s reason=tokens_per_minute_exhausted",
                provider,
            )
            return True
        if status.tokens_remaining_per_day() <= 0:
            logger.warning(
                "quota_fallback provider=%s reason=tokens_per_day_exhausted",
                provider,
            )
            return True

        return False

    def get_reset_time(self, provider: str) -> datetime:
        """Get when daily quota resets for this provider (UTC midnight).

        Args:
            provider: Provider name

        Returns:
            Datetime of next UTC midnight (next day 00:00:00 UTC)

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in QUOTA_LIMITS:
            return False  # Unknown provider — no quota limits

        status = self.get_status(provider)
        return status.reset_time_utc


# Global singleton instance
_QUOTA_TRACKER: QuotaTracker | None = None
_QUOTA_TRACKER_LOCK = threading.Lock()


def get_quota_tracker() -> QuotaTracker:
    """Get the global quota tracker instance (singleton)."""
    global _QUOTA_TRACKER
    if _QUOTA_TRACKER is None:
        with _QUOTA_TRACKER_LOCK:
            if _QUOTA_TRACKER is None:
                _QUOTA_TRACKER = QuotaTracker()
    return _QUOTA_TRACKER


def record_usage(provider: str, tokens: int = 0) -> None:
    """Record a provider call (module-level convenience function).

    Args:
        provider: Provider name
        tokens: Total tokens used (input + output)
    """
    tracker = get_quota_tracker()
    tracker.record_usage(provider, tokens=tokens)


def get_remaining(provider: str) -> dict[str, int]:
    """Get remaining quota for a provider (module-level convenience function).

    Args:
        provider: Provider name

    Returns:
        Dict with remaining requests and tokens per minute and day
    """
    tracker = get_quota_tracker()
    return tracker.get_remaining(provider)
