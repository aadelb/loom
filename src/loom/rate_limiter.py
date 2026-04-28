"""Rate limiter for MCP tool calls (async + sync).

Sliding-window counter per tool category. Returns an error dict instead
of raising so callers can pass it straight back to the MCP client.

Supports optional SQLite persistence for rate limit state across restarts.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.rate_limiter")


def _get_persistence_db() -> Path | None:
    """Get the path to the rate limit persistence database if enabled.

    Returns None if persistence is disabled, otherwise returns the DB path.
    """
    from loom.config import get_config

    cfg = get_config()
    if not cfg.get("RATE_LIMIT_PERSIST", False):
        return None

    db_dir = Path.home() / ".loom"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "rate_limits.db"


def _init_persistence_db(db_path: Path) -> None:
    """Initialize the rate limit persistence database."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limits (
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                timestamp REAL NOT NULL,
                PRIMARY KEY (category, key, timestamp)
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to initialize persistence DB: %s", e)


def _load_from_db(
    db_path: Path, category: str, key: str, window_seconds: int
) -> list[float]:
    """Load timestamps for a key from the database (within the window)."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        now = time.time()
        cutoff = now - window_seconds

        cursor.execute(
            "SELECT timestamp FROM rate_limits WHERE category = ? AND key = ? AND timestamp > ? ORDER BY timestamp",
            (category, key, cutoff),
        )
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        logger.warning("Failed to load from persistence DB: %s", e)
        return []


def _save_to_db(db_path: Path, category: str, key: str, timestamp: float) -> None:
    """Save a single timestamp to the database."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO rate_limits (category, key, timestamp) VALUES (?, ?, ?)",
            (category, key, timestamp),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to save to persistence DB: %s", e)


def _cleanup_old_entries(db_path: Path, window_seconds: int) -> None:
    """Remove old entries from the database (>window_seconds old)."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cutoff = time.time() - window_seconds
        cursor.execute("DELETE FROM rate_limits WHERE timestamp <= ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to cleanup old entries: %s", e)


class RateLimiter:
    """Sliding-window rate limiter backed by asyncio.Lock with optional persistence."""

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._db_path = _get_persistence_db()
        if self._db_path:
            _init_persistence_db(self._db_path)

    async def check(self, key: str = "global") -> bool:
        """Return True if the call is within limits, False otherwise."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Load from DB if persistence is enabled
            if self._db_path:
                db_timestamps = _load_from_db(self._db_path, "global", key, self.window_seconds)
                window = [t for t in db_timestamps if t > cutoff]
            else:
                window = [t for t in self._calls[key] if t > cutoff]

            if len(window) >= self.max_calls:
                self._calls[key] = window
                return False

            window.append(now)
            self._calls[key] = window

            # Save to DB if persistence is enabled
            if self._db_path:
                _save_to_db(self._db_path, "global", key, now)
                _cleanup_old_entries(self._db_path, self.window_seconds)

            # Prune empty keys to prevent unbounded memory growth
            empty_keys = [k for k, v in self._calls.items() if not v]
            for k in empty_keys:
                del self._calls[k]

            return True

    def remaining(self, key: str = "global") -> int:
        now = time.time()
        cutoff = now - self.window_seconds

        if self._db_path:
            db_timestamps = _load_from_db(self._db_path, "global", key, self.window_seconds)
            window = [t for t in db_timestamps if t > cutoff]
        else:
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
    """Sliding-window rate limiter for synchronous functions (threading.Lock) with optional persistence."""

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._db_path = _get_persistence_db()
        if self._db_path:
            _init_persistence_db(self._db_path)

    def check(self, key: str = "global") -> bool:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Load from DB if persistence is enabled
            if self._db_path:
                db_timestamps = _load_from_db(self._db_path, "sync", key, self.window_seconds)
                window = [t for t in db_timestamps if t > cutoff]
            else:
                window = [t for t in self._calls[key] if t > cutoff]

            if len(window) >= self.max_calls:
                self._calls[key] = window
                return False

            window.append(now)
            self._calls[key] = window

            # Save to DB if persistence is enabled
            if self._db_path:
                _save_to_db(self._db_path, "sync", key, now)
                _cleanup_old_entries(self._db_path, self.window_seconds)

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
