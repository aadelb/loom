"""Usage metering — tracks credit consumption per customer.

Provides:
- Per-call logging with customer_id, tool_name, credits_used, timestamp
- Daily accumulation per customer
- JSONL-based storage for auditability
- Usage retrieval and analytics (by tool, top tools)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_METER_DIR = Path.home() / ".loom" / "meters"


def _ensure_dir() -> None:
    """Ensure meter directory exists."""
    _METER_DIR.mkdir(parents=True, exist_ok=True)


def record_usage(
    customer_id: str,
    tool_name: str,
    credits_used: int,
    duration_ms: float = 0,
) -> dict[str, Any]:
    """Record a tool usage event.

    Appends one JSONL line to customer's daily meter file:
    {customer_id}_{YYYY-MM-DD}.jsonl

    Args:
        customer_id: Customer identifier
        tool_name: Tool name (research_* or plain name)
        credits_used: Credit cost deducted
        duration_ms: Execution duration in milliseconds

    Returns:
        Entry dict with timestamp, customer_id, tool_name, credits_used, duration_ms
    """
    _ensure_dir()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "customer_id": customer_id,
        "tool_name": tool_name,
        "credits_used": credits_used,
        "duration_ms": round(duration_ms, 1),
    }
    meter_file = _METER_DIR / f"{customer_id}_{today}.jsonl"
    with open(meter_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def get_usage(
    customer_id: str,
    date: str | None = None,
) -> dict[str, Any]:
    """Get usage stats for a customer on a given date.

    Returns aggregated totals and breakdown by tool.

    Args:
        customer_id: Customer identifier
        date: Date in YYYY-MM-DD format (defaults to today UTC)

    Returns:
        Dict with:
        - customer_id: Customer identifier
        - date: Date queried
        - total_credits: Total credits consumed
        - total_calls: Total number of calls
        - by_tool: Dict mapping tool names to total credits
    """
    _ensure_dir()
    if date is None:
        date = datetime.now(UTC).strftime("%Y-%m-%d")

    meter_file = _METER_DIR / f"{customer_id}_{date}.jsonl"
    if not meter_file.exists():
        return {
            "customer_id": customer_id,
            "date": date,
            "total_credits": 0,
            "total_calls": 0,
            "by_tool": {},
        }

    total_credits = 0
    total_calls = 0
    by_tool: dict[str, int] = {}

    with open(meter_file) as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                total_credits += entry["credits_used"]
                total_calls += 1
                tool = entry["tool_name"]
                by_tool[tool] = by_tool.get(tool, 0) + entry["credits_used"]

    return {
        "customer_id": customer_id,
        "date": date,
        "total_credits": total_credits,
        "total_calls": total_calls,
        "by_tool": by_tool,
    }


def get_top_tools(
    customer_id: str,
    date: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get top tools by credit usage for a customer on a given date.

    Tools sorted by total credits in descending order.

    Args:
        customer_id: Customer identifier
        date: Date in YYYY-MM-DD format (defaults to today UTC)
        limit: Maximum number of tools to return

    Returns:
        List of dicts with tool name and total credits, sorted by credits descending
    """
    usage = get_usage(customer_id, date)
    sorted_tools = sorted(usage["by_tool"].items(), key=lambda x: -x[1])
    return [{"tool": t, "credits": c} for t, c in sorted_tools[:limit]]
