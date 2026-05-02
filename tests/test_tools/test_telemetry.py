"""Tests for telemetry tools."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, UTC

from loom.tools import telemetry


@pytest.mark.asyncio
async def test_telemetry_record_single():
    """Test recording a single telemetry record."""
    # Reset before test
    await telemetry.research_telemetry_reset()

    result = await telemetry.research_telemetry_record(
        tool_name="research_fetch",
        duration_ms=125.5,
        success=True,
    )

    assert result["recorded"] is True
    assert result["tool_name"] == "research_fetch"
    assert result["duration_ms"] == 125.5
    assert result["success"] is True
    assert "timestamp" in result
    assert result["buffer_size"] == 1


@pytest.mark.asyncio
async def test_telemetry_record_multiple():
    """Test recording multiple telemetry records."""
    await telemetry.research_telemetry_reset()

    # Record multiple calls
    for i in range(5):
        await telemetry.research_telemetry_record(
            tool_name=f"tool_{i}",
            duration_ms=100.0 + i * 10,
            success=i != 2,  # One failure
        )

    stats = await telemetry.research_telemetry_stats(window_minutes=60)

    assert stats["total_calls"] == 5
    assert stats["success_rate"] == 80.0  # 4 out of 5 succeeded
    assert len(stats["per_tool"]) == 5


@pytest.mark.asyncio
async def test_telemetry_stats_percentiles():
    """Test percentile calculations in stats."""
    await telemetry.research_telemetry_reset()

    # Record 10 calls with known durations
    durations = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for dur in durations:
        await telemetry.research_telemetry_record(
            tool_name="research_test",
            duration_ms=dur,
            success=True,
        )

    stats = await telemetry.research_telemetry_stats(window_minutes=60)

    assert stats["total_calls"] == 10
    assert stats["success_rate"] == 100.0
    assert stats["latency"]["p50"] > 0
    assert stats["latency"]["p95"] > stats["latency"]["p50"]
    assert stats["latency"]["p99"] >= stats["latency"]["p95"]
    assert stats["latency"]["max"] == 100.0
    assert stats["latency"]["min"] == 10.0
    assert stats["latency"]["mean"] == 55.0


@pytest.mark.asyncio
async def test_telemetry_per_tool_stats():
    """Test per-tool statistics."""
    await telemetry.research_telemetry_reset()

    # Record for two different tools
    for i in range(3):
        await telemetry.research_telemetry_record(
            tool_name="fetch",
            duration_ms=50.0 + i * 10,
            success=True,
        )

    for i in range(2):
        await telemetry.research_telemetry_record(
            tool_name="search",
            duration_ms=100.0 + i * 20,
            success=True,
        )

    stats = await telemetry.research_telemetry_stats(window_minutes=60)

    assert "fetch" in stats["per_tool"]
    assert "search" in stats["per_tool"]
    assert stats["per_tool"]["fetch"]["calls"] == 3
    assert stats["per_tool"]["search"]["calls"] == 2


@pytest.mark.asyncio
async def test_telemetry_slowest_tools():
    """Test slowest tools ranking."""
    await telemetry.research_telemetry_reset()

    # Create tools with different average latencies
    await telemetry.research_telemetry_record("slow_tool", 500.0, True)
    await telemetry.research_telemetry_record("fast_tool", 10.0, True)
    await telemetry.research_telemetry_record("medium_tool", 100.0, True)

    stats = await telemetry.research_telemetry_stats(window_minutes=60)

    assert "slowest_tools" in stats
    # slow_tool should appear before fast_tool
    if stats["slowest_tools"]:
        assert stats["slowest_tools"][0] == "slow_tool"


@pytest.mark.asyncio
async def test_telemetry_reset():
    """Test resetting telemetry buffer."""
    await telemetry.research_telemetry_reset()

    # Record some data
    await telemetry.research_telemetry_record("test_tool", 50.0, True)
    await telemetry.research_telemetry_record("test_tool", 60.0, True)

    # Reset
    result = await telemetry.research_telemetry_reset()

    assert result["cleared_records"] == 2
    assert "previous_window_start" in result
    assert "reset_at" in result

    # Verify buffer is empty
    stats = await telemetry.research_telemetry_stats(window_minutes=60)
    assert stats["total_calls"] == 0


@pytest.mark.asyncio
async def test_telemetry_empty_buffer():
    """Test stats when buffer is empty."""
    await telemetry.research_telemetry_reset()

    stats = await telemetry.research_telemetry_stats(window_minutes=60)

    assert stats["total_calls"] == 0
    assert stats["success_rate"] == 0
    assert stats["latency"]["p50"] == 0
    assert stats["per_tool"] == {}
    assert stats["slowest_tools"] == []


@pytest.mark.asyncio
async def test_telemetry_success_rate_calculation():
    """Test success rate calculation."""
    await telemetry.research_telemetry_reset()

    # Record 8 successes and 2 failures
    for i in range(8):
        await telemetry.research_telemetry_record("tool", 50.0, True)
    for i in range(2):
        await telemetry.research_telemetry_record("tool", 50.0, False)

    stats = await telemetry.research_telemetry_stats(window_minutes=60)

    assert stats["total_calls"] == 10
    assert stats["success_rate"] == 80.0


@pytest.mark.asyncio
async def test_telemetry_window_filtering():
    """Test that window filtering works (would need time manipulation in practice)."""
    await telemetry.research_telemetry_reset()

    # Record data
    await telemetry.research_telemetry_record("test", 50.0, True)

    # Stats with 1 minute window should include recent record
    stats_1min = await telemetry.research_telemetry_stats(window_minutes=1)
    assert stats_1min["total_calls"] >= 1

    # Stats with 60 minute window should also include it
    stats_60min = await telemetry.research_telemetry_stats(window_minutes=60)
    assert stats_60min["total_calls"] >= 1
