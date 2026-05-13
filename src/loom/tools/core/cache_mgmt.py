"""Cache management tools for Loom — view stats, clear old entries."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

try:
    from loom.cache import get_cache
    _CACHE_AVAILABLE = True
except ImportError:
    _CACHE_AVAILABLE = False
    get_cache = None  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.cache")


@handle_tool_errors("research_cache_stats")
def research_cache_stats() -> dict[str, Any]:
    """Return cache statistics.

    Returns:
        Dict with keys: size_mb, entry_count, oldest, newest
    """
    cache = get_cache()
    cache_dir = Path(cache.base_dir)

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
        try:
            if f.is_file():
                st = f.stat()
                total_bytes += st.st_size
                entry_count += 1
                timestamps.append(st.st_mtime)
        except FileNotFoundError:
            # File deleted by another process between is_file() and stat()
            continue

    size_mb = total_bytes / (1024 * 1024)

    return {
        "size_mb": round(size_mb, 2),
        "entry_count": entry_count,
        "oldest": (
            datetime.fromtimestamp(min(timestamps), UTC).isoformat() if timestamps else None
        ),
        "newest": (
            datetime.fromtimestamp(max(timestamps), UTC).isoformat() if timestamps else None
        ),
        "cache_dir": str(cache_dir),
    }


@handle_tool_errors("research_cache_clear")
def research_cache_clear(older_than_days: int | None = None) -> dict[str, Any]:
    """Remove cache entries older than N days.

    Uses CACHE_TTL_DAYS from config if older_than_days not specified.

    Args:
        older_than_days: delete entries older than this many days (default from config)

    Returns:
        Dict with keys: deleted_count, freed_mb
    """
    if older_than_days is None:
        from loom.config import get_config

        older_than_days = int(_cfg().get("CACHE_TTL_DAYS", 30))
    cache = get_cache()
    cache_dir = Path(cache.base_dir)

    if not cache_dir.exists():
        return {"deleted_count": 0, "freed_mb": 0.0}

    cutoff = time.time() - (older_than_days * 24 * 3600)
    deleted_count = 0
    freed_bytes = 0

    for f in cache_dir.rglob("*.json"):
        try:
            if f.is_file():
                st = f.stat()
                if st.st_mtime < cutoff:
                    freed_bytes += st.st_size
                    f.unlink()
                    deleted_count += 1
        except (FileNotFoundError, OSError):
            # File deleted by another process or permission issue
            continue

    logger.info(
        "cache_clear deleted_count=%d freed_mb=%.2f",
        deleted_count,
        freed_bytes / (1024 * 1024),
    )

    return {
        "deleted_count": deleted_count,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
    }
