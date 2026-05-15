"""Idempotency layer for financial operations in billing system.

Prevents double-charging and duplicate transactions by:
- Generating idempotency keys (SHA-256 hash of operation params)
- Checking if operation was previously executed
- Caching results with 24-hour TTL
- Returning cached result on duplicate requests

Uses Redis (with in-memory fallback) for distributed idempotency.
Supports graceful degradation when Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

log = logging.getLogger("loom.billing.idempotency")


def generate_idempotency_key(
    user_id: str,
    operation: str,
    params: dict[str, Any] | None = None,
    timestamp_bucket: int | None = None,
) -> str:
    """Generate idempotency key using SHA-256.

    Combines user_id, operation, params, and timestamp_bucket into
    a deterministic SHA-256 hash. The timestamp_bucket groups requests
    into hourly windows (optional) for finer granularity control.

    Args:
        user_id: Customer/user identifier
        operation: Operation type (e.g., 'stripe_charge', 'credit_deduct')
        params: Operation parameters dict (JSON-serializable)
        timestamp_bucket: Optional Unix timestamp (default: current hourly bucket)

    Returns:
        SHA-256 hex digest (64 character string)

    Example:
        >>> key = generate_idempotency_key('cust_123', 'stripe_charge', {'amount': 9999})
        >>> len(key)
        64
    """
    if params is None:
        params = {}

    if timestamp_bucket is None:
        # Default: hourly bucket (3600 seconds)
        timestamp_bucket = int(time.time()) // 3600

    # Build deterministic input string
    params_str = json.dumps(params, sort_keys=True, default=str)
    content = f"{user_id}:{operation}:{params_str}:{timestamp_bucket}"

    # Return SHA-256 hex digest
    return hashlib.sha256(content.encode()).hexdigest()


class IdempotencyManager:
    """Manages idempotency checks and result caching for financial operations.

    Integrates with Redis (or in-memory fallback) to prevent duplicate
    charges and transactions. Automatically handles TTL expiry and graceful
    degradation if Redis is unavailable.
    """

    # Default TTL for idempotency records (24 hours)
    DEFAULT_TTL_SECONDS = 86400

    # Cache key prefix
    CACHE_PREFIX = "idempotency"

    def __init__(self, redis_store: Any | None = None) -> None:
        """Initialize idempotency manager.

        Args:
            redis_store: Optional RedisStore instance. If None, will attempt
                        to import and use the global singleton.
        """
        self._redis_store = redis_store
        self._initialized = False

    async def _ensure_redis(self) -> Any | None:
        """Lazily initialize Redis store.

        Returns:
            RedisStore instance if available, None if Redis unavailable.
        """
        if self._initialized:
            return self._redis_store

        if self._redis_store is None:
            try:
                from loom.redis_store import get_redis_store
                self._redis_store = await get_redis_store()
            except Exception as e:
                log.warning("redis_initialization_failed fallback=none error=%s", str(e))
                self._redis_store = None

        self._initialized = True
        return self._redis_store

    async def check_and_store(
        self,
        idempotency_key: str,
        operation_result: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any] | None:
        """Check if operation was already executed; store result if new.

        If idempotency key exists in cache, returns the cached result.
        If key is new, stores the provided result and returns None.

        Args:
            idempotency_key: Idempotency key (from generate_idempotency_key)
            operation_result: Result dict to cache (required if key is new)
            ttl_seconds: Cache TTL (default: 24 hours)

        Returns:
            Cached result dict if key exists, None if key is new and stored.

        Raises:
            ValueError: If key is new but operation_result is None
        """
        if ttl_seconds is None:
            ttl_seconds = self.DEFAULT_TTL_SECONDS

        cache_key = f"{self.CACHE_PREFIX}:{idempotency_key}"
        redis = await self._ensure_redis()

        if redis is None:
            log.warning(
                "idempotency_check_skipped redis_unavailable key=%s",
                idempotency_key[:16],
            )
            return None

        try:
            # Check if key exists
            cached = await redis.cache_get(cache_key)
            if cached is not None:
                log.info(
                    "idempotency_hit key=%s result_id=%s",
                    idempotency_key[:16],
                    cached.get("id", "unknown")[:16],
                )
                return cached

            # Key is new, store result
            if operation_result is None:
                raise ValueError(
                    f"operation_result required for new idempotency key: {idempotency_key[:16]}"
                )

            # Atomic set-if-not-exists to prevent double-charge on concurrent requests
            if hasattr(redis, "cache_set_nx"):
                stored = await redis.cache_set_nx(cache_key, operation_result, ttl_seconds)
                if not stored:
                    # Another request stored first — return that result
                    existing = await redis.cache_get(cache_key)
                    if existing is not None:
                        return existing
            else:
                await redis.cache_set(cache_key, operation_result, ttl_seconds)
            log.info(
                "idempotency_stored key=%s result_id=%s ttl=%d",
                idempotency_key[:16],
                operation_result.get("id", "unknown")[:16],
                ttl_seconds,
            )
            return None

        except ValueError:
            raise
        except Exception as e:
            log.error(
                "idempotency_check_error key=%s error=%s",
                idempotency_key[:16],
                str(e),
            )
            # Graceful degradation: return None on error
            return None

    async def clear_key(self, idempotency_key: str) -> bool:
        """Manually clear an idempotency key from cache.

        Useful for testing or manual reconciliation.

        Args:
            idempotency_key: Key to clear

        Returns:
            True if key was deleted, False otherwise
        """
        cache_key = f"{self.CACHE_PREFIX}:{idempotency_key}"
        redis = await self._ensure_redis()

        if redis is None:
            log.warning("idempotency_clear_skipped redis_unavailable")
            return False

        try:
            await redis.cache_delete(cache_key)
            log.info("idempotency_key_cleared key=%s", idempotency_key[:16])
            return True
        except Exception as e:
            log.error("idempotency_clear_error key=%s error=%s", idempotency_key[:16], str(e))
            return False

    async def clear_prefix(self, user_id: str) -> int:
        """Clear all idempotency keys for a given user.

        Args:
            user_id: User/customer identifier

        Returns:
            Number of keys deleted
        """
        cache_prefix = f"{self.CACHE_PREFIX}:*{user_id}*"
        redis = await self._ensure_redis()

        if redis is None:
            log.warning("idempotency_clear_prefix_skipped redis_unavailable")
            return 0

        try:
            count = await redis.cache_clear_prefix(cache_prefix)
            log.info("idempotency_keys_cleared_prefix user_id=%s count=%d", user_id[:16], count)
            return count
        except Exception as e:
            log.error(
                "idempotency_clear_prefix_error user_id=%s error=%s",
                user_id[:16],
                str(e),
            )
            return 0


# Global singleton instance
_idempotency_manager: IdempotencyManager | None = None


async def get_idempotency_manager() -> IdempotencyManager:
    """Get or create the global idempotency manager singleton.

    Returns:
        IdempotencyManager instance
    """
    global _idempotency_manager

    if _idempotency_manager is None:
        _idempotency_manager = IdempotencyManager()

    return _idempotency_manager
