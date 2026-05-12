"""Data export/import utilities for backup and migration."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.data_export")


@handle_tool_errors("research_export_config")
async def research_export_config() -> dict[str, Any]:
    """Export current server configuration as JSON."""
    try:
        from loom.config import CONFIG

        return {
            "config": dict(CONFIG),
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "keys_present": sum(1 for v in CONFIG.values() if v),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_export_config"}


@handle_tool_errors("research_export_strategies")
async def research_export_strategies(format: str = "json") -> dict[str, Any]:
    """Export all reframing strategies."""
    try:
        from loom.tools.reframe_strategies import ALL_STRATEGIES

        strategies = [{"name": k, **v} for k, v in ALL_STRATEGIES.items()]
        return {
            "total": len(strategies),
            "strategies": strategies[:50],
            "truncated": len(strategies) > 50,
            "format": format,
        }
    except ImportError:
        return {"error": "strategies module not available", "total": 0}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_export_strategies"}


@handle_tool_errors("research_export_cache")
async def research_export_cache(limit: int = 50) -> dict[str, Any]:
    """Export recent cache entries metadata (not content)."""
    try:
        from loom.cache import get_cache

        cache = get_cache()
        cache_dir = Path(cache.base_dir)
        entries = []

        # Run blocking filesystem operations in thread pool
        file_stats = await asyncio.to_thread(
            lambda: [(f, f.stat()) for f in cache_dir.glob("**/*.json")]
        )
        file_stats.sort(key=lambda x: x[1].st_mtime, reverse=True)
        for f, st in file_stats[:limit]:
            entries.append(
                {
                    "path": str(f.relative_to(cache_dir)),
                    "size_kb": st.st_size / 1024,
                    "modified": time.ctime(st.st_mtime),
                }
            )
        return {"entries": entries, "total_found": len(entries), "cache_dir": str(cache_dir)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_export_cache"}
