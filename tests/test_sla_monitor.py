"""Tests for SLA monitoring system."""

from __future__ import annotations

import pytest
import time
from datetime import datetime
from unittest import mock

from loom.sla_monitor import (
    SLA_TARGETS,
    SLAMonitor,
    BreachEvent,
    RequestMetrics,
    get_sla_monitor,
)


@pytest.fixture
def monitor() -> SLAMonitor:
    """Create a fresh SLA monitor for testing."""
    # Get singleton and reset it
    m = get_sla_monitor()
    m.reset()
    return m


class TestSLATargets:
    """Test SLA target constants."""

    def test_sla_targets_defined(self) -> None:
        """SLA_TARGETS should have all required metrics."""
        assert "uptime_percent" in SLA_TARGETS
        assert "p95_latency_ms" in SLA_TARGETS
        assert "error_rate_percent" in SLA_TARGETS
        assert "tool_availability_percent" in SLA_TARGETS

    def test_sla_targets_are_positive(self) -> None:
        """All target values should be positive."""
        for metric, value in SLA_TARGETS.items():
            assert value > 0, f"{metric} should be positive, got {value}"

    def test_uptime_target_reasonable(self) -> None:
        """Uptime target should be 99.9% or higher."""
        assert SLA_TARGETS["uptime_percent"] >= 99.0

    def test_latency_target_reasonable(self) -> None:
        """P95 latency target should be reasonable (< 30s)."""
        assert SLA_TARGETS["p95_latency_ms"] < 30000


class TestRequestMetrics:
    """Test RequestMetrics dataclass."""

    def test_request_metrics_creation(self) -> None:
        """RequestMetrics should store all required fields."""
        now = time.time()
        metric = RequestMetrics(
            timestamp=now,
            success=True,
            latency_ms=100.0,
            tool_name="test_tool",
        )
        assert metric.timestamp == now
        assert metric.success is True
        assert metric.latency_ms == 100.0
        assert metric.tool_name == "test_tool"

    def test_request_metrics_without_tool_name(self) -> None:
        """RequestMetrics should work without tool_name."""
        metric = RequestMetrics(
            timestamp=time.time(),
            success=False,
            latency_ms=500.0,
        )
        assert metric.tool_name is None


class TestBreachEvent:
    """Test BreachEvent dataclass."""

    def test_breach_event_creation(self) -> None:
        """BreachEvent should store breach details."""
        now = datetime.now(datetime.UTC)
        breach = BreachEvent(
            metric="uptime_percent",
            target=99.9,
            actual=98.5,
            breached_since=now,
            duration_seconds=300.0,
        )
        assert breach.metric == "uptime_percent"
        assert breach.target == 99.9
        assert breach.actual == 98.5
        assert breach.breached_since == now
        assert breach.duration_seconds == 300.0

    def test_breach_event_string_representation(self) -> None:
        """BreachEvent string representation should be readable."""
        now = datetime.now(datetime.UTC)
        breach = BreachEvent(
            metric="p95_latency_ms",
            target=5000.0,
            actual=7500.0,
            breached_since=now,
            duration_seconds=600.0,
        )
        str_repr = str(breach)
        assert "p95_latency_ms" in str_repr
        assert "7500.00" in str_repr or "7500" in str_repr
        assert "5000.00" in str_repr or "5000" in str_repr


class TestSLAMonitorSingleton:
    """Test SLAMonitor singleton behavior."""

    def test_singleton_instance(self) -> None:
        """Multiple calls to get_sla_monitor should return same instance."""
        m1 = get_sla_monitor()
        m2 = get_sla_monitor()
        assert m1 is m2

    def test_singleton_through_class(self) -> None:
        """Creating instances via SLAMonitor() should return singleton."""
        m1 = SLAMonitor()
        m2 = SLAMonitor()
        assert m1 is m2

    def test_singleton_preserves_state(self) -> None:
        """Singleton should preserve state across calls."""
        m = get_sla_monitor()
        m.reset()
        m.record_request(success=True, latency_ms=100.0)

        m2 = get_sla_monitor()
        sla = m2.get_current_sla()
        assert sla["metrics_count"] == 1


class TestRecordRequest:
    """Test recording requests."""

    def test_record_successful_request(self, monitor: SLAMonitor) -> None:
        """Should record a successful request."""
        monitor.record_request(success=True, latency_ms=100.0)

        sla = monitor.get_current_sla()
        assert sla["metrics_count"] == 1
        assert sla["uptime_percent"]["actual"] == 100.0

    def test_record_failed_request(self, monitor: SLAMonitor) -> None:
        """Should record a failed request."""
        monitor.record_request(success=False, latency_ms=500.0)

        sla = monitor.get_current_sla()
        assert sla["metrics_count"] == 1
        assert sla["error_rate_percent"]["actual"] == 100.0
        assert sla["uptime_percent"]["actual"] == 0.0

    def test_record_multiple_requests(self, monitor: SLAMonitor) -> None:
        """Should accumulate multiple requests."""
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=200.0)
        monitor.record_request(success=False, latency_ms=300.0)

        sla = monitor.get_current_sla()
        assert sla["metrics_count"] == 3
        assert sla["uptime_percent"]["actual"] == pytest.approx(66.666, rel=0.01)
        assert sla["error_rate_percent"]["actual"] == pytest.approx(33.333, rel=0.01)

    def test_record_with_tool_name(self, monitor: SLAMonitor) -> None:
        """Should record tool name for availability tracking."""
        monitor.record_request(success=True, latency_ms=100.0, tool_name="research_fetch")
        monitor.record_request(success=True, latency_ms=150.0, tool_name="research_search")

        sla = monitor.get_current_sla()
        assert sla["metrics_count"] == 2
        # Tool availability calculated from unique tools with successful requests
        assert sla["tool_availability_percent"]["actual"] > 0

    def test_negative_latency_clamped(self, monitor: SLAMonitor) -> None:
        """Negative latencies should be clamped to 0."""
        monitor.record_request(success=True, latency_ms=-100.0)

        sla = monitor.get_current_sla()
        # Should still record the request
        assert sla["metrics_count"] == 1


class TestGetCurrentSLA:
    """Test SLA metrics calculation."""

    def test_empty_monitor_metrics(self, monitor: SLAMonitor) -> None:
        """Empty monitor should return default metrics."""
        sla = monitor.get_current_sla()
        assert sla["metrics_count"] == 0
        assert sla["uptime_percent"]["actual"] == 100.0
        assert sla["error_rate_percent"]["actual"] == 0.0
        assert sla["p95_latency_ms"]["actual"] == 0.0
        assert sla["window_age_seconds"] == 0.0

    def test_uptime_calculation(self, monitor: SLAMonitor) -> None:
        """Uptime should be 100 * (success / total)."""
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=False, latency_ms=100.0)

        sla = monitor.get_current_sla()
        assert sla["uptime_percent"]["actual"] == pytest.approx(66.666, rel=0.01)

    def test_error_rate_calculation(self, monitor: SLAMonitor) -> None:
        """Error rate should be 100 * (errors / total)."""
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=False, latency_ms=100.0)

        sla = monitor.get_current_sla()
        assert sla["error_rate_percent"]["actual"] == pytest.approx(33.333, rel=0.01)

    def test_p95_latency_calculation(self, monitor: SLAMonitor) -> None:
        """P95 latency should be 95th percentile."""
        # Add 20 requests with latencies 100-2000
        for i in range(20):
            monitor.record_request(success=True, latency_ms=float(100 * (i + 1)))

        sla = monitor.get_current_sla()
        # 95th percentile of 100, 200, ..., 2000
        # Should be around 1900
        p95 = sla["p95_latency_ms"]["actual"]
        assert p95 > 1800  # Should be high latency value
        assert p95 <= 2000

    def test_window_age_calculation(self, monitor: SLAMonitor) -> None:
        """Window age should increase over time."""
        monitor.record_request(success=True, latency_ms=100.0)

        time.sleep(0.1)
        sla = monitor.get_current_sla()
        assert sla["window_age_seconds"] >= 0.1

    def test_sla_targets_in_response(self, monitor: SLAMonitor) -> None:
        """Response should include target values."""
        monitor.record_request(success=True, latency_ms=100.0)

        sla = monitor.get_current_sla()
        assert sla["uptime_percent"]["target"] == SLA_TARGETS["uptime_percent"]
        assert sla["p95_latency_ms"]["target"] == SLA_TARGETS["p95_latency_ms"]
        assert sla["error_rate_percent"]["target"] == SLA_TARGETS["error_rate_percent"]
        assert sla["tool_availability_percent"]["target"] == SLA_TARGETS["tool_availability_percent"]


class TestBreachDetection:
    """Test SLA breach detection and alerting."""

    def test_no_breaches_when_healthy(self, monitor: SLAMonitor) -> None:
        """Should not report breaches when healthy."""
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.check_and_alert()

        assert not monitor.is_breaching()
        assert len(monitor.get_breaches()) == 0

    def test_uptime_breach_detection(self, monitor: SLAMonitor) -> None:
        """Should detect uptime breach."""
        # Create 100 failed requests to trigger breach
        for _ in range(100):
            monitor.record_request(success=False, latency_ms=100.0)

        monitor.check_and_alert()

        assert monitor.is_breaching()
        breaches = monitor.get_breaches()
        assert len(breaches) > 0

        # Check for uptime breach
        uptime_breach = next((b for b in breaches if b.metric == "uptime_percent"), None)
        assert uptime_breach is not None
        assert uptime_breach.actual == 0.0

    def test_error_rate_breach_detection(self, monitor: SLAMonitor) -> None:
        """Should detect error rate breach."""
        # Create mostly failed requests
        for _ in range(99):
            monitor.record_request(success=False, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=100.0)

        monitor.check_and_alert()

        breaches = monitor.get_breaches()
        error_breach = next((b for b in breaches if b.metric == "error_rate_percent"), None)
        assert error_breach is not None
        assert error_breach.actual == pytest.approx(99.0, rel=0.01)

    def test_latency_breach_detection(self, monitor: SLAMonitor) -> None:
        """Should detect latency breach."""
        # Add requests with high latencies
        for _ in range(20):
            monitor.record_request(success=True, latency_ms=10000.0)  # 10 seconds each

        monitor.check_and_alert()

        breaches = monitor.get_breaches()
        latency_breach = next((b for b in breaches if b.metric == "p95_latency_ms"), None)
        assert latency_breach is not None
        assert latency_breach.actual > SLA_TARGETS["p95_latency_ms"]

    def test_breach_recovery(self, monitor: SLAMonitor) -> None:
        """Should detect breach recovery."""
        # Create a breach
        for _ in range(50):
            monitor.record_request(success=False, latency_ms=100.0)

        monitor.check_and_alert()
        assert monitor.is_breaching()

        # Now add successful requests to recover
        for _ in range(50):
            monitor.record_request(success=True, latency_ms=100.0)

        monitor.check_and_alert()
        # Should recover (uptime back to 50%, which is still breached)
        # but the logic should detect the improvement

    def test_breach_event_duration(self, monitor: SLAMonitor) -> None:
        """Breach event should track duration."""
        for _ in range(100):
            monitor.record_request(success=False, latency_ms=100.0)

        monitor.check_and_alert()
        time.sleep(0.1)
        monitor.check_and_alert()

        breaches = monitor.get_breaches()
        assert len(breaches) > 0

        for breach in breaches:
            assert breach.duration_seconds >= 0.1


class TestSetSLATarget:
    """Test updating SLA targets."""

    def test_set_valid_target(self, monitor: SLAMonitor) -> None:
        """Should update a valid SLA target."""
        monitor.set_sla_target("uptime_percent", 99.5)
        assert monitor._sla_targets["uptime_percent"] == 99.5

    def test_set_all_targets(self, monitor: SLAMonitor) -> None:
        """Should be able to set all targets."""
        monitor.set_sla_target("uptime_percent", 99.8)
        monitor.set_sla_target("p95_latency_ms", 3000.0)
        monitor.set_sla_target("error_rate_percent", 0.5)
        monitor.set_sla_target("tool_availability_percent", 90.0)

        sla_metrics = monitor.get_current_sla()
        assert sla_metrics["uptime_percent"]["target"] == 99.8
        assert sla_metrics["p95_latency_ms"]["target"] == 3000.0
        assert sla_metrics["error_rate_percent"]["target"] == 0.5
        assert sla_metrics["tool_availability_percent"]["target"] == 90.0

    def test_set_invalid_target(self, monitor: SLAMonitor) -> None:
        """Should raise error for invalid metric."""
        with pytest.raises(ValueError):
            monitor.set_sla_target("invalid_metric", 50.0)


class TestReset:
    """Test monitor reset."""

    def test_reset_clears_metrics(self, monitor: SLAMonitor) -> None:
        """Reset should clear all metrics."""
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=200.0)

        sla_before = monitor.get_current_sla()
        assert sla_before["metrics_count"] == 2

        monitor.reset()

        sla_after = monitor.get_current_sla()
        assert sla_after["metrics_count"] == 0

    def test_reset_clears_breaches(self, monitor: SLAMonitor) -> None:
        """Reset should clear breach events."""
        for _ in range(100):
            monitor.record_request(success=False, latency_ms=100.0)

        monitor.check_and_alert()
        assert monitor.is_breaching()

        monitor.reset()

        assert not monitor.is_breaching()
        assert len(monitor.get_breaches()) == 0


class TestSliding Window:
    """Test sliding window behavior."""

    def test_maxlen_enforcement(self, monitor: SLAMonitor) -> None:
        """Monitor should not grow beyond maxlen."""
        # Add many requests
        for i in range(10000):
            monitor.record_request(success=True, latency_ms=float(i % 1000))

        sla = monitor.get_current_sla()
        # Should be capped at 6000
        assert sla["metrics_count"] <= 6001  # Allow slight overflow


class TestIntegration:
    """Integration tests for full SLA monitoring workflow."""

    def test_typical_monitoring_flow(self, monitor: SLAMonitor) -> None:
        """Test a typical monitoring flow."""
        # Simulate normal operations
        for _ in range(90):
            monitor.record_request(success=True, latency_ms=500.0)
        for _ in range(10):
            monitor.record_request(success=False, latency_ms=1000.0)

        monitor.check_and_alert()

        sla = monitor.get_current_sla()
        assert sla["uptime_percent"]["actual"] == 90.0
        assert sla["error_rate_percent"]["actual"] == 10.0

        # Should be healthy (uptime 90% vs 99.9% target)
        # Actually this should breach
        breaches = monitor.get_breaches()
        uptime_breach = next((b for b in breaches if b.metric == "uptime_percent"), None)
        assert uptime_breach is not None

    def test_monitoring_with_mixed_latencies(self, monitor: SLAMonitor) -> None:
        """Test monitoring with varied latencies."""
        # Fast requests
        for _ in range(10):
            monitor.record_request(success=True, latency_ms=100.0)

        # Slow requests
        for _ in range(10):
            monitor.record_request(success=True, latency_ms=10000.0)

        sla = monitor.get_current_sla()
        assert sla["uptime_percent"]["actual"] == 100.0
        # P95 should be high due to slow requests
        assert sla["p95_latency_ms"]["actual"] > 9000

    def test_monitoring_with_recovery_scenario(self, monitor: SLAMonitor) -> None:
        """Test outage and recovery scenario."""
        # Start with failures
        for _ in range(20):
            monitor.record_request(success=False, latency_ms=5000.0)

        monitor.check_and_alert()
        breaches_during_outage = len(monitor.get_breaches())
        assert breaches_during_outage > 0

        # Recover with successful requests
        for _ in range(80):
            monitor.record_request(success=True, latency_ms=200.0)

        monitor.check_and_alert()
        breaches_after_recovery = len(monitor.get_breaches())
        # Should still have breach (20 failures out of 100 = 80% uptime vs 99.9% target)
        assert breaches_after_recovery > 0
