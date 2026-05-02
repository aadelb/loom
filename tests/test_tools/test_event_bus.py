"""Tests for the Event Bus system."""

from __future__ import annotations

import asyncio
import pytest

from loom.tools import event_bus


@pytest.mark.asyncio
async def test_research_event_emit():
    """Test emitting an event to the bus."""
    result = await event_bus.research_event_emit(
        event_type="test_event",
        data={"message": "test payload"},
    )

    assert result["emitted"] is True
    assert result["event_type"] == "test_event"
    assert "event_id" in result
    assert isinstance(result["subscribers_notified"], int)


@pytest.mark.asyncio
async def test_research_event_subscribe():
    """Test subscribing to event types."""
    result = await event_bus.research_event_subscribe(
        event_type="order_created",
        callback_tool="payment_processor",
    )

    assert result["subscribed"] is True
    assert result["event_type"] == "order_created"
    assert "subscription_id" in result


@pytest.mark.asyncio
async def test_research_event_history():
    """Test retrieving event history."""
    # Emit some events
    await event_bus.research_event_emit(
        event_type="event_a",
        data={"x": 1},
    )
    await event_bus.research_event_emit(
        event_type="event_b",
        data={"y": 2},
    )
    await event_bus.research_event_emit(
        event_type="event_a",
        data={"x": 3},
    )

    # Get all events
    result = await event_bus.research_event_history()
    assert isinstance(result["events"], list)
    assert result["total"] >= 3

    # Get filtered events
    result_filtered = await event_bus.research_event_history(event_type="event_a")
    assert all(e["event_type"] == "event_a" for e in result_filtered["events"])


@pytest.mark.asyncio
async def test_event_history_limit():
    """Test that limit parameter is respected."""
    # Clear and emit fresh events
    event_bus._events.clear()
    for i in range(10):
        await event_bus.research_event_emit(
            event_type="test",
            data={"index": i},
        )

    result = await event_bus.research_event_history(limit=5)
    assert len(result["events"]) == 5
    assert result["total"] == 10


@pytest.mark.asyncio
async def test_event_history_ordering():
    """Test that recent events are returned first."""
    event_bus._events.clear()
    await event_bus.research_event_emit(
        event_type="test",
        data={"order": 1},
    )
    await asyncio.sleep(0.01)
    await event_bus.research_event_emit(
        event_type="test",
        data={"order": 2},
    )

    result = await event_bus.research_event_history(limit=2)
    # Most recent first
    assert result["events"][0]["data"]["order"] == 2
    assert result["events"][1]["data"]["order"] == 1


@pytest.mark.asyncio
async def test_subscription_tracking():
    """Test that subscriptions are properly tracked."""
    event_bus._subscribers.clear()

    await event_bus.research_event_subscribe(
        event_type="fetch_complete",
        callback_tool="data_processor",
    )
    await event_bus.research_event_subscribe(
        event_type="fetch_complete",
        callback_tool="logger",
    )

    # Emit event and check notification count
    result = await event_bus.research_event_emit(
        event_type="fetch_complete",
        data={"url": "https://example.com"},
    )
    assert result["subscribers_notified"] == 2


@pytest.mark.asyncio
async def test_empty_event_history():
    """Test retrieving history when no events exist."""
    event_bus._events.clear()
    result = await event_bus.research_event_history()
    assert result["events"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_event_bus_deque_maxlen():
    """Test that event bus respects deque maxlen of 1000."""
    event_bus._events.clear()

    # Emit 1100 events
    for i in range(1100):
        await event_bus.research_event_emit(
            event_type="stress_test",
            data={"index": i},
        )

    # Only last 1000 should remain
    result = await event_bus.research_event_history(limit=1100)
    assert len(result["events"]) == 1000
    assert result["total"] == 1000
