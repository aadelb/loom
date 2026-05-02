"""Comprehensive audit logging for tool invocations — JSONL-based with daily rotation.

Tools:
    research_audit_record — Record a tool invocation audit trail entry
    research_audit_query — Query audit entries by tool, caller, time window
    research_audit_export — Export audit trail for compliance review
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger("loom.tools.audit_log")

AUDIT_DIR = Path.home() / ".loom" / "audit"


async def research_audit_record(
    tool_name: str,
    params: dict | None = None,
    result_summary: str = "",
    caller: str = "anonymous",
    duration_ms: float = 0,
) -> dict[str, Any]:
    """Record an audit trail entry for a tool call.

    Args:
        tool_name: Name of the tool that was called
        params: Dict of parameters (hashed, not stored as-is)
        result_summary: Brief result summary (max 200 chars)
        caller: Identifier of the caller
        duration_ms: Execution duration in milliseconds

    Returns:
        Dict with audit_id and recorded status
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # Hash params to avoid logging sensitive data
    params_hash = (
        hashlib.sha256(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()
        if params
        else ""
    )

    # Truncate result summary
    result_summary = result_summary[:200] if result_summary else ""

    # Create audit entry
    audit_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    entry = {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "tool": tool_name,
        "caller": caller,
        "params_hash": params_hash,
        "result_summary": result_summary,
        "duration_ms": duration_ms,
    }

    # Append to daily JSONL file (atomic line write)
    audit_file = AUDIT_DIR / f"{today}.jsonl"
    try:
        with audit_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info(
            "audit_record",
            audit_id=audit_id,
            tool=tool_name,
            caller=caller,
        )
        return {"audit_id": audit_id, "recorded": True}
    except Exception as e:
        logger.error("audit_record_failed", error=str(e), tool=tool_name)
        return {"audit_id": audit_id, "recorded": False, "error": str(e)}


async def research_audit_query(
    tool: str = "",
    caller: str = "",
    since_hours: int = 24,
    limit: int = 100,
) -> dict[str, Any]:
    """Query audit trail entries with filtering and time window.

    Args:
        tool: Filter by tool name (empty = all tools)
        caller: Filter by caller (empty = all callers)
        since_hours: Lookback window in hours
        limit: Max entries to return

    Returns:
        Dict with entries list, total_matching, and time_range
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=since_hours)
    entries = []

    # Read audit files in date range
    for audit_file in sorted(AUDIT_DIR.glob("*.jsonl")):
        try:
            file_date_str = audit_file.stem
            file_date = datetime.fromisoformat(file_date_str).replace(tzinfo=UTC)
            if file_date < cutoff:
                continue
        except (ValueError, AttributeError):
            continue

        try:
            with audit_file.open("r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry.get("timestamp", ""))

                    # Filter by time
                    if entry_time < cutoff:
                        continue

                    # Filter by tool
                    if tool and entry.get("tool") != tool:
                        continue

                    # Filter by caller
                    if caller and entry.get("caller") != caller:
                        continue

                    entries.append(entry)
                    if len(entries) >= limit:
                        break
        except Exception as e:
            logger.warning("audit_query_read_error", file=str(audit_file), error=str(e))
            continue

        if len(entries) >= limit:
            break

    # Extract time range
    time_range = None
    if entries:
        times = [datetime.fromisoformat(e["timestamp"]) for e in entries]
        time_range = {"earliest": min(times).isoformat(), "latest": max(times).isoformat()}

    return {
        "entries": entries[:limit],
        "total_matching": len(entries),
        "time_range": time_range,
        "query_filters": {"tool": tool or "all", "caller": caller or "all", "since_hours": since_hours},
    }


async def research_audit_export(
    format: str = "jsonl",
    days: int = 7,
) -> dict[str, Any]:
    """Export audit trail for compliance review.

    Args:
        format: Output format ('jsonl' or 'json')
        days: Number of days to include in export

    Returns:
        Dict with export metadata and summary
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days)
    entries = []
    tools_seen = set()
    callers_seen = set()

    # Read all matching audit files
    for audit_file in sorted(AUDIT_DIR.glob("*.jsonl")):
        try:
            file_date_str = audit_file.stem
            file_date = datetime.fromisoformat(file_date_str).replace(tzinfo=UTC)
            if file_date < cutoff:
                continue
        except (ValueError, AttributeError):
            continue

        try:
            with audit_file.open("r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    entries.append(entry)
                    tools_seen.add(entry.get("tool", "unknown"))
                    callers_seen.add(entry.get("caller", "unknown"))
        except Exception as e:
            logger.warning("audit_export_read_error", file=str(audit_file), error=str(e))
            continue

    # Format output
    output_path = AUDIT_DIR / f"export_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    if format == "json":
        output_path = output_path.with_suffix(".json")
        output_path.write_text(json.dumps(entries, indent=2))
    else:  # jsonl
        output_path = output_path.with_suffix(".jsonl")
        with output_path.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    return {
        "format": format,
        "entries_count": len(entries),
        "date_range": {
            "start": cutoff.isoformat(),
            "end": now.isoformat(),
        },
        "file_path": str(output_path),
        "summary": {
            "unique_tools": len(tools_seen),
            "unique_callers": len(callers_seen),
            "total_calls": len(entries),
        },
    }
