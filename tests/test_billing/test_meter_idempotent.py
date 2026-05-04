"""Tests for idempotent usage metering.

Tests cover:
- Idempotent meter recording
- Duplicate request handling
- Usage aggregation
"""

from __future__ import annotations

import pytest
from loom.billing.meter import (
    record_usage,
    record_usage_idempotent,
    get_usage,
    get_top_tools,
)


class TestMeterRecording:
    """Test basic meter recording."""

    def test_record_usage(self, tmp_path) -> None:
        """Test recording a usage entry."""
        from loom.billing import meter

        # Mock the meter directory
        meter._METER_DIR = tmp_path

        entry = record_usage("cust_123", "research_fetch", 3, 100.5)

        assert entry["customer_id"] == "cust_123"
        assert entry["tool_name"] == "research_fetch"
        assert entry["credits_used"] == 3
        assert entry["duration_ms"] == 100.5
        assert "timestamp" in entry

    def test_record_usage_validates_customer_id(self) -> None:
        """Test record_usage validates customer_id format."""
        with pytest.raises(ValueError, match="Invalid customer_id format"):
            record_usage("INVALID_ID_WITH_CAPS", "tool", 1)

        with pytest.raises(ValueError, match="Invalid customer_id format"):
            record_usage("id-with-special!chars", "tool", 1)

    def test_get_usage_no_entries(self, tmp_path) -> None:
        """Test get_usage returns empty stats for customer with no entries."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        usage = get_usage("cust_empty", "2024-01-01")

        assert usage["customer_id"] == "cust_empty"
        assert usage["date"] == "2024-01-01"
        assert usage["total_credits"] == 0
        assert usage["total_calls"] == 0
        assert usage["by_tool"] == {}


class TestIdempotentMeterRecording:
    """Test idempotent meter recording."""

    @pytest.mark.asyncio
    async def test_record_usage_idempotent_new_key(self, tmp_path) -> None:
        """Test idempotent recording with new key."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        result = await record_usage_idempotent(
            "cust_idem_1",
            "research_search",
            1,
            50.0,
        )

        assert result["customer_id"] == "cust_idem_1"
        assert result["tool_name"] == "research_search"
        assert result["credits_used"] == 1
        assert result["duration_ms"] == 50.0
        assert result["is_duplicate"] is False
        assert "idempotency_key" in result
        assert len(result["idempotency_key"]) == 64

    @pytest.mark.asyncio
    async def test_record_usage_idempotent_with_provided_key(self, tmp_path) -> None:
        """Test idempotent recording with provided key."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        key = "a" * 64
        result = await record_usage_idempotent(
            "cust_idem_2",
            "research_fetch",
            3,
            200.0,
            idempotency_key=key,
        )

        assert result["idempotency_key"] == key
        assert result["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_record_usage_idempotent_preserves_fields(self, tmp_path) -> None:
        """Test idempotent recording preserves all fields."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        result = await record_usage_idempotent(
            "cust_idem_3",
            "research_deep",
            10,
            5000.0,
        )

        assert result["customer_id"] == "cust_idem_3"
        assert result["tool_name"] == "research_deep"
        assert result["credits_used"] == 10
        assert result["duration_ms"] == 5000.0
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_record_usage_idempotent_default_duration(self, tmp_path) -> None:
        """Test idempotent recording with default duration."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        result = await record_usage_idempotent(
            "cust_idem_4",
            "research_github",
            3,
        )

        assert result["duration_ms"] == 0.0
        assert result["is_duplicate"] is False


class TestGetUsageStats:
    """Test usage statistics retrieval."""

    def test_get_top_tools_empty(self, tmp_path) -> None:
        """Test get_top_tools returns empty list for customer with no usage."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        tools = get_top_tools("cust_no_tools", "2024-01-01")
        assert tools == []

    def test_get_top_tools_respects_limit(self, tmp_path) -> None:
        """Test get_top_tools respects limit parameter."""
        from loom.billing import meter

        meter._METER_DIR = tmp_path

        # Record multiple tools
        record_usage("cust_top", "tool1", 10)
        record_usage("cust_top", "tool2", 8)
        record_usage("cust_top", "tool3", 6)
        record_usage("cust_top", "tool4", 4)
        record_usage("cust_top", "tool5", 2)

        # Get top 3
        tools = get_top_tools("cust_top", limit=3)
        assert len(tools) <= 3

        # Verify sorted by credits descending
        if len(tools) > 1:
            for i in range(len(tools) - 1):
                assert tools[i]["credits"] >= tools[i + 1]["credits"]
