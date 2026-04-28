"""Unit tests for research_metrics — Prometheus metric collection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from loom.tools.metrics import research_metrics


class TestMetricsCollection:
    """research_metrics collects tool, cost, and cache metrics."""

    def test_metrics_empty_logs(self, tmp_cache_dir: Path) -> None:
        """Metrics on empty cache dir return zero metrics."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            result = research_metrics()
            assert "timestamp" in result
            assert "metrics" in result
            assert "help" in result
            assert "format" in result
            assert result["format"] == "prometheus_text_exposition"
            # Metrics should be empty dicts when no logs exist
            assert isinstance(result["metrics"]["loom_tool_calls_total"], dict)
        finally:
            pass

    def test_metrics_with_tool_logs(self, tmp_cache_dir: Path) -> None:
        """Metrics read tool call logs and report call counts."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        logs_dir = tmp_cache_dir / "logs"
        logs_dir.mkdir()

        try:
            # Create tool_calls_*.json with sample data
            tool_log = logs_dir / "tool_calls_2026-04-27.json"
            tool_log.write_text(
                json.dumps({"tool": "fetch", "latency_ms": 150.5, "error": None})
                + "\n"
                + json.dumps({"tool": "fetch", "latency_ms": 200.0, "error": None})
                + "\n"
                + json.dumps(
                    {"tool": "search", "latency_ms": 100.0, "error": "TimeoutError"}
                )
                + "\n"
            )

            result = research_metrics()
            metrics = result["metrics"]

            # Check call counts
            assert metrics["loom_tool_calls_total"].get("tool=fetch") == 2
            assert metrics["loom_tool_calls_total"].get("tool=search") == 1

            # Check latency percentiles (p50, p95, p99)
            assert metrics["loom_tool_latency_p50_ms"].get("tool=fetch") == 175.25
            assert metrics["loom_tool_errors_total"].get('tool=search,error="TimeoutError"') == 1
        finally:
            pass

    def test_metrics_with_cost_logs(self, tmp_cache_dir: Path) -> None:
        """Metrics aggregate LLM provider costs."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        logs_dir = tmp_cache_dir / "logs"
        logs_dir.mkdir()

        try:
            # Create llm_cost_*.json with cost data
            cost_log = logs_dir / "llm_cost_2026-04-27.json"
            cost_log.write_text(
                json.dumps(
                    {"provider": "nvidia", "model": "nv-embed", "cost_usd": 0.01}
                )
                + "\n"
                + json.dumps(
                    {"provider": "openai", "model": "gpt-4", "cost_usd": 0.05}
                )
                + "\n"
                + json.dumps(
                    {"provider": "nvidia", "model": "nv-embed", "cost_usd": 0.02}
                )
                + "\n"
            )

            result = research_metrics()
            metrics = result["metrics"]

            # Check cost aggregation
            assert metrics["loom_cost_usd_total"].get("provider=nvidia") == 0.03
            assert metrics["loom_cost_usd_total"].get("provider=openai") == 0.05
        finally:
            pass

    def test_metrics_cache_hits(self, tmp_cache_dir: Path) -> None:
        """Metrics count recent cache files as hits."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            # Create some cache files
            day_dir = tmp_cache_dir / "2026-04-27"
            day_dir.mkdir()
            (day_dir / "file1.json").write_text('{"data":"cached"}')
            (day_dir / "file2.json").write_text('{"data":"cached"}')

            result = research_metrics()
            metrics = result["metrics"]

            # Should detect recent files
            assert metrics["loom_cache_hits_total"].get("all", 0) >= 2
            assert metrics["loom_cache_misses_total"].get("all", 0) == 0
        finally:
            pass

    def test_metrics_percentile_calculation(self) -> None:
        """Percentile function correctly calculates p50, p95, p99."""
        from loom.tools.metrics import _percentile

        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        assert _percentile(values, 50) == 55  # Median
        assert _percentile(values, 95) == 100  # Top ~5%
        assert _percentile(values, 0) == 10  # Min

    def test_metrics_structure_validation(self, tmp_cache_dir: Path) -> None:
        """Metrics result has correct Prometheus structure."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            result = research_metrics()

            # Check all required metric names are present
            required_metrics = [
                "loom_tool_calls_total",
                "loom_tool_latency_p50_ms",
                "loom_tool_latency_p95_ms",
                "loom_tool_latency_p99_ms",
                "loom_tool_errors_total",
                "loom_cost_usd_total",
                "loom_rate_limit_hits_total",
                "loom_cache_hits_total",
                "loom_cache_misses_total",
            ]

            for metric_name in required_metrics:
                assert metric_name in result["metrics"]
                assert metric_name in result["help"]
                assert isinstance(result["metrics"][metric_name], dict)
        finally:
            pass

    def test_metrics_malformed_json_skipped(self, tmp_cache_dir: Path) -> None:
        """Metrics gracefully skip malformed log entries."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        logs_dir = tmp_cache_dir / "logs"
        logs_dir.mkdir()

        try:
            # Create log with mix of valid and invalid JSON
            tool_log = logs_dir / "tool_calls_2026-04-27.json"
            tool_log.write_text(
                json.dumps({"tool": "fetch", "latency_ms": 100.0, "error": None})
                + "\n"
                + "invalid json line\n"
                + json.dumps({"tool": "search", "latency_ms": 200.0, "error": None})
                + "\n"
            )

            result = research_metrics()
            metrics = result["metrics"]

            # Should count valid entries only
            assert metrics["loom_tool_calls_total"].get("tool=fetch") == 1
            assert metrics["loom_tool_calls_total"].get("tool=search") == 1
        finally:
            pass
