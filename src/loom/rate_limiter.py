"""Rate limiter for MCP tool calls (async + sync).

Sliding-window counter per tool category. Returns an error dict instead
of raising so callers can pass it straight back to the MCP client.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("loom.rate_limiter")


class RateLimiter:
    """Sliding-window rate limiter backed by asyncio.Lock."""

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str = "global") -> bool:
        """Return True if the call is within limits, False otherwise."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            window = [t for t in self._calls[key] if t > cutoff]
            if len(window) >= self.max_calls:
                self._calls[key] = window
                return False
            window.append(now)
            self._calls[key] = window
            # Prune empty keys to prevent unbounded memory growth
            empty_keys = [k for k, v in self._calls.items() if not v]
            for k in empty_keys:
                del self._calls[k]
            return True

    def remaining(self, key: str = "global") -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        window = [t for t in self._calls[key] if t > cutoff]
        return max(0, self.max_calls - len(window))


# Global limiters keyed by tool category — initialised lazily by _get_limiter.
_limiters: dict[str, RateLimiter] = {}


def _get_limiter(name: str) -> RateLimiter:
    if name not in _limiters:
        from loom.config import get_config

        cfg = get_config()
        defaults = {
            "search": cfg.get("RATE_LIMIT_SEARCH_PER_MIN", 30),
            "deep": cfg.get("RATE_LIMIT_DEEP_PER_MIN", 5),
            "llm": cfg.get("RATE_LIMIT_LLM_PER_MIN", 20),
            "fetch": cfg.get("RATE_LIMIT_FETCH_PER_MIN", 60),
        }
        limit = defaults.get(name, 30)
        _limiters[name] = RateLimiter(max_calls=limit, window_seconds=60)
    return _limiters[name]


def rate_limited(category: str) -> Callable[..., Any]:
    """Decorator that rate-limits an async tool function.

    When the limit is exceeded the decorated function returns
    ``{"error": "rate_limit_exceeded", ...}`` instead of running.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = _get_limiter(category)
            if not await limiter.check():
                logger.warning(
                    "rate_limit_exceeded category=%s function=%s",
                    category,
                    fn.__name__,
                )
                return {
                    "error": "rate_limit_exceeded",
                    "category": category,
                    "retry_after_seconds": limiter.window_seconds,
                }
            return await fn(*args, **kwargs)

        return wrapper

    return decorator


async def check_rate_limit(category: str) -> dict[str, Any] | None:
    """Check rate limit for a category. Returns error dict if exceeded, None if OK."""
    limiter = _get_limiter(category)
    if not await limiter.check():
        logger.warning("rate_limit_exceeded category=%s", category)
        return {
            "error": "rate_limit_exceeded",
            "category": category,
            "retry_after_seconds": limiter.window_seconds,
        }
    return None


class SyncRateLimiter:
    """Sliding-window rate limiter for synchronous functions (threading.Lock)."""

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str = "global") -> bool:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            window = [t for t in self._calls[key] if t > cutoff]
            if len(window) >= self.max_calls:
                self._calls[key] = window
                return False
            window.append(now)
            self._calls[key] = window
            empty_keys = [k for k, v in self._calls.items() if not v]
            for k in empty_keys:
                del self._calls[k]
            return True


_sync_limiters: dict[str, SyncRateLimiter] = {}


def _get_sync_limiter(name: str) -> SyncRateLimiter:
    if name not in _sync_limiters:
        from loom.config import get_config

        cfg = get_config()
        defaults = {
            "search": cfg.get("RATE_LIMIT_SEARCH_PER_MIN", 30),
            "deep": cfg.get("RATE_LIMIT_DEEP_PER_MIN", 5),
            "llm": cfg.get("RATE_LIMIT_LLM_PER_MIN", 20),
            "fetch": cfg.get("RATE_LIMIT_FETCH_PER_MIN", 60),
        }
        limit = defaults.get(name, 30)
        _sync_limiters[name] = SyncRateLimiter(max_calls=limit, window_seconds=60)
    return _sync_limiters[name]


def sync_rate_limited(category: str) -> Callable[..., Any]:
    """Decorator that rate-limits a sync tool function."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = _get_sync_limiter(category)
            if not limiter.check():
                logger.warning(
                    "rate_limit_exceeded category=%s function=%s",
                    category,
                    fn.__name__,
                )
                return {
                    "error": "rate_limit_exceeded",
                    "category": category,
                    "retry_after_seconds": limiter.window_seconds,
                }
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def reset_all() -> None:
    """Reset all limiters (for tests)."""
    _limiters.clear()
    _sync_limiters.clear()
