"""Redis management tools.

Provides MCP tools for monitoring and managing the Redis backend:
  - research_redis_stats: Show connection pool stats, memory usage, cache metrics
  - research_redis_flush_cache: Clear cache namespace
"""

from __future__ import annotations

import logging
from typing import Any
from loom.error_responses import handle_tool_errors

log = logging.getLogger("loom.tools.redis_tools")


@handle_tool_errors("research_redis_stats")
async def research_redis_stats() -> dict[str, Any]:
    """Get Redis connection pool and memory usage statistics.

    Returns:
        Dict with keys:
          - redis_available: bool (whether redis module is installed)
          - connected: bool (whether connected to Redis)
          - redis_url: str (masked connection URL)
          - memory_usage_mb: float (MB used by Redis)
          - memory_usage_bytes: int (raw bytes)
          - connection_pool_size: int (max connections in pool)
          - error: str (if applicable)

    Example:
        ```python
        stats = await research_redis_stats()
        print(f"Connected: {stats['connected']}")
        print(f"Memory: {stats['memory_usage_mb']} MB")
        ```
    """
    try:
        from loom.redis_store import get_redis_store

        store = await get_redis_store()
        stats = await store.health_check()

        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        log.error("redis_stats_error: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
        }


@handle_tool_errors("research_redis_flush_cache")
async def research_redis_flush_cache(
    prefix: str = "cache:",
) -> dict[str, Any]:
    """Clear Redis cache entries with given prefix.

    Removes all cache entries matching the specified prefix pattern.
    Use with caution — this is destructive.

    Args:
        prefix: Key prefix to match (default: "cache:").
                Examples:
                  - "cache:" — clear all cache entries
                  - "cache:research_" — clear research tool cache
                  - "cache:fetch:" — clear fetch tool cache

    Returns:
        Dict with keys:
          - status: "success" or "error"
          - keys_deleted: int (number of keys removed)
          - prefix: str (prefix that was matched)
          - error: str (if status is error)

    Example:
        ```python
        result = await research_redis_flush_cache(prefix="cache:fetch:")
        print(f"Deleted {result['keys_deleted']} cache entries")
        ```
    """
    try:
        from loom.redis_store import get_redis_store

        if not prefix:
            return {
                "status": "error",
                "error": "prefix cannot be empty",
            }

        store = await get_redis_store()
        count = await store.cache_clear_prefix(prefix)

        return {
            "status": "success",
            "keys_deleted": count,
            "prefix": prefix,
        }
    except Exception as e:
        log.error("redis_flush_cache_error prefix=%s: %s", prefix, str(e))
        return {
            "status": "error",
            "error": str(e),
            "prefix": prefix,
        }
