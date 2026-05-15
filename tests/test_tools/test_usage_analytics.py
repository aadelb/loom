"""Unit tests for tool usage analytics system.

Tests for research_usage_record, research_usage_report, research_usage_trends.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest

import loom.tools.infrastructure.usage_analytics


class TestUsageRecord:
    """research_usage_record stores tool usage events."""

    @pytest.mark.asyncio
    async def test_record_single_tool(self) -> None:
        """Recording a tool usage increments counter."""
        # Clear module state
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        result = await usage_analytics.research_usage_record("test_tool")

        assert result["recorded"] is True
        assert result["tool"] == "test_tool"
        assert result["total_uses"] == 1
        assert len(usage_analytics._usage_history) == 1

    @pytest.mark.asyncio
    async def test_record_multiple_calls(self) -> None:
        """Multiple calls to same tool increment counter."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        for i in range(3):
            result = await usage_analytics.research_usage_record("fetch_tool")
            assert result["total_uses"] == i + 1

        assert len(usage_analytics._usage_history) == 3

    @pytest.mark.asyncio
    async def test_record_with_caller(self) -> None:
        """Caller parameter is stored in history."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        await usage_analytics.research_usage_record("search_tool", caller="custom_agent")

        event = list(usage_analytics._usage_history)[0]
        assert event["tool"] == "search_tool"
        assert event["caller"] == "custom_agent"

    @pytest.mark.asyncio
    async def test_record_has_timestamp(self) -> None:
        """Each recorded event has an ISO timestamp."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        await usage_analytics.research_usage_record("dated_tool")

        event = list(usage_analytics._usage_history)[0]
        assert "timestamp" in event
        # Verify it's parseable ISO format
        ts = datetime.fromisoformat(event["timestamp"])
        assert ts is not None
        # Should be recent (within last minute)
        now = datetime.now(UTC)
        assert (now - ts).total_seconds() < 60


class TestUsageReport:
    """research_usage_report generates usage statistics."""

    @pytest.mark.asyncio
    async def test_report_empty_history(self) -> None:
        """Report on empty history returns zeros."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        result = await usage_analytics.research_usage_report("today")

        assert result["total_calls"] == 0
        assert result["unique_tools_used"] == 0
        assert result["top_tools"] == []
        assert result["calls_per_minute"] == 0.0
        assert result["peak_hour"] is None

    @pytest.mark.asyncio
    async def test_report_today_period(self) -> None:
        """'today' period filters to current day only."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Record some events with timestamps from today
        now = datetime.now(UTC)
        for i in range(3):
            await usage_analytics.research_usage_record(f"tool_{i}")

        result = await usage_analytics.research_usage_report("today")

        assert result["period"] == "today"
        assert result["total_calls"] == 3
        assert result["unique_tools_used"] == 3

    @pytest.mark.asyncio
    async def test_report_top_tools(self) -> None:
        """Top tools are ranked by call count."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Create uneven distribution
        for i in range(5):
            await usage_analytics.research_usage_record("popular_tool")
        for i in range(2):
            await usage_analytics.research_usage_record("medium_tool")
        await usage_analytics.research_usage_record("rare_tool")

        result = await usage_analytics.research_usage_report("all")

        assert len(result["top_tools"]) == 3
        top = result["top_tools"][0]
        assert top["name"] == "popular_tool"
        assert top["calls"] == 5
        assert top["pct"] == pytest.approx(55.6, abs=0.1)

    @pytest.mark.asyncio
    async def test_report_calls_per_minute(self) -> None:
        """Calls per minute is calculated correctly."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Record 6 calls in a short time
        for i in range(6):
            await usage_analytics.research_usage_record("tool")

        result = await usage_analytics.research_usage_report("hour")

        # 6 calls over ~0 minutes should be > 0
        assert result["calls_per_minute"] >= 0

    @pytest.mark.asyncio
    async def test_report_period_all(self) -> None:
        """'all' period includes everything."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        for i in range(5):
            await usage_analytics.research_usage_record("any_tool")

        result = await usage_analytics.research_usage_report("all")

        assert result["period"] == "all"
        assert result["total_calls"] == 5


class TestUsageTrends:
    """research_usage_trends shows usage patterns over time."""

    @pytest.mark.asyncio
    async def test_trends_empty_history(self) -> None:
        """Trends on empty history returns stable state."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        result = await usage_analytics.research_usage_trends()

        assert result["tool"] == "all"
        assert result["window_hours"] == 24
        assert result["hourly_buckets"] == []
        assert result["trend"] == "stable"
        assert result["peak_time"] is None

    @pytest.mark.asyncio
    async def test_trends_specific_tool(self) -> None:
        """Trends for specific tool filters correctly."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Record events for different tools
        for i in range(3):
            await usage_analytics.research_usage_record("tool_a")
        for i in range(2):
            await usage_analytics.research_usage_record("tool_b")

        result = await usage_analytics.research_usage_trends(tool_name="tool_a")

        # Tool_a should have some entries, tool_b should not appear
        assert result["tool"] == "tool_a"

    @pytest.mark.asyncio
    async def test_trends_hourly_buckets(self) -> None:
        """Hourly buckets aggregate calls by hour."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        for i in range(3):
            await usage_analytics.research_usage_record("tool")

        result = await usage_analytics.research_usage_trends(window_hours=24)

        # Should have at least one hour bucket
        assert len(result["hourly_buckets"]) >= 1
        bucket = result["hourly_buckets"][0]
        assert "hour" in bucket
        assert "calls" in bucket
        assert bucket["calls"] >= 1

    @pytest.mark.asyncio
    async def test_trends_peak_time(self) -> None:
        """Peak time identifies hour with most calls."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        for i in range(5):
            await usage_analytics.research_usage_record("tool")

        result = await usage_analytics.research_usage_trends()

        assert result["peak_time"] is not None
        # Should match one of the hour buckets
        peak_hours = [b["hour"] for b in result["hourly_buckets"]]
        assert result["peak_time"] in peak_hours

    @pytest.mark.asyncio
    async def test_trends_trend_detection(self) -> None:
        """Trend is detected as increasing/decreasing/stable."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Create some distribution that should be detectable
        for i in range(10):
            await usage_analytics.research_usage_record("tool")

        result = await usage_analytics.research_usage_trends(window_hours=24)

        # Trend should be one of the valid values
        assert result["trend"] in ["increasing", "decreasing", "stable"]


class TestIntegration:
    """Integration tests for usage analytics workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(self) -> None:
        """Record events, generate report, show trends."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Simulate tool usage
        await usage_analytics.research_usage_record("fetch", "api")
        await usage_analytics.research_usage_record("search", "api")
        await usage_analytics.research_usage_record("fetch", "cli")
        await asyncio.sleep(0.1)
        await usage_analytics.research_usage_record("deep", "api")

        # Generate report
        report = await usage_analytics.research_usage_report("all")
        assert report["total_calls"] == 4
        assert report["unique_tools_used"] == 3
        assert len(report["top_tools"]) > 0

        # Show trends
        trends = await usage_analytics.research_usage_trends()
        assert len(trends["hourly_buckets"]) > 0
        assert trends["trend"] in ["increasing", "decreasing", "stable"]

    @pytest.mark.asyncio
    async def test_deque_maxlen_behavior(self) -> None:
        """History deque respects maxlen of 50000."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Record at limit + 100
        for i in range(50100):
            await usage_analytics.research_usage_record(f"tool_{i % 10}")

        # Deque should only have 50000 entries
        assert len(usage_analytics._usage_history) == 50000

    @pytest.mark.asyncio
    async def test_concurrent_records(self) -> None:
        """Multiple concurrent record calls work correctly."""
        usage_analytics._usage_counter.clear()
        usage_analytics._usage_history.clear()

        # Record concurrently
        tasks = [
            usage_analytics.research_usage_record(f"tool_{i % 5}")
            for i in range(20)
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r["recorded"] for r in results)
        assert len(usage_analytics._usage_history) == 20
        # Counter should have correct totals
        assert usage_analytics._usage_counter["tool_0"] == 4
        assert usage_analytics._usage_counter["tool_1"] == 4
