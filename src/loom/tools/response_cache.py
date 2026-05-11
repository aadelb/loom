"""Response cache optimizer for deduplicating similar queries.

Provides in-memory cache with TTL for storing and looking up query-response
pairs. Uses normalized query keys (lowercase, sorted words) for deduplication.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.response_cache")

# Module-level cache: {normalized_key: {response, expires_at, tool_name, created_at}}
_response_cache: dict[str, dict[str, Any]] = {}
_cache_stats = {"hits": 0, "misses": 0}


def _normalize_query(query: str) -> str:
    """Normalize query by lowercasing, stripping, and sorting words.

    Args:
        query: Raw query string

    Returns:
        Normalized query key
    """
    words = query.lower().strip().split()
    sorted_words = sorted(set(words))  # Remove duplicates + sort
    normalized = " ".join(sorted_words)
    # Create hash for long queries (>256 chars)
    if len(normalized) > 256:
        return hashlib.sha256(normalized.encode()).hexdigest()
    return normalized


def research_cache_store(
    query: str,
    response: str,
    tool_name: str = "",
    ttl_hours: int = 24,
) -> dict[str, Any]:
    """Store a query-response pair in memory cache.

    Args:
        query: The query string to cache
        response: The response to store
        tool_name: Optional name of the tool that generated response
        ttl_hours: Time-to-live in hours (default 24)

    Returns:
        Dict with keys:
        - cached: True if stored successfully
        - cache_key: Normalized query key
        - expires_at: ISO 8601 timestamp when entry expires
        - cache_size: Current cache entry count
    """
    try:
        cache_key = _normalize_query(query)
        expires_at = time.time() + (ttl_hours * 3600)

        _response_cache[cache_key] = {
            "response": response,
            "expires_at": expires_at,
            "tool_name": tool_name,
            "created_at": time.time(),
        }

        expires_dt = datetime.fromtimestamp(expires_at, UTC).isoformat()

        logger.info(
            "cache_stored",
            cache_key=cache_key[:16],
            ttl_hours=ttl_hours,
            tool_name=tool_name,
        )

        return {
            "cached": True,
            "cache_key": cache_key[:64],
            "expires_at": expires_dt,
            "cache_size": len(_response_cache),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_cache_store"}


def research_cache_lookup(query: str) -> dict[str, Any]:
    """Look up cached response for similar query.

    Args:
        query: Query to look up

    Returns:
        Dict with keys:
        - hit: True if found and not expired
        - response: Cached response (None if miss)
        - cache_key: Normalized query key
        - age_seconds: Age of cache entry (None if miss)
    """
    try:
        cache_key = _normalize_query(query)
        now = time.time()

        if cache_key not in _response_cache:
            _cache_stats["misses"] += 1
            logger.debug("cache_miss", cache_key=cache_key[:16])
            return {
                "hit": False,
                "response": None,
                "cache_key": cache_key[:64],
                "age_seconds": None,
            }

        entry = _response_cache[cache_key]

        # Check TTL
        if now > entry["expires_at"]:
            del _response_cache[cache_key]
            _cache_stats["misses"] += 1
            logger.debug("cache_expired", cache_key=cache_key[:16])
            return {
                "hit": False,
                "response": None,
                "cache_key": cache_key[:64],
                "age_seconds": None,
            }

        # Cache hit
        _cache_stats["hits"] += 1
        age_seconds = int(now - entry["created_at"])
        logger.debug("cache_hit", cache_key=cache_key[:16], age_seconds=age_seconds)

        return {
            "hit": True,
            "response": entry["response"],
            "cache_key": cache_key[:64],
            "age_seconds": age_seconds,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_cache_lookup"}


def research_response_cache_stats() -> dict[str, Any]:
    """Return response cache statistics.

    Returns:
        Dict with keys:
        - entries: Number of valid cache entries
        - hits: Total cache hits
        - misses: Total cache misses
        - hit_rate_pct: Hit rate percentage (0-100)
        - oldest_entry: ISO timestamp of oldest entry
        - newest_entry: ISO timestamp of newest entry
        - memory_estimate_kb: Rough memory estimate in KB
    """
    try:
        now = time.time()

        # Clean expired entries
        expired = [k for k, v in _response_cache.items() if now > v["expires_at"]]
        for k in expired:
            del _response_cache[k]

        total_entries = len(_response_cache)
        total_requests = _cache_stats["hits"] + _cache_stats["misses"]
        hit_rate = (
            round(100 * _cache_stats["hits"] / total_requests, 2)
            if total_requests > 0
            else 0.0
        )

        # Calculate timestamps
        timestamps = [v["created_at"] for v in _response_cache.values()]
        oldest = (
            datetime.fromtimestamp(min(timestamps), UTC).isoformat()
            if timestamps
            else None
        )
        newest = (
            datetime.fromtimestamp(max(timestamps), UTC).isoformat()
            if timestamps
            else None
        )

        # Rough memory estimate (response + metadata per entry)
        memory_kb = sum(len(v["response"]) for v in _response_cache.values()) // 1024
        memory_kb += total_entries * 0.5  # ~500 bytes overhead per entry

        return {
            "entries": total_entries,
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "hit_rate_pct": hit_rate,
            "oldest_entry": oldest,
            "newest_entry": newest,
            "memory_estimate_kb": round(memory_kb, 2),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_response_cache_stats"}
