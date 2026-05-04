"""Usage metering — tracks credit consumption per customer.

Provides:
- Per-call logging with customer_id, tool_name, credits_used, timestamp
- Daily accumulation per customer
- JSONL-based storage (JSON backend) or PostgreSQL (postgres backend)
- Usage retrieval and analytics (by tool, top tools)
- Idempotent usage recording to prevent duplicate meter entries

Backend selection:
- LOOM_BILLING_BACKEND env var: "postgres", "json" (default)
- If PostgreSQL unavailable, automatically falls back to JSONL
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_METER_DIR = Path.home() / ".loom" / "meters"
_SAFE_ID_RE = re.compile(r"^[a-z0-9_-]{1,64}$")

# Backend selection
_BILLING_BACKEND = os.environ.get("LOOM_BILLING_BACKEND", "json").lower()

# Lazy import pg_store
_pg_store = None


async def _get_pg_store():
    """Lazy-load and return PgStore instance, or None if unavailable."""
    global _pg_store
    if _pg_store is None:
        try:
            from loom.pg_store import get_store
            _pg_store = await get_store()
        except Exception as e:
            log.warning(f"pg_store unavailable, falling back to JSONL: {e}")
            _pg_store = False  # Mark as permanently unavailable
    return _pg_store if _pg_store is not False else None


# ===== JSON fallback functions (existing, unchanged) =====


def _validate_customer_id(customer_id: str) -> str:
    if not _SAFE_ID_RE.match(customer_id):
        raise ValueError(f"Invalid customer_id format: {customer_id[:20]}")
    return customer_id


def _ensure_dir() -> None:
    """Ensure meter directory exists."""
    _METER_DIR.mkdir(parents=True, exist_ok=True)


def record_usage_json(
    customer_id: str,
    tool_name: str,
    credits_used: int,
    duration_ms: float = 0,
) -> dict[str, Any]:
    """Record a tool usage event to JSON JSONL file.

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
    _validate_customer_id(customer_id)
    meter_file = _METER_DIR / f"{customer_id}_{today}.jsonl"
    with open(meter_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


async def record_usage(
    customer_id: str,
    tool_name: str,
    credits_used: int,
    duration_ms: float = 0,
) -> dict[str, Any]:
    """Record a tool usage event.

    Writes to PostgreSQL (if configured) or JSONL file (fallback).

    Args:
        customer_id: Customer identifier
        tool_name: Tool name (research_* or plain name)
        credits_used: Credit cost deducted
        duration_ms: Execution duration in milliseconds

    Returns:
        Entry dict with timestamp, customer_id, tool_name, credits_used, duration_ms
    """
    timestamp = datetime.now(UTC).isoformat()
    entry = {
        "timestamp": timestamp,
        "customer_id": customer_id,
        "tool_name": tool_name,
        "credits_used": credits_used,
        "duration_ms": round(duration_ms, 1),
    }

    if _BILLING_BACKEND == "postgres":
        store = await _get_pg_store()
        if store:
            try:
                await store.record_usage(
                    customer_id=customer_id,
                    tool_name=tool_name,
                    credits=credits_used,
                    duration_ms=duration_ms
                )
                log.debug(
                    f"Recorded usage in PG: customer={customer_id}, tool={tool_name}, credits={credits_used}"
                )
                return entry
            except Exception as e:
                log.error(f"Failed to record usage in PG: {e}, falling back to JSONL")

    # Fall back to JSON
    return record_usage_json(customer_id, tool_name, credits_used, duration_ms)


async def record_usage_idempotent(
    customer_id: str,
    tool_name: str,
    credits_used: int,
    duration_ms: float = 0,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Record a tool usage event with idempotency protection.

    Prevents duplicate meter entries by checking idempotency cache.
    If the operation was already recorded, returns cached entry.

    Args:
        customer_id: Customer identifier
        tool_name: Tool name (research_* or plain name)
        credits_used: Credit cost deducted
        duration_ms: Execution duration in milliseconds
        idempotency_key: Optional idempotency key (auto-generated if not provided)

    Returns:
        Entry dict with:
        - timestamp, customer_id, tool_name, credits_used, duration_ms
        - idempotency_key: The key used
        - is_duplicate: True if this was cached from previous request
    """
    from loom.billing.idempotency import (
        generate_idempotency_key,
        get_idempotency_manager,
    )

    # Generate key if not provided
    if idempotency_key is None:
        idempotency_key = generate_idempotency_key(
            customer_id,
            "meter_record",
            {
                "tool_name": tool_name,
                "credits_used": credits_used,
                "duration_ms": round(duration_ms, 1),
            },
        )

    # Check if operation already recorded
    manager = await get_idempotency_manager()
    cached_entry = await manager.check_and_store(idempotency_key)

    if cached_entry is not None:
        # Return cached entry from previous execution
        return {
            "timestamp": cached_entry["timestamp"],
            "customer_id": cached_entry["customer_id"],
            "tool_name": cached_entry["tool_name"],
            "credits_used": cached_entry["credits_used"],
            "duration_ms": cached_entry["duration_ms"],
            "idempotency_key": idempotency_key,
            "is_duplicate": True,
        }

    # Record new entry
    entry = await record_usage(customer_id, tool_name, credits_used, duration_ms)

    # Store result for future idempotent checks
    operation_result = {
        "timestamp": entry["timestamp"],
        "customer_id": entry["customer_id"],
        "tool_name": entry["tool_name"],
        "credits_used": entry["credits_used"],
        "duration_ms": entry["duration_ms"],
    }
    await manager.check_and_store(idempotency_key, operation_result)

    return {
        **entry,
        "idempotency_key": idempotency_key,
        "is_duplicate": False,
    }


def get_usage_json(
    customer_id: str,
    date: str | None = None,
) -> dict[str, Any]:
    """Get usage stats from JSON JSONL file.

    Args:
        customer_id: Customer identifier
        date: Date in YYYY-MM-DD format (defaults to today UTC)

    Returns:
        Dict with customer_id, date, total_credits, total_calls, by_tool
    """
    _ensure_dir()
    _validate_customer_id(customer_id)
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


async def get_usage(
    customer_id: str,
    date: str | None = None,
) -> dict[str, Any]:
    """Get usage stats for a customer on a given date.

    Returns aggregated totals and breakdown by tool from PostgreSQL or JSONL.

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
    if date is None:
        date = datetime.now(UTC).strftime("%Y-%m-%d")

    if _BILLING_BACKEND == "postgres":
        store = await _get_pg_store()
        if store:
            try:
                result = await store.get_usage(customer_id, date)
                return {
                    "customer_id": result["customer_id"],
                    "date": date,
                    "total_credits": result.get("total_credits", 0),
                    "total_calls": result.get("total_calls", 0),
                    "by_tool": result.get("by_tool", {}),
                }
            except Exception as e:
                log.error(f"Failed to get usage from PG: {e}, falling back to JSONL")

    # Fall back to JSON
    return get_usage_json(customer_id, date)


def get_top_tools_json(
    customer_id: str,
    date: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get top tools by credit usage from JSON JSONL file.

    Args:
        customer_id: Customer identifier
        date: Date in YYYY-MM-DD format (defaults to today UTC)
        limit: Maximum number of tools to return

    Returns:
        List of dicts with tool name and total credits
    """
    usage = get_usage_json(customer_id, date)
    sorted_tools = sorted(usage["by_tool"].items(), key=lambda x: -x[1])
    return [{"tool": t, "credits": c} for t, c in sorted_tools[:limit]]


async def get_top_tools(
    customer_id: str,
    date: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get top tools by credit usage for a customer on a given date.

    Tools sorted by total credits in descending order, from PostgreSQL or JSONL.

    Args:
        customer_id: Customer identifier
        date: Date in YYYY-MM-DD format (defaults to today UTC)
        limit: Maximum number of tools to return

    Returns:
        List of dicts with tool name and total credits, sorted by credits descending
    """
    if _BILLING_BACKEND == "postgres":
        store = await _get_pg_store()
        if store:
            try:
                top_tools = await store.get_top_tools(customer_id, limit)
                return [{"tool": t["tool_name"], "credits": t["credits"]} for t in top_tools]
            except Exception as e:
                log.error(f"Failed to get top tools from PG: {e}, falling back to JSONL")

    # Fall back to JSON
    return get_top_tools_json(customer_id, date, limit)
