"""Cache management tools for Loom — view stats, clear old entries."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from mcp.types import TextContent

from loom.cache import get_cache

logger = logging.getLogger("loom.tools.cache")


def research_cache_stats() -> dict[str, Any]:
    """Return cache statistics.

    Returns:
        Dict with keys: size_mb, entry_count, oldest, newest
    """
    cache = get_cache()
    cache_dir = Path(cache.cache_dir)

    if not cache_dir.exists():
        return {
            "size_mb": 0,
            "entry_count": 0,
            "oldest": None,
            "newest": None,
            "cache_dir": str(cache_dir),
        }

    total_bytes = 0
    entry_count = 0
    timestamps = []

    for f in cache_dir.rglob("*.json"):
        if f.is_file():
            total_bytes += f.stat().st_size
            entry_count += 1
            timestamps.append(f.stat().st_mtime)

    size_mb = total_bytes / (1024 * 1024)

    return {
        "size_mb": round(size_mb, 2),
        "entry_count": entry_count,
        "oldest": (
            datetime.fromtimestamp(min(timestamps), UTC).isoformat()
            if timestamps
            else None
        ),
        "newest": (
            datetime.fromtimestamp(max(timestamps), UTC).isoformat()
            if timestamps
            else None
        ),
        "cache_dir": str(cache_dir),
    }


def research_cache_clear(older_than_days: int = 30) -> dict[str, Any]:
    """Remove cache entries older than N days.

    Args:
        older_than_days: delete entries older than this many days

    Returns:
        Dict with keys: deleted_count, freed_mb
    """
    cache = get_cache()
    cache_dir = Path(cache.cache_dir)

    if not cache_dir.exists():
        return {"deleted_count": 0, "freed_mb": 0.0}

    cutoff = time.time() - (older_than_days * 24 * 3600)
    deleted_count = 0
    freed_bytes = 0

    for f in cache_dir.rglob("*.json"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            try:
                freed_bytes += f.stat().st_size
                f.unlink()
                deleted_count += 1
            except OSError:
                logger.warning("cache_clear_failed path=%s", f)

    freed_mb = freed_bytes / (1024 * 1024)

    return {
        "deleted_count": deleted_count,
        "freed_mb": round(freed_mb, 2),
        "older_than_days": older_than_days,
    }


def tool_cache_stats() -> list[TextContent]:
    """MCP wrapper for research_cache_stats."""
    result = research_cache_stats()
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_cache_clear(older_than_days: int = 30) -> list[TextContent]:
    """MCP wrapper for research_cache_clear."""
    result = research_cache_clear(older_than_days)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
