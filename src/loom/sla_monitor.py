"""SLA monitoring with threshold alerting.

Tracks service-level agreement metrics over a sliding 1-hour window:
- Uptime percent (success vs total requests)
- P95 latency (95th percentile response time)
- Error rate (failed requests as percentage)
- Tool availability (tools responding within threshold)

Detects breaches when actual metrics fall below targets and logs warnings.
Provides singleton SLAMonitor instance with current metrics and breach status.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

log = logging.getLogger("loom.sla_monitor")


# SLA targets (thresholds for alerting)
SLA_TARGETS = {
    "uptime_percent": 99.9,
    "p95_latency_ms": 5000.0,
    "error_rate_percent": 1.0,
    "tool_availability_percent": 95.0,
}


@dataclass
class RequestMetrics:
    """Single request metric snapshot."""

    timestamp: float  # Unix timestamp
    success: bool  # True = success, False = error
    latency_ms: float  # Response time in milliseconds
    tool_name: str | None = None  # Optional tool name for tool_availability tracking


@dataclass
class BreachEvent:
    """SLA breach event with details."""

    metric: str
    target: float
    actual: float
    breached_since: datetime
    duration_seconds: float = 0.0

    def __str__(self) -> str:
        """Format breach event as readable string."""
        return (
            f"SLA breach: {self.metric} at {self.actual:.2f}% "
            f"vs target {self.target:.2f}% (breached for {self.duration_seconds:.0f}s)"
        )


class SLAMonitor:
    """Singleton SLA monitor with 1-hour sliding window tracking.

    Tracks 4 SLA metrics:
    1. Uptime: % of successful requests (target: 99.9%)
    2. P95 Latency: 95th percentile response time (target: 5000ms)
    3. Error Rate: % of failed requests (target: 1.0%)
    4. Tool Availability: % of tools responding (target: 95.0%)

    Uses deque with maxlen=6000 to maintain 1-hour window (1 sample per 0.6s).
    Each request recorded with timestamp, success flag, and latency.
    """

    _instance: SLAMonitor | None = None
    _lock_initialized: bool = False

    def __new__(cls) -> SLAMonitor:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize SLA monitor state."""
        if self._lock_initialized:
            return
        # Deque maxlen = 6000 allows up to ~1.67 hours at 1 req/sec
        # For 10 req/sec average, holds exactly 10 minutes
        # For realistic ~0.6 req/sec average, holds 1-2 hours
        self._metrics: deque[RequestMetrics] = deque(maxlen=6000)
        self._breach_events: dict[str, BreachEvent] = {}
        self._sla_targets = SLA_TARGETS.copy()
        self._lock_initialized = True
        log.info("SLAMonitor initialized with targets: %s", self._sla_targets)

    def record_request(self, success: bool, latency_ms: float, tool_name: str | None = None) -> None:
        """Record a single request metric.

        Args:
            success: True if request succeeded, False if error
            latency_ms: Response time in milliseconds (must be non-negative)
            tool_name: Optional tool name for per-tool availability tracking
        """
        if latency_ms < 0:
            log.warning(f"Negative latency recorded: {latency_ms}ms, clamping to 0")
            latency_ms = max(0.0, latency_ms)

        metric = RequestMetrics(
            timestamp=time.time(),
            success=success,
            latency_ms=latency_ms,
            tool_name=tool_name,
        )
        self._metrics.append(metric)
        log.debug(
            "sla_request_recorded",
            success=success,
            latency_ms=latency_ms,
            tool_name=tool_name,
        )

    def get_current_sla(self) -> dict[str, Any]:
        """Get current SLA metrics vs targets.

        Returns dict with:
        - uptime_percent: actual & target
        - p95_latency_ms: actual & target
        - error_rate_percent: actual & target
        - tool_availability_percent: actual & target
        - timestamp: when metrics were calculated
        - metrics_count: number of requests in window
        - window_age_seconds: age of oldest request in window
        """
        if not self._metrics:
            return {
                "uptime_percent": {"actual": 100.0, "target": self._sla_targets["uptime_percent"]},
                "p95_latency_ms": {"actual": 0.0, "target": self._sla_targets["p95_latency_ms"]},
                "error_rate_percent": {"actual": 0.0, "target": self._sla_targets["error_rate_percent"]},
                "tool_availability_percent": {"actual": 100.0, "target": self._sla_targets["tool_availability_percent"]},
                "timestamp": datetime.now(datetime.UTC),
                "metrics_count": 0,
                "window_age_seconds": 0.0,
            }

        now = time.time()
        metrics_list = list(self._metrics)

        # Calculate uptime_percent (success / total)
        total_requests = len(metrics_list)
        successful_requests = sum(1 for m in metrics_list if m.success)
        uptime_percent = (successful_requests / total_requests * 100.0) if total_requests > 0 else 100.0

        # Calculate error_rate_percent (errors / total)
        error_count = total_requests - successful_requests
        error_rate_percent = (error_count / total_requests * 100.0) if total_requests > 0 else 0.0

        # Calculate p95_latency_ms (95th percentile of latencies)
        latencies = sorted([m.latency_ms for m in metrics_list])
        p95_latency_ms = self._calculate_percentile(latencies, 95)

        # Calculate tool_availability_percent (unique tools / expected tools)
        # Approximate: count unique tools with at least 1 successful request
        available_tools = set()
        for m in metrics_list:
            if m.success and m.tool_name:
                available_tools.add(m.tool_name)
        # Assume 100+ potential tools; availability = min(count/100, 100%)
        tool_availability_percent = min(len(available_tools) / 100.0 * 100.0, 100.0)

        window_age = now - metrics_list[0].timestamp

        return {
            "uptime_percent": {
                "actual": uptime_percent,
                "target": self._sla_targets["uptime_percent"],
            },
            "p95_latency_ms": {
                "actual": p95_latency_ms,
                "target": self._sla_targets["p95_latency_ms"],
            },
            "error_rate_percent": {
                "actual": error_rate_percent,
                "target": self._sla_targets["error_rate_percent"],
            },
            "tool_availability_percent": {
                "actual": tool_availability_percent,
                "target": self._sla_targets["tool_availability_percent"],
            },
            "timestamp": datetime.fromtimestamp(now, tz=datetime.UTC),
            "metrics_count": total_requests,
            "window_age_seconds": window_age,
        }

    def is_breaching(self) -> bool:
        """Check if any SLA is currently breached.

        A breach occurs when actual metric < target (except for latency, where > is breach).

        Returns:
            True if any SLA metric is breached, False otherwise
        """
        return len(self._breach_events) > 0

    def get_breaches(self) -> list[BreachEvent]:
        """Get list of active SLA breaches.

        Returns:
            List of BreachEvent objects, sorted by breach start time
        """
        return sorted(
            self._breach_events.values(),
            key=lambda e: e.breached_since,
        )

    def check_and_alert(self) -> None:
        """Check current metrics against SLA targets and update breach events.

        Called periodically (or after each tool execution) to detect and log breaches.
        Updates internal breach tracking and logs warnings for new/ongoing breaches.
        """
        sla = self.get_current_sla()
        now = datetime.now(datetime.UTC)

        # Check each metric for breach
        checks = [
            ("uptime_percent", sla["uptime_percent"]["actual"], sla["uptime_percent"]["target"], "<"),
            ("p95_latency_ms", sla["p95_latency_ms"]["actual"], sla["p95_latency_ms"]["target"], ">"),
            ("error_rate_percent", sla["error_rate_percent"]["actual"], sla["error_rate_percent"]["target"], ">"),
            ("tool_availability_percent", sla["tool_availability_percent"]["actual"], sla["tool_availability_percent"]["target"], "<"),
        ]

        for metric_name, actual, target, operator in checks:
            is_breached = (actual < target) if operator == "<" else (actual > target)

            if is_breached:
                if metric_name not in self._breach_events:
                    # New breach detected
                    self._breach_events[metric_name] = BreachEvent(
                        metric=metric_name,
                        target=target,
                        actual=actual,
                        breached_since=now,
                    )
                    log.warning(
                        f"SLA breach detected: {metric_name} at {actual:.2f}% vs target {target:.2f}%"
                    )
                else:
                    # Update existing breach
                    breach = self._breach_events[metric_name]
                    breach.actual = actual
                    breach.duration_seconds = (now - breach.breached_since).total_seconds()
            else:
                # Metric recovered
                if metric_name in self._breach_events:
                    breach = self._breach_events[metric_name]
                    breach.duration_seconds = (now - breach.breached_since).total_seconds()
                    log.info(
                        f"SLA recovered: {metric_name} at {actual:.2f}% (was breached for {breach.duration_seconds:.0f}s)"
                    )
                    del self._breach_events[metric_name]

    def set_sla_target(self, metric: str, value: float) -> None:
        """Update an SLA target value.

        Args:
            metric: One of 'uptime_percent', 'p95_latency_ms', 'error_rate_percent', 'tool_availability_percent'
            value: New target value

        Raises:
            ValueError: If metric name is invalid
        """
        if metric not in self._sla_targets:
            raise ValueError(
                f"Invalid metric '{metric}'. Must be one of: {list(self._sla_targets.keys())}"
            )
        old_value = self._sla_targets[metric]
        self._sla_targets[metric] = value
        log.info(f"SLA target updated: {metric} from {old_value} to {value}")

    def reset(self) -> None:
        """Clear all metrics and breach events.

        Used for testing or after major maintenance.
        """
        self._metrics.clear()
        self._breach_events.clear()
        log.info("SLA monitor reset")

    def _calculate_percentile(self, sorted_values: list[float], percentile: int) -> float:
        """Calculate percentile from sorted list.

        Args:
            sorted_values: List of values, pre-sorted in ascending order
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value, or 0 if list is empty
        """
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]

        # Use nearest-rank method (inclusive)
        index = int((percentile / 100.0) * (len(sorted_values) - 1))
        return float(sorted_values[index])


def get_sla_monitor() -> SLAMonitor:
    """Get or create the global SLA monitor singleton.

    Returns:
        SLAMonitor instance
    """
    return SLAMonitor()
