"""Shared result cache for research_deep and research_full_pipeline.

Allows bidirectional result sharing between deep and full_pipeline tools
to avoid duplicate work on complex queries.

Module-level _SHARED_RESULTS dict is keyed by normalized query hash (SHA-256).
Each entry has a TTL of 5 minutes.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger("loom.research_cache_shared")

# Shared result cache: keyed by normalized query hash
_SHARED_RESULTS: dict[str, dict[str, Any]] = {}

# TTL in seconds (5 minutes)
_RESULT_TTL = 300

# Sentinel for "entry found but result is None"
_CACHE_HIT_SENTINEL = object()

# Lazy lock for thread-safe shared cache access
_shared_lock: asyncio.Lock | None = None


def _get_shared_lock() -> asyncio.Lock:
    """Get or create the shared cache lock (lazy initialization)."""
    global _shared_lock
    if _shared_lock is None:
        _shared_lock = asyncio.Lock()
    return _shared_lock


def _normalize_query_hash(query: str) -> str:
    """Generate SHA-256 hash of normalized query (lowercase, trimmed)."""
    normalized = query.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


async def check_shared_cache(query: str) -> dict[str, Any] | None:
    """Check shared cache for results on this query.

    Args:
        query: search query string

    Returns:
        Cached result dict if found and not expired, else None.
    """
    query_hash = _normalize_query_hash(query)

    async with _get_shared_lock():
        cached = _SHARED_RESULTS.get(query_hash)

        if cached is None:
            return None

        # Check if expired
        stored_time = cached.get("_stored_at", 0)
        if time.time() - stored_time > _RESULT_TTL:
            logger.debug("shared_cache_expired query_hash=%s", query_hash[:8])
            del _SHARED_RESULTS[query_hash]
            return None

        logger.debug("shared_cache_hit query_hash=%s age_secs=%.1f", query_hash[:8], time.time() - stored_time)
        # Use sentinel to distinguish "not in cache" from "cached result is None"
        return cached.get("results", _CACHE_HIT_SENTINEL)


async def store_shared_cache(query: str, results: dict[str, Any]) -> None:
    """Store results in shared cache.

    Args:
        query: search query string
        results: result dict to cache (search results, pages fetched, etc.)
    """
    query_hash = _normalize_query_hash(query)
    async with _get_shared_lock():
        _SHARED_RESULTS[query_hash] = {
            "results": results,
            "_stored_at": time.time(),
        }
        logger.debug("shared_cache_store query_hash=%s", query_hash[:8])


async def clear_shared_cache() -> None:
    """Clear all entries from shared cache (useful for testing)."""
    async with _get_shared_lock():
        _SHARED_RESULTS.clear()
        logger.debug("shared_cache_cleared")


async def _cleanup_expired_entries() -> int:
    """Remove all expired entries from shared cache.

    Returns:
        Number of entries removed.
    """
    now = time.time()
    async with _get_shared_lock():
        expired_keys = [
            key
            for key, cached in _SHARED_RESULTS.items()
            if now - cached.get("_stored_at", 0) > _RESULT_TTL
        ]
        for key in expired_keys:
            del _SHARED_RESULTS[key]
        if expired_keys:
            logger.debug("shared_cache_cleanup removed=%d", len(expired_keys))
        return len(expired_keys)
