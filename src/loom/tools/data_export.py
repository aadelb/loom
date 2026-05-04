"""Data export/import utilities for backup and migration."""
from __future__ import annotations
import json, time, logging
from typing import Any
from pathlib import Path

logger = logging.getLogger("loom.tools.data_export")


async def research_export_config() -> dict[str, Any]:
    """Export current server configuration as JSON."""
    from loom.config import CONFIG
    return {"config": dict(CONFIG), "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "keys_present": sum(1 for v in CONFIG.values() if v)}


async def research_export_strategies(format: str = "json") -> dict[str, Any]:
    """Export all reframing strategies."""
    try:
        from loom.tools.reframe_strategies import ALL_STRATEGIES
        strategies = [{"name": k, **v} for k, v in ALL_STRATEGIES.items()]
        return {"total": len(strategies), "strategies": strategies[:50], "truncated": len(strategies) > 50, "format": format}
    except ImportError:
        return {"error": "strategies module not available", "total": 0}


async def research_export_cache(limit: int = 50) -> dict[str, Any]:
    """Export recent cache entries metadata (not content)."""
    from loom.cache import get_cache
    cache = get_cache()
    cache_dir = Path(cache._cache_dir)
    entries = []
    for f in sorted(cache_dir.rglob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        entries.append({"path": str(f.relative_to(cache_dir)), "size_kb": f.stat().st_size / 1024, "modified": time.ctime(f.stat().st_mtime)})
    return {"entries": entries, "total_found": len(entries), "cache_dir": str(cache_dir)}
