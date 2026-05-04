"""Tool usage analytics system with Redis fallback for Loom MCP server.

Tracks tool invocations, performance metrics, error rates, and generates
comprehensive analytics dashboards.
"""

from __future__ import annotations

import logging
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("loom.analytics")

# In-memory fallback storage
_call_records: list[dict[str, Any]] = []  # List of all recorded calls
_tool_usage: Counter[str] = Counter()  # Total calls per tool
_tool_errors: Counter[str] = Counter()  # Error count per tool
_tool_durations: defaultdict[str, list[float]] = defaultdict(list)  # Durations per tool


class ToolAnalytics:
    """Singleton analytics tracker for tool usage and performance.

    Thread-safe recording of tool calls with Redis support and in-memory fallback.
    """

    _instance: ToolAnalytics | None = None

    def __init__(self) -> None:
        """Initialize analytics with Redis or in-memory storage."""
        self.use_redis = False
        self.redis_client = None

        # Try to initialize Redis if configured
        try:
            redis_enabled = os.getenv("LOOM_ANALYTICS_REDIS", "").lower() == "true"
            if redis_enabled:
                import redis
                redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_db = int(os.getenv("REDIS_DB", "0"))

                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                )
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info("analytics_redis_enabled")
        except Exception as e:
            logger.debug(f"Redis unavailable for analytics, using in-memory: {e}")
            self.use_redis = False

    @classmethod
    def get_instance(cls) -> ToolAnalytics:
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = ToolAnalytics()
        return cls._instance

    def record_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        user_id: str | None = None,
    ) -> None:
        """Record a tool call with performance metrics.

        Args:
            tool_name: Name of the tool called
            duration_ms: Execution duration in milliseconds
            success: Whether call succeeded
            user_id: Optional user identifier
        """
        timestamp = datetime.now(UTC).isoformat()

        record = {
            "tool": tool_name,
            "duration_ms": duration_ms,
            "success": success,
            "user_id": user_id or "anonymous",
            "timestamp": timestamp,
        }

        if self.use_redis:
            self._record_to_redis(record)
        else:
            self._record_to_memory(record)

    def _record_to_memory(self, record: dict[str, Any]) -> None:
        """Record call to in-memory storage."""
        _call_records.append(record)

        # Keep only last 100k records
        if len(_call_records) > 100000:
            _call_records.pop(0)

        tool_name = record["tool"]
        _tool_usage[tool_name] += 1
        _tool_durations[tool_name].append(record["duration_ms"])

        if not record["success"]:
            _tool_errors[tool_name] += 1

    def _record_to_redis(self, record: dict[str, Any]) -> None:
        """Record call to Redis storage."""
        if not self.redis_client:
            return

        try:
            tool_name = record["tool"]
            timestamp = record["timestamp"]

            # Increment tool call count (sorted set for rankings)
            self.redis_client.zincrby("loom:tools:calls", 1, tool_name)

            # Store duration for percentile calculations
            self.redis_client.lpush(f"loom:tools:durations:{tool_name}", record["duration_ms"])

            # Store call record with TTL (30 days)
            self.redis_client.setex(
                f"loom:call:{timestamp}:{tool_name}",
                30 * 24 * 3600,
                str(record),
            )

            # Track errors
            if not record["success"]:
                self.redis_client.zincrby("loom:tools:errors", 1, tool_name)

            # Hourly stats
            hour_key = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:00")
            self.redis_client.zincrby(f"loom:stats:hourly", 1, hour_key)
        except Exception as e:
            logger.error(f"Redis record error: {e}")

    def get_top_tools(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get most-used tools.

        Args:
            limit: Maximum number of tools to return

        Returns:
            List of dicts with tool_name, call_count, percentage
        """
        if self.use_redis and self.redis_client:
            return self._get_top_tools_redis(limit)
        else:
            return self._get_top_tools_memory(limit)

    def _get_top_tools_memory(self, limit: int) -> list[dict[str, Any]]:
        """Get top tools from in-memory storage."""
        total_calls = sum(_tool_usage.values())
        if total_calls == 0:
            return []

        result = []
        for tool_name, count in _tool_usage.most_common(limit):
            result.append({
                "tool_name": tool_name,
                "call_count": count,
                "percentage": round((count / total_calls) * 100, 2),
            })
        return result

    def _get_top_tools_redis(self, limit: int) -> list[dict[str, Any]]:
        """Get top tools from Redis."""
        if not self.redis_client:
            return []

        try:
            # Get total calls
            total_calls = self.redis_client.zcard("loom:tools:calls")
            if total_calls == 0:
                return []

            # Get top tools
            top_results = self.redis_client.zrevrange(
                "loom:tools:calls", 0, limit - 1, withscores=True
            )

            result = []
            for tool_name, score in top_results:
                result.append({
                    "tool_name": tool_name,
                    "call_count": int(score),
                    "percentage": round((float(score) / total_calls) * 100, 2),
                })
            return result
        except Exception as e:
            logger.error(f"Redis get_top_tools error: {e}")
            return []

    def get_slow_tools(self, threshold_ms: float = 5000) -> list[dict[str, Any]]:
        """Get tools exceeding performance threshold.

        Args:
            threshold_ms: Duration threshold in milliseconds

        Returns:
            List of dicts with tool_name, avg_duration, max_duration, count
        """
        if self.use_redis and self.redis_client:
            return self._get_slow_tools_redis(threshold_ms)
        else:
            return self._get_slow_tools_memory(threshold_ms)

    def _get_slow_tools_memory(self, threshold_ms: float) -> list[dict[str, Any]]:
        """Get slow tools from in-memory storage."""
        result = []
        for tool_name, durations in _tool_durations.items():
            if not durations:
                continue

            avg_duration = sum(durations) / len(durations)
            if avg_duration >= threshold_ms:
                result.append({
                    "tool_name": tool_name,
                    "avg_duration_ms": round(avg_duration, 2),
                    "max_duration_ms": max(durations),
                    "min_duration_ms": min(durations),
                    "call_count": len(durations),
                })

        return sorted(result, key=lambda x: x["avg_duration_ms"], reverse=True)

    def _get_slow_tools_redis(self, threshold_ms: float) -> list[dict[str, Any]]:
        """Get slow tools from Redis."""
        if not self.redis_client:
            return []

        try:
            result = []
            # Get all tools
            tools = self.redis_client.zrange("loom:tools:calls", 0, -1)

            for tool_name in tools:
                durations = self.redis_client.lrange(
                    f"loom:tools:durations:{tool_name}", 0, -1
                )
                if not durations:
                    continue

                durations_float = [float(d) for d in durations]
                avg_duration = sum(durations_float) / len(durations_float)

                if avg_duration >= threshold_ms:
                    result.append({
                        "tool_name": tool_name,
                        "avg_duration_ms": round(avg_duration, 2),
                        "max_duration_ms": max(durations_float),
                        "min_duration_ms": min(durations_float),
                        "call_count": len(durations_float),
                    })

            return sorted(result, key=lambda x: x["avg_duration_ms"], reverse=True)
        except Exception as e:
            logger.error(f"Redis get_slow_tools error: {e}")
            return []

    def get_error_rates(self) -> dict[str, float]:
        """Get error rate percentage per tool.

        Returns:
            Dict mapping tool_name -> error_rate_percentage
        """
        if self.use_redis and self.redis_client:
            return self._get_error_rates_redis()
        else:
            return self._get_error_rates_memory()

    def _get_error_rates_memory(self) -> dict[str, float]:
        """Get error rates from in-memory storage."""
        result = {}
        for tool_name in _tool_usage.keys():
            total = _tool_usage[tool_name]
            errors = _tool_errors.get(tool_name, 0)
            if total > 0:
                result[tool_name] = round((errors / total) * 100, 2)
        return result

    def _get_error_rates_redis(self) -> dict[str, float]:
        """Get error rates from Redis."""
        if not self.redis_client:
            return {}

        try:
            result = {}
            # Get all tools
            tools = self.redis_client.zrange("loom:tools:calls", 0, -1)

            for tool_name in tools:
                total = int(self.redis_client.zscore("loom:tools:calls", tool_name) or 0)
                errors = int(self.redis_client.zscore("loom:tools:errors", tool_name) or 0)

                if total > 0:
                    result[tool_name] = round((errors / total) * 100, 2)

            return result
        except Exception as e:
            logger.error(f"Redis get_error_rates error: {e}")
            return {}

    def get_unused_tools(self, all_tools: list[str] | None = None) -> list[str]:
        """Get list of tools never called.

        Args:
            all_tools: Optional list of all available tool names to check against

        Returns:
            List of tool names with zero calls
        """
        if not all_tools:
            return []

        if self.use_redis and self.redis_client:
            used_tools = self.redis_client.zrange("loom:tools:calls", 0, -1)
        else:
            used_tools = set(_tool_usage.keys())

        return [t for t in all_tools if t not in used_tools]

    def get_hourly_stats(self) -> dict[str, Any]:
        """Get hourly call statistics for last 24 hours.

        Returns:
            Dict with hourly buckets, total_calls, peak_hour
        """
        if self.use_redis and self.redis_client:
            return self._get_hourly_stats_redis()
        else:
            return self._get_hourly_stats_memory()

    def _get_hourly_stats_memory(self) -> dict[str, Any]:
        """Get hourly stats from in-memory storage."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=24)

        hourly_buckets = defaultdict(int)

        for record in _call_records:
            ts = datetime.fromisoformat(record["timestamp"])
            if ts >= cutoff:
                hour_key = ts.strftime("%Y-%m-%d %H:00")
                hourly_buckets[hour_key] += 1

        if not hourly_buckets:
            return {
                "hourly_buckets": [],
                "total_calls_24h": 0,
                "peak_hour": None,
                "avg_calls_per_hour": 0.0,
            }

        sorted_hours = sorted(hourly_buckets.items())
        total_calls = sum(hourly_buckets.values())
        peak_hour = max(hourly_buckets.items(), key=lambda x: x[1])[0]

        return {
            "hourly_buckets": [{"hour": h, "calls": c} for h, c in sorted_hours],
            "total_calls_24h": total_calls,
            "peak_hour": peak_hour,
            "avg_calls_per_hour": round(total_calls / 24, 2),
        }

    def _get_hourly_stats_redis(self) -> dict[str, Any]:
        """Get hourly stats from Redis."""
        if not self.redis_client:
            return {
                "hourly_buckets": [],
                "total_calls_24h": 0,
                "peak_hour": None,
                "avg_calls_per_hour": 0.0,
            }

        try:
            now = datetime.now(UTC)
            cutoff = now - timedelta(hours=24)

            hourly_buckets = defaultdict(int)

            # Get all hourly stats
            all_hours = self.redis_client.zrange("loom:stats:hourly", 0, -1, withscores=True)

            for hour_key, score in all_hours:
                ts = datetime.fromisoformat(hour_key.replace(" 00", "T00:00:00"))
                if ts >= cutoff:
                    hourly_buckets[hour_key] = int(score)

            if not hourly_buckets:
                return {
                    "hourly_buckets": [],
                    "total_calls_24h": 0,
                    "peak_hour": None,
                    "avg_calls_per_hour": 0.0,
                }

            sorted_hours = sorted(hourly_buckets.items())
            total_calls = sum(hourly_buckets.values())
            peak_hour = max(hourly_buckets.items(), key=lambda x: x[1])[0]

            return {
                "hourly_buckets": [{"hour": h, "calls": c} for h, c in sorted_hours],
                "total_calls_24h": total_calls,
                "peak_hour": peak_hour,
                "avg_calls_per_hour": round(total_calls / 24, 2),
            }
        except Exception as e:
            logger.error(f"Redis get_hourly_stats error: {e}")
            return {
                "hourly_buckets": [],
                "total_calls_24h": 0,
                "peak_hour": None,
                "avg_calls_per_hour": 0.0,
            }

    def get_total_calls_today(self) -> int:
        """Get total calls made today (UTC).

        Returns:
            Number of calls since midnight UTC
        """
        now = datetime.now(UTC)
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if self.use_redis and self.redis_client:
            try:
                today_key = cutoff.strftime("%Y-%m-%d")
                # Count all hours for today
                count = 0
                for hour in range(24):
                    hour_key = f"{today_key} {hour:02d}:00"
                    score = self.redis_client.zscore("loom:stats:hourly", hour_key)
                    if score:
                        count += int(score)
                return count
            except Exception as e:
                logger.error(f"Redis get_total_calls_today error: {e}")

        # Fallback to memory
        count = 0
        for record in _call_records:
            ts = datetime.fromisoformat(record["timestamp"])
            if ts >= cutoff:
                count += 1
        return count

    def get_total_calls_this_hour(self) -> int:
        """Get total calls made this hour (UTC).

        Returns:
            Number of calls in current hour
        """
        now = datetime.now(UTC)
        cutoff = now.replace(minute=0, second=0, microsecond=0)

        if self.use_redis and self.redis_client:
            try:
                hour_key = cutoff.strftime("%Y-%m-%d %H:00")
                score = self.redis_client.zscore("loom:stats:hourly", hour_key)
                return int(score or 0)
            except Exception as e:
                logger.error(f"Redis get_total_calls_this_hour error: {e}")

        # Fallback to memory
        count = 0
        for record in _call_records:
            ts = datetime.fromisoformat(record["timestamp"])
            if ts >= cutoff:
                count += 1
        return count

    def get_average_response_time(self) -> float:
        """Get average response time across all calls.

        Returns:
            Average duration in milliseconds
        """
        if self.use_redis and self.redis_client:
            return self._get_average_response_time_redis()
        else:
            return self._get_average_response_time_memory()

    def _get_average_response_time_memory(self) -> float:
        """Get average response time from in-memory storage."""
        if not _call_records:
            return 0.0

        total_duration = sum(r["duration_ms"] for r in _call_records)
        return round(total_duration / len(_call_records), 2)

    def _get_average_response_time_redis(self) -> float:
        """Get average response time from Redis."""
        if not self.redis_client:
            return 0.0

        try:
            tools = self.redis_client.zrange("loom:tools:calls", 0, -1)
            if not tools:
                return 0.0

            total_duration = 0.0
            total_calls = 0

            for tool_name in tools:
                durations = self.redis_client.lrange(
                    f"loom:tools:durations:{tool_name}", 0, -1
                )
                if durations:
                    total_duration += sum(float(d) for d in durations)
                    total_calls += len(durations)

            if total_calls == 0:
                return 0.0

            return round(total_duration / total_calls, 2)
        except Exception as e:
            logger.error(f"Redis get_average_response_time error: {e}")
            return 0.0


async def research_analytics_dashboard(
    include_unused: bool = False,
    all_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Generate comprehensive tool usage analytics dashboard.

    Returns aggregated analytics across all metrics including top tools,
    slow tools, error rates, hourly statistics, and more.

    Args:
        include_unused: If True and all_tools provided, include unused tool list
        all_tools: Optional list of all available tool names for unused detection

    Returns:
        Dict with keys:
        - top_tools: Top 20 most-used tools with percentages
        - slow_tools: Top 10 tools exceeding 5000ms threshold
        - high_error_tools: Top 10 tools with highest error rates
        - unused_tools_count: Count of tools never called (if all_tools provided)
        - total_calls_today: Calls since midnight UTC
        - total_calls_this_hour: Calls in current hour
        - average_response_time_ms: Mean duration across all calls
        - hourly_stats: Last 24 hours bucketed by hour
        - timestamp: ISO timestamp of report generation
    """
    analytics = ToolAnalytics.get_instance()

    # Gather all metrics
    top_tools = analytics.get_top_tools(limit=20)
    slow_tools = analytics.get_slow_tools(threshold_ms=5000)[:10]
    error_rates = analytics.get_error_rates()

    # Sort by error rate and get top 10
    high_error_tools = sorted(
        [
            {"tool_name": tool, "error_rate": rate}
            for tool, rate in error_rates.items()
        ],
        key=lambda x: x["error_rate"],
        reverse=True,
    )[:10]

    # Get unused tools if requested
    unused_count = 0
    if include_unused and all_tools:
        unused_tools = analytics.get_unused_tools(all_tools)
        unused_count = len(unused_tools)

    # Get hourly stats
    hourly_stats = analytics.get_hourly_stats()

    # Get summary stats
    total_calls_today = analytics.get_total_calls_today()
    total_calls_this_hour = analytics.get_total_calls_this_hour()
    avg_response_time = analytics.get_average_response_time()

    return {
        "top_tools": top_tools,
        "slow_tools": slow_tools,
        "high_error_tools": high_error_tools,
        "unused_tools_count": unused_count,
        "total_calls_today": total_calls_today,
        "total_calls_this_hour": total_calls_this_hour,
        "average_response_time_ms": avg_response_time,
        "hourly_stats": hourly_stats,
        "timestamp": datetime.now(UTC).isoformat(),
    }
