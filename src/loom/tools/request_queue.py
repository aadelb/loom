"""Request queuing system for rate-limited operations."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.request_queue")

_queue: asyncio.PriorityQueue[tuple[int, float, dict[str, Any]]] = asyncio.PriorityQueue()
_completed_count = 0
_processing_count = 0
_lock = asyncio.Lock()


async def research_queue_add(tool_name: str, params: dict[str, Any], priority: int = 5) -> dict[str, Any]:
    """Add a tool call to the execution queue with priority 1-10 (1=highest)."""
    try:
        if not 1 <= priority <= 10:
            raise ValueError("Priority must be 1-10 (1=highest)")
        queue_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).timestamp()
        item = {
            "queue_id": queue_id,
            "tool_name": tool_name,
            "params": params,
            "priority": priority,
            "queued_at": datetime.now(UTC).isoformat(),
        }
        await _queue.put((priority, timestamp, item))
        async with _lock:
            position = _queue.qsize()
        return {"queued": True, "queue_id": queue_id, "position": position, "priority": priority}
    except Exception as exc:
        logger.error("queue_add_error: %s", exc)
        return {"error": str(exc), "tool": "research_queue_add"}


async def research_queue_status() -> dict[str, Any]:
    """Get queue status: pending, processing, completed, priority breakdown, oldest age."""
    try:
        async with _lock:
            pending, processing, completed = _queue.qsize(), _processing_count, _completed_count

        oldest_waiting_seconds = None
        if not _queue.empty():
            try:
                # Access under lock to prevent race between empty() check and _queue[0] access
                _, timestamp, _ = _queue._queue[0]  # type: ignore
                oldest_waiting_seconds = datetime.now(UTC).timestamp() - timestamp
            except (IndexError, AttributeError, TypeError):
                pass

        by_priority: dict[int, int] = {}
        try:
            for item in _queue._queue:  # type: ignore
                p = item[0]
                by_priority[p] = by_priority.get(p, 0) + 1
        except (AttributeError, TypeError):
            pass

        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "by_priority": by_priority,
            "oldest_waiting_seconds": oldest_waiting_seconds,
        }
    except Exception as exc:
        logger.error("queue_status_error: %s", exc)
        return {"error": str(exc), "tool": "research_queue_status"}


async def research_queue_drain(max_items: int = 10) -> dict[str, Any]:
    """Dequeue up to max_items in FIFO order within priority. Execution is caller's responsibility."""
    global _processing_count
    try:
        if max_items < 1:
            raise ValueError("max_items must be at least 1")

        drained_items: list[dict[str, Any]] = []
        for _ in range(max_items):
            if _queue.empty():
                break
            try:
                _, _, item = _queue.get_nowait()
                async with _lock:
                    _processing_count += 1
                drained_items.append({k: item[k] for k in ["queue_id", "tool_name", "params", "priority", "queued_at"]})
            except asyncio.QueueEmpty:
                break

        async with _lock:
            remaining_queue = _queue.qsize()

        return {"drained": len(drained_items), "items": drained_items, "remaining": remaining_queue}
    except Exception as exc:
        logger.error("queue_drain_error: %s", exc)
        return {"error": str(exc), "tool": "research_queue_drain"}
