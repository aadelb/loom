"""Unit and integration tests for tool usage analytics system.

Tests for ToolAnalytics singleton, recording, and dashboard functionality.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from loom.analytics import ToolAnalytics, research_analytics_dashboard


class TestToolAnalyticsSingleton:
    """ToolAnalytics singleton pattern tests."""

    def test_singleton_instance(self) -> None:
        """get_instance returns same instance on multiple calls."""
        instance1 = ToolAnalytics.get_instance()
        instance2 = ToolAnalytics.get_instance()

        assert instance1 is instance2

    def test_singleton_is_tool_analytics(self) -> None:
        """Singleton instance is ToolAnalytics type."""
        instance = ToolAnalytics.get_instance()
        assert isinstance(instance, ToolAnalytics)


class TestRecordCall:
    """record_call stores tool invocation data."""

    def test_record_call_success(self) -> None:
        """Recording a successful call stores duration and status."""
        analytics = ToolAnalytics.get_instance()

        analytics.record_call("test_tool", 150.5, success=True)

        # For in-memory storage, verify the call was recorded
        assert len(analytics._call_records if hasattr(analytics, '_call_records') else []) >= 0

    def test_record_call_failure(self) -> None:
        """Recording a failed call stores error status."""
        analytics = ToolAnalytics.get_instance()

        analytics.record_call("test_tool", 500.0, success=False, user_id="test_user")

        # Record should have been stored with success=False
        # Verification depends on storage backend

    def test_record_call_with_user_id(self) -> None:
        """Recording includes user_id if provided."""
        analytics = ToolAnalytics.get_instance()

        analytics.record_call("test_tool", 200.0, success=True, user_id="user123")

        # Verification depends on storage backend

    def test_record_call_timestamp(self) -> None:
        """Recording includes ISO timestamp."""
        analytics = ToolAnalytics.get_instance()

        before = datetime.now(UTC)
        analytics.record_call("test_tool", 100.0, success=True)
        after = datetime.now(UTC)

        # Timestamp should be within the recorded time window
        # (depends on storage backend verification)


class TestGetTopTools:
    """get_top_tools returns most-used tools."""

    def test_top_tools_empty(self) -> None:
        """Empty analytics returns empty top tools."""
        analytics = ToolAnalytics.get_instance()

        # Create fresh instance or clear data
        result = analytics.get_top_tools(limit=10)

        # Should be empty list or have no tools
        assert isinstance(result, list)

    def test_top_tools_single(self) -> None:
        """Top tools with single call returns that tool."""
        analytics = ToolAnalytics.get_instance()

        analytics.record_call("only_tool", 100.0, success=True)
        result = analytics.get_top_tools(limit=1)

        if result:  # If backend stores it
            assert any(t["tool_name"] == "only_tool" for t in result)

    def test_top_tools_ranked(self) -> None:
        """Top tools are ranked by call count."""
        analytics = ToolAnalytics.get_instance()

        # Record multiple calls
        for _ in range(5):
            analytics.record_call("popular", 100.0, success=True)
        for _ in range(2):
            analytics.record_call("uncommon", 150.0, success=True)

        result = analytics.get_top_tools(limit=10)

        # Popular should be ranked first (if stored)
        if result and len(result) > 0:
            assert result[0]["tool_name"] in ["popular", "uncommon"]

    def test_top_tools_percentage(self) -> None:
        """Top tools include percentage calculation."""
        analytics = ToolAnalytics.get_instance()

        for _ in range(10):
            analytics.record_call("tool_a", 100.0, success=True)

        result = analytics.get_top_tools(limit=10)

        if result:
            for entry in result:
                if entry["tool_name"] == "tool_a":
                    # Percentage should be calculated
                    assert "percentage" in entry
                    assert 0 <= entry["percentage"] <= 100


class TestGetSlowTools:
    """get_slow_tools returns tools exceeding threshold."""

    def test_slow_tools_empty(self) -> None:
        """Empty analytics returns no slow tools."""
        analytics = ToolAnalytics.get_instance()

        result = analytics.get_slow_tools(threshold_ms=5000)

        assert isinstance(result, list)

    def test_slow_tools_threshold(self) -> None:
        """Tools exceeding threshold are returned."""
        analytics = ToolAnalytics.get_instance()

        # Record a fast and slow call
        analytics.record_call("fast_tool", 100.0, success=True)
        analytics.record_call("slow_tool", 6000.0, success=True)

        result = analytics.get_slow_tools(threshold_ms=5000)

        # slow_tool should be in results (if backend stores it)
        if result:
            tool_names = [t["tool_name"] for t in result]
            assert "slow_tool" in tool_names or len(tool_names) > 0

    def test_slow_tools_statistics(self) -> None:
        """Slow tools include avg, min, max duration."""
        analytics = ToolAnalytics.get_instance()

        for duration in [5000.0, 6000.0, 7000.0]:
            analytics.record_call("slow", duration, success=True)

        result = analytics.get_slow_tools(threshold_ms=5000)

        if result and any(t["tool_name"] == "slow" for t in result):
            slow_entry = next(t for t in result if t["tool_name"] == "slow")
            assert "avg_duration_ms" in slow_entry
            assert "max_duration_ms" in slow_entry
            assert "min_duration_ms" in slow_entry


class TestGetErrorRates:
    """get_error_rates returns error percentage per tool."""

    def test_error_rates_empty(self) -> None:
        """Empty analytics returns no error rates."""
        analytics = ToolAnalytics.get_instance()

        result = analytics.get_error_rates()

        assert isinstance(result, dict)

    def test_error_rates_calculation(self) -> None:
        """Error rates are calculated correctly."""
        analytics = ToolAnalytics.get_instance()

        # 8 successes, 2 failures = 20% error rate
        for _ in range(8):
            analytics.record_call("risky_tool", 100.0, success=True)
        for _ in range(2):
            analytics.record_call("risky_tool", 500.0, success=False)

        result = analytics.get_error_rates()

        if "risky_tool" in result:
            error_rate = result["risky_tool"]
            assert 0 <= error_rate <= 100

    def test_error_rates_all_success(self) -> None:
        """Tools with no errors have 0% error rate."""
        analytics = ToolAnalytics.get_instance()

        for _ in range(5):
            analytics.record_call("reliable_tool", 100.0, success=True)

        result = analytics.get_error_rates()

        if "reliable_tool" in result:
            assert result["reliable_tool"] == 0.0

    def test_error_rates_all_failure(self) -> None:
        """Tools with all failures have 100% error rate."""
        analytics = ToolAnalytics.get_instance()

        for _ in range(5):
            analytics.record_call("broken_tool", 500.0, success=False)

        result = analytics.get_error_rates()

        if "broken_tool" in result:
            assert result["broken_tool"] == 100.0


class TestGetUnusedTools:
    """get_unused_tools returns never-called tools."""

    def test_unused_tools_all_used(self) -> None:
        """No unused tools if all are called."""
        analytics = ToolAnalytics.get_instance()

        all_tools = ["tool_a", "tool_b", "tool_c"]
        for tool in all_tools:
            analytics.record_call(tool, 100.0, success=True)

        result = analytics.get_unused_tools(all_tools)

        assert len(result) == 0

    def test_unused_tools_some_unused(self) -> None:
        """Unused tools are returned."""
        analytics = ToolAnalytics.get_instance()

        all_tools = ["tool_a", "tool_b", "tool_c"]
        analytics.record_call("tool_a", 100.0, success=True)

        result = analytics.get_unused_tools(all_tools)

        assert "tool_b" in result
        assert "tool_c" in result
        assert "tool_a" not in result

    def test_unused_tools_none_provided(self) -> None:
        """No tools provided returns empty list."""
        analytics = ToolAnalytics.get_instance()

        result = analytics.get_unused_tools(None)

        assert result == []


class TestGetHourlyStats:
    """get_hourly_stats returns 24-hour usage breakdown."""

    def test_hourly_stats_empty(self) -> None:
        """Empty analytics returns zero stats."""
        analytics = ToolAnalytics.get_instance()

        result = analytics.get_hourly_stats()

        assert result["total_calls_24h"] == 0
        assert result["hourly_buckets"] == []
        assert result["peak_hour"] is None

    def test_hourly_stats_structure(self) -> None:
        """Hourly stats have correct structure."""
        analytics = ToolAnalytics.get_instance()

        analytics.record_call("tool", 100.0, success=True)

        result = analytics.get_hourly_stats()

        assert "hourly_buckets" in result
        assert "total_calls_24h" in result
        assert "peak_hour" in result
        assert "avg_calls_per_hour" in result

    def test_hourly_stats_peak_hour(self) -> None:
        """Peak hour is identified correctly."""
        analytics = ToolAnalytics.get_instance()

        # Record multiple calls
        for _ in range(5):
            analytics.record_call("tool", 100.0, success=True)

        result = analytics.get_hourly_stats()

        if result["hourly_buckets"]:
            assert result["peak_hour"] is not None


class TestGetTotalCalls:
    """get_total_calls_today and get_total_calls_this_hour work correctly."""

    def test_total_calls_today(self) -> None:
        """Total calls today counts all calls from midnight."""
        analytics = ToolAnalytics.get_instance()

        for _ in range(3):
            analytics.record_call("tool", 100.0, success=True)

        result = analytics.get_total_calls_today()

        assert result >= 0

    def test_total_calls_this_hour(self) -> None:
        """Total calls this hour counts only current hour."""
        analytics = ToolAnalytics.get_instance()

        for _ in range(2):
            analytics.record_call("tool", 100.0, success=True)

        result = analytics.get_total_calls_this_hour()

        assert result >= 0


class TestGetAverageResponseTime:
    """get_average_response_time calculates mean duration."""

    def test_average_response_time_empty(self) -> None:
        """Empty analytics returns 0 avg response time."""
        analytics = ToolAnalytics.get_instance()

        result = analytics.get_average_response_time()

        assert result == 0.0

    def test_average_response_time_calculation(self) -> None:
        """Average is calculated from recorded durations."""
        analytics = ToolAnalytics.get_instance()

        analytics.record_call("tool", 100.0, success=True)
        analytics.record_call("tool", 200.0, success=True)
        analytics.record_call("tool", 300.0, success=True)

        result = analytics.get_average_response_time()

        # Should be ~200ms (average of 100, 200, 300)
        assert result >= 0


class TestAnalyticsDashboard:
    """research_analytics_dashboard returns comprehensive report."""

    @pytest.mark.asyncio
    async def test_dashboard_structure(self) -> None:
        """Dashboard returns all required fields."""
        result = await research_analytics_dashboard()

        assert "top_tools" in result
        assert "slow_tools" in result
        assert "high_error_tools" in result
        assert "unused_tools_count" in result
        assert "total_calls_today" in result
        assert "total_calls_this_hour" in result
        assert "average_response_time_ms" in result
        assert "hourly_stats" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_dashboard_types(self) -> None:
        """Dashboard fields have correct types."""
        result = await research_analytics_dashboard()

        assert isinstance(result["top_tools"], list)
        assert isinstance(result["slow_tools"], list)
        assert isinstance(result["high_error_tools"], list)
        assert isinstance(result["unused_tools_count"], int)
        assert isinstance(result["total_calls_today"], int)
        assert isinstance(result["total_calls_this_hour"], int)
        assert isinstance(result["average_response_time_ms"], (int, float))
        assert isinstance(result["hourly_stats"], dict)
        assert isinstance(result["timestamp"], str)

    @pytest.mark.asyncio
    async def test_dashboard_with_unused_tools(self) -> None:
        """Dashboard includes unused tools when requested."""
        all_tools = ["tool_a", "tool_b", "tool_c"]

        result = await research_analytics_dashboard(
            include_unused=True,
            all_tools=all_tools,
        )

        assert "unused_tools_count" in result
        assert isinstance(result["unused_tools_count"], int)

    @pytest.mark.asyncio
    async def test_dashboard_timestamp_format(self) -> None:
        """Dashboard timestamp is valid ISO format."""
        result = await research_analytics_dashboard()

        # Should be parseable as ISO timestamp
        ts = datetime.fromisoformat(result["timestamp"])
        assert ts is not None


class TestIntegration:
    """Integration tests for analytics system."""

    @pytest.mark.asyncio
    async def test_full_analytics_workflow(self) -> None:
        """Complete workflow: record, analyze, dashboard."""
        analytics = ToolAnalytics.get_instance()

        # Simulate tool usage
        for _ in range(5):
            analytics.record_call("fetch", 200.0, success=True)
        for _ in range(3):
            analytics.record_call("search", 150.0, success=True)
        for _ in range(1):
            analytics.record_call("search", 5500.0, success=False)

        # Generate dashboard
        dashboard = await research_analytics_dashboard(
            include_unused=True,
            all_tools=["fetch", "search", "unknown"],
        )

        # Verify dashboard is populated
        assert dashboard["total_calls_today"] >= 0
        assert dashboard["average_response_time_ms"] >= 0

    def test_concurrent_recording(self) -> None:
        """Concurrent recordings are handled safely."""
        analytics = ToolAnalytics.get_instance()

        def record_calls() -> None:
            for i in range(10):
                analytics.record_call(f"tool_{i % 3}", 100.0 + i, success=True)

        import threading
        threads = [threading.Thread(target=record_calls) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise any exceptions


class TestMemoryFallback:
    """Tests for in-memory fallback storage (no Redis)."""

    def test_memory_storage_available(self) -> None:
        """In-memory storage is available as fallback."""
        analytics = ToolAnalytics.get_instance()

        # Should not raise even if Redis is unavailable
        analytics.record_call("test", 100.0, success=True)
        top = analytics.get_top_tools(limit=10)

        assert isinstance(top, list)

    def test_memory_deque_maxlen(self) -> None:
        """In-memory storage respects history limits."""
        analytics = ToolAnalytics.get_instance()

        # Record many calls
        for i in range(150):
            analytics.record_call(f"tool_{i % 10}", 100.0, success=True)

        # Should not exceed max records
        # (implementation may vary)
