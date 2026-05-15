"""Deadletter queue management tools.

Provides MCP tools for monitoring and managing the deadletter queue:
- research_dlq_stats: Get queue statistics
- research_dlq_retry_now: Force immediate retry of a specific item
"""
from __future__ import annotations

import json
import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.deadletter import get_dlq
    _DLQ_AVAILABLE = True
except ImportError:
    _DLQ_AVAILABLE = False
    get_dlq = None  # type: ignore[assignment]

log = logging.getLogger("loom.tools.dlq_management")


@handle_tool_errors("research_dlq_stats")
async def research_dlq_stats() -> dict[str, Any]:
    """Get deadletter queue statistics.

    Returns queue status including pending items, failed items, retry counts,
    and timing information. Useful for monitoring tool reliability and
    identifying problematic tools.

    Returns:
        Dict with keys:
        - pending: Number of items awaiting retry
        - failed: Number of items in permanent failure table
        - total_retried: Total retry attempts across all items
        - avg_retry_count: Average retries per pending item
        - oldest_pending: ISO timestamp of oldest pending item
    """
    try:
        dlq = get_dlq()
        stats = dlq.get_stats()

        log.info("dlq_stats_retrieved stats=%s", stats)

        return {
            "status": "success",
            "stats": stats,
            "message": f"DLQ has {stats['pending']} pending and {stats['failed']} failed items",
        }
    except Exception as e:
        log.error("dlq_stats_error error=%s", str(e), exc_info=True)
        return {
            "status": "error",
            "error": "failed_to_retrieve_stats",
            "message": str(e),
        }


@handle_tool_errors("research_dlq_retry_now")
async def research_dlq_retry_now(dlq_id: int) -> dict[str, Any]:
    """Force immediate retry of a deadletter queue item.

    Note: This marks the item as ready for retry by moving next_retry_at
    to the past. The background worker will pick it up on the next poll cycle.

    Args:
        dlq_id: ID of the DLQ item to retry

    Returns:
        Dict with status and result message
    """
    try:
        dlq = get_dlq()
        target_item = None

        with dlq._lock:
            with dlq._get_connection() as conn:
                row = conn.execute(
                    "SELECT id, tool_name, retry_count FROM dlq_pending WHERE id = ?",
                    (dlq_id,),
                ).fetchone()

                if not row:
                    return {
                        "status": "error",
                        "error": "item_not_found",
                        "message": f"DLQ item {dlq_id} not found in pending queue",
                    }

                target_item = dict(row)

        # Reset next_retry_at to now to make item immediately available
        with dlq._lock:
            with dlq._get_connection() as conn:
                from datetime import UTC, datetime

                now_iso = datetime.now(UTC).isoformat()
                conn.execute(
                    "UPDATE dlq_pending SET next_retry_at = ? WHERE id = ?",
                    (now_iso, dlq_id),
                )
                conn.commit()

        log.info(
            "dlq_retry_now dlq_id=%d tool_name=%s retry_count=%d",
            dlq_id,
            target_item["tool_name"],
            target_item["retry_count"],
        )

        return {
            "status": "success",
            "dlq_id": dlq_id,
            "tool_name": target_item["tool_name"],
            "retry_count": target_item["retry_count"],
            "message": f"Scheduled immediate retry for {target_item['tool_name']} (retry #{target_item['retry_count'] + 1})",
        }
    except Exception as e:
        log.error("dlq_retry_now_error dlq_id=%d error=%s", dlq_id, str(e), exc_info=True)
        return {
            "status": "error",
            "error": "retry_failed",
            "message": str(e),
        }


@handle_tool_errors("research_dlq_list")
async def research_dlq_list(tool_name: str | None = None, include_failed: bool = False) -> dict[str, Any]:
    """List deadletter queue items.

    Args:
        tool_name: Optional filter by tool name
        include_failed: If True, include permanently failed items

    Returns:
        Dict with status and list of items
    """
    try:
        dlq = get_dlq()

        if tool_name:
            items = dlq.get_items_by_tool(tool_name, include_failed=include_failed)
        else:
            # Get all pending items
            with dlq._lock:
                with dlq._get_connection() as conn:
                    rows = conn.execute(
                        "SELECT id, tool_name, params_json, error, retry_count, created_at FROM dlq_pending"
                    ).fetchall()
                    items = [dict(row) for row in rows]

            if include_failed:
                with dlq._lock:
                    with dlq._get_connection() as conn:
                        rows = conn.execute(
                            "SELECT id, tool_name, params_json, error, retry_count, created_at FROM dlq_failed"
                        ).fetchall()
                        failed_items = [
                            {**dict(row), "status": "failed"} for row in rows
                        ]
                        for item in items:
                            item["status"] = "pending"
                        items.extend(failed_items)

        # Parse params_json for display
        for item in items:
            try:
                item["params"] = json.loads(item.pop("params_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                item["params"] = {}

        log.info("dlq_list_retrieved count=%d tool_name=%s", len(items), tool_name)

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        log.error("dlq_list_error error=%s", str(e), exc_info=True)
        return {
            "status": "error",
            "error": "list_failed",
            "message": str(e),
        }


@handle_tool_errors("research_dlq_clear_failed")
async def research_dlq_clear_failed(days: int = 30) -> dict[str, Any]:
    """Clear permanently failed items older than specified days.

    Args:
        days: Remove failed items older than this many days

    Returns:
        Dict with status and count of deleted items
    """
    try:
        if days < 1:
            return {
                "status": "error",
                "error": "invalid_days",
                "message": "days must be at least 1",
            }

        dlq = get_dlq()
        deleted = dlq.cleanup_old_failed(days=days)

        log.info("dlq_clear_failed days=%d deleted=%d", days, deleted)

        return {
            "status": "success",
            "days": days,
            "deleted": deleted,
            "message": f"Deleted {deleted} failed items older than {days} days",
        }
    except Exception as e:
        log.error("dlq_clear_failed_error error=%s", str(e), exc_info=True)
        return {
            "status": "error",
            "error": "cleanup_failed",
            "message": str(e),
        }
