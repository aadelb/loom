#!/usr/bin/env python3
"""Analyze and compare Loom MCP load test results.

Reads JSON load test reports and provides:
- Detailed analysis per test
- Comparison between multiple runs
- Performance regression detection
- Recommendations for optimization

Usage:
    python3 scripts/analyze_load_test.py <report.json>                    # Single report
    python3 scripts/analyze_load_test.py <baseline.json> <current.json>   # Comparison
    python3 scripts/analyze_load_test.py <dir> --all                     # All reports in dir

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime


@dataclass
class AnalysisResult:
    """Result of analyzing a single test."""
    name: str
    status: str
    success_rate: float
    throughput_rps: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


class LoadTestAnalyzer:
    """Analyze load test results."""

    def __init__(self, report_path: str | Path):
        self.report_path = Path(report_path)
        self.report = self._load_report()

    def _load_report(self) -> dict[str, Any]:
        """Load JSON report from disk."""
        with open(self.report_path) as f:
            return json.load(f)

    def analyze(self) -> None:
        """Print detailed analysis of a single report."""
        print(f"\n{'='*70}")
        print(f"Load Test Analysis: {self.report_path}")
        print(f"{'='*70}\n")

        report = self.report
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Duration: {report['total_duration_sec']:.1f}s")
        print(f"Overall Status: {report['overall_status']}\n")

        print("Summary:")
        summary = report['summary']
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Warned: {summary['warned']}")
        print(f"  Failed: {summary['failed']}\n")

        print("Test Results:\n")
        for test in report['test_results']:
            self._print_test_analysis(test)

    def _print_test_analysis(self, test: dict[str, Any]) -> None:
        """Print analysis for a single test."""
        print(f"  {test['name']}")
        print(f"    Status: {test['status']}")
        print(f"    Duration: {test['duration_sec']:.1f}s")
        print(f"    Requests: {test['request_count']}")
        print(f"    Success Rate: {test['success_rate']}")
        print(f"    Throughput: {test['throughput_rps']} req/s")

        latency = test['latency_ms']
        print(f"    Latency (ms):")
        print(f"      Avg:  {latency['avg']}")
        print(f"      P50:  {latency['p50']}")
        print(f"      P95:  {latency['p95']}")
        print(f"      P99:  {latency['p99']}")

        if test['error']:
            print(f"    Error: {test['error']}")

        # Recommendations
        recommendations = self._get_recommendations(test)
        if recommendations:
            print(f"    Recommendations:")
            for rec in recommendations:
                print(f"      - {rec}")

        print()

    def _get_recommendations(self, test: dict[str, Any]) -> list[str]:
        """Generate recommendations based on test results."""
        recs = []

        # Parse metrics
        success_rate = float(test['success_rate'].rstrip('%'))
        throughput_rps = float(test['throughput_rps'])
        p99_latency = float(test['latency_ms']['p99'])
        avg_latency = float(test['latency_ms']['avg'])

        # Check success rate
        if success_rate < 80:
            recs.append("Critical: Success rate below 80% - investigate failures")
        elif success_rate < 95:
            recs.append("Success rate below 95% - monitor for reliability issues")

        # Check throughput
        if throughput_rps < 5 and "Throughput" in test['name']:
            recs.append("Throughput below 5 req/s - check server capacity")
        elif throughput_rps < 10 and "Sustained" in test['name']:
            recs.append("Sustained load below target - consider optimization")

        # Check latency variance
        if avg_latency > 0:
            variance_ratio = p99_latency / avg_latency
            if variance_ratio > 5:
                recs.append(f"High latency variance (P99 {variance_ratio:.1f}x avg) - check for outliers")

        # Check for specific test issues
        if test['status'] == "FAIL":
            recs.append("Test failed - review error logs")
        elif test['status'] == "WARN":
            recs.append("Test warned - monitor for degradation")

        return recs


class LoadTestComparator:
    """Compare two load test results."""

    def __init__(self, baseline: str | Path, current: str | Path):
        self.baseline_path = Path(baseline)
        self.current_path = Path(current)
        self.baseline = self._load_report(self.baseline_path)
        self.current = self._load_report(self.current_path)

    def _load_report(self, path: Path) -> dict[str, Any]:
        """Load JSON report."""
        with open(path) as f:
            return json.load(f)

    def compare(self) -> None:
        """Print comparison between baseline and current."""
        print(f"\n{'='*70}")
        print("Load Test Comparison")
        print(f"{'='*70}")
        print(f"Baseline: {self.baseline_path}")
        print(f"Current:  {self.current_path}")
        print(f"\n{'='*70}\n")

        # Overall comparison
        print("Overall Status:")
        print(f"  Baseline: {self.baseline['overall_status']}")
        print(f"  Current:  {self.current['overall_status']}")

        baseline_summary = self.baseline['summary']
        current_summary = self.current['summary']
        print(f"\nResults Summary:")
        print(f"  Baseline: {baseline_summary['passed']} PASS, "
              f"{baseline_summary['warned']} WARN, {baseline_summary['failed']} FAIL")
        print(f"  Current:  {current_summary['passed']} PASS, "
              f"{current_summary['warned']} WARN, {current_summary['failed']} FAIL")

        # Test-by-test comparison
        print(f"\n{'='*70}")
        print("Test-by-Test Comparison")
        print(f"{'='*70}\n")

        baseline_tests = {t['name']: t for t in self.baseline['test_results']}
        current_tests = {t['name']: t for t in self.current['test_results']}

        for test_name in baseline_tests:
            if test_name in current_tests:
                self._compare_tests(
                    test_name,
                    baseline_tests[test_name],
                    current_tests[test_name],
                )

    def _compare_tests(
        self,
        name: str,
        baseline: dict[str, Any],
        current: dict[str, Any],
    ) -> None:
        """Compare two test results."""
        print(f"  {name}:")

        # Status comparison
        status_change = (
            "✓ Improved" if (baseline['status'] != "PASS" and current['status'] == "PASS")
            else "✗ Regressed" if (baseline['status'] == "PASS" and current['status'] != "PASS")
            else "→ Same"
        )
        print(f"    Status: {baseline['status']} → {current['status']} {status_change}")

        # Success rate comparison
        baseline_success = float(baseline['success_rate'].rstrip('%'))
        current_success = float(current['success_rate'].rstrip('%'))
        diff = current_success - baseline_success
        print(f"    Success Rate: {baseline_success:.1f}% → {current_success:.1f}% ({diff:+.1f}%)")

        # Throughput comparison
        baseline_rps = float(baseline['throughput_rps'])
        current_rps = float(current['throughput_rps'])
        pct_change = ((current_rps - baseline_rps) / baseline_rps * 100) if baseline_rps > 0 else 0
        print(f"    Throughput: {baseline_rps:.2f} → {current_rps:.2f} req/s ({pct_change:+.1f}%)")

        # Latency comparison
        baseline_lat = float(baseline['latency_ms']['avg'])
        current_lat = float(current['latency_ms']['avg'])
        lat_pct = ((current_lat - baseline_lat) / baseline_lat * 100) if baseline_lat > 0 else 0
        print(f"    Avg Latency: {baseline_lat:.1f}ms → {current_lat:.1f}ms ({lat_pct:+.1f}%)")

        # P99 latency
        baseline_p99 = float(baseline['latency_ms']['p99'])
        current_p99 = float(current['latency_ms']['p99'])
        p99_pct = ((current_p99 - baseline_p99) / baseline_p99 * 100) if baseline_p99 > 0 else 0
        print(f"    P99 Latency: {baseline_p99:.1f}ms → {current_p99:.1f}ms ({p99_pct:+.1f}%)")

        print()

    def generate_summary(self) -> str:
        """Generate one-line summary of comparison."""
        baseline_status = self.baseline['overall_status']
        current_status = self.current['overall_status']

        if current_status == "PASS" and baseline_status != "PASS":
            return "✓ Performance IMPROVED"
        elif current_status != "PASS" and baseline_status == "PASS":
            return "✗ Performance REGRESSED"
        elif current_status == baseline_status:
            return "→ Performance STABLE"
        else:
            return "? Status CHANGED"


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single report:  python3 analyze_load_test.py <report.json>")
        print("  Comparison:     python3 analyze_load_test.py <baseline.json> <current.json>")
        sys.exit(1)

    if len(sys.argv) == 2:
        # Single report analysis
        analyzer = LoadTestAnalyzer(sys.argv[1])
        analyzer.analyze()
    else:
        # Comparison
        comparator = LoadTestComparator(sys.argv[1], sys.argv[2])
        comparator.compare()
        print(f"Summary: {comparator.generate_summary()}")


if __name__ == "__main__":
    main()
