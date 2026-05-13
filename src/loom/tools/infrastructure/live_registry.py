"""Live Tool Registry for tracking runtime status of all tools.

Dynamically scans tool modules, tracks importability, function availability,
health metrics, and usage patterns.
"""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import asyncio
import importlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.tools import error_wrapper

log = logging.getLogger("loom.tools.live_registry")

# Module-level cache of registry data
_registry_cache: dict[str, Any] = {
    "last_refresh": None,
    "modules": {},
    "refresh_time_ms": 0,
}

# Lock for thread-safe cache access
_registry_lock: asyncio.Lock | None = None

# Cache validity in seconds (5 minutes)
_CACHE_TTL_SECONDS = 300

# Tools directory path
_TOOLS_DIR = Path(__file__).parent


def _get_registry_lock() -> asyncio.Lock:
    """Get or create the registry lock."""
    global _registry_lock
    if _registry_lock is None:
        _registry_lock = asyncio.Lock()
    return _registry_lock


@handle_tool_errors("research_registry_status")
async def research_registry_status() -> dict[str, Any]:
    """Return live status of ALL registered tools.

    Scans all tool modules and returns their import status, function counts,
    health status, and usage metrics.

    Returns:
        Dict with keys: total_modules, healthy, degraded, failed,
        tools (list of status dicts), last_refresh
    """
    try:
        await _scan_modules()
        async with _get_registry_lock():
            # Take snapshot to prevent concurrent modification during iteration
            cache_snapshot = dict(_registry_cache["modules"])
            last_refresh = _registry_cache["last_refresh"]

        healthy = sum(1 for m in cache_snapshot.values() if m["status"] == "healthy")
        degraded = sum(1 for m in cache_snapshot.values() if m["status"] == "degraded")
        failed = sum(1 for m in cache_snapshot.values() if m["status"] == "failed")

        tools_list = [
            {
                "module": name,
                "status": data["status"],
                "functions_count": data["functions_count"],
                "last_error": data.get("last_error"),
                "last_used": data.get("last_used"),
                "importable": data["importable"],
            }
            for name, data in sorted(cache_snapshot.items())
        ]

        return {
            "total_modules": len(cache_snapshot),
            "healthy": healthy,
            "degraded": degraded,
            "failed": failed,
            "tools": tools_list,
            "last_refresh": last_refresh,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_registry_status"}


@handle_tool_errors("research_registry_search")
async def research_registry_search(
    query: str = "",
    status: str = "all",
    category: str = "",
) -> dict[str, Any]:
    """Search the live registry with filters.

    Args:
        query: Search term (matches module name or docstring)
        status: Filter by status - "all", "healthy", "degraded", "failed"
        category: Filter by tool category prefix (e.g., "research_", "dark_")

    Returns:
        Dict with keys: matching (list of tool dicts), total, query, filters
    """
    try:
        await _scan_modules()
        async with _get_registry_lock():
            # Take snapshot to prevent concurrent modification during iteration
            cache_snapshot = dict(_registry_cache["modules"])

        matching = []
        for name, data in cache_snapshot.items():
            # Apply status filter
            if status != "all" and data["status"] != status:
                continue

            # Apply category filter
            if category and not name.startswith(category):
                continue

            # Apply query filter
            if (
                query
                and query.lower() not in name.lower()
                and query.lower() not in data.get("docstring", "").lower()
            ):
                continue

            matching.append(
                {
                    "module": name,
                    "functions": data["functions_count"],
                    "status": data["status"],
                    "docstring_preview": (data.get("docstring", "")[:100] + "...")
                    if data.get("docstring")
                    else None,
                    "importable": data["importable"],
                }
            )

        return {
            "matching": sorted(matching, key=lambda x: x["module"]),
            "total": len(matching),
            "query": query,
            "filters": {"status": status, "category": category},
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_registry_search"}


@handle_tool_errors("research_registry_refresh")
async def research_registry_refresh() -> dict[str, Any]:
    """Force re-scan all modules, update health status.

    Tries importing each module, records errors, and refreshes cache.

    Returns:
        Dict with keys: scanned, healthy, errors (list of error dicts), refresh_time_ms
    """
    try:
        async with _get_registry_lock():
            start_time = time.time()
            # Clear cache safely within lock
            _registry_cache["modules"].clear()

            error_stats = await error_wrapper.research_error_stats()
            error_data = error_stats.get("error_data", {})

            # Get tool modules from tools directory
            tool_files = sorted(_TOOLS_DIR.glob("*.py"))
            tool_modules = [
                f.stem for f in tool_files if not f.stem.startswith("_") and f.name != "live_registry.py"
            ]

            errors = []
            healthy_count = 0

            for module_name in tool_modules:
                try:
                    mod = importlib.import_module(f"loom.tools.{module_name}")
                    functions = [
                        n for n in dir(mod) if n.startswith("research_") and callable(getattr(mod, n))
                    ]
                    docstring = (mod.__doc__ or "").split("\n")[0]

                    # Check health from error stats
                    has_errors = any(f in error_data for f in functions)
                    last_error = None
                    for func in functions:
                        if func in error_data:
                            last_error = error_data[func].get("last_error")
                            break

                    status = "degraded" if has_errors else "healthy"
                    if has_errors:
                        pass  # Keep degraded
                    else:
                        healthy_count += 1

                    _registry_cache["modules"][module_name] = {
                        "importable": True,
                        "status": status,
                        "functions_count": len(functions),
                        "functions": functions,
                        "docstring": docstring,
                        "last_error": last_error,
                        "last_used": None,  # Would come from usage_analytics
                    }
                except Exception as e:
                    _registry_cache["modules"][module_name] = {
                        "importable": False,
                        "status": "failed",
                        "functions_count": 0,
                        "functions": [],
                        "docstring": None,
                        "last_error": str(e),
                        "last_used": None,
                    }
                    errors.append({"module": module_name, "error": str(e)})

            refresh_time_ms = int((time.time() - start_time) * 1000)
            _registry_cache["last_refresh"] = datetime.now(UTC).isoformat()
            _registry_cache["refresh_time_ms"] = refresh_time_ms

        return {
            "scanned": len(tool_modules),
            "healthy": healthy_count,
            "degraded": len(tool_modules) - healthy_count - len(errors),
            "failed": len(errors),
            "errors": errors,
            "refresh_time_ms": refresh_time_ms,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_registry_refresh"}


async def _scan_modules() -> None:
    """Scan and cache all tool modules if not recently cached."""
    # Refresh if cache is empty or older than cache TTL (5 minutes)
    last_refresh = _registry_cache.get("last_refresh")
    cache_is_empty = not _registry_cache["modules"]
    cache_is_stale = False

    if last_refresh:
        last_refresh_dt = datetime.fromisoformat(last_refresh)
        cache_is_stale = (datetime.now(UTC) - last_refresh_dt).total_seconds() > _CACHE_TTL_SECONDS
    else:
        cache_is_stale = True

    if cache_is_empty or cache_is_stale:
        await research_registry_refresh()
