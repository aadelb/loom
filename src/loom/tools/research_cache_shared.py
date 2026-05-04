"""Shared result cache for research_deep and research_full_pipeline.

Allows bidirectional result sharing between deep and full_pipeline tools
to avoid duplicate work on complex queries.

Module-level _SHARED_RESULTS dict is keyed by normalized query hash (SHA-256).
Each entry has a TTL of 5 minutes.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger("loom.research_cache_shared")

# Shared result cache: keyed by normalized query hash
_SHARED_RESULTS: dict[str, dict[str, Any]] = {}

# TTL in seconds (5 minutes)
_RESULT_TTL = 300


def _normalize_query_hash(query: str) -> str:
    """Generate SHA-256 hash of normalized query (lowercase, trimmed)."""
    normalized = query.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def check_shared_cache(query: str) -> dict[str, Any] | None:
    """Check shared cache for results on this query.

    Args:
        query: search query string

    Returns:
        Cached result dict if found and not expired, else None.
    """
    query_hash = _normalize_query_hash(query)
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
    return cached.get("results")


def store_shared_cache(query: str, results: dict[str, Any]) -> None:
    """Store results in shared cache.

    Args:
        query: search query string
        results: result dict to cache (search results, pages fetched, etc.)
    """
    query_hash = _normalize_query_hash(query)
    _SHARED_RESULTS[query_hash] = {
        "results": results,
        "_stored_at": time.time(),
    }
    logger.debug("shared_cache_store query_hash=%s", query_hash[:8])


def clear_shared_cache() -> None:
    """Clear all entries from shared cache (useful for testing)."""
    _SHARED_RESULTS.clear()
    logger.debug("shared_cache_cleared")
