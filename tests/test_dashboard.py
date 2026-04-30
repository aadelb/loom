"""Unit tests for usage dashboard module.

Tests:
- Dashboard returns all required fields (REQ-083)
- Credits remaining calculated correctly
- Usage percentage calculated correctly
- Top tools sorted by credits in descending order
- Unknown customer returns error
- No usage returns zeros
- Alert thresholds at 50%, 80%, 100%
- No alert below 50%
- Alert levels are correct (info < warning < critical)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from loom.billing.dashboard import get_dashboard, get_usage_alerts
from loom.billing.customers import create_customer
from loom.billing.meter import record_usage


class TestDashboardFieldsAndCalculations:
    """Tests for dashboard field presence and calculation accuracy."""

    def test_dashboard_returns_all_required_fields(self) -> None:
        """Dashboard returns all fields required by REQ-083."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                # Create customer
                result = create_customer("Test User", "test@example.com", "pro")
                customer_id = result["customer_id"]

                # Get dashboard
                dashboard = get_dashboard(customer_id)

                # Check all required fields present
                required_fields = [
                    "customer_id",
                    "tier",
                    "credits_total",
                    "credits_used",
                    "credits_remaining",
                    "usage_percent",
                    "calls_today",
                    "top_tools",
                    "by_tool",
                    "date",
                ]
                for field in required_fields:
                    assert field in dashboard, f"Missing field: {field}"

    def test_credits_remaining_calculated_correctly(self) -> None:
        """Credits remaining = total - used (never negative)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                # Create customer with 100 credits
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                # Record 30 credit usage
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage(customer_id, "research_fetch", 30)

                # Check calculation
                dashboard = get_dashboard(customer_id, today)
                assert dashboard["credits_total"] == 500  # free tier
                assert dashboard["credits_used"] == 30
                assert dashboard["credits_remaining"] == 470

    def test_credits_remaining_never_negative(self) -> None:
        """Credits remaining is never negative (clamped to 0)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                # Create customer with 100 credits
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                # Record 600 credit usage (exceeds limit)
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                for _ in range(200):  # 200 * 3 credits = 600
                    record_usage(customer_id, "research_deep", 10)

                # Check clamped to 0
                dashboard = get_dashboard(customer_id, today)
                assert dashboard["credits_remaining"] >= 0

    def test_usage_percent_calculated_correctly(self) -> None:
        """Usage percent = (used / total) * 100, rounded to 1 decimal."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                # Create customer with 1000 credits
                result = create_customer("Test User", "test@example.com", "pro")
                customer_id = result["customer_id"]

                # Record 250 credit usage (25%)
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage(customer_id, "research_fetch", 250)

                dashboard = get_dashboard(customer_id, today)
                # 250 / 10000 * 100 = 2.5
                assert dashboard["usage_percent"] == 2.5

    def test_usage_percent_avoids_division_by_zero(self) -> None:
        """Usage percent handles zero total credits gracefully."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                # Manually create customer with 0 credits
                customers = {
                    "test_cust": {
                        "name": "Test",
                        "email": "test@example.com",
                        "tier": "free",
                        "api_key": "hash",
                        "credits": 0,
                        "active": True,
                    }
                }
                customers_file.parent.mkdir(parents=True, exist_ok=True)
                customers_file.write_text(json.dumps(customers))

                dashboard = get_dashboard("test_cust")
                # Should not raise ZeroDivisionError
                assert "usage_percent" in dashboard
                assert dashboard["usage_percent"] == 0.0


class TestTopToolsAndBreakdown:
    """Tests for top tools and usage breakdown."""

    def test_top_tools_sorted_by_credits_descending(self) -> None:
        """Top tools returned in descending order by credit cost."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "pro")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # Record usage in non-sorted order
                record_usage(customer_id, "research_fetch", 30)  # 30 total
                record_usage(customer_id, "research_deep", 100)  # 100 total
                record_usage(customer_id, "research_search", 10)  # 10 total

                dashboard = get_dashboard(customer_id, today)
                top_tools = dashboard["top_tools"]

                # Check sorted by credits descending
                assert len(top_tools) == 3
                assert top_tools[0]["tool"] == "research_deep"
                assert top_tools[0]["credits"] == 100
                assert top_tools[1]["tool"] == "research_fetch"
                assert top_tools[1]["credits"] == 30
                assert top_tools[2]["tool"] == "research_search"
                assert top_tools[2]["credits"] == 10

    def test_by_tool_breakdown_matches_meter_data(self) -> None:
        """by_tool breakdown matches aggregated meter data."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "pro")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage(customer_id, "research_fetch", 10)
                record_usage(customer_id, "research_fetch", 20)  # 30 total
                record_usage(customer_id, "research_search", 5)

                dashboard = get_dashboard(customer_id, today)
                by_tool = dashboard["by_tool"]

                assert by_tool["research_fetch"] == 30
                assert by_tool["research_search"] == 5


class TestUnknownCustomer:
    """Tests for handling unknown/missing customers."""

    def test_unknown_customer_returns_error(self) -> None:
        """Dashboard returns error dict for unknown customer."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                dashboard = get_dashboard("nonexistent_customer")

                assert "error" in dashboard
                assert dashboard["error"] == "customer_not_found"
                assert dashboard["customer_id"] == "nonexistent_customer"


class TestZeroUsage:
    """Tests for customers with no usage."""

    def test_no_usage_returns_zeros(self) -> None:
        """Dashboard returns zero usage for customers with no meter entries."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                dashboard = get_dashboard(customer_id)

                assert dashboard["credits_used"] == 0
                assert dashboard["calls_today"] == 0
                assert dashboard["top_tools"] == []
                assert dashboard["by_tool"] == {}
                assert dashboard["usage_percent"] == 0.0


class TestUsageAlerts:
    """Tests for usage alert thresholds and levels."""

    def test_alert_at_50_percent_threshold(self) -> None:
        """Alert triggered at exactly 50% usage (info level)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # 50% of 500 credits = 250
                record_usage(customer_id, "research_fetch", 250)

                alerts = get_usage_alerts(customer_id)

                assert len(alerts) == 1
                assert alerts[0]["level"] == "info"
                assert alerts[0]["message"] == "50% of credits used"
                assert alerts[0]["percent"] == 50.0

    def test_alert_at_80_percent_threshold(self) -> None:
        """Alert triggered at exactly 80% usage (warning level)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # 80% of 500 credits = 400
                record_usage(customer_id, "research_fetch", 400)

                alerts = get_usage_alerts(customer_id)

                assert len(alerts) == 1
                assert alerts[0]["level"] == "warning"
                assert alerts[0]["message"] == "80% of credits used"
                assert alerts[0]["percent"] == 80.0

    def test_alert_at_100_percent_threshold(self) -> None:
        """Alert triggered at 100% usage (critical level)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # 100% of 500 credits
                record_usage(customer_id, "research_fetch", 500)

                alerts = get_usage_alerts(customer_id)

                assert len(alerts) == 1
                assert alerts[0]["level"] == "critical"
                assert alerts[0]["message"] == "Credit limit reached"
                assert alerts[0]["percent"] == 100.0

    def test_no_alert_below_50_percent(self) -> None:
        """No alert triggered below 50% usage."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # 40% of 500 credits = 200
                record_usage(customer_id, "research_fetch", 200)

                alerts = get_usage_alerts(customer_id)

                assert len(alerts) == 0

    def test_no_alert_for_unknown_customer(self) -> None:
        """get_usage_alerts returns empty list for unknown customer."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                alerts = get_usage_alerts("nonexistent_customer")

                assert alerts == []

    def test_alert_above_80_percent_shows_warning_not_info(self) -> None:
        """Alert at 85% shows warning (not info from 50% threshold)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # 85% of 500 credits = 425
                record_usage(customer_id, "research_fetch", 425)

                alerts = get_usage_alerts(customer_id)

                assert len(alerts) == 1
                assert alerts[0]["level"] == "warning"
                # Should be warning, not info
                assert alerts[0]["level"] != "info"

    def test_alert_above_100_percent_shows_critical_only(self) -> None:
        """Alert above 100% shows critical (not lower thresholds)."""
        with TemporaryDirectory(prefix="loom_dashboard_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            meter_dir = Path(tmpdir) / "meters"
            with patch(
                "loom.billing.customers._CUSTOMERS_FILE", customers_file
            ), patch("loom.billing.meter._METER_DIR", meter_dir):
                result = create_customer("Test User", "test@example.com", "free")
                customer_id = result["customer_id"]

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                # 120% of 500 credits = 600
                for _ in range(200):
                    record_usage(customer_id, "research_deep", 10)

                alerts = get_usage_alerts(customer_id)

                # Should have exactly one critical alert
                assert len(alerts) == 1
                assert alerts[0]["level"] == "critical"
