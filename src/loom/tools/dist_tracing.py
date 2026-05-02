"""Distributed tracing system for tracking requests across tool chains."""

from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from mcp.types import TextContent

logger = logging.getLogger("loom.tools.dist_tracing")

TRACES: OrderedDict[str, dict[str, Any]] = OrderedDict()
MAX_TRACES = 1000


async def research_trace_create(operation: str, parent_trace_id: str = "") -> dict[str, Any]:
    """Create a new trace span."""
    trace_id, span_id = uuid4().hex, uuid4().hex[:16]
    started_at = datetime.now(UTC).isoformat()
    TRACES[trace_id] = {
        "spans": [{"span_id": span_id, "started_at": started_at, "completed_at": None, "duration_ms": None, "status": "pending", "metadata": {}}],
        "start_time": time.time(),
        "operation": operation,
        "parent_trace_id": parent_trace_id or None,
        "status": "pending",
    }
    while len(TRACES) > MAX_TRACES:
        TRACES.popitem(last=False)
    return {"trace_id": trace_id, "span_id": span_id, "parent_trace_id": parent_trace_id or None, "operation": operation, "started_at": started_at}


async def research_trace_complete(trace_id: str, span_id: str = "", status: str = "ok", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Complete a trace/span."""
    if trace_id not in TRACES:
        return {"error": f"trace_id not found: {trace_id}"}
    trace = TRACES[trace_id]
    duration_ms = round((time.time() - trace["start_time"]) * 1000, 2)
    completed_at = datetime.now(UTC).isoformat()
    for span in trace["spans"]:
        if not span_id or span["span_id"] == span_id:
            if span["status"] == "pending":
                span.update({"completed_at": completed_at, "duration_ms": duration_ms, "status": status, "metadata": metadata or {}})
    trace["status"] = status
    return {"trace_id": trace_id, "duration_ms": duration_ms, "status": status, "spans_count": len(trace["spans"])}


async def research_trace_query(operation: str = "", limit: int = 50, min_duration_ms: float = 0) -> dict[str, Any]:
    """Query completed traces."""
    results = [
        {
            "trace_id": tid,
            "operation": t["operation"],
            "duration_ms": round((time.time() - t["start_time"]) * 1000, 2),
            "spans_count": len(t["spans"]),
            "status": t["status"],
            "started_at": t["spans"][0]["started_at"],
        }
        for tid, t in TRACES.items()
        if t["status"] != "pending" and (not operation or t["operation"] == operation) and round((time.time() - t["start_time"]) * 1000, 2) >= min_duration_ms
    ]
    results.sort(key=lambda x: x["duration_ms"], reverse=True)
    results = results[:limit]
    durations = [r["duration_ms"] for r in results]
    avg = round(statistics.mean(durations), 2) if durations else 0
    p95 = round(statistics.quantiles(durations, n=20)[18], 2) if len(durations) > 1 else 0
    return {"traces": results, "total": len(results), "avg_duration_ms": avg, "p95_duration_ms": p95}


def tool_trace_create(operation: str, parent_trace_id: str = "") -> list[TextContent]:
    """MCP wrapper for research_trace_create."""
    result = asyncio.run(research_trace_create(operation, parent_trace_id))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_trace_complete(trace_id: str, span_id: str = "", status: str = "ok", metadata: dict[str, Any] | None = None) -> list[TextContent]:
    """MCP wrapper for research_trace_complete."""
    result = asyncio.run(research_trace_complete(trace_id, span_id, status, metadata))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_trace_query(operation: str = "", limit: int = 50, min_duration_ms: float = 0) -> list[TextContent]:
    """MCP wrapper for research_trace_query."""
    result = asyncio.run(research_trace_query(operation, limit, min_duration_ms))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
