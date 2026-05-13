"""Semantic cache management tools — stats, clear old entries."""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

from loom.semantic_cache import get_semantic_cache

logger = logging.getLogger("loom.tools.semantic_cache")


async def research_semantic_cache_stats() -> dict[str, Any]:
    """Return semantic cache statistics.

    Includes hit rate, cache size, and estimated cost savings from cache hits.

    Returns:
        Dict with keys:
        - total_queries: Total get/put operations
        - cache_hits: Successful cache hits
        - cache_misses: Cache misses
        - semantic_hits: Hits via semantic matching
        - hit_rate: Hit rate percentage
        - entries_cached: Total cached entries
        - estimated_savings_usd: Estimated cost savings
        - cache_dir: Cache directory path
    """
    try:
        cache = get_semantic_cache()
        stats = cache.get_stats()
        stats["cache_dir"] = str(cache.cache_dir)
        return stats
    except Exception as exc:
        return {"error": str(exc), "tool": "research_semantic_cache_stats"}


async def research_semantic_cache_clear(older_than_days: int = 30) -> dict[str, Any]:
    """Remove semantic cache entries older than N days.

    Args:
        older_than_days: Delete entries older than this many days (default 30)

    Returns:
        Dict with keys:
        - deleted_count: Number of files removed
        - older_than_days: Cutoff days used
    """
    try:
        cache = get_semantic_cache()
        deleted_count = await cache.clear_older_than(older_than_days)
        return {
            "deleted_count": deleted_count,
            "older_than_days": older_than_days,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_semantic_cache_clear"}


async def tool_semantic_cache_stats() -> list[TextContent]:
    """MCP wrapper for research_semantic_cache_stats."""
    result = await research_semantic_cache_stats()
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def tool_semantic_cache_clear(older_than_days: int = 30) -> list[TextContent]:
    """MCP wrapper for research_semantic_cache_clear."""
    result = await research_semantic_cache_clear(older_than_days)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
