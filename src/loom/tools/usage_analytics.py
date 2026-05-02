"""Tool usage analytics system for Loom MCP server.

Tracks, records, and analyzes tool usage patterns across the system.
"""

from __future__ import annotations

import logging
from collections import Counter, deque
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("loom.tools.usage_analytics")

# Module-level storage: Counter for totals, deque for time-series (max 50k events)
_usage_counter: Counter[str] = Counter()
_usage_history: deque[dict[str, Any]] = deque(maxlen=50000)


async def research_usage_record(tool_name: str, caller: str = "mcp") -> dict[str, Any]:
    """Record a tool usage event.

    Args:
        tool_name: Name of the tool being used
        caller: Source of the call (default: "mcp")

    Returns:
        Dict with keys: recorded (bool), tool (str), total_uses (int)
    """
    timestamp = datetime.now(UTC).isoformat()

    # Record in counter
    _usage_counter[tool_name] += 1

    # Record in history deque with timestamp
    _usage_history.append(
        {"tool": tool_name, "caller": caller, "timestamp": timestamp}
    )

    return {
        "recorded": True,
        "tool": tool_name,
        "total_uses": _usage_counter[tool_name],
    }


async def research_usage_report(period: str = "today") -> dict[str, Any]:
    """Generate usage report for a specified period.

    Args:
        period: Time window - "today", "hour", or "all"

    Returns:
        Dict with keys: period, total_calls, unique_tools_used, top_tools,
        calls_per_minute, peak_hour
    """
    now = datetime.now(UTC)

    # Determine cutoff time
    if period == "hour":
        cutoff = now - timedelta(hours=1)
    elif period == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # "all"
        cutoff = datetime.min.replace(tzinfo=UTC)

    # Filter history by period
    period_events = [
        e
        for e in _usage_history
        if datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]

    if not period_events:
        return {
            "period": period,
            "total_calls": 0,
            "unique_tools_used": 0,
            "top_tools": [],
            "calls_per_minute": 0.0,
            "peak_hour": None,
        }

    # Calculate metrics
    total_calls = len(period_events)
    tool_counts = Counter(e["tool"] for e in period_events)
    unique_tools = len(tool_counts)

    # Top tools with percentages
    top_tools = [
        {
            "name": tool,
            "calls": count,
            "pct": round((count / total_calls) * 100, 1),
        }
        for tool, count in tool_counts.most_common(10)
    ]

    # Calls per minute
    time_range = (now - cutoff).total_seconds() / 60
    calls_per_minute = round(total_calls / time_range, 2) if time_range > 0 else 0.0

    # Peak hour (hour with most calls)
    hour_buckets: dict[str, int] = {}
    for event in period_events:
        ts = datetime.fromisoformat(event["timestamp"])
        hour_key = ts.strftime("%Y-%m-%d %H:00")
        hour_buckets[hour_key] = hour_buckets.get(hour_key, 0) + 1

    peak_hour = (
        max(hour_buckets, key=hour_buckets.get)
        if hour_buckets
        else None
    )

    return {
        "period": period,
        "total_calls": total_calls,
        "unique_tools_used": unique_tools,
        "top_tools": top_tools,
        "calls_per_minute": calls_per_minute,
        "peak_hour": peak_hour,
    }


async def research_usage_trends(
    tool_name: str = "", window_hours: int = 24
) -> dict[str, Any]:
    """Show usage trends over a time window.

    Args:
        tool_name: Specific tool to analyze (empty = overall trend)
        window_hours: Number of hours to look back (default: 24)

    Returns:
        Dict with keys: tool, window_hours, hourly_buckets, trend, peak_time
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=window_hours)

    # Filter events by tool and time window
    filtered_events = [
        e
        for e in _usage_history
        if datetime.fromisoformat(e["timestamp"]) >= cutoff
        and (not tool_name or e["tool"] == tool_name)
    ]

    if not filtered_events:
        return {
            "tool": tool_name or "all",
            "window_hours": window_hours,
            "hourly_buckets": [],
            "trend": "stable",
            "peak_time": None,
        }

    # Group by hour
    hour_buckets_list: dict[str, int] = {}
    for event in filtered_events:
        ts = datetime.fromisoformat(event["timestamp"])
        hour_key = ts.strftime("%Y-%m-%d %H:00")
        hour_buckets_list[hour_key] = hour_buckets_list.get(hour_key, 0) + 1

    # Convert to sorted list
    sorted_hours = sorted(hour_buckets_list.items())
    hourly_buckets = [
        {"hour": hour, "calls": calls} for hour, calls in sorted_hours
    ]

    # Determine trend
    if len(hourly_buckets) < 2:
        trend = "stable"
    else:
        first_half_avg = sum(
            h["calls"] for h in hourly_buckets[: len(hourly_buckets) // 2]
        ) / max(len(hourly_buckets) // 2, 1)
        second_half_avg = sum(
            h["calls"] for h in hourly_buckets[len(hourly_buckets) // 2 :]
        ) / max((len(hourly_buckets) + 1) // 2, 1)

        if second_half_avg > first_half_avg * 1.1:
            trend = "increasing"
        elif second_half_avg < first_half_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

    # Peak time
    peak_time = (
        max(sorted_hours, key=lambda x: x[1])[0]
        if sorted_hours
        else None
    )

    return {
        "tool": tool_name or "all",
        "window_hours": window_hours,
        "hourly_buckets": hourly_buckets,
        "trend": trend,
        "peak_time": peak_time,
    }
