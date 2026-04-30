"""Offline mode support — serve from cache when providers are down.

Implements graceful fallback to cached data when external providers fail,
with stale data indicators for consumers to make informed decisions.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.cache import get_cache

log = logging.getLogger("loom.offline")


def serve_stale_or_error(cache_key: str, error: Exception) -> dict[str, Any]:
    """Try to serve stale cache data, or return structured error.

    When a provider call fails (timeout, connection error, 5xx), attempts to
    serve cached data from a previous successful call. If no cache exists,
    returns a structured error dict that upstream callers can handle gracefully.

    Args:
        cache_key: the key used to store/retrieve from cache
        error: the exception that caused the provider failure

    Returns:
        Dict with one of two shapes:

        Cache hit (stale data available):
            {
                "data": <cached_data>,
                "cached_at": "2026-04-29T10:00:00+00:00",
                "freshness_hours": 24.5,
                "is_stale": True,
                "source": "cache_fallback",
                "original_error": "Connection timeout",
            }

        Cache miss (no data available):
            {
                "data": None,
                "is_stale": False,
                "error": "provider_unavailable",
                "message": "Provider failed and no cache available: Connection timeout",
                "source": "error",
            }
    """
    cache = get_cache()
    cached = cache.get_with_metadata(cache_key)

    if cached and cached.get("data"):
        # Stale data available — serve it with warning
        log.info(
            "serving_stale_cache cache_key=%s cached_at=%s freshness_hours=%s error=%s",
            cache_key,
            cached.get("cached_at"),
            cached.get("freshness_hours"),
            str(error),
        )
        return {
            "data": cached["data"],
            "cached_at": cached["cached_at"],
            "freshness_hours": cached["freshness_hours"],
            "is_stale": True,
            "source": "cache_fallback",
            "original_error": str(error),
        }

    # No cache available — return graceful error
    log.warning(
        "provider_failed_no_cache cache_key=%s error=%s",
        cache_key,
        str(error),
    )
    return {
        "data": None,
        "is_stale": False,
        "error": "provider_unavailable",
        "message": f"Provider failed and no cache available: {error}",
        "source": "error",
    }
