"""Prometheus metrics collection and export for monitoring dashboards.

Tool:
- research_metrics: Return Prometheus-compatible metrics for monitoring
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.metrics")

# Prometheus metric types
_METRIC_HELP = {
    "loom_tool_calls_total": "Total number of tool calls by tool name",
    "loom_tool_latency_p50_ms": "Tool latency p50 in milliseconds",
    "loom_tool_latency_p95_ms": "Tool latency p95 in milliseconds",
    "loom_tool_latency_p99_ms": "Tool latency p99 in milliseconds",
    "loom_tool_errors_total": "Total errors by tool and error type",
    "loom_cost_usd_total": "Total cost in USD by provider",
    "loom_rate_limit_hits_total": "Total rate limit hits by provider",
    "loom_cache_hits_total": "Total cache hits",
    "loom_cache_misses_total": "Total cache misses",
}


def _read_cost_logs() -> dict[str, dict[str, Any]]:
    """Read cost tracker logs and aggregate by provider.

    Returns:
        Dict mapping provider -> {count, total_cost, models: {model: cost}}
    """
    cache_dir = Path.home() / ".cache" / "loom" / "logs"
    if not cache_dir.exists():
        return {}

    import json

    provider_stats: dict[str, dict[str, Any]] = {}

    try:
        for log_file in sorted(cache_dir.glob("llm_cost_*.json")):
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if not entry:
                                continue

                            provider = entry.get("provider", "unknown")
                            model = entry.get("model", "unknown")
                            cost = entry.get("cost_usd", 0.0)

                            if provider not in provider_stats:
                                provider_stats[provider] = {
                                    "count": 0,
                                    "total_cost": 0.0,
                                    "models": {},
                                }

                            provider_stats[provider]["count"] += 1
                            provider_stats[provider]["total_cost"] += cost

                            if model not in provider_stats[provider]["models"]:
                                provider_stats[provider]["models"][model] = 0.0
                            provider_stats[provider]["models"][model] += cost

                        except (json.JSONDecodeError, ValueError):
                            continue

            except Exception as e:
                logger.warning("metrics_read_cost_error file=%s: %s", log_file.name, e)
                continue

    except Exception as e:
        logger.error("metrics_read_cost_logs_error: %s", e)

    return provider_stats


def _read_tool_metrics() -> dict[str, dict[str, Any]]:
    """Read tool call metrics from logs.

    Returns:
        Dict mapping tool_name -> {calls, latencies: [...], errors: {...}}
    """
    cache_dir = Path.home() / ".cache" / "loom" / "logs"
    if not cache_dir.exists():
        return {}

    import json

    tool_metrics: dict[str, dict[str, Any]] = {}

    try:
        for log_file in sorted(cache_dir.glob("tool_calls_*.json")):
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if not entry:
                                continue

                            tool_name = entry.get("tool", "unknown")
                            latency_ms = entry.get("latency_ms", 0.0)
                            error = entry.get("error")

                            if tool_name not in tool_metrics:
                                tool_metrics[tool_name] = {
                                    "calls": 0,
                                    "latencies": [],
                                    "errors": {},
                                }

                            tool_metrics[tool_name]["calls"] += 1
                            tool_metrics[tool_name]["latencies"].append(latency_ms)

                            if error:
                                error_type = type(error).__name__ if isinstance(error, Exception) else str(error)
                                tool_metrics[tool_name]["errors"][error_type] = (
                                    tool_metrics[tool_name]["errors"].get(error_type, 0) + 1
                                )

                        except (json.JSONDecodeError, ValueError):
                            continue

            except Exception as e:
                logger.warning("metrics_read_tool_error file=%s: %s", log_file.name, e)
                continue

    except Exception as e:
        logger.error("metrics_read_tool_logs_error: %s", e)

    return tool_metrics


def _percentile(values: list[float], p: int) -> float:
    """Calculate percentile from list of values.

    Args:
        values: list of numeric values
        p: percentile (0-100)

    Returns:
        Percentile value, or 0 if empty
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int((p / 100.0) * (len(sorted_vals) - 1))
    return sorted_vals[idx]


def research_metrics() -> dict[str, Any]:
    """Return Prometheus-compatible metrics for Grafana dashboard.

    Collects:
    - tool call counts by tool
    - latency percentiles (p50, p95, p99) by tool
    - cost per provider
    - error rates by tool and error type
    - rate limit hits (if rate limiting is enabled)

    Returns:
        Dict mapping metric_name -> {labels_dict: value} with Prometheus format.
        Example:
        {
            "loom_tool_calls_total": {
                "tool=fetch": 150,
                "tool=search": 280
            },
            "loom_cost_usd_total": {
                "provider=nvidia": 12.34,
                "provider=openai": 45.67
            }
        }
    """
    now = datetime.now(UTC)

    # Initialize result
    metrics: dict[str, dict[str, Any]] = {
        name: {} for name in _METRIC_HELP.keys()
    }

    # Read tool call metrics
    tool_metrics = _read_tool_metrics()
    for tool_name, stats in tool_metrics.items():
        # Call counts
        metrics["loom_tool_calls_total"][f"tool={tool_name}"] = stats["calls"]

        # Latency percentiles
        latencies = stats["latencies"]
        if latencies:
            metrics["loom_tool_latency_p50_ms"][f"tool={tool_name}"] = round(
                _percentile(latencies, 50), 2
            )
            metrics["loom_tool_latency_p95_ms"][f"tool={tool_name}"] = round(
                _percentile(latencies, 95), 2
            )
            metrics["loom_tool_latency_p99_ms"][f"tool={tool_name}"] = round(
                _percentile(latencies, 99), 2
            )

        # Error counts
        for error_type, count in stats["errors"].items():
            label = f'tool={tool_name},error="{error_type}"'
            metrics["loom_tool_errors_total"][label] = count

    # Read cost metrics
    provider_stats = _read_cost_logs()
    for provider_name, stats in provider_stats.items():
        metrics["loom_cost_usd_total"][f"provider={provider_name}"] = round(
            stats["total_cost"], 2
        )

    # Cache hit/miss (simplified — would need to read actual cache logs)
    cache_dir = Path.home() / ".cache" / "loom"
    if cache_dir.exists():
        try:
            cache_files = list(cache_dir.rglob("*.json"))
            # Estimate: files modified in last hour = recent hits
            recent_threshold = time.time() - 3600
            recent_files = [f for f in cache_files if f.stat().st_mtime > recent_threshold]
            metrics["loom_cache_hits_total"]["all"] = len(recent_files)
            metrics["loom_cache_misses_total"]["all"] = 0  # Would need dedicated tracking
        except Exception as e:
            logger.warning("metrics_cache_error: %s", e)

    # Add metadata
    result = {
        "timestamp": now.isoformat(),
        "metrics": metrics,
        "help": _METRIC_HELP,
        "format": "prometheus_text_exposition",
    }

    logger.info("metrics_generated timestamp=%s", now.isoformat())
    return result
