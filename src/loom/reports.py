"""Test suite report generators for production readiness.

Generates:
1. "What Works" report — passing tests grouped by category
2. "What Doesn't Work" report — failures with error patterns and severity ranking
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_what_works_report(
    test_results: list[dict[str, Any]], output_path: Path | None = None
) -> dict[str, Any]:
    """Generate 'What Works' report from test results.

    Analyzes passing tests and groups them by category for readability.
    Calculates pass rate and provides summary statistics.

    Args:
        test_results: List of test result dicts with at least:
            - name: test name (str)
            - status: "passed" or "failed" (str)
            - category: test category (str, optional)
        output_path: Optional path to write JSON report to

    Returns:
        Dict with:
        - title: Report title
        - total_tests: Total test count
        - passed: Number of passing tests
        - failed: Number of failing tests
        - pass_rate: Percentage (0-100)
        - working_categories: Dict[category, list of test names]
        - summary: Human-readable summary
    """
    passed = [t for t in test_results if t.get("status") == "passed"]
    failed = [t for t in test_results if t.get("status") == "failed"]

    # Group passed tests by category
    by_category: dict[str, list[str]] = {}
    for t in passed:
        cat = t.get("category", "uncategorized")
        test_name = t.get("name", "unknown")
        by_category.setdefault(cat, []).append(test_name)

    # Calculate pass rate safely
    total = len(test_results)
    pass_rate = round(len(passed) / max(total, 1) * 100, 1)

    report = {
        "title": "What Works — Loom v3 Production Readiness",
        "total_tests": total,
        "passed": len(passed),
        "failed": len(failed),
        "pass_rate": pass_rate,
        "working_categories": by_category,
        "summary": f"{len(passed)}/{total} tests passing ({pass_rate}%)",
    }

    if output_path:
        output_path.write_text(json.dumps(report, indent=2))

    return report


def generate_failure_report(
    test_results: list[dict[str, Any]], output_path: Path | None = None
) -> dict[str, Any]:
    """Generate 'What Doesn't Work' failure analysis report.

    Analyzes failing tests, groups by category, identifies error patterns,
    and provides severity-ranked recommendations.

    Args:
        test_results: List of test result dicts with at least:
            - name: test name (str)
            - status: "passed" or "failed" (str)
            - category: test category (str, optional)
            - error: error message (str, optional)
            - error_type: error type (str, optional, e.g. "TimeoutError")
        output_path: Optional path to write JSON report to

    Returns:
        Dict with:
        - title: Report title
        - total_failures: Number of failing tests
        - failure_categories: Dict[category, list of {name, error} dicts]
        - error_patterns: Dict[error_type, count]
        - recommendations: List of action items sorted by severity
    """
    failed = [t for t in test_results if t.get("status") == "failed"]

    # Group failed tests by category
    by_category: dict[str, list[dict[str, Any]]] = {}
    for t in failed:
        cat = t.get("category", "uncategorized")
        test_name = t.get("name", "unknown")
        error_msg = t.get("error", "unknown")
        by_category.setdefault(cat, []).append(
            {"name": test_name, "error": error_msg}
        )

    # Count error patterns
    patterns: dict[str, int] = {}
    for t in failed:
        error_type = t.get("error_type", "unknown")
        patterns[error_type] = patterns.get(error_type, 0) + 1

    # Generate recommendations sorted by failure count (severity)
    recommendations = [
        f"Fix {cat}: {len(items)} failures"
        for cat, items in sorted(by_category.items(), key=lambda x: -len(x[1]))
    ]

    report = {
        "title": "What Doesn't Work — Loom v3 Known Issues",
        "total_failures": len(failed),
        "failure_categories": by_category,
        "error_patterns": patterns,
        "recommendations": recommendations,
    }

    if output_path:
        output_path.write_text(json.dumps(report, indent=2))

    return report
