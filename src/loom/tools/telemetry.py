"""Load and latency telemetry system for Loom tools."""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.telemetry")

_telemetry_buffer: deque[dict[str, Any]] = deque(maxlen=10000)
_buffer_start_time: float | None = None


async def research_telemetry_record(
    tool_name: str,
    duration_ms: float,
    success: bool = True,
) -> dict[str, Any]:
    """Record tool latency after execution."""
    global _buffer_start_time
    if _buffer_start_time is None:
        _buffer_start_time = datetime.now(UTC).timestamp()

    timestamp = datetime.now(UTC).isoformat()
    _telemetry_buffer.append({
        "tool_name": tool_name,
        "duration_ms": float(duration_ms),
        "success": bool(success),
        "timestamp": timestamp,
    })
    logger.debug("telemetry_record tool_name=%s duration_ms=%s success=%s", tool_name, duration_ms, success)
    return {
        "recorded": True,
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "success": success,
        "timestamp": timestamp,
        "buffer_size": len(_telemetry_buffer),
    }


async def research_telemetry_stats(window_minutes: int = 60) -> dict[str, Any]:
    """Calculate p50/p95/p99 latency percentiles, grouped by tool."""
    if not _telemetry_buffer:
        return {"window_minutes": window_minutes, "total_calls": 0, "success_rate": 0,
                "latency": {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "max": 0, "min": 0},
                "per_tool": {}, "slowest_tools": []}

    cutoff = datetime.now(UTC).timestamp() - (window_minutes * 60)
    windowed = [r for r in _telemetry_buffer
                if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).timestamp() > cutoff]

    if not windowed:
        return {"window_minutes": window_minutes, "total_calls": 0, "success_rate": 0,
                "latency": {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "max": 0, "min": 0},
                "per_tool": {}, "slowest_tools": []}

    total, successes = len(windowed), sum(1 for r in windowed if r["success"])
    durations = sorted([r["duration_ms"] for r in windowed])

    def pctl(data: list[float], p: float) -> float:
        return float(data[min(int(len(data) * p / 100), len(data) - 1)])

    latency = {"p50": pctl(durations, 50), "p95": pctl(durations, 95), "p99": pctl(durations, 99),
               "mean": sum(durations) / len(durations) if durations else 0,
               "max": max(durations) if durations else 0, "min": min(durations) if durations else 0}

    per_tool: dict[str, dict[str, Any]] = {}
    for r in windowed:
        t = r["tool_name"]
        if t not in per_tool:
            per_tool[t] = {"calls": 0, "durations": [], "successes": 0}
        per_tool[t]["calls"] += 1
        per_tool[t]["durations"].append(r["duration_ms"])
        if r["success"]:
            per_tool[t]["successes"] += 1

    per_tool_stats = {}
    for t, d in per_tool.items():
        ds = sorted(d["durations"])
        per_tool_stats[t] = {"calls": d["calls"], "p50": pctl(ds, 50), "p95": pctl(ds, 95),
                             "p99": pctl(ds, 99), "mean": sum(ds) / len(ds) if ds else 0,
                             "success_rate": d["successes"] / d["calls"] * 100 if d["calls"] > 0 else 0}

    slowest = sorted(per_tool_stats.items(), key=lambda x: x[1]["p95"], reverse=True)[:10]
    return {"window_minutes": window_minutes, "total_calls": total,
            "success_rate": round(successes / total * 100, 2) if total > 0 else 0,
            "latency": {k: round(v, 2) for k, v in latency.items()},
            "per_tool": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in per_tool_stats.items()},
            "slowest_tools": [n for n, _ in slowest]}


async def research_telemetry_reset() -> dict[str, Any]:
    """Clear telemetry buffer."""
    global _buffer_start_time
    cleared = len(_telemetry_buffer)
    start = datetime.fromtimestamp(_buffer_start_time, UTC).isoformat() if _buffer_start_time else None
    _telemetry_buffer.clear()
    _buffer_start_time = None
    logger.info("telemetry_reset cleared_records=%d", cleared)
    return {"cleared_records": cleared, "previous_window_start": start, "reset_at": datetime.now(UTC).isoformat()}
