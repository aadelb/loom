#!/usr/bin/env python3
"""Analyze real_query_test report and generate insights.

Usage:
    python3 scripts/analyze_test_report.py [report_path]
    Default: ./real_query_test_report.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_report(path: str) -> dict:
    """Load JSON report."""
    with open(path) as f:
        return json.load(f)


def analyze_report(report: dict) -> None:
    """Analyze report and print insights."""
    tools = report["tools"]
    summary = report["summary"]

    print("=" * 80)
    print("REAL QUERY TEST REPORT ANALYSIS")
    print("=" * 80)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Total tools: {summary['total']}")
    print()

    # Status breakdown
    print("STATUS BREAKDOWN")
    print("-" * 80)
    ok_pct = summary["ok"] / summary["total"] * 100 if summary["total"] > 0 else 0
    error_pct = summary["error"] / summary["total"] * 100 if summary["total"] > 0 else 0
    timeout_pct = summary["timeout"] / summary["total"] * 100 if summary["total"] > 0 else 0
    skip_pct = summary["skip"] / summary["total"] * 100 if summary["total"] > 0 else 0

    print(f"✓ OK:       {summary['ok']:3d} ({ok_pct:5.1f}%)")
    print(f"✗ ERROR:    {summary['error']:3d} ({error_pct:5.1f}%)")
    print(f"⏱ TIMEOUT:  {summary['timeout']:3d} ({timeout_pct:5.1f}%)")
    print(f"⊘ SKIP:     {summary['skip']:3d} ({skip_pct:5.1f}%)")
    print()

    # Timing analysis
    print("TIMING ANALYSIS")
    print("-" * 80)
    ok_tools = [t for t in tools if t["status"] == "OK"]
    if ok_tools:
        times = [t["time_ms"] for t in ok_tools]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        median_time = sorted(times)[len(times) // 2]

        print(f"Average: {avg_time:7.0f}ms")
        print(f"Median:  {median_time:7d}ms")
        print(f"Min:     {min_time:7d}ms")
        print(f"Max:     {max_time:7d}ms")
        print()

        # Response size analysis
        sizes = [t["response_size"] for t in ok_tools if t["response_size"] > 0]
        if sizes:
            avg_size = sum(sizes) / len(sizes)
            total_size = sum(sizes)
            print(f"Total response data: {total_size:,} bytes")
            print(f"Average per tool:   {avg_size:,.0f} bytes")
            print(f"Largest response:   {max(sizes):,} bytes")
        print()

    # Error breakdown
    if summary["error"] > 0:
        print("ERROR DETAILS")
        print("-" * 80)
        error_tools = [t for t in tools if t["status"] == "ERROR"]
        error_types = defaultdict(list)
        for tool in error_tools:
            error_detail = tool["error_detail"] or "Unknown"
            # Extract error type (first part before colon)
            error_type = error_detail.split(":")[0].strip()[:50]
            error_types[error_type].append(tool["tool_name"])

        for error_type in sorted(error_types.keys()):
            count = len(error_types[error_type])
            print(f"  {error_type}: {count} tools")
            for tool_name in sorted(error_types[error_type])[:3]:
                print(f"    - {tool_name}")
            if count > 3:
                print(f"    ... and {count - 3} more")
        print()

    # Timeout breakdown
    if summary["timeout"] > 0:
        print("TIMEOUT TOOLS")
        print("-" * 80)
        timeout_tools = sorted([t["tool_name"] for t in tools if t["status"] == "TIMEOUT"])
        for tool_name in timeout_tools:
            print(f"  - {tool_name}")
        print()

    # Skip breakdown
    if summary["skip"] > 0:
        print("SKIPPED TOOLS")
        print("-" * 80)
        skip_tools = sorted([t["tool_name"] for t in tools if t["status"] == "SKIP"])
        for tool_name in skip_tools:
            print(f"  - {tool_name}")
        print()

    # Top performers (fastest successful tools)
    if ok_tools:
        print("TOP PERFORMERS (Fastest)")
        print("-" * 80)
        fastest = sorted(ok_tools, key=lambda t: t["time_ms"])[:5]
        for i, tool in enumerate(fastest, 1):
            print(f"{i}. {tool['tool_name']:40s} {tool['time_ms']:5d}ms")
        print()

        # Slowest successful tools
        print("SLOWEST SUCCESSFUL TOOLS")
        print("-" * 80)
        slowest = sorted(ok_tools, key=lambda t: t["time_ms"], reverse=True)[:5]
        for i, tool in enumerate(slowest, 1):
            print(f"{i}. {tool['tool_name']:40s} {tool['time_ms']:5d}ms")
    print()

    # Recommendations
    print("RECOMMENDATIONS")
    print("-" * 80)
    if summary["error"] > 0:
        print("1. Investigate ERROR tools:")
        error_tools = [t for t in tools if t["status"] == "ERROR"]
        for tool in error_tools[:3]:
            print(f"   - {tool['tool_name']}: {tool['error_detail'][:60]}")
    if summary["timeout"] > 0:
        print(f"2. {summary['timeout']} tools timed out - increase timeout thresholds")
    if ok_pct >= 95:
        print(f"3. Excellent success rate ({ok_pct:.1f}%) - system is healthy")
    elif ok_pct >= 80:
        print(f"4. Good success rate ({ok_pct:.1f}%) but monitor ERROR/TIMEOUT tools")
    else:
        print(f"5. LOW success rate ({ok_pct:.1f}%) - investigate system issues")

    print("=" * 80)


def main():
    """Main entry point."""
    report_path = sys.argv[1] if len(sys.argv) > 1 else "./real_query_test_report.json"

    if not Path(report_path).exists():
        print(f"ERROR: Report not found: {report_path}")
        sys.exit(1)

    try:
        report = load_report(report_path)
        analyze_report(report)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
