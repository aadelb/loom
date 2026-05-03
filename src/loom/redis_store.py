"""Redis abstraction layer for distributed state management.

Provides a unified interface for rate limiting, caching, sessions, and cost tracking
across multiple uvicorn workers. Implements graceful degradation to in-memory storage
if Redis is unavailable.

Features:
  - Sliding window rate limiting (per user/category)
  - Key-value caching with TTL
  - Session storage with TTL
  - Cost tracking (per customer)
  - Distributed locking
  - Connection pooling with max 20 connections
  - Fallback to local dict if Redis unavailable
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from typing import Any

log = logging.getLogger("loom.redis_store")

# Try to import redis.asyncio (aioredis)
try:
    from redis.asyncio import ConnectionPool, Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    log = logging.getLogger("loom.redis_store")


class RedisStore:
    """Unified Redis abstraction for distributed state.

    Provides methods for rate limiting, caching, sessions, and cost tracking.
    Falls back to in-memory storage (dict) if Redis is unavailable.

    Thread-safe via asyncio.Lock for in-memory fallback.
    """

    def __init__(self, redis_url: str | None = None, max_connections: int = 20) -> None:
        """Initialize Redis store with optional fallback to in-memory.

        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379)
                      Set to empty string to force in-memory mode.
            max_connections: Max connections in pool (default: 20)
        """
        self._redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379"
        )
        self._max_connections = max_connections
        self._redis: Redis | None = None
        self._pool: ConnectionPool | None = None
        self._redis_available = False

        # In-memory fallback storage
        self._local_cache: dict[str, tuple[Any, float]] = {}  # (value, expiry_time)
        self._local_sessions: dict[str, tuple[dict[str, Any], float]] = {}
        self._local_rate_limits: dict[str, list[float]] = defaultdict(list)
        self._local_costs: dict[str, float] = defaultdict(float)
        self._local_locks: dict[str, bool] = {}
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Connect to Redis. Returns True if successful, False otherwise.

        On failure, falls back to in-memory storage silently.
        """
        if not REDIS_AVAILABLE:
            log.warning(
                "redis_module_not_installed "
                "install redis[hiredis] to enable Redis backend"
            )
            return False

        if self._redis_url == "":
            log.info("redis_disabled explicit empty url")
            return False

        try:
            self._pool = ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._max_connections,
                decode_responses=True,
            )
            self._redis = Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()  # type: ignore[misc]
            self._redis_available = True
            log.info("redis_connected url=%s pool_size=%d", self._redis_url, self._max_connections)
            return True
        except Exception as e:
            log.warning(
                "redis_connection_failed error=%s url=%s fallback=local_memory",
                str(e),
                self._redis_url,
            )
            self._redis = None
            self._pool = None
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        self._redis_available = False

    async def rate_limit_check(
        self,
        user_id: str,
        category: str,
        limit: int,
        window_seconds: int = 60,
    ) -> bool:
        """Check sliding window rate limit.

        Returns True if call is allowed, False if limit exceeded.

        Args:
            user_id: User identifier (can be "global" for shared limits)
            category: Tool category (search, deep, llm, fetch, etc)
            limit: Max calls allowed in window
            window_seconds: Time window in seconds (default: 60)

        Returns:
            True if within limits, False if exceeded.
        """
        key = f"ratelimit:{user_id}:{category}"
        now = time.time()
        cutoff = now - window_seconds

        if self._redis_available and self._redis:
            try:
                # Use Redis sorted set with timestamps as scores
                # Remove old entries
                await self._redis.zremrangebyscore(key, 0, cutoff)

                # Get current count
                count = await self._redis.zcard(key)

                if count >= limit:
                    return False

                # Add current timestamp
                await self._redis.zadd(key, {str(now): now})
                # Set expiry to window + 60s buffer
                await self._redis.expire(key, window_seconds + 60)

                return True
            except Exception as e:
                log.warning(
                    "redis_ratelimit_check_error user_id=%s category=%s error=%s",
                    user_id,
                    category,
                    str(e),
                )
                # Fall through to local fallback
                self._redis_available = False

        # Local in-memory fallback
        async with self._lock:
            timestamps = self._local_rate_limits[key]
            # Clean old timestamps
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= limit:
                self._local_rate_limits[key] = timestamps
                return False

            timestamps.append(now)
            self._local_rate_limits[key] = timestamps
            return True

    async def cache_get(self, key: str) -> Any | None:
        """Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise.
        """
        if self._redis_available and self._redis:
            try:
                value = await self._redis.get(key)
                if value:
                    return json.loads(value)  # type: ignore[no-any-return]
                return None
            except Exception as e:
                log.warning("redis_cache_get_error key=%s error=%s", key, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            if key in self._local_cache:
                value, expiry = self._local_cache[key]
                if time.time() <= expiry:
                    return value
                # Expired
                del self._local_cache[key]
            return None

    async def cache_set(
        self, key: str, value: Any, ttl_seconds: int = 3600
    ) -> None:
        """Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        """
        if self._redis_available and self._redis:
            try:
                await self._redis.setex(key, ttl_seconds, json.dumps(value))
                return
            except Exception as e:
                log.warning("redis_cache_set_error key=%s error=%s", key, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            expiry = time.time() + ttl_seconds
            self._local_cache[key] = (value, expiry)

    async def cache_delete(self, key: str) -> None:
        """Delete cached value.

        Args:
            key: Cache key
        """
        if self._redis_available and self._redis:
            try:
                await self._redis.delete(key)
                return
            except Exception as e:
                log.warning("redis_cache_delete_error key=%s error=%s", key, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            self._local_cache.pop(key, None)

    async def session_get(self, name: str) -> dict[str, Any] | None:
        """Get session data.

        Args:
            name: Session name

        Returns:
            Session data dict if exists, None otherwise.
        """
        key = f"session:{name}"

        if self._redis_available and self._redis:
            try:
                value = await self._redis.get(key)
                if value:
                    return json.loads(value)  # type: ignore[no-any-return]
                return None
            except Exception as e:
                log.warning("redis_session_get_error name=%s error=%s", name, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            if key in self._local_sessions:
                data, expiry = self._local_sessions[key]
                if time.time() <= expiry:
                    return data
                del self._local_sessions[key]
            return None

    async def session_set(
        self, name: str, data: dict[str, Any], ttl_seconds: int = 86400
    ) -> None:
        """Set session data with TTL.

        Args:
            name: Session name
            data: Session data dict
            ttl_seconds: Time-to-live in seconds (default: 24 hours)
        """
        key = f"session:{name}"

        if self._redis_available and self._redis:
            try:
                await self._redis.setex(key, ttl_seconds, json.dumps(data))
                return
            except Exception as e:
                log.warning("redis_session_set_error name=%s error=%s", name, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            expiry = time.time() + ttl_seconds
            self._local_sessions[key] = (data, expiry)

    async def session_delete(self, name: str) -> None:
        """Delete session.

        Args:
            name: Session name
        """
        key = f"session:{name}"

        if self._redis_available and self._redis:
            try:
                await self._redis.delete(key)
                return
            except Exception as e:
                log.warning("redis_session_delete_error name=%s error=%s", name, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            self._local_sessions.pop(key, None)

    async def cost_track(self, customer_id: str, amount: float) -> None:
        """Track cost for a customer (accumulate).

        Args:
            customer_id: Customer identifier
            amount: Amount to add (in dollars or cents, depending on system)
        """
        key = f"cost:{customer_id}"

        if self._redis_available and self._redis:
            try:
                await self._redis.incrbyfloat(key, amount)
                # Set expiry to 30 days for cost tracking
                await self._redis.expire(key, 30 * 86400)
                return
            except Exception as e:
                log.warning("redis_cost_track_error customer=%s error=%s", customer_id, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            self._local_costs[key] += amount

    async def cost_get(self, customer_id: str) -> float:
        """Get accumulated cost for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            Accumulated cost amount.
        """
        key = f"cost:{customer_id}"

        if self._redis_available and self._redis:
            try:
                value = await self._redis.get(key)
                return float(value) if value else 0.0
            except Exception as e:
                log.warning("redis_cost_get_error customer=%s error=%s", customer_id, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            return self._local_costs.get(key, 0.0)

    async def cost_reset(self, customer_id: str) -> None:
        """Reset accumulated cost for a customer.

        Args:
            customer_id: Customer identifier
        """
        key = f"cost:{customer_id}"

        if self._redis_available and self._redis:
            try:
                await self._redis.delete(key)
                return
            except Exception as e:
                log.warning("redis_cost_reset_error customer=%s error=%s", customer_id, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            self._local_costs.pop(key, None)

    async def lock_acquire(
        self, name: str, timeout_seconds: int = 30
    ) -> bool:
        """Acquire a distributed lock.

        Args:
            name: Lock name
            timeout_seconds: Lock expiry time (default: 30 seconds)

        Returns:
            True if lock acquired, False if already held.
        """
        key = f"lock:{name}"
        value = str(time.time())

        if self._redis_available and self._redis:
            try:
                # Use SET with NX (only if not exists) and EX (expiry)
                result = await self._redis.set(
                    key,
                    value,
                    nx=True,
                    ex=timeout_seconds,
                )
                return result is not None
            except Exception as e:
                log.warning("redis_lock_acquire_error name=%s error=%s", name, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            if name not in self._local_locks:
                self._local_locks[name] = True
                return True
            return False

    async def lock_release(self, name: str) -> None:
        """Release a distributed lock.

        Args:
            name: Lock name
        """
        key = f"lock:{name}"

        if self._redis_available and self._redis:
            try:
                await self._redis.delete(key)
                return
            except Exception as e:
                log.warning("redis_lock_release_error name=%s error=%s", name, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            self._local_locks.pop(name, None)

    async def health_check(self) -> dict[str, Any]:
        """Check Redis health and return stats.

        Returns:
            Dict with keys:
              - redis_available: bool
              - redis_url: str (masked password)
              - connected: bool
              - error: str (if applicable)
              - memory_usage_bytes: int (if Redis available)
              - connection_pool_size: int (if Redis available)
        """
        result: dict[str, Any] = {
            "redis_available": REDIS_AVAILABLE,
            "redis_url": self._redis_url.split("@")[-1]
            if "@" in self._redis_url
            else self._redis_url,
            "connected": self._redis_available,
        }

        if self._redis_available and self._redis:
            try:
                info = await self._redis.info("memory")
                result["memory_usage_bytes"] = info.get("used_memory", 0)
                result["memory_usage_mb"] = round(
                    info.get("used_memory", 0) / (1024 * 1024), 2
                )

                if self._pool:
                    result["connection_pool_size"] = self._pool.connection_kwargs.get(
                        "max_connections", self._max_connections
                    )

                return result
            except Exception as e:
                result["error"] = f"health_check_failed: {e!s}"
                self._redis_available = False

        return result

    async def cache_clear_prefix(self, prefix: str) -> int:
        """Clear all cache entries with given prefix.

        Args:
            prefix: Key prefix to match (e.g., "cache:research_*")

        Returns:
            Number of keys deleted.
        """
        if self._redis_available and self._redis:
            try:
                pattern = f"{prefix}*"
                cursor = 0
                count = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern)
                    if keys:
                        count += await self._redis.delete(*keys)
                    if cursor == 0:
                        break
                return count
            except Exception as e:
                log.warning("redis_cache_clear_prefix_error prefix=%s error=%s", prefix, str(e))
                self._redis_available = False

        # Local fallback
        async with self._lock:
            # Simple prefix matching (not glob-style)
            keys_to_delete = [k for k in self._local_cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._local_cache[k]
            return len(keys_to_delete)


# Global singleton instance
_redis_store: RedisStore | None = None
_store_lock = asyncio.Lock()


async def get_redis_store(
    redis_url: str | None = None, max_connections: int = 20
) -> RedisStore:
    """Get or create the global Redis store singleton.

    Args:
        redis_url: Redis connection URL (optional)
        max_connections: Max pool connections (default: 20)

    Returns:
        RedisStore instance.
    """
    global _redis_store

    if _redis_store is None:
        async with _store_lock:
            if _redis_store is None:
                _redis_store = RedisStore(redis_url, max_connections)
                await _redis_store.connect()

    return _redis_store


async def close_redis_store() -> None:
    """Close the global Redis store singleton."""
    global _redis_store

    if _redis_store:
        await _redis_store.close()
        _redis_store = None
