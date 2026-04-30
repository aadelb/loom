"""Example usage of report generation functions.

This module demonstrates how to use the report generators to create
production readiness reports from test results.
"""

from __future__ import annotations

from pathlib import Path

from loom.reports import generate_failure_report, generate_what_works_report


def example_generate_reports() -> None:
    """Example: Generate both reports from test results."""

    # Sample test results from pytest output or custom test runner
    test_results = [
        {"name": "test_fetch_http", "status": "passed", "category": "fetch"},
        {"name": "test_fetch_ssl", "status": "passed", "category": "fetch"},
        {"name": "test_fetch_timeout", "status": "failed", "category": "fetch",
         "error": "Timeout after 30 seconds", "error_type": "TimeoutError"},
        {"name": "test_search_exa", "status": "passed", "category": "search"},
        {"name": "test_search_api", "status": "failed", "category": "search",
         "error": "API rate limit exceeded", "error_type": "RateLimitError"},
        {"name": "test_analysis_metadata", "status": "passed", "category": "analysis"},
    ]

    # Generate "What Works" report
    works_report = generate_what_works_report(
        test_results,
        output_path=Path("what_works.json")
    )

    print("What Works Report:")
    print(f"  Pass rate: {works_report['pass_rate']}%")
    print(f"  Tests passing: {works_report['passed']}/{works_report['total_tests']}")
    print(f"  Working categories: {list(works_report['working_categories'].keys())}")

    # Generate "What Doesn't Work" report
    failure_report = generate_failure_report(
        test_results,
        output_path=Path("what_doesnt_work.json")
    )

    print("\nWhat Doesn't Work Report:")
    print(f"  Total failures: {failure_report['total_failures']}")
    print(f"  Error patterns: {failure_report['error_patterns']}")
    print(f"  Recommendations:")
    for rec in failure_report['recommendations']:
        print(f"    - {rec}")


if __name__ == "__main__":
    example_generate_reports()
