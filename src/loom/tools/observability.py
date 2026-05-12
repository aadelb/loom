"""Observability tools for distributed tracing and operation tracking."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.observability")


def _get_trace_db() -> Path:
    db_dir = Path.home() / ".loom" / "traces"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "observability.db"


def _init_db() -> None:
    db_path = _get_trace_db()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS traces ("
            "trace_id TEXT PRIMARY KEY, "
            "operation TEXT NOT NULL, "
            "status TEXT DEFAULT 'pending', "
            "started_at TEXT NOT NULL, "
            "ended_at TEXT, "
            "duration_ms INTEGER, "
            "result_summary TEXT, "
            "metadata TEXT, "
            "created_at TEXT NOT NULL)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_operation ON traces(operation)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_started_at ON traces(started_at)")
        conn.commit()


@handle_tool_errors("research_trace_start")
def research_trace_start(
    operation: str, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Start a trace for an operation.

    Returns: trace_id, operation, started_at
    """
    try:
        _init_db()
        trace_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        db_path = _get_trace_db()

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO traces (trace_id, operation, status, started_at, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (trace_id, operation, "pending", started_at, json.dumps(metadata or {}), started_at),
            )
            conn.commit()
        logger.info("trace_started trace_id=%s operation=%s", trace_id, operation)
        return {"trace_id": trace_id, "operation": operation, "started_at": started_at}
    except Exception as exc:
        logger.error("trace_start failed for operation=%s: %s", operation, exc)
        return {"trace_id": "", "operation": operation, "started_at": "", "error": str(exc)}


@handle_tool_errors("research_trace_end")
def research_trace_end(
    trace_id: str, status: str = "success", result_summary: str = ""
) -> dict[str, Any]:
    """End a trace and record duration.

    Returns: trace_id, duration_ms, status
    """
    try:
        _init_db()
        ended_at = datetime.now(UTC).isoformat()
        db_path = _get_trace_db()
        duration_ms = 0

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT started_at FROM traces WHERE trace_id = ?", (trace_id,))
            row = cursor.fetchone()

            if row:
                started_at = datetime.fromisoformat(row[0])
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=UTC)
                ended_at_dt = datetime.fromisoformat(ended_at)
                if ended_at_dt.tzinfo is None:
                    ended_at_dt = ended_at_dt.replace(tzinfo=UTC)
                duration_ms = int((ended_at_dt - started_at).total_seconds() * 1000)

            conn.execute(
                "UPDATE traces SET status = ?, ended_at = ?, duration_ms = ?, result_summary = ? "
                "WHERE trace_id = ?",
                (status, ended_at, duration_ms, result_summary, trace_id),
            )
            conn.commit()
        logger.info("trace_ended trace_id=%s status=%s duration_ms=%d", trace_id, status, duration_ms)
        return {"trace_id": trace_id, "duration_ms": duration_ms, "status": status}
    except Exception as exc:
        logger.error("trace_end failed for trace_id=%s: %s", trace_id, exc)
        return {"trace_id": trace_id, "duration_ms": 0, "status": "error", "error": str(exc)}


@handle_tool_errors("research_traces_list")
def research_traces_list(
    limit: int = 20, operation: str | None = None
) -> dict[str, Any]:
    """List recent traces with timing and status.

    Returns: traces, total_count, avg_duration_ms
    """
    try:
        _init_db()
        db_path = _get_trace_db()
        traces: list[dict[str, Any]] = []
        total_count = 0
        avg_duration_ms = 0.0

        with sqlite3.connect(db_path) as conn:
            if operation:
                count_query = "SELECT COUNT(*) FROM traces WHERE operation = ?"
                list_query = (
                    "SELECT trace_id, operation, status, started_at, ended_at, duration_ms, "
                    "result_summary FROM traces WHERE operation = ? ORDER BY started_at DESC LIMIT ?"
                )
                params = (operation, limit)
                count_params = (operation,)
            else:
                count_query = "SELECT COUNT(*) FROM traces"
                list_query = (
                    "SELECT trace_id, operation, status, started_at, ended_at, duration_ms, "
                    "result_summary FROM traces ORDER BY started_at DESC LIMIT ?"
                )
                params = (limit,)
                count_params = ()

            cursor = conn.execute(count_query, count_params)
            total_count = cursor.fetchone()[0]

            avg_query = "SELECT AVG(duration_ms) FROM traces WHERE duration_ms IS NOT NULL"
            avg_params = ()
            if operation:
                avg_query += " AND operation = ?"
                avg_params = (operation,)
            cursor = conn.execute(avg_query, avg_params)
            result = cursor.fetchone()
            avg_duration_ms = float(result[0]) if result[0] else 0.0

            cursor = conn.execute(list_query, params)
            for row in cursor.fetchall():
                traces.append({
                    "trace_id": row[0],
                    "operation": row[1],
                    "status": row[2],
                    "started_at": row[3],
                    "ended_at": row[4],
                    "duration_ms": row[5],
                    "result_summary": row[6],
                })

        logger.info("traces_listed count=%d total=%d op=%s", len(traces), total_count, operation)
        return {
            "traces": traces,
            "total_count": total_count,
            "avg_duration_ms": round(avg_duration_ms, 2),
        }
    except Exception as exc:
        logger.error("traces_list failed for operation=%s: %s", operation, exc)
        return {"traces": [], "total_count": 0, "avg_duration_ms": 0.0, "error": str(exc)}


def tool_trace_start(operation: str, metadata: dict[str, Any] | None = None) -> list[TextContent]:
    """Start a new distributed trace for an operation (MCP wrapper).

    Args:
        operation: operation name to trace
        metadata: optional metadata dict to attach to trace

    Returns:
        Formatted trace information (trace_id, operation, started_at)
    """
    result = research_trace_start(operation, metadata)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_trace_end(trace_id: str, status: str = "success", result_summary: str = "") -> list[TextContent]:
    """End a distributed trace and record final status and duration (MCP wrapper).

    Args:
        trace_id: trace ID from tool_trace_start
        status: final status (success, failure, warning, cancelled, etc.)
        result_summary: optional summary of trace outcome

    Returns:
        Formatted trace completion information (trace_id, duration_ms, status)
    """
    result = research_trace_end(trace_id, status, result_summary)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_traces_list(limit: int = 20, operation: str | None = None) -> list[TextContent]:
    """List recent distributed traces with timing statistics (MCP wrapper).

    Args:
        limit: max number of traces to return
        operation: filter by operation name (None for all operations)

    Returns:
        Formatted list of traces with total count and average duration statistics
    """
    result = research_traces_list(limit, operation)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
