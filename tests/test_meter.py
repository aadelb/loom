"""Unit tests for usage metering module.

Tests:
- record_usage creates JSONL files with valid entries
- Multiple records accumulate in same file
- get_usage returns correct totals and breakdown
- get_usage handles missing files gracefully
- Different customers have separate files
- Date filtering works correctly
- get_top_tools returns sorted list
- get_top_tools respects limit parameter
- JSONL format is parseable
- Timestamps are valid ISO format
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from loom.billing.meter import (
    get_top_tools,
    get_usage,
    record_usage,
)


class TestRecordUsage:
    """Tests for recording usage events."""

    def test_record_usage_creates_file(self) -> None:
        """record_usage creates JSONL file with customer_id and date."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage("cust_123", "research_fetch", 3)

                expected_file = meter_dir / f"cust_123_{today}.jsonl"
                assert expected_file.exists()

    def test_record_usage_writes_jsonl_entry(self) -> None:
        """record_usage writes valid JSON object with newline."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage("cust_123", "research_fetch", 3)

                meter_file = meter_dir / f"cust_123_{today}.jsonl"
                content = meter_file.read_text()
                lines = content.strip().split("\n")
                assert len(lines) == 1

                entry = json.loads(lines[0])
                assert entry["customer_id"] == "cust_123"
                assert entry["tool_name"] == "research_fetch"
                assert entry["credits_used"] == 3

    def test_record_usage_includes_timestamp(self) -> None:
        """record_usage includes ISO format timestamp."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                meter_file = meter_dir / f"cust_123_{today}.jsonl"
                entry = json.loads(meter_file.read_text().strip())

                assert "timestamp" in entry
                # Verify it's parseable as ISO format
                timestamp = datetime.fromisoformat(entry["timestamp"])
                assert timestamp.year == datetime.now(UTC).year

    def test_record_usage_includes_duration(self) -> None:
        """record_usage includes duration_ms rounded to 1 decimal."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3, duration_ms=1234.567)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                meter_file = meter_dir / f"cust_123_{today}.jsonl"
                entry = json.loads(meter_file.read_text().strip())

                assert entry["duration_ms"] == 1234.6

    def test_record_usage_returns_entry(self) -> None:
        """record_usage returns entry dict."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                result = record_usage("cust_123", "research_fetch", 3, duration_ms=500)

                assert result["customer_id"] == "cust_123"
                assert result["tool_name"] == "research_fetch"
                assert result["credits_used"] == 3
                assert result["duration_ms"] == 500.0
                assert "timestamp" in result

    def test_record_usage_multiple_records_accumulate(self) -> None:
        """Multiple record_usage calls append to same JSONL file."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)
                record_usage("cust_123", "research_search", 1)
                record_usage("cust_123", "research_deep", 10)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                meter_file = meter_dir / f"cust_123_{today}.jsonl"
                lines = meter_file.read_text().strip().split("\n")
                assert len(lines) == 3

    def test_record_usage_different_customers_separate_files(self) -> None:
        """Different customers have separate meter files."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage("cust_123", "research_fetch", 3)
                record_usage("cust_456", "research_search", 1)

                file1 = meter_dir / f"cust_123_{today}.jsonl"
                file2 = meter_dir / f"cust_456_{today}.jsonl"
                assert file1.exists()
                assert file2.exists()
                assert file1 != file2


class TestGetUsage:
    """Tests for retrieving usage statistics."""

    def test_get_usage_returns_correct_totals(self) -> None:
        """get_usage sums total_credits and total_calls."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)
                record_usage("cust_123", "research_search", 1)
                record_usage("cust_123", "research_deep", 10)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                usage = get_usage("cust_123", today)

                assert usage["total_credits"] == 14
                assert usage["total_calls"] == 3

    def test_get_usage_breakdown_by_tool(self) -> None:
        """get_usage includes by_tool breakdown."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)
                record_usage("cust_123", "research_fetch", 3)
                record_usage("cust_123", "research_search", 1)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                usage = get_usage("cust_123", today)

                assert usage["by_tool"]["research_fetch"] == 6
                assert usage["by_tool"]["research_search"] == 1

    def test_get_usage_missing_date_returns_zeros(self) -> None:
        """get_usage returns zeros for non-existent date."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                usage = get_usage("cust_nonexistent", "2000-01-01")

                assert usage["customer_id"] == "cust_nonexistent"
                assert usage["date"] == "2000-01-01"
                assert usage["total_credits"] == 0
                assert usage["total_calls"] == 0
                assert usage["by_tool"] == {}

    def test_get_usage_defaults_to_today(self) -> None:
        """get_usage defaults to today's date when date=None."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)

                usage = get_usage("cust_123", None)
                today = datetime.now(UTC).strftime("%Y-%m-%d")

                assert usage["date"] == today
                assert usage["total_credits"] == 3

    def test_get_usage_includes_all_fields(self) -> None:
        """get_usage result includes all expected fields."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                usage = get_usage("cust_123", today)

                assert "customer_id" in usage
                assert "date" in usage
                assert "total_credits" in usage
                assert "total_calls" in usage
                assert "by_tool" in usage

    def test_get_usage_accumulates_same_tool_multiple_calls(self) -> None:
        """get_usage correctly accumulates same tool over multiple calls."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                for _ in range(5):
                    record_usage("cust_123", "research_search", 1)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                usage = get_usage("cust_123", today)

                assert usage["by_tool"]["research_search"] == 5
                assert usage["total_calls"] == 5
                assert usage["total_credits"] == 5


class TestGetTopTools:
    """Tests for top tools retrieval."""

    def test_get_top_tools_returns_sorted_list(self) -> None:
        """get_top_tools returns tools sorted by credits descending."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_search", 1)
                record_usage("cust_123", "research_fetch", 3)
                record_usage("cust_123", "research_deep", 10)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                top = get_top_tools("cust_123", today)

                assert len(top) == 3
                assert top[0]["tool"] == "research_deep"
                assert top[0]["credits"] == 10
                assert top[1]["tool"] == "research_fetch"
                assert top[1]["credits"] == 3
                assert top[2]["tool"] == "research_search"
                assert top[2]["credits"] == 1

    def test_get_top_tools_respects_limit(self) -> None:
        """get_top_tools respects limit parameter."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                for i in range(20):
                    record_usage("cust_123", f"tool_{i}", i)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                top = get_top_tools("cust_123", today, limit=5)

                assert len(top) == 5
                # Top 5 should be tools with highest credits (19, 18, 17, 16, 15)
                assert top[0]["credits"] == 19
                assert top[4]["credits"] == 15

    def test_get_top_tools_returns_empty_for_missing_date(self) -> None:
        """get_top_tools returns empty list for non-existent date."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                top = get_top_tools("cust_nonexistent", "2000-01-01")

                assert top == []

    def test_get_top_tools_default_limit_10(self) -> None:
        """get_top_tools default limit is 10."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                for i in range(15):
                    record_usage("cust_123", f"tool_{i}", i)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                top = get_top_tools("cust_123", today)  # No limit specified

                assert len(top) == 10

    def test_get_top_tools_includes_tool_and_credits(self) -> None:
        """get_top_tools items have tool and credits keys."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                record_usage("cust_123", "research_fetch", 3)

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                top = get_top_tools("cust_123", today)

                assert len(top) == 1
                assert "tool" in top[0]
                assert "credits" in top[0]


class TestMeterIntegration:
    """Integration tests across multiple functions."""

    def test_full_workflow_record_and_retrieve(self) -> None:
        """Full workflow: record multiple events and retrieve aggregated stats."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                # Record multiple tool invocations
                record_usage("cust_alice", "research_fetch", 3, duration_ms=100)
                record_usage("cust_alice", "research_fetch", 3, duration_ms=150)
                record_usage("cust_alice", "research_search", 1, duration_ms=50)
                record_usage("cust_alice", "research_deep", 10, duration_ms=500)

                # Retrieve usage
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                usage = get_usage("cust_alice", today)

                assert usage["total_calls"] == 4
                assert usage["total_credits"] == 17
                assert usage["by_tool"]["research_fetch"] == 6
                assert usage["by_tool"]["research_search"] == 1
                assert usage["by_tool"]["research_deep"] == 10

                # Get top tools
                top = get_top_tools("cust_alice", today, limit=3)
                assert len(top) == 3
                assert top[0]["tool"] == "research_deep"

    def test_multiple_customers_isolated(self) -> None:
        """Multiple customers have completely isolated meter data."""
        with TemporaryDirectory(prefix="loom_meter_") as tmpdir:
            meter_dir = Path(tmpdir) / "meters"
            with patch("loom.billing.meter._METER_DIR", meter_dir):
                today = datetime.now(UTC).strftime("%Y-%m-%d")

                # Customer 1
                record_usage("cust_alice", "research_fetch", 3)
                record_usage("cust_alice", "research_search", 1)

                # Customer 2
                record_usage("cust_bob", "research_deep", 10)
                record_usage("cust_bob", "research_deep", 10)

                # Verify isolation
                alice_usage = get_usage("cust_alice", today)
                bob_usage = get_usage("cust_bob", today)

                assert alice_usage["total_credits"] == 4
                assert bob_usage["total_credits"] == 20
                assert "research_fetch" in alice_usage["by_tool"]
                assert "research_fetch" not in bob_usage["by_tool"]
                assert "research_deep" not in alice_usage["by_tool"]
                assert "research_deep" in bob_usage["by_tool"]
