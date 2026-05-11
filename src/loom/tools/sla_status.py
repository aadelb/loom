"""MCP tool for SLA monitoring and status reporting.

Provides research_sla_status() tool that returns current SLA metrics,
breach status, and alert history.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from loom.sla_monitor import get_sla_monitor

log = logging.getLogger("loom.tools.sla_status")


def research_sla_status() -> dict[str, Any]:
    """Get current SLA metrics and breach status.

    Returns:
        Dictionary with:
        - current_sla: Current metrics vs targets
          - uptime_percent: {actual, target}
          - p95_latency_ms: {actual, target}
          - error_rate_percent: {actual, target}
          - tool_availability_percent: {actual, target}
          - timestamp: When metrics were calculated
          - metrics_count: Number of requests in 1-hour window
          - window_age_seconds: Age of oldest request
        - is_breaching: Boolean, True if any SLA is breached
        - breaches: List of active breach events with:
          - metric: Metric name
          - target: Target value
          - actual: Current actual value
          - breached_since: Timestamp breach started
          - duration_seconds: How long breach has been active
        - status: "healthy" | "degraded" | "critical"

    Example:
        >>> result = research_sla_status()
        >>> if result["is_breaching"]:
        ...     for breach in result["breaches"]:
        ...         print(f"{breach['metric']}: {breach['actual']:.1f}% vs {breach['target']:.1f}%")
    """
    try:
        monitor = get_sla_monitor()

        # Check and update breach status
        monitor.check_and_alert()

        # Get current metrics
        sla_metrics = monitor.get_current_sla()

        # Get active breaches
        breaches = monitor.get_breaches()
        breach_dicts = [
            {
                "metric": breach.metric,
                "target": breach.target,
                "actual": breach.actual,
                "breached_since": breach.breached_since.isoformat(),
                "duration_seconds": breach.duration_seconds,
            }
            for breach in breaches
        ]

        # Determine overall status
        is_breaching = monitor.is_breaching()
        if not is_breaching:
            overall_status = "healthy"
        elif len(breaches) == 1 and breaches[0].actual >= breaches[0].target * 0.95:
            # Minor breach (within 5%)
            overall_status = "degraded"
        else:
            overall_status = "critical"

        return {
            "current_sla": {
                "uptime_percent": sla_metrics["uptime_percent"],
                "p95_latency_ms": sla_metrics["p95_latency_ms"],
                "error_rate_percent": sla_metrics["error_rate_percent"],
                "tool_availability_percent": sla_metrics["tool_availability_percent"],
                "timestamp": sla_metrics["timestamp"].isoformat(),
                "metrics_count": sla_metrics["metrics_count"],
                "window_age_seconds": sla_metrics["window_age_seconds"],
            },
            "is_breaching": is_breaching,
            "breaches": breach_dicts,
            "status": overall_status,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_sla_status"}
