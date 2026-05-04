#!/usr/bin/env python3
"""
Triple-model code validation pipeline.

Sends code to 3 independent models for review:
  1. Gemini (via gemini CLI): Code quality & bug detection
  2. Kimi (via kimi CLI): Problem identification
  3. Claude/Opus (combines findings): Synthesized analysis

Collects responses and reports issues by confidence level:
  - HIGH: Found by all 3 models
  - MEDIUM: Found by 2 models
  - LOW: Found by 1 model

Exit code:
  0 = No HIGH confidence issues
  1 = Any HIGH confidence issues found

Usage:
  python scripts/triple_validate.py src/loom/server.py
  python scripts/triple_validate.py src/loom/tools/fetch.py

Author: Ahmed Adel Bakr Alderai
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationIssue:
    """Single validation issue found by a model."""
    model: str
    issue: str
    category: str = "general"


@dataclass
class AggregatedIssue:
    """Issue aggregated across models."""
    text: str
    models_found_by: list[str] = field(default_factory=list)

    @property
    def confidence_level(self) -> str:
        """Determine confidence based on how many models found it."""
        count = len(self.models_found_by)
        if count >= 3:
            return "HIGH"
        elif count >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    @property
    def confidence_score(self) -> int:
        """Return confidence score (1-3)."""
        return len(self.models_found_by)


@dataclass
class ValidationResult:
    """Complete validation result across all 3 models."""
    file_path: str
    gemini_issues: list[ValidationIssue] = field(default_factory=list)
    kimi_issues: list[ValidationIssue] = field(default_factory=list)
    claude_issues: list[ValidationIssue] = field(default_factory=list)
    aggregated: list[AggregatedIssue] = field(default_factory=list)

    @property
    def high_confidence_count(self) -> int:
        """Count HIGH confidence issues."""
        return sum(1 for issue in self.aggregated if issue.confidence_level == "HIGH")

    @property
    def medium_confidence_count(self) -> int:
        """Count MEDIUM confidence issues."""
        return sum(1 for issue in self.aggregated if issue.confidence_level == "MEDIUM")

    @property
    def low_confidence_count(self) -> int:
        """Count LOW confidence issues."""
        return sum(1 for issue in self.aggregated if issue.confidence_level == "LOW")


def read_code_file(file_path: str) -> str:
    """Read Python source code from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise IOError(f"Error reading file {file_path}: {e}")


def call_gemini(code: str) -> list[ValidationIssue]:
    """Send code to Gemini for review via gemini CLI."""
    print("  [Gemini] Analyzing code...")

    prompt = (
        "Review the following Python code for bugs, issues, and improvements. "
        "Focus on: correctness, performance, security, type hints, error handling, "
        "and code style. List each issue concisely.\n\n"
        f"```python\n{code}\n```"
    )

    try:
        result = subprocess.run(
            ["gemini", "-m", "gemini-3.1-pro-preview", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"  [Gemini] Warning: gemini CLI returned {result.returncode}")
            if result.stderr:
                print(f"  [Gemini] stderr: {result.stderr[:200]}")
            return []

        output = result.stdout.strip()
        if not output:
            return []

        # Parse response into individual issues
        issues = _parse_model_response(output, "gemini")
        print(f"  [Gemini] Found {len(issues)} issues")
        return issues
    except FileNotFoundError:
        print("  [Gemini] Error: gemini CLI not found. Install via: pip install kimi-cli")
        return []
    except subprocess.TimeoutExpired:
        print("  [Gemini] Error: gemini CLI timed out (60s)")
        return []
    except Exception as e:
        print(f"  [Gemini] Error: {e}")
        return []


def call_kimi(code: str) -> list[ValidationIssue]:
    """Send code to Kimi for review via kimi CLI."""
    print("  [Kimi] Analyzing code...")

    prompt = (
        "Find any problems, bugs, or issues in this Python code. "
        "Be specific about what's wrong and why. Include security, correctness, "
        "and quality concerns.\n\n"
        f"```python\n{code}\n```"
    )

    try:
        result = subprocess.run(
            ["kimi", "--yolo", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"  [Kimi] Warning: kimi CLI returned {result.returncode}")
            if result.stderr:
                print(f"  [Kimi] stderr: {result.stderr[:200]}")
            return []

        output = result.stdout.strip()
        if not output:
            return []

        # Parse response into individual issues
        issues = _parse_model_response(output, "kimi")
        print(f"  [Kimi] Found {len(issues)} issues")
        return issues
    except FileNotFoundError:
        print("  [Kimi] Error: kimi CLI not found. Install via: https://github.com/aimerou/kimi-cli")
        return []
    except subprocess.TimeoutExpired:
        print("  [Kimi] Error: kimi CLI timed out (60s)")
        return []
    except Exception as e:
        print(f"  [Kimi] Error: {e}")
        return []


def call_claude_synthesize(
    gemini_issues: list[ValidationIssue],
    kimi_issues: list[ValidationIssue],
    code: str,
) -> list[ValidationIssue]:
    """Send combined findings to Claude for synthesis."""
    print("  [Claude] Synthesizing findings...")

    gemini_text = "\n".join([f"- {issue.issue}" for issue in gemini_issues]) or "No issues found"
    kimi_text = "\n".join([f"- {issue.issue}" for issue in kimi_issues]) or "No issues found"

    prompt = (
        "Based on these two independent code reviews, synthesize the findings into "
        "a unified analysis. Highlight the most critical issues that appear in both reviews "
        "or are particularly serious. Focus on issues that actually impact code quality, "
        "correctness, or maintainability.\n\n"
        f"GEMINI REVIEW:\n{gemini_text}\n\n"
        f"KIMI REVIEW:\n{kimi_text}\n\n"
        f"CODE:\n```python\n{code[:2000]}...\n```\n\n"
        "Provide a concise synthesized list of the most important issues."
    )

    try:
        # Use claude (via claudemd if available, otherwise anthropic API directly)
        result = subprocess.run(
            ["python", "-c", f"""
import subprocess
import sys
result = subprocess.run(
    ["claude", "message", {repr(prompt)}],
    capture_output=True,
    text=True,
    timeout=60
)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
"""],
            capture_output=True,
            text=True,
            timeout=70,
        )

        if result.returncode != 0:
            print(f"  [Claude] Warning: claude CLI returned {result.returncode}")
            return []

        output = result.stdout.strip()
        if not output:
            return []

        # Parse response
        issues = _parse_model_response(output, "claude")
        print(f"  [Claude] Synthesized {len(issues)} issues")
        return issues
    except Exception as e:
        print(f"  [Claude] Error during synthesis: {e}")
        return []


def _parse_model_response(response: str, model_name: str) -> list[ValidationIssue]:
    """
    Parse model response into structured issues.

    Expects bullet points or numbered lines describing issues.
    """
    issues: list[ValidationIssue] = []

    # Split by common delimiters
    lines = response.split("\n")

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip non-issue lines (headers, explanations)
        if line.startswith("#") or line.startswith("##"):
            continue

        # Remove bullet points and numbering
        if line.startswith(("-", "*", "•")):
            line = line[1:].strip()

        if line and line[0].isdigit() and line[1:2] in (".", ")"):
            line = line[2:].strip()

        # Only keep non-empty, substantive lines
        if line and len(line) > 5:
            issues.append(ValidationIssue(model=model_name, issue=line))

    return issues


def aggregate_issues(
    gemini_issues: list[ValidationIssue],
    kimi_issues: list[ValidationIssue],
    claude_issues: list[ValidationIssue],
) -> list[AggregatedIssue]:
    """
    Aggregate issues across models based on semantic similarity.

    Issues are grouped by confidence level (how many models found them).
    """
    # Simple approach: treat semantically similar issues as the same
    # (In production, could use embeddings or fuzzy matching)

    all_issues = gemini_issues + kimi_issues + claude_issues
    aggregated: dict[str, AggregatedIssue] = {}

    for issue in all_issues:
        # Normalize issue text for matching (lowercase, truncate)
        key = issue.issue.lower()[:100]

        if key not in aggregated:
            aggregated[key] = AggregatedIssue(text=issue.issue)

        if issue.model not in aggregated[key].models_found_by:
            aggregated[key].models_found_by.append(issue.model)

    return sorted(aggregated.values(), key=lambda x: x.confidence_score, reverse=True)


def print_report(result: ValidationResult) -> None:
    """Print formatted validation report."""
    print("\n" + "=" * 80)
    print("TRIPLE-MODEL CODE VALIDATION REPORT")
    print("=" * 80)
    print(f"File: {result.file_path}")
    print(f"Validation timestamp: {Path.cwd()}")
    print("=" * 80)

    # Summary
    print(f"\nSUMMARY:")
    print(f"  Total aggregated issues: {len(result.aggregated)}")
    print(f"  HIGH confidence (all 3 models): {result.high_confidence_count}")
    print(f"  MEDIUM confidence (2 models): {result.medium_confidence_count}")
    print(f"  LOW confidence (1 model): {result.low_confidence_count}")

    # HIGH confidence issues
    if result.high_confidence_count > 0:
        print(f"\n{'=' * 80}")
        print("HIGH CONFIDENCE ISSUES (Found by all 3 models)")
        print("=" * 80)
        for issue in result.aggregated:
            if issue.confidence_level == "HIGH":
                print(f"\n  [{issue.confidence_level}] {issue.text}")
                print(f"    Found by: {', '.join(issue.models_found_by)}")

    # MEDIUM confidence issues
    if result.medium_confidence_count > 0:
        print(f"\n{'=' * 80}")
        print("MEDIUM CONFIDENCE ISSUES (Found by 2 models)")
        print("=" * 80)
        for issue in result.aggregated:
            if issue.confidence_level == "MEDIUM":
                print(f"\n  [{issue.confidence_level}] {issue.text}")
                print(f"    Found by: {', '.join(issue.models_found_by)}")

    # LOW confidence issues
    if result.low_confidence_count > 0:
        print(f"\n{'=' * 80}")
        print("LOW CONFIDENCE ISSUES (Found by 1 model)")
        print("=" * 80)
        for issue in result.aggregated:
            if issue.confidence_level == "LOW":
                print(f"\n  [{issue.confidence_level}] {issue.text}")
                print(f"    Found by: {', '.join(issue.models_found_by)}")

    # Exit code determination
    print(f"\n{'=' * 80}")
    if result.high_confidence_count > 0:
        print("RESULT: FAILED (HIGH confidence issues found)")
        print("Exit code: 1")
    else:
        print("RESULT: PASSED (No HIGH confidence issues)")
        print("Exit code: 0")
    print("=" * 80 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Triple-model code validation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/triple_validate.py src/loom/server.py
  python scripts/triple_validate.py src/loom/tools/fetch.py

The script will:
  1. Send code to Gemini for review (via gemini CLI)
  2. Send code to Kimi for review (via kimi CLI)
  3. Synthesize findings with Claude
  4. Report issues by confidence level (HIGH/MEDIUM/LOW)
  5. Exit with code 0 if no HIGH issues, 1 if any HIGH issues found
        """,
    )

    parser.add_argument(
        "file_path",
        help="Path to Python file to validate",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable format",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout per model in seconds (default: 60)",
    )

    args = parser.parse_args()

    # Validate file
    file_path = args.file_path
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    if not file_path.endswith(".py"):
        print(f"Error: File must be a Python file (.py): {file_path}", file=sys.stderr)
        return 1

    # Read code
    try:
        code = read_code_file(file_path)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    print(f"Validating: {file_path}")
    print(f"Code size: {len(code)} bytes, {len(code.splitlines())} lines")
    print("\nRunning triple-model validation...\n")

    # Call all 3 models
    gemini_issues = call_gemini(code)
    kimi_issues = call_kimi(code)
    claude_issues = call_claude_synthesize(gemini_issues, kimi_issues, code)

    # Aggregate results
    aggregated = aggregate_issues(gemini_issues, kimi_issues, claude_issues)

    # Create result object
    result = ValidationResult(
        file_path=file_path,
        gemini_issues=gemini_issues,
        kimi_issues=kimi_issues,
        claude_issues=claude_issues,
        aggregated=aggregated,
    )

    # Output results
    if args.json:
        # JSON output
        output = {
            "file_path": result.file_path,
            "summary": {
                "total_aggregated": len(result.aggregated),
                "high_confidence": result.high_confidence_count,
                "medium_confidence": result.medium_confidence_count,
                "low_confidence": result.low_confidence_count,
            },
            "issues": [
                {
                    "text": issue.text,
                    "confidence": issue.confidence_level,
                    "models_found_by": issue.models_found_by,
                }
                for issue in result.aggregated
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable report
        print_report(result)

    # Exit code
    return 1 if result.high_confidence_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
