"""Audit trail querying and statistics tools for Loom MCP server.

Provides MCP tools to query audit logs and generate compliance reports:
  - research_audit_query: Query audit entries by tool name and time range
  - research_audit_stats: Generate audit statistics (calls, errors, costs, duration)

Audit logs are stored in:
  1. Primary: PostgreSQL audit_log table (if database.type == "postgresql")
  2. Fallback: SQLite audit.db in ~/.loom/audit/
  3. Always: Structured JSON audit log files (/var/log/loom/audit.jsonl)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.audit_query")


@dataclass
class AuditQueryResult:
    """Result of an audit query."""

    entries: list[dict[str, Any]]
    count: int
    total_count: int
    timestamp: str
    query_duration_ms: float


@dataclass
class AuditStats:
    """Audit statistics summary."""

    total_calls: int
    successful_calls: int
    failed_calls: int
    timeout_calls: int
    other_error_calls: int
    top_tools: dict[str, int]
    top_errors: dict[str, int]
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    total_duration_ms: float
    total_cost_credits: float
    timestamp: str


def _get_audit_dir() -> Path:
    """Get audit directory path from environment or default.

    Returns:
        Path to audit directory
    """
    audit_dir = os.getenv("LOOM_AUDIT_DIR", "")
    if audit_dir:
        return Path(audit_dir)

    return Path.home() / ".loom" / "audit"


def _get_jsonl_log_path() -> Path:
    """Get structured JSON audit log file path.

    Returns:
        Path to audit.jsonl file (typically /var/log/loom/audit.jsonl)
    """
    log_path = os.getenv("LOOM_AUDIT_LOG_PATH", "/var/log/loom/audit.jsonl")
    return Path(log_path)


def _parse_audit_entry(entry_dict: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate an audit entry dictionary.

    Args:
        entry_dict: Raw audit entry from JSON

    Returns:
        Parsed entry with standardized types
    """
    return {
        "client_id": entry_dict.get("client_id", "unknown"),
        "tool_name": entry_dict.get("tool_name", "unknown"),
        "params_summary": entry_dict.get("params_summary", {}),
        "timestamp": entry_dict.get("timestamp", ""),
        "duration_ms": int(entry_dict.get("duration_ms", 0)),
        "status": entry_dict.get("status", "unknown"),
        "signature": entry_dict.get("signature", ""),
        "_verified": entry_dict.get("_verified", False),
    }


def _load_jsonl_entries(
    tool_name: str = "",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Load audit entries from JSONL log file.

    Args:
        tool_name: Filter by tool name (empty = all tools)
        start_time: Filter by start time (inclusive)
        end_time: Filter by end time (inclusive)
        limit: Maximum entries to return

    Returns:
        List of audit entries
    """
    entries = []
    log_path = _get_jsonl_log_path()

    if not log_path.exists():
        logger.debug(f"Audit log not found: {log_path}")
        return entries

    try:
        with open(log_path) as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue

                try:
                    entry_dict = json.loads(line)
                    entry = _parse_audit_entry(entry_dict)

                    # Filter by tool name
                    if tool_name and entry["tool_name"] != tool_name:
                        continue

                    # Filter by time range
                    if entry["timestamp"]:
                        try:
                            entry_time = datetime.fromisoformat(entry["timestamp"])
                            if start_time and entry_time < start_time:
                                continue
                            if end_time and entry_time > end_time:
                                continue
                        except ValueError:
                            pass

                    entries.append(entry)

                    # Stop if we've reached the limit
                    if len(entries) >= limit:
                        break

                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse audit entry: {line}")
                    continue

    except OSError as e:
        logger.error(f"Error reading audit log: {e}")

    return entries


def _load_daily_jsonl_entries(
    tool_name: str = "",
    hours: int = 24,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Load audit entries from daily JSONL files in audit directory.

    Args:
        tool_name: Filter by tool name (empty = all tools)
        hours: Look back N hours
        limit: Maximum entries to return

    Returns:
        List of audit entries
    """
    entries = []
    audit_dir = _get_audit_dir()

    if not audit_dir.exists():
        logger.debug(f"Audit directory not found: {audit_dir}")
        return entries

    # Calculate date range
    now = datetime.now(UTC)
    cutoff_time = now - timedelta(hours=hours)

    try:
        # Collect all JSONL files in date range
        for log_file in sorted(audit_dir.glob("*.jsonl"), reverse=True):
            # Extract date from filename (YYYY-MM-DD.jsonl)
            date_str = log_file.stem

            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=UTC
                )
                # Skip files before cutoff date
                if file_date < cutoff_time:
                    continue
            except ValueError:
                # Skip files with invalid date format
                continue

            # Read entries from this file
            try:
                with open(log_file) as f:
                    for line in f:
                        line = line.rstrip("\n")
                        if not line:
                            continue

                        try:
                            entry_dict = json.loads(line)
                            entry = _parse_audit_entry(entry_dict)

                            # Filter by tool name
                            if tool_name and entry["tool_name"] != tool_name:
                                continue

                            # Filter by time
                            if entry["timestamp"]:
                                try:
                                    entry_time = datetime.fromisoformat(
                                        entry["timestamp"]
                                    )
                                    if entry_time < cutoff_time:
                                        continue
                                except ValueError:
                                    pass

                            entries.append(entry)

                            # Stop if we've reached the limit
                            if len(entries) >= limit:
                                return entries

                        except json.JSONDecodeError:
                            continue

            except OSError as e:
                logger.debug(f"Error reading audit file {log_file}: {e}")
                continue

    except OSError as e:
        logger.error(f"Error scanning audit directory: {e}")

    return entries


async def research_audit_query(
    tool_name: str = "",
    hours: int = 24,
    limit: int = 100,
) -> dict[str, Any]:
    """Query audit log entries by tool name and time range.

    Searches audit logs from the last N hours and returns matching entries.
    Entries include tool name, execution duration, status, and parameters (PII-scrubbed).

    Args:
        tool_name: Filter by tool name (empty = all tools)
        hours: Look back N hours (1-720, default 24)
        limit: Maximum entries to return (1-1000, default 100)

    Returns:
        Dict with keys:
        - entries: List of audit entries matching the query
        - count: Number of entries returned
        - total_count: Total matching entries in audit log
        - timestamp: Query timestamp (ISO UTC)
        - query_duration_ms: Query execution time

    Raises:
        ValueError: If parameters are out of range
    """
    # Validate input parameters
    if not isinstance(hours, int) or hours < 1 or hours > 720:
        raise ValueError("hours must be between 1 and 720")
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")

    start_time = datetime.now(UTC) - timedelta(hours=hours)
    query_start = datetime.now(UTC)

    # Load entries from daily JSONL files
    entries = _load_daily_jsonl_entries(tool_name, hours, limit)

    query_duration = (datetime.now(UTC) - query_start).total_seconds() * 1000

    return {
        "entries": [asdict(e) if isinstance(e, dict) else e for e in entries],
        "count": len(entries),
        "total_count": len(entries),  # Approximation; actual total would require scan
        "timestamp": datetime.now(UTC).isoformat(),
        "query_duration_ms": query_duration,
    }


async def research_audit_stats(
    hours: int = 24,
) -> dict[str, Any]:
    """Generate audit statistics for compliance reporting.

    Summarizes tool call metrics: success/failure counts, top tools, error types,
    duration statistics, and cost estimates.

    Args:
        hours: Look back N hours (1-720, default 24)

    Returns:
        Dict with keys:
        - total_calls: Total tool invocations
        - successful_calls: Calls with status == "success"
        - failed_calls: Calls with status == "error"
        - timeout_calls: Calls with status == "timeout"
        - other_error_calls: Other error statuses
        - top_tools: Dict of {tool_name: call_count}, top 10
        - top_errors: Dict of {error_type: count}, top 10
        - avg_duration_ms: Average execution duration
        - min_duration_ms: Minimum execution duration
        - max_duration_ms: Maximum execution duration
        - total_duration_ms: Sum of all durations
        - total_cost_credits: Estimated total credits used
        - timestamp: Stats timestamp (ISO UTC)

    Raises:
        ValueError: If hours out of range
    """
    # Validate input parameters
    if not isinstance(hours, int) or hours < 1 or hours > 720:
        raise ValueError("hours must be between 1 and 720")

    # Load all entries for the time period
    entries = _load_daily_jsonl_entries("", hours, 10000)

    if not entries:
        return {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "timeout_calls": 0,
            "other_error_calls": 0,
            "top_tools": {},
            "top_errors": {},
            "avg_duration_ms": 0.0,
            "min_duration_ms": 0.0,
            "max_duration_ms": 0.0,
            "total_duration_ms": 0.0,
            "total_cost_credits": 0.0,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Calculate statistics
    tool_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    durations: list[int] = []
    successful_count = 0
    failed_count = 0
    timeout_count = 0
    other_error_count = 0

    for entry in entries:
        # Count by tool
        tool_name = entry.get("tool_name", "unknown")
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        # Count by status
        status = entry.get("status", "unknown")
        if status == "success":
            successful_count += 1
        elif status == "error":
            failed_count += 1
        elif status == "timeout":
            timeout_count += 1
        else:
            other_error_count += 1

        # Collect durations
        duration_ms = entry.get("duration_ms", 0)
        if duration_ms > 0:
            durations.append(duration_ms)

    # Calculate top tools (sort by count, descending)
    top_tools = dict(
        sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    # Calculate duration statistics
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    min_duration = min(durations) if durations else 0.0
    max_duration = max(durations) if durations else 0.0
    total_duration = sum(durations)

    # Estimate costs (1 credit per second, minimum 1 credit per call)
    total_cost = sum(max(1, int(d / 1000)) for d in durations)

    # Top errors (errors are in the status field or inferred)
    # For now, track "error" and "timeout" as error types
    if failed_count > 0:
        error_counts["error"] = failed_count
    if timeout_count > 0:
        error_counts["timeout"] = timeout_count
    if other_error_count > 0:
        error_counts["other"] = other_error_count

    return {
        "total_calls": len(entries),
        "successful_calls": successful_count,
        "failed_calls": failed_count,
        "timeout_calls": timeout_count,
        "other_error_calls": other_error_count,
        "top_tools": top_tools,
        "top_errors": error_counts,
        "avg_duration_ms": round(avg_duration, 2),
        "min_duration_ms": min_duration,
        "max_duration_ms": max_duration,
        "total_duration_ms": total_duration,
        "total_cost_credits": total_cost,
        "timestamp": datetime.now(UTC).isoformat(),
    }
