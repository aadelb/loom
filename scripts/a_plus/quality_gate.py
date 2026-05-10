"""A+ quality gate — validates tool files without AI.

Usage:
    python scripts/a_plus/quality_gate.py src/loom/tools/fetch.py
    python scripts/a_plus/quality_gate.py src/loom/tools/ --category core
    python scripts/a_plus/quality_gate.py src/loom/tools/ --check stubs-only
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class QualityIssue:
    file: str
    line: int
    issue: str
    severity: str  # "critical", "high", "medium", "low"


@dataclass
class QualityReport:
    file: str
    issues: list[QualityIssue] = field(default_factory=list)
    passed: bool = True

    def add(self, line: int, issue: str, severity: str = "medium") -> None:
        self.issues.append(QualityIssue(self.file, line, issue, severity))
        if severity in ("critical", "high"):
            self.passed = False


def check_file(path: Path) -> QualityReport:
    """Run A+ quality checks on a single file."""
    report = QualityReport(file=str(path))
    content = path.read_text()
    lines = content.splitlines()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        report.add(e.lineno or 0, f"SyntaxError: {e.msg}", "critical")
        return report

    for node in ast.walk(tree):
        # Check: bare except clauses
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            report.add(node.lineno, "Bare except: clause — catch specific exceptions", "high")

        # Check: NotImplementedError (stub)
        if isinstance(node, ast.Raise) and node.exc:
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                if node.exc.func.id == "NotImplementedError":
                    report.add(node.lineno, "Stub: raises NotImplementedError", "critical")

        # Check: missing type hints on function defs
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("research_") or node.name.startswith("tool_"):
                if node.returns is None:
                    report.add(node.lineno, f"Missing return type hint: {node.name}", "medium")
                for arg in node.args.args:
                    if arg.arg != "self" and arg.annotation is None:
                        report.add(
                            node.lineno,
                            f"Missing type hint for param '{arg.arg}' in {node.name}",
                            "low",
                        )

    # Check: hardcoded API keys
    for i, line in enumerate(lines, 1):
        if "api_key" in line.lower() and ("=" in line) and ("os.environ" not in line) and ("getenv" not in line):
            if any(q in line for q in ['"sk-', '"key-', "'sk-", "'key-"]):
                report.add(i, "Possible hardcoded API key", "critical")

    return report


def check_stubs_only(path: Path) -> list[QualityReport]:
    """Find only stub tools (NotImplementedError)."""
    reports = []
    for f in sorted(path.glob("*.py")):
        content = f.read_text()
        if "NotImplementedError" in content:
            report = QualityReport(file=str(f))
            for i, line in enumerate(content.splitlines(), 1):
                if "NotImplementedError" in line:
                    report.add(i, "Stub: NotImplementedError", "critical")
            reports.append(report)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="A+ Quality Gate")
    parser.add_argument("path", help="File or directory to check")
    parser.add_argument("--category", help="Registration category to check")
    parser.add_argument("--check", choices=["stubs-only", "full"], default="full")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    target = Path(args.path)

    if args.check == "stubs-only":
        if target.is_dir():
            reports = check_stubs_only(target)
        else:
            print("--check stubs-only requires a directory", file=sys.stderr)
            sys.exit(1)
    elif target.is_file():
        reports = [check_file(target)]
    elif target.is_dir():
        reports = [check_file(f) for f in sorted(target.glob("*.py"))]
    else:
        print(f"Path not found: {target}", file=sys.stderr)
        sys.exit(1)

    # Output
    failed = [r for r in reports if not r.passed]
    total_issues = sum(len(r.issues) for r in reports)

    if args.json:
        data = {
            "total_files": len(reports),
            "passed": len(reports) - len(failed),
            "failed": len(failed),
            "total_issues": total_issues,
            "reports": [
                {
                    "file": r.file,
                    "passed": r.passed,
                    "issues": [
                        {"line": i.line, "issue": i.issue, "severity": i.severity}
                        for i in r.issues
                    ],
                }
                for r in reports
                if r.issues
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"\nA+ Quality Gate: {len(reports)} files checked")
        print(f"  Passed: {len(reports) - len(failed)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Total issues: {total_issues}")
        if failed:
            print("\nFailed files:")
            for r in failed:
                print(f"\n  {r.file}:")
                for issue in r.issues:
                    print(f"    L{issue.line} [{issue.severity}] {issue.issue}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
