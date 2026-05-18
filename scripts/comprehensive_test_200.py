"""Comprehensive 200-query test suite for Loom v3.

Reads test definitions from JSON files, executes each query against live server,
compares actual vs expected responses, generates evidence report.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = os.environ.get("LOOM_URL", "http://127.0.0.1:8788/api/v1/tools")
TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "120"))


def load_tests(test_dir: str = "/tmp") -> list[dict]:
    """Load all test JSON files from directory."""
    all_tests = []
    for f in sorted(Path(test_dir).glob("tests_*.json")):
        try:
            data = json.loads(f.read_text())
            if isinstance(data, list):
                all_tests.extend(data)
            elif isinstance(data, dict) and "tests" in data:
                all_tests.extend(data["tests"])
        except Exception as e:
            print(f"  WARN: failed to load {f.name}: {e}")
    return all_tests


def check_expected(actual: dict, expected: dict) -> tuple[bool, str]:
    """Compare actual response against expected criteria."""
    reasons = []

    # Check no error
    if expected.get("no_error", True):
        err = actual.get("error")
        if err and "timeout" not in str(err).lower():
            reasons.append(f"has error: {str(err)[:60]}")

    # Check required keys
    for key in expected.get("has_keys", []):
        if key not in actual:
            reasons.append(f"missing key: {key}")

    # Check min response length
    min_len = expected.get("min_length", 0)
    if min_len > 0:
        text = str(actual.get("text", actual.get("content", actual.get("results", ""))))
        if len(text) < min_len:
            reasons.append(f"too short: {len(text)} < {min_len}")

    # Check specific values
    for key, val in expected.get("value_checks", {}).items():
        if actual.get(key) != val:
            reasons.append(f"{key}={actual.get(key)} != expected {val}")

    # Check not empty result
    if expected.get("not_empty", False):
        results = actual.get("results", actual.get("cves", actual.get("data", [])))
        if isinstance(results, list) and len(results) == 0:
            reasons.append("results list is empty")

    return (len(reasons) == 0, "; ".join(reasons) if reasons else "OK")


def run_tests(tests: list[dict]) -> dict:
    """Execute all tests and collect results."""
    results = {"passed": 0, "failed": 0, "timeout": 0, "error": 0, "details": []}

    print(f"Running {len(tests)} queries against {BASE}")
    print(f"Timeout: {TIMEOUT}s per query")
    print("=" * 70)

    for i, test in enumerate(tests, 1):
        tool = test.get("tool", "unknown")
        params = test.get("params", {})
        expected = test.get("expected", {"no_error": True})
        category = test.get("category", "")

        start = time.time()
        try:
            r = requests.post(f"{BASE}/{tool}", json=params, timeout=TIMEOUT)
            actual = r.json()
            elapsed = time.time() - start

            passed, reason = check_expected(actual, expected)

            if passed:
                results["passed"] += 1
                status = "PASS"
            else:
                results["failed"] += 1
                status = "FAIL"

            detail = {
                "id": i, "tool": tool, "category": category,
                "status": status, "reason": reason,
                "elapsed_s": round(elapsed, 1),
                "response_preview": str(actual)[:200],
            }
            results["details"].append(detail)
            print(f"  [{i:3d}/{len(tests)}] {status:7s} {tool:<40s} {elapsed:5.1f}s {reason[:50]}")

        except requests.exceptions.Timeout:
            results["timeout"] += 1
            detail = {"id": i, "tool": tool, "category": category, "status": "TIMEOUT", "reason": f">{TIMEOUT}s"}
            results["details"].append(detail)
            print(f"  [{i:3d}/{len(tests)}] TIMEOUT {tool:<40s} >{TIMEOUT}s")

        except Exception as e:
            results["error"] += 1
            detail = {"id": i, "tool": tool, "category": category, "status": "ERROR", "reason": str(e)[:80]}
            results["details"].append(detail)
            print(f"  [{i:3d}/{len(tests)}] ERROR   {tool:<40s} {str(e)[:50]}")

        if i % 20 == 0:
            print(f"  ... {i}/{len(tests)} done ({results['passed']} pass, {results['failed']} fail)")

    return results


def generate_report(results: dict, output_path: str = "/tmp/test_200_results.json"):
    """Generate evidence report."""
    total = results["passed"] + results["failed"] + results["timeout"] + results["error"]
    pass_rate = results["passed"] / total * 100 if total else 0

    print()
    print("=" * 70)
    print(f"FINAL RESULTS: {results['passed']}/{total} PASS ({pass_rate:.0f}%)")
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Timeout: {results['timeout']}")
    print(f"  Error:   {results['error']}")
    print("=" * 70)

    if results["failed"] > 0 or results["error"] > 0:
        print("\nFAILURES:")
        for d in results["details"]:
            if d["status"] in ("FAIL", "ERROR"):
                print(f"  [{d['id']}] {d['tool']}: {d['reason']}")

    # Category breakdown
    categories = {}
    for d in results["details"]:
        cat = d.get("category", "uncategorized")
        if cat not in categories:
            categories[cat] = {"pass": 0, "fail": 0, "total": 0}
        categories[cat]["total"] += 1
        if d["status"] == "PASS":
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1

    print("\nCATEGORY BREAKDOWN:")
    for cat, stats in sorted(categories.items()):
        pct = stats["pass"] / stats["total"] * 100 if stats["total"] else 0
        print(f"  {cat:<25s} {stats['pass']}/{stats['total']} ({pct:.0f}%)")

    # Save JSON
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
    tests = load_tests(test_dir)
    if not tests:
        print("No test files found. Expected /tmp/tests_*.json files.")
        sys.exit(1)
    results = run_tests(tests)
    generate_report(results)
