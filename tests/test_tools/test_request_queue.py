"""Tests for request queue system."""

from __future__ import annotations

import asyncio

import pytest

import loom.tools.infrastructure.request_queue


@pytest.mark.asyncio
async def test_queue_add_basic():
    """Test adding items to queue."""
    result = await request_queue.research_queue_add(
        tool_name="research_fetch",
        params={"url": "https://example.com"},
        priority=5,
    )

    assert result["queued"] is True
    assert result["queue_id"] is not None
    assert result["position"] >= 1
    assert result["priority"] == 5


@pytest.mark.asyncio
async def test_queue_add_priority_validation():
    """Test priority bounds validation."""
    with pytest.raises(ValueError, match="Priority must be 1-10"):
        await request_queue.research_queue_add(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            priority=0,
        )

    with pytest.raises(ValueError, match="Priority must be 1-10"):
        await request_queue.research_queue_add(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            priority=11,
        )


@pytest.mark.asyncio
async def test_queue_status_empty():
    """Test queue status when empty."""
    # Clear queue first
    request_queue._queue = asyncio.PriorityQueue()
    request_queue._completed_count = 0
    request_queue._processing_count = 0

    status = await request_queue.research_queue_status()

    assert status["pending"] == 0
    assert status["processing"] == 0
    assert status["completed"] == 0
    assert status["by_priority"] == {}
    assert status["oldest_waiting_seconds"] is None


@pytest.mark.asyncio
async def test_queue_status_with_items():
    """Test queue status with pending items."""
    # Clear queue first
    request_queue._queue = asyncio.PriorityQueue()
    request_queue._completed_count = 0
    request_queue._processing_count = 0

    # Add multiple items with different priorities
    await request_queue.research_queue_add(
        tool_name="research_fetch", params={"url": "https://example1.com"}, priority=1
    )
    await request_queue.research_queue_add(
        tool_name="research_search", params={"q": "test"}, priority=5
    )
    await request_queue.research_queue_add(
        tool_name="research_deep", params={"query": "test"}, priority=5
    )

    status = await request_queue.research_queue_status()

    assert status["pending"] == 3
    assert status["by_priority"][1] == 1
    assert status["by_priority"][5] == 2
    assert status["oldest_waiting_seconds"] is not None
    assert status["oldest_waiting_seconds"] >= 0


@pytest.mark.asyncio
async def test_queue_drain_empty():
    """Test draining empty queue."""
    request_queue._queue = asyncio.PriorityQueue()
    request_queue._completed_count = 0
    request_queue._processing_count = 0

    result = await request_queue.research_queue_drain(max_items=5)

    assert result["drained"] == 0
    assert result["items"] == []
    assert result["remaining"] == 0


@pytest.mark.asyncio
async def test_queue_drain_respects_max_items():
    """Test drain respects max_items limit."""
    request_queue._queue = asyncio.PriorityQueue()
    request_queue._completed_count = 0
    request_queue._processing_count = 0

    # Add 5 items
    for i in range(5):
        await request_queue.research_queue_add(
            tool_name=f"tool_{i}",
            params={"index": i},
            priority=5,
        )

    # Drain only 2
    result = await request_queue.research_queue_drain(max_items=2)

    assert result["drained"] == 2
    assert len(result["items"]) == 2
    assert result["remaining"] == 3

    # Verify items have expected structure
    for item in result["items"]:
        assert "queue_id" in item
        assert "tool_name" in item
        assert "params" in item
        assert "priority" in item
        assert "queued_at" in item


@pytest.mark.asyncio
async def test_queue_drain_max_items_validation():
    """Test drain validates max_items."""
    with pytest.raises(ValueError, match="max_items must be at least 1"):
        await request_queue.research_queue_drain(max_items=0)

    with pytest.raises(ValueError, match="max_items must be at least 1"):
        await request_queue.research_queue_drain(max_items=-1)


@pytest.mark.asyncio
async def test_queue_priority_ordering():
    """Test that higher priority items are dequeued first."""
    request_queue._queue = asyncio.PriorityQueue()
    request_queue._completed_count = 0
    request_queue._processing_count = 0

    # Add items with different priorities
    id1 = (await request_queue.research_queue_add("t1", {"x": 1}, priority=10))["queue_id"]
    id2 = (await request_queue.research_queue_add("t2", {"x": 2}, priority=1))["queue_id"]
    id3 = (await request_queue.research_queue_add("t3", {"x": 3}, priority=5))["queue_id"]

    # Drain should get priority=1 first, then priority=5, then priority=10
    result = await request_queue.research_queue_drain(max_items=3)

    assert len(result["items"]) == 3
    assert result["items"][0]["queue_id"] == id2  # priority 1
    assert result["items"][1]["queue_id"] == id3  # priority 5
    assert result["items"][2]["queue_id"] == id1  # priority 10


@pytest.mark.asyncio
async def test_completed_count_tracking():
    """Test that completed count is tracked correctly."""
    request_queue._queue = asyncio.PriorityQueue()
    request_queue._completed_count = 0
    request_queue._processing_count = 0

    # Add and drain items
    await request_queue.research_queue_add("t1", {"x": 1}, priority=5)
    await request_queue.research_queue_add("t2", {"x": 2}, priority=5)

    result = await request_queue.research_queue_drain(max_items=2)

    assert result["drained"] == 2
    status = await request_queue.research_queue_status()
    assert status["completed"] == 2
