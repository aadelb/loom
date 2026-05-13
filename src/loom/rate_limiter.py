"""Rate limiter for MCP tool calls (async + sync).

Sliding-window counter per tool category. Supports per-user rate limiting with
tier-based limits (free, pro, enterprise). Returns an error dict instead of
raising so callers can pass it straight back to the MCP client.

Supports optional Redis as primary backend (distributed, fast) with SQLite
persistence fallback for rate limit state across restarts.
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
from typing import Any, Literal

logger = logging.getLogger("loom.rate_limiter")

# Tier-based rate limits: (requests per minute, requests per day)
TIER_LIMITS = {
    "free": {"per_min": 10, "per_day": 100},
    "pro": {"per_min": 60, "per_day": 10000},
    "enterprise": {"per_min": 300, "per_day": None},  # None = unlimited
}

TierType = Literal["free", "pro", "enterprise"]


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
                user_id TEXT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                timestamp REAL NOT NULL,
                PRIMARY KEY (user_id, category, key, timestamp)
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to initialize persistence DB: %s", e)


def _load_from_db(
    db_path: Path,
    category: str,
    key: str,
    window_seconds: int,
    user_id: str | None = None,
) -> list[float]:
    """Load timestamps for a key from the database (within the window)."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        now = time.time()
        cutoff = now - window_seconds

        if user_id is None:
            cursor.execute(
                "SELECT timestamp FROM rate_limits WHERE user_id IS NULL AND category = ? AND key = ? AND timestamp > ? ORDER BY timestamp",
                (category, key, cutoff),
            )
        else:
            cursor.execute(
                "SELECT timestamp FROM rate_limits WHERE user_id = ? AND category = ? AND key = ? AND timestamp > ? ORDER BY timestamp",
                (user_id, category, key, cutoff),
            )
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        logger.warning("Failed to load from persistence DB: %s", e)
        return []


def _save_to_db(
    db_path: Path,
    category: str,
    key: str,
    timestamp: float,
    user_id: str | None = None,
) -> None:
    """Save a single timestamp to the database."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO rate_limits (user_id, category, key, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, category, key, timestamp),
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
    """Sliding-window rate limiter backed by asyncio.Lock with Redis primary and SQLite fallback.

    Supports per-user rate limiting with tier-based limits.
    """

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._db_path = _get_persistence_db()
        if self._db_path:
            _init_persistence_db(self._db_path)

    async def check(
        self,
        category: str = "global",
        key: str = "global",
        user_id: str | None = None,
        tier: TierType = "free",
    ) -> bool:
        """Return True if the call is within limits, False otherwise.

        Args:
            category: Tool category (search, deep, llm, fetch, etc)
            key: Additional key for bucketing (typically user_id or global)
            user_id: User ID for per-user rate limiting. If None, use global limits.
            tier: User tier (free, pro, enterprise) for determining limits.

        Returns:
            True if call is allowed, False if rate limit exceeded.
        """
        # Get tier limits
        tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        max_per_min = tier_limits["per_min"]

        # Try Redis first (distributed, fast)
        try:
            from loom.redis_store import get_redis_store

            store = await get_redis_store()
            if store._redis_available:
                # Redis is available and connected
                allowed = await store.rate_limit_check(
                    user_id or "global", category, max_per_min, self.window_seconds
                )
                if not allowed:
                    logger.debug(
                        "redis_ratelimit_exceeded user_id=%s category=%s tier=%s",
                        user_id,
                        category,
                        tier,
                    )
                    return False
                logger.debug(
                    "redis_ratelimit_allowed user_id=%s category=%s tier=%s",
                    user_id,
                    category,
                    tier,
                )
                return True
        except Exception as e:
            logger.debug(
                "redis_ratelimit_fallback error=%s user_id=%s category=%s",
                str(e),
                user_id,
                category,
            )
            pass  # Fall back to SQLite/in-memory

        # SQLite + in-memory fallback (existing logic)
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Composite key for tracking: (user_id, category)
            tracking_key = f"{user_id}:{category}"

            # Load from DB if persistence is enabled
            if self._db_path:
                db_timestamps = await asyncio.to_thread(
                    _load_from_db,
                    self._db_path,
                    category,
                    tracking_key,
                    self.window_seconds,
                    user_id,
                )
                window = [t for t in db_timestamps if t > cutoff]
            else:
                window = [t for t in self._calls[tracking_key] if t > cutoff]

            if len(window) >= max_per_min:
                self._calls[tracking_key] = window
                return False

            window.append(now)
            self._calls[tracking_key] = window

            # Save to DB if persistence is enabled
            if self._db_path:
                await asyncio.to_thread(
                    _save_to_db,
                    self._db_path,
                    category,
                    tracking_key,
                    now,
                    user_id,
                )
                await asyncio.to_thread(
                    _cleanup_old_entries, self._db_path, self.window_seconds
                )

            # Prune empty keys to prevent unbounded memory growth
            empty_keys = [k for k, v in self._calls.items() if not v]
            for k in empty_keys:
                del self._calls[k]

            return True

    async def remaining(
        self,
        category: str = "global",
        key: str = "global",
        user_id: str | None = None,
        tier: TierType = "free",
    ) -> int:
        """Return the number of calls remaining in the current window.

        Args:
            category: Tool category (search, deep, llm, fetch, etc)
            key: Additional key for bucketing (typically user_id or global)
            user_id: User ID for per-user rate limiting. If None, use global limits.
            tier: User tier (free, pro, enterprise) for determining limits.

        Returns:
            Number of calls remaining in the window.
        """
        async with self._lock:
            now = time.time()

            # Get tier limits
            tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
            max_per_min = tier_limits["per_min"]

            cutoff = now - self.window_seconds
            tracking_key = f"{user_id}:{category}"

            if self._db_path:
                db_timestamps = await asyncio.to_thread(
                    _load_from_db,
                    self._db_path,
                    category,
                    tracking_key,
                    self.window_seconds,
                    user_id,
                )
                window = [t for t in db_timestamps if t > cutoff]
            else:
                window = [t for t in self._calls[tracking_key] if t > cutoff]

            return max(0, max_per_min - len(window))


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

    Note: Does not extract user_id from function arguments. Use
    check_rate_limit_with_user for per-user limiting in tool functions.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = _get_limiter(category)
            if not await limiter.check(category=category):
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

        wrapper._rate_limited = True
        return wrapper

    return decorator


async def check_rate_limit(category: str) -> dict[str, Any] | None:
    """Check rate limit for a category. Returns error dict if exceeded, None if OK."""
    limiter = _get_limiter(category)
    if not await limiter.check(category=category):
        logger.warning("rate_limit_exceeded category=%s", category)
        return {
            "error": "rate_limit_exceeded",
            "category": category,
            "retry_after_seconds": limiter.window_seconds,
        }
    return None


async def check_rate_limit_with_user(
    category: str, user_id: str | None = None, tier: TierType = "free"
) -> dict[str, Any] | None:
    """Check per-user rate limit. Returns error dict if exceeded, None if OK.

    Args:
        category: Tool category (search, deep, llm, fetch, etc)
        user_id: User ID for per-user limiting. If None, falls back to global limits.
        tier: User tier (free, pro, enterprise).

    Returns:
        Error dict with rate limit details if exceeded, None if OK.
    """
    limiter = _get_limiter(category)
    key = user_id or "global"
    if not await limiter.check(
        category=category, key=key, user_id=user_id, tier=tier
    ):
        tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        logger.warning(
            "rate_limit_exceeded category=%s user_id=%s tier=%s",
            category,
            user_id,
            tier,
        )
        return {
            "error": "rate_limit_exceeded",
            "category": category,
            "user_id": user_id,
            "tier": tier,
            "limit_per_min": tier_limits["per_min"],
            "retry_after_seconds": limiter.window_seconds,
        }
    return None


class SyncRateLimiter:
    """Sliding-window rate limiter for synchronous functions (threading.Lock) with optional persistence.

    Supports per-user rate limiting with tier-based limits.
    """

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._db_path = _get_persistence_db()
        if self._db_path:
            _init_persistence_db(self._db_path)

    def check(
        self,
        category: str = "global",
        key: str = "global",
        user_id: str | None = None,
        tier: TierType = "free",
    ) -> bool:
        """Return True if the call is within limits, False otherwise.

        Args:
            category: Tool category (search, deep, llm, fetch, etc)
            key: Additional key for bucketing (typically user_id or global)
            user_id: User ID for per-user rate limiting. If None, use global limits.
            tier: User tier (free, pro, enterprise) for determining limits.

        Returns:
            True if call is allowed, False if rate limit exceeded.
        """
        with self._lock:
            now = time.time()

            # Get tier limits
            tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
            max_per_min = tier_limits["per_min"]

            # Use per-minute limits
            cutoff = now - self.window_seconds

            # Composite key for tracking: (user_id, category)
            tracking_key = f"{user_id}:{category}"

            # Load from DB if persistence is enabled
            if self._db_path:
                db_timestamps = _load_from_db(
                    self._db_path, category, tracking_key, self.window_seconds, user_id
                )
                window = [t for t in db_timestamps if t > cutoff]
            else:
                window = [t for t in self._calls[tracking_key] if t > cutoff]

            if len(window) >= max_per_min:
                self._calls[tracking_key] = window
                return False

            window.append(now)
            self._calls[tracking_key] = window

            # Save to DB if persistence is enabled
            if self._db_path:
                _save_to_db(
                    self._db_path, category, tracking_key, now, user_id
                )
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
            if not limiter.check(category=category):
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

        wrapper._rate_limited = True
        return wrapper

    return decorator


def check_sync_rate_limit_with_user(
    category: str, user_id: str | None = None, tier: TierType = "free"
) -> dict[str, Any] | None:
    """Check per-user rate limit (sync). Returns error dict if exceeded, None if OK.

    Args:
        category: Tool category (search, deep, llm, fetch, etc)
        user_id: User ID for per-user limiting. If None, falls back to global limits.
        tier: User tier (free, pro, enterprise).

    Returns:
        Error dict with rate limit details if exceeded, None if OK.
    """
    limiter = _get_sync_limiter(category)
    key = user_id or "global"
    if not limiter.check(category=category, key=key, user_id=user_id, tier=tier):
        tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        logger.warning(
            "rate_limit_exceeded category=%s user_id=%s tier=%s",
            category,
            user_id,
            tier,
        )
        return {
            "error": "rate_limit_exceeded",
            "category": category,
            "user_id": user_id,
            "tier": tier,
            "limit_per_min": tier_limits["per_min"],
            "retry_after_seconds": limiter.window_seconds,
        }
    return None


def reset_all() -> None:
    """Reset all limiters (for tests)."""
    _limiters.clear()
    _sync_limiters.clear()
