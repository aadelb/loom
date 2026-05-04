"""Per-tool latency tracking with percentile calculations.

Singleton ToolLatencyTracker maintains a sliding window of execution times
per tool (max 1000 samples). Provides percentile stats (p50, p75, p90, p95, p99),
sample count, and average latency. Identifies slow tools exceeding p95 threshold.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict, deque
from typing import Any

log = logging.getLogger("loom.tool_latency")


class ToolLatencyTracker:
    """Singleton tracker for per-tool execution latencies with percentile calculations.

    Uses a sliding window (deque maxlen=1000) per tool for memory efficiency.
    Calculates percentiles lazily using statistics.quantiles on sorted data.
    """

    _instance: ToolLatencyTracker | None = None
    _lock_initialized: bool = False

    def __new__(cls) -> ToolLatencyTracker:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize tracker state."""
        if self._lock_initialized:
            return
        self._latencies: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=1000))
        self._lock_initialized = True

    def record(self, tool_name: str, duration_ms: float) -> None:
        """Record execution duration for a tool.

        Args:
            tool_name: Name of the tool (e.g., 'research_fetch')
            duration_ms: Execution time in milliseconds
        """
        if duration_ms < 0:
            log.warning(f"Negative duration for {tool_name}: {duration_ms}ms, skipping")
            return

        self._latencies[tool_name].append(duration_ms)
        log.debug(f"Recorded latency for {tool_name}: {duration_ms:.1f}ms")

    def get_percentiles(self, tool_name: str) -> dict[str, Any]:
        """Get percentile statistics for a tool.

        Returns dict with keys: p50, p75, p90, p95, p99, count, avg, min, max.
        Returns empty stats if tool has no recorded latencies.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary with percentile stats and metadata
        """
        latencies = self._latencies.get(tool_name)
        if not latencies or len(latencies) == 0:
            return {
                "p50": 0,
                "p75": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
                "count": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "tool": tool_name,
            }

        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)
        avg_latency = sum(sorted_latencies) / count

        # Use statistics.quantiles for consistent percentile calculation
        # n=100 means percentiles 0-100
        quantiles = statistics.quantiles(sorted_latencies, n=100)

        return {
            "p50": quantiles[49],  # 50th percentile (median)
            "p75": quantiles[74],  # 75th percentile
            "p90": quantiles[89],  # 90th percentile
            "p95": quantiles[94],  # 95th percentile
            "p99": quantiles[98],  # 99th percentile
            "count": count,
            "avg": avg_latency,
            "min": min(sorted_latencies),
            "max": max(sorted_latencies),
            "tool": tool_name,
        }

    def get_all_latencies(self) -> dict[str, dict[str, Any]]:
        """Get percentile stats for all tracked tools.

        Returns:
            Dictionary mapping tool_name -> percentile stats dict
        """
        return {
            tool_name: self.get_percentiles(tool_name)
            for tool_name in sorted(self._latencies.keys())
        }

    def get_slow_tools(self, threshold_p95_ms: float = 5000) -> list[dict[str, Any]]:
        """Get tools exceeding p95 latency threshold.

        Args:
            threshold_p95_ms: p95 threshold in milliseconds (default 5000ms)

        Returns:
            List of tool stats dicts for tools exceeding threshold, sorted by p95 desc
        """
        slow_tools = []
        for tool_name in self._latencies.keys():
            stats = self.get_percentiles(tool_name)
            if stats["count"] > 0 and stats["p95"] > threshold_p95_ms:
                slow_tools.append(stats)

        # Sort by p95 descending
        return sorted(slow_tools, key=lambda x: x["p95"], reverse=True)

    def reset_tool(self, tool_name: str) -> None:
        """Clear latency history for a tool.

        Args:
            tool_name: Name of the tool to reset
        """
        if tool_name in self._latencies:
            self._latencies[tool_name].clear()
            log.info(f"Reset latency history for {tool_name}")

    def reset_all(self) -> None:
        """Clear all latency history."""
        self._latencies.clear()
        log.info("Reset all latency history")


def get_latency_tracker() -> ToolLatencyTracker:
    """Get singleton ToolLatencyTracker instance.

    Returns:
        The global ToolLatencyTracker instance
    """
    return ToolLatencyTracker()
