"""Cache optimization and analysis tools — delegates to cache_analytics."""
from __future__ import annotations

import asyncio
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.tools.core.cache_analytics import (
        research_cache_analyze as _real_analyze,
        research_cache_optimize as _real_optimize,
    )
    _DELEGATE_AVAILABLE = True
except ImportError:
    _DELEGATE_AVAILABLE = False


@handle_tool_errors("research_cache_optimize")
async def research_cache_optimize() -> dict[str, Any]:
    """Optimize cache usage and return statistics."""
    if _DELEGATE_AVAILABLE:
        return await asyncio.to_thread(_real_optimize)
    return {"error": "cache_analytics module not available", "tool": "research_cache_optimize"}


@handle_tool_errors("research_cache_analyze")
async def research_cache_analyze() -> dict[str, Any]:
    """Analyze cache performance metrics."""
    if _DELEGATE_AVAILABLE:
        return await asyncio.to_thread(_real_analyze)
    return {"error": "cache_analytics module not available", "tool": "research_cache_analyze"}
