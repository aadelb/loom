"""MCP tool for lazy tool loader statistics and monitoring.

Provides research_loader_stats() MCP tool to query loading statistics,
monitor lazy-loading performance, and troubleshoot tool import issues.
"""

from __future__ import annotations

from typing import Any

from loom.tool_loader import get_loader


async def research_loader_stats() -> dict[str, Any]:
    """Get lazy tool loader statistics and loading performance metrics.

    Provides detailed information about:
    - Number of registered, loaded, and failed tools
    - Average load time and per-tool load times
    - List of failed tools for troubleshooting

    Returns:
        Dict with:
        - loaded_count: Number of successfully loaded tools
        - failed_count: Number of tools that failed to load
        - registered_count: Total registered tools
        - avg_load_time_ms: Average load time in milliseconds
        - load_times_by_tool: Dict mapping each loaded tool to its load time
        - failed_tools: List of tool names that failed to load
        - cache_size_count: Number of tools in cache

    Example output:
        {
            "loaded_count": 47,
            "failed_count": 2,
            "registered_count": 220,
            "avg_load_time_ms": 18.5,
            "load_times_by_tool": {
                "research_fetch": 45.2,
                "research_spider": 12.1,
                ...
            },
            "failed_tools": ["research_custom_1", "research_custom_2"],
            "cache_size_count": 47
        }
    """
    loader = get_loader()
    stats = loader.get_load_stats()

    # Add cache size for visibility
    stats["cache_size_count"] = stats["loaded_count"]

    return stats
