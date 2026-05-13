"""Distributed tracing system for tracking requests across tool chains."""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from loom.error_responses import handle_tool_errors

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.dist_tracing")

TRACES: OrderedDict[str, dict[str, Any]] = OrderedDict()
MAX_TRACES = 1000
_TRACES_LOCK = Lock()  # Protect against concurrent modifications


@handle_tool_errors("research_trace_create")
async def research_trace_create(operation: str, parent_trace_id: str = "") -> dict[str, Any]:
    """Create a new trace span."""
    try:
        trace_id, span_id = uuid4().hex, uuid4().hex[:16]
        started_at = datetime.now(timezone.utc).isoformat()
        with _TRACES_LOCK:
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
    except Exception as exc:
        logger.exception("Error in research_trace_create: %s", exc)
        return {"error": str(exc), "tool": "research_trace_create"}


@handle_tool_errors("research_trace_complete")
async def research_trace_complete(trace_id: str, span_id: str = "", status: str = "ok", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Complete a trace/span."""
    try:
        with _TRACES_LOCK:
            if trace_id not in TRACES:
                return {"error": f"trace_id not found: {trace_id}"}
            trace = TRACES[trace_id]
            duration_ms = round((time.time() - trace["start_time"]) * 1000, 2)
            completed_at = datetime.now(timezone.utc).isoformat()
            for span in trace["spans"]:
                # Only update matching span if span_id provided; otherwise update first pending
                if (span_id and span["span_id"] == span_id) or (not span_id and span["status"] == "pending"):
                    if span["status"] == "pending":
                        span.update({"completed_at": completed_at, "duration_ms": duration_ms, "status": status, "metadata": metadata or {}})
                    break  # Complete only the first matching span
            trace["status"] = status
        return {"trace_id": trace_id, "duration_ms": duration_ms, "status": status, "spans_count": len(trace["spans"])}
    except Exception as exc:
        logger.exception("Error in research_trace_complete: %s", exc)
        return {"error": str(exc), "tool": "research_trace_complete"}


@handle_tool_errors("research_trace_query")
async def research_trace_query(operation: str = "", limit: int = 50, min_duration_ms: float = 0) -> dict[str, Any]:
    """Query completed traces."""
    try:
        with _TRACES_LOCK:
            results = []
            for tid, t in TRACES.items():
                if t["status"] == "pending":
                    continue
                if operation and t["operation"] != operation:
                    continue
                # Use completed duration if available, otherwise current elapsed time
                if t["spans"] and t["spans"][0].get("duration_ms") is not None:
                    duration_ms = t["spans"][0]["duration_ms"]
                else:
                    duration_ms = round((time.time() - t["start_time"]) * 1000, 2)
                if duration_ms < min_duration_ms:
                    continue
                results.append({
                    "trace_id": tid,
                    "operation": t["operation"],
                    "duration_ms": duration_ms,
                    "spans_count": len(t["spans"]),
                    "status": t["status"],
                    "started_at": t["spans"][0]["started_at"],
                })
        results.sort(key=lambda x: x["duration_ms"], reverse=True)
        results = results[:limit]
        durations = [r["duration_ms"] for r in results]
        avg = round(statistics.mean(durations), 2) if durations else 0
        # Calculate p95 safely: need at least 20 samples for n=20 quantiles
        p95 = 0.0
        if len(durations) >= 20:
            p95 = round(statistics.quantiles(durations, n=20)[18], 2)
        elif len(durations) > 1:
            # For smaller samples, use a proportional percentile
            sorted_durations = sorted(durations)
            idx = int(len(sorted_durations) * 0.95) - 1
            p95 = round(sorted_durations[max(0, idx)], 2)
        return {"traces": results, "total": len(results), "avg_duration_ms": avg, "p95_duration_ms": p95}
    except Exception as exc:
        logger.exception("Error in research_trace_query: %s", exc)
        return {"error": str(exc), "tool": "research_trace_query"}


async def tool_trace_create(operation: str, parent_trace_id: str = "") -> list[TextContent]:
    """MCP wrapper for research_trace_create."""
    if TextContent is None:
        return [{"error": "TextContent not available"}]  # type: ignore[return-value]
    result = await research_trace_create(operation, parent_trace_id)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def tool_trace_complete(trace_id: str, span_id: str = "", status: str = "ok", metadata: dict[str, Any] | None = None) -> list[TextContent]:
    """MCP wrapper for research_trace_complete."""
    if TextContent is None:
        return [{"error": "TextContent not available"}]  # type: ignore[return-value]
    result = await research_trace_complete(trace_id, span_id, status, metadata)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def tool_trace_query(operation: str = "", limit: int = 50, min_duration_ms: float = 0) -> list[TextContent]:
    """MCP wrapper for research_trace_query."""
    if TextContent is None:
        return [{"error": "TextContent not available"}]  # type: ignore[return-value]
    result = await research_trace_query(operation, limit, min_duration_ms)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
