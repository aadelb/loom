#!/usr/bin/env python3
"""24-hour continuous soak test for Loom MCP server.

Runs continuously, calling a rotating set of lightweight tools every N seconds.
Tracks memory, response time, errors, and generates degradation/leak alerts.

Usage:
    python scripts/soak_test.py --duration 24h --interval 10s --output /tmp/soak.json
    python scripts/soak_test.py --duration 1h --interval 5s  # Quick test
    python scripts/soak_test.py --duration 10m --interval 2s  # Very quick test
"""

from __future__ import annotations

import argparse
import inspect
import asyncio
import json
import logging
import os
import psutil
import signal
import sys
import time
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add src to path so loom imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Suppress Loom logging during tests
logging.disable(logging.CRITICAL)
os.environ["LOOM_LOG_LEVEL"] = "CRITICAL"

# Import tool functions
from loom.tools.cache_mgmt import research_cache_stats
from loom.tools.quota_status import research_quota_status
from loom.tools.security_auditor import research_security_audit
from loom.tools.reputation_scorer import research_source_reputation


@dataclass
class ToolCall:
    """Single tool invocation record."""

    tool_name: str
    timestamp: str
    response_time_ms: float
    memory_mb: float
    error: str | None
    error_type: str | None
    result_keys: list[str] | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SummaryWindow:
    """5-minute rolling summary."""

    window_start: str
    window_end: str
    total_calls: int
    successful_calls: int
    error_count: int
    error_rate_pct: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    memory_start_mb: float
    memory_end_mb: float
    memory_delta_mb: float
    tools_called: dict[str, int]
    errors_by_type: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SoakTester:
    """Continuous stress tester for Loom MCP server."""

    def __init__(
        self,
        duration_seconds: int,
        interval_seconds: int,
        output_path: Path,
    ) -> None:
        """Initialize soak tester.

        Args:
            duration_seconds: Total test duration in seconds
            interval_seconds: Seconds between tool calls
            output_path: Path to write final report
        """
        self.duration_seconds = duration_seconds
        self.interval_seconds = interval_seconds
        self.output_path = output_path
        self.running = True
        self.start_time = time.time()
        self.baseline_memory_mb: float | None = None
        self.tool_calls: list[ToolCall] = []
        self.summaries: list[SummaryWindow] = []
        self.tools = [
            ("research_cache_stats", self._call_cache_stats),
            ("research_quota_status", self._call_quota_status),
            ("research_security_audit", self._call_security_audit),
        ]
        self.tool_index = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigint(self, signum: int, frame: Any) -> None:
        """Handle Ctrl+C gracefully."""
        self.running = False
        print("\n[SOAK TEST] SIGINT received, wrapping up...")

    def _handle_sigterm(self, signum: int, frame: Any) -> None:
        """Handle SIGTERM gracefully."""
        self.running = False
        print("\n[SOAK TEST] SIGTERM received, wrapping up...")

    def get_memory_mb(self) -> float:
        """Get current process memory in MB."""
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024 * 1024)

    async def _call_cache_stats(self) -> dict[str, Any]:
        """Call research_cache_stats."""
        return research_cache_stats()

    async def _call_quota_status(self) -> dict[str, Any]:
        """Call research_quota_status."""
        return research_quota_status()

    async def _call_security_audit(self) -> dict[str, Any]:
        """Call research_security_audit."""
        return await research_security_audit()

    def _get_next_tool(self) -> tuple[str, Any]:
        """Get next tool to call in rotation."""
        tool_name, tool_func = self.tools[self.tool_index]
        self.tool_index = (self.tool_index + 1) % len(self.tools)
        return tool_name, tool_func

    async def call_tool(self) -> ToolCall:
        """Call a single tool and record metrics."""
        tool_name, tool_func = self._get_next_tool()
        timestamp = datetime.now(UTC).isoformat()
        memory_before = self.get_memory_mb()
        start_time = time.time()
        error = None
        error_type = None
        result_keys = None

        try:
            result = tool_func() if not inspect.iscoroutinefunction(tool_func) else (
                await tool_func()
            )
            if isinstance(result, dict):
                result_keys = list(result.keys())
        except Exception as e:
            error = str(e)
            error_type = type(e).__name__

        elapsed_ms = (time.time() - start_time) * 1000
        memory_after = self.get_memory_mb()

        call = ToolCall(
            tool_name=tool_name,
            timestamp=timestamp,
            response_time_ms=round(elapsed_ms, 2),
            memory_mb=round(memory_after, 2),
            error=error,
            error_type=error_type,
            result_keys=result_keys,
        )

        return call

    async def run_test(self) -> None:
        """Run the soak test."""
        print("[SOAK TEST] Starting 24-hour continuous test")
        print(f"[SOAK TEST] Duration: {self.duration_seconds}s ({self.duration_seconds/3600:.1f}h)")
        print(f"[SOAK TEST] Interval: {self.interval_seconds}s")
        print(f"[SOAK TEST] Output: {self.output_path}")
        print("[SOAK TEST] Press Ctrl+C to stop early\n")

        # Record baseline
        self.baseline_memory_mb = self.get_memory_mb()
        print(f"[SOAK TEST] Baseline memory: {self.baseline_memory_mb:.2f} MB\n")

        last_summary_time = time.time()
        call_count = 0

        while self.running:
            elapsed = time.time() - self.start_time
            if elapsed > self.duration_seconds:
                self.running = False
                break

            # Call tool
            call = await self.call_tool()
            self.tool_calls.append(call)
            call_count += 1

            # Print progress
            status = "OK" if call.error is None else f"ERR: {call.error_type}"
            print(
                f"[{call_count}] {call.tool_name:25s} {call.response_time_ms:6.1f}ms "
                f"MEM:{call.memory_mb:7.1f}MB {status}"
            )

            # Generate 5-minute summary
            now = time.time()
            if now - last_summary_time >= 300:  # 5 minutes
                summary = self._generate_summary_window()
                self.summaries.append(summary)
                self._print_summary(summary)
                self._check_degradation(summary)
                self._check_leak(summary)
                last_summary_time = now

            # Wait for next call
            await asyncio.sleep(self.interval_seconds)

        # Final summary
        print("\n[SOAK TEST] Test complete, generating final report...")
        self._generate_final_report()

    def _generate_summary_window(self) -> SummaryWindow:
        """Generate 5-minute summary from recent calls."""
        # Use last ~300 seconds of calls (roughly 5 min window)
        window_calls = [
            c
            for c in self.tool_calls[-int(300 / self.interval_seconds) :]
        ]

        if not window_calls:
            # Return empty summary
            return SummaryWindow(
                window_start=datetime.now(UTC).isoformat(),
                window_end=datetime.now(UTC).isoformat(),
                total_calls=0,
                successful_calls=0,
                error_count=0,
                error_rate_pct=0.0,
                avg_response_time_ms=0.0,
                min_response_time_ms=0.0,
                max_response_time_ms=0.0,
                memory_start_mb=0.0,
                memory_end_mb=0.0,
                memory_delta_mb=0.0,
                tools_called={},
                errors_by_type={},
            )

        total = len(window_calls)
        successful = sum(1 for c in window_calls if c.error is None)
        errors = total - successful
        error_rate = (errors / total * 100) if total > 0 else 0.0

        response_times = [c.response_time_ms for c in window_calls]
        avg_response = sum(response_times) / len(response_times) if response_times else 0.0
        min_response = min(response_times) if response_times else 0.0
        max_response = max(response_times) if response_times else 0.0

        # Tool call counts
        tools_called: dict[str, int] = {}
        for call in window_calls:
            tools_called[call.tool_name] = tools_called.get(call.tool_name, 0) + 1

        # Error type counts
        errors_by_type: dict[str, int] = {}
        for call in window_calls:
            if call.error_type:
                errors_by_type[call.error_type] = (
                    errors_by_type.get(call.error_type, 0) + 1
                )

        memory_start = window_calls[0].memory_mb
        memory_end = window_calls[-1].memory_mb
        memory_delta = memory_end - memory_start

        return SummaryWindow(
            window_start=window_calls[0].timestamp,
            window_end=window_calls[-1].timestamp,
            total_calls=total,
            successful_calls=successful,
            error_count=errors,
            error_rate_pct=round(error_rate, 2),
            avg_response_time_ms=round(avg_response, 2),
            min_response_time_ms=round(min_response, 2),
            max_response_time_ms=round(max_response, 2),
            memory_start_mb=round(memory_start, 2),
            memory_end_mb=round(memory_end, 2),
            memory_delta_mb=round(memory_delta, 2),
            tools_called=tools_called,
            errors_by_type=errors_by_type,
        )

    def _print_summary(self, summary: SummaryWindow) -> None:
        """Print summary to console."""
        print(
            f"\n[5-MIN SUMMARY] Calls:{summary.total_calls} OK:{summary.successful_calls} "
            f"ERR:{summary.error_count} ({summary.error_rate_pct:.1f}%)"
        )
        print(
            f"                Response: {summary.avg_response_time_ms:.1f}ms avg "
            f"({summary.min_response_time_ms:.1f}-{summary.max_response_time_ms:.1f}ms)"
        )
        print(
            f"                Memory: {summary.memory_start_mb:.1f}→{summary.memory_end_mb:.1f}MB "
            f"({summary.memory_delta_mb:+.1f}MB)"
        )
        print(f"                Tools: {summary.tools_called}")

    def _check_degradation(self, summary: SummaryWindow) -> None:
        """Check if response time degraded >50% from baseline."""
        if len(self.summaries) < 2:
            return

        first_summary = self.summaries[0]
        baseline = first_summary.avg_response_time_ms
        current = summary.avg_response_time_ms

        if baseline > 0 and current > baseline * 1.5:
            pct_increase = ((current - baseline) / baseline) * 100
            print(
                f"\n[ALERT] DEGRADATION: Response time increased {pct_increase:.1f}% "
                f"({baseline:.1f}ms → {current:.1f}ms)"
            )

    def _check_leak(self, summary: SummaryWindow) -> None:
        """Check if memory leaked >100MB from baseline."""
        if not self.baseline_memory_mb:
            return

        delta = summary.memory_end_mb - self.baseline_memory_mb
        if delta > 100:
            print(
                f"\n[ALERT] MEMORY LEAK: Memory increased {delta:.1f}MB "
                f"(baseline: {self.baseline_memory_mb:.1f}MB → current: {summary.memory_end_mb:.1f}MB)"
            )

    def _generate_final_report(self) -> None:
        """Generate final JSON report."""
        if not self.tool_calls:
            print("[SOAK TEST] No tool calls recorded")
            return

        # Calculate overall stats
        successful = sum(1 for c in self.tool_calls if c.error is None)
        errors = len(self.tool_calls) - successful
        error_rate = (errors / len(self.tool_calls) * 100) if self.tool_calls else 0.0

        response_times = [c.response_time_ms for c in self.tool_calls]
        avg_response = sum(response_times) / len(response_times) if response_times else 0.0

        # Tool call distribution
        tools_called: dict[str, int] = {}
        for call in self.tool_calls:
            tools_called[call.tool_name] = tools_called.get(call.tool_name, 0) + 1

        # Error distribution
        errors_by_type: dict[str, int] = {}
        for call in self.tool_calls:
            if call.error_type:
                errors_by_type[call.error_type] = (
                    errors_by_type.get(call.error_type, 0) + 1
                )

        final_memory = self.tool_calls[-1].memory_mb if self.tool_calls else 0.0
        memory_growth = (
            final_memory - self.baseline_memory_mb if self.baseline_memory_mb else 0.0
        )

        report = {
            "test_metadata": {
                "start_time": datetime.fromtimestamp(
                    self.start_time, UTC
                ).isoformat(),
                "end_time": datetime.now(UTC).isoformat(),
                "duration_seconds": int(time.time() - self.start_time),
                "total_calls": len(self.tool_calls),
            },
            "test_parameters": {
                "target_duration_seconds": self.duration_seconds,
                "interval_seconds": self.interval_seconds,
            },
            "overall_stats": {
                "total_calls": len(self.tool_calls),
                "successful_calls": successful,
                "error_count": errors,
                "error_rate_pct": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response, 2),
                "min_response_time_ms": round(min(response_times), 2) if response_times else 0,
                "max_response_time_ms": round(max(response_times), 2) if response_times else 0,
            },
            "memory_metrics": {
                "baseline_memory_mb": round(self.baseline_memory_mb, 2)
                if self.baseline_memory_mb
                else 0.0,
                "final_memory_mb": round(final_memory, 2),
                "memory_growth_mb": round(memory_growth, 2),
                "growth_exceeded_100mb": memory_growth > 100,
            },
            "tool_distribution": tools_called,
            "error_types": errors_by_type,
            "window_summaries": [s.to_dict() for s in self.summaries],
            "all_calls": [c.to_dict() for c in self.tool_calls],
        }

        # Write report
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n[SOAK TEST] Report written to: {self.output_path}")
        print(
            f"[SOAK TEST] Summary: {successful}/{len(self.tool_calls)} calls successful, "
            f"{error_rate:.1f}% error rate"
        )
        print(
            f"[SOAK TEST] Memory: baseline {self.baseline_memory_mb:.2f}MB → "
            f"final {final_memory:.2f}MB ({memory_growth:+.2f}MB)"
        )

        # Print human-readable summary
        self._print_human_summary(report)

    def _print_human_summary(self, report: dict[str, Any]) -> None:
        """Print human-readable summary to console."""
        print("\n" + "=" * 70)
        print("SOAK TEST FINAL REPORT")
        print("=" * 70)

        meta = report["test_metadata"]
        print(
            f"\nTest Duration: {meta['duration_seconds']}s ({meta['duration_seconds']/3600:.2f}h)"
        )
        print(f"Total Tool Calls: {meta['total_calls']}")

        stats = report["overall_stats"]
        print(f"\nCall Success Rate: {stats['successful_calls']}/{stats['total_calls']} "
              f"({100 - stats['error_rate_pct']:.1f}%)")
        print(f"Error Rate: {stats['error_rate_pct']:.1f}%")
        print(f"Response Time: {stats['avg_response_time_ms']:.1f}ms avg "
              f"({stats['min_response_time_ms']:.1f}-{stats['max_response_time_ms']:.1f}ms)")

        mem = report["memory_metrics"]
        print(f"\nMemory Baseline: {mem['baseline_memory_mb']:.2f}MB")
        print(f"Memory Final: {mem['final_memory_mb']:.2f}MB")
        print(f"Memory Growth: {mem['memory_growth_mb']:+.2f}MB")
        if mem["growth_exceeded_100mb"]:
            print("  LEAK DETECTED: Growth exceeds 100MB threshold")

        print(f"\nTools Called: {report['tool_distribution']}")

        if report["error_types"]:
            print(f"Error Types: {report['error_types']}")

        print("\n" + "=" * 70)


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="24-hour continuous soak test for Loom MCP server"
    )
    parser.add_argument(
        "--duration",
        type=str,
        default="24h",
        help="Test duration (e.g., '24h', '1h', '30m', '60s')",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="10s",
        help="Seconds between tool calls (e.g., '10s', '5s', '1m')",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/soak_test_report.json"),
        help="Output JSON report path",
    )

    args = parser.parse_args()

    # Parse duration
    duration_seconds = _parse_duration(args.duration)
    interval_seconds = _parse_duration(args.interval)

    print(f"[SOAK TEST] Configuration:")
    print(f"  Duration: {duration_seconds}s ({duration_seconds/3600:.1f}h)")
    print(f"  Interval: {interval_seconds}s")
    print(f"  Output: {args.output}\n")

    tester = SoakTester(duration_seconds, interval_seconds, args.output)
    await tester.run_test()


def _parse_duration(duration_str: str) -> int:
    """Parse duration string like '24h', '30m', '60s' to seconds."""
    duration_str = duration_str.strip().lower()

    if duration_str.endswith("h"):
        return int(duration_str[:-1]) * 3600
    elif duration_str.endswith("m"):
        return int(duration_str[:-1]) * 60
    elif duration_str.endswith("s"):
        return int(duration_str[:-1])
    else:
        # Assume seconds
        return int(duration_str)


if __name__ == "__main__":
    asyncio.run(main())
