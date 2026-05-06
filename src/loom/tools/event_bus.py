"""Event Bus system for tool-to-tool communication.

Provides pub/sub event emission, subscription, and history retrieval
for asynchronous tool-to-tool messaging without direct coupling.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger("loom.tools.event_bus")

# Module-level event storage and subscriptions
_events: deque[dict[str, Any]] = deque(maxlen=1000)
_subscribers: dict[str, list[dict[str, Any]]] = defaultdict(list)


async def research_event_emit(
    event_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Emit an event to the bus and notify subscribers.

    Args:
        event_type: Type/category of the event (e.g., "fetch_complete", "error")
        data: Event payload as dict

    Returns:
        Dict with keys: emitted (bool), event_type, subscribers_notified (int), event_id
    """
    event_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()

    event = {
        "event_id": event_id,
        "event_type": event_type,
        "data": data,
        "timestamp": timestamp,
    }

    _events.append(event)

    # Notify all subscribers for this event type
    subscribers_notified = 0
    for sub in _subscribers.get(event_type, []):
        logger.info(
            "event_notify event_id=%s event_type=%s callback_tool=%s",
            event_id,
            event_type,
            sub.get("callback_tool", "unknown"),
        )
        subscribers_notified += 1

    logger.info(
        "event_emitted event_id=%s event_type=%s subscribers=%d",
        event_id,
        event_type,
        subscribers_notified,
    )

    return {
        "emitted": True,
        "event_type": event_type,
        "event_id": event_id,
        "subscribers_notified": subscribers_notified,
    }


async def research_event_subscribe(
    event_type: str,
    callback_tool: str = "",
) -> dict[str, Any]:
    """Subscribe to events of a specific type.

    Args:
        event_type: Event type to subscribe to (wildcard "*" for all events)
        callback_tool: Optional name of the tool handling events (for logging)

    Returns:
        Dict with keys: subscribed (bool), event_type, subscription_id
    """
    subscription_id = str(uuid4())

    subscription = {
        "subscription_id": subscription_id,
        "callback_tool": callback_tool,
        "subscribed_at": datetime.now(UTC).isoformat(),
    }

    _subscribers[event_type].append(subscription)

    logger.info(
        "subscription_created event_type=%s subscription_id=%s callback_tool=%s",
        event_type,
        subscription_id,
        callback_tool,
    )

    return {
        "subscribed": True,
        "event_type": event_type,
        "subscription_id": subscription_id,
    }


async def research_event_history(
    event_type: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Get recent events from the bus.

    Args:
        event_type: Filter by event type (empty string = all types)
        limit: Max events to return (1-1000)

    Returns:
        Dict with keys: events (list of event dicts), total (total count)
    """
    # Clamp limit to valid range
    limit = max(1, min(limit, 1000))

    # Filter and reverse to get most recent first
    all_events = list(_events)
    if event_type:
        all_events = [e for e in all_events if e["event_type"] == event_type]

    recent_events = all_events[-limit:][::-1]

    logger.info(
        "history_retrieved event_type=%s count=%d total=%d",
        event_type if event_type else "all",
        len(recent_events),
        len(all_events),
    )

    return {
        "events": recent_events,
        "total": len(all_events),
    }
