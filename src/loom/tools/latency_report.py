"""MCP tool for accessing per-tool latency statistics and generating reports.

Exposes research_latency_report() to retrieve latency percentiles, identify slow tools,
and analyze performance characteristics of the Loom MCP service.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.tool_latency import get_latency_tracker

log = logging.getLogger("loom.tools.latency_report")


async def research_latency_report(tool_name: str = "") -> dict[str, Any]:
    """Get latency statistics for one tool or all tools.

    Returns percentile latencies (p50, p75, p90, p95, p99), sample count, average,
    min, and max. If tool_name is empty, returns all tools sorted by p95 descending.
    Highlights tools with p95 > 1000ms as potentially slow.

    Args:
        tool_name: Specific tool name (e.g., 'research_fetch'). If empty, returns all tools.

    Returns:
        Dictionary with latency stats:
        - If tool_name specified: single tool stats dict
        - If tool_name empty: list of all tools sorted by p95 descending
        - Always includes 'slow_tools' list (p95 > 1000ms)
    """
    tracker = get_latency_tracker()

    if tool_name.strip():
        # Get stats for specific tool
        stats = tracker.get_percentiles(tool_name)
        if stats["count"] == 0:
            return {
                "error": f"no_data",
                "message": f"Tool '{tool_name}' has no recorded latencies yet.",
                "tool": tool_name,
            }
        return {
            "tool": tool_name,
            "stats": stats,
            "is_slow": stats["p95"] > 1000,
            "slow_warning": "p95 exceeds 1000ms" if stats["p95"] > 1000 else None,
        }
    else:
        # Get stats for all tools
        all_stats = tracker.get_all_latencies()

        if not all_stats:
            return {
                "error": "no_tools_tracked",
                "message": "No latency data collected yet. Tools must be called first.",
                "total_tools": 0,
            }

        # Sort by p95 descending
        sorted_tools = sorted(
            [s for s in all_stats.values() if s["count"] > 0],
            key=lambda x: x["p95"],
            reverse=True,
        )
        
        # Guard: ensure we have at least two data points for meaningful stats
        if len(sorted_tools) < 2:
            return {
                "error": "insufficient_data",
                "message": "At least 2 tools with data needed for comparison",
                "total_tools_tracked": len(all_stats),
                "total_tools_with_data": len(sorted_tools),
            }

        # Find slow tools (p95 > 1000ms)
        slow_tools = [s for s in sorted_tools if s["p95"] > 1000]

        return {
            "total_tools_tracked": len(all_stats),
            "total_tools_with_data": len(sorted_tools),
            "tools": sorted_tools,
            "slow_tools": slow_tools,
            "slow_count": len(slow_tools),
            "slow_threshold_ms": 1000,
        }
