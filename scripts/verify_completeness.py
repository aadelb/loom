#!/usr/bin/env python3
"""Verify documentation completeness against actual registered tools.

Compares create_app() tool list against:
- docs/tools-reference.md
- docs/help.md
- CLAUDE.md

Exits non-zero if any mismatch found. Run as CI check or pre-commit.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def get_registered_tools() -> list[str]:
    from loom.server import create_app
    app = create_app()
    return sorted(app._tool_manager._tools.keys())


def get_tools_reference_count() -> tuple[int, list[str]]:
    path = ROOT / "docs" / "tools-reference.md"
    if not path.exists():
        return 0, []
    text = path.read_text()
    match = re.search(r"\*\*Total:\s*(\d+)\s*tools\*\*", text)
    claimed = int(match.group(1)) if match else 0
    sections = re.findall(r"^#{2,3} (research_\w+|fetch_\w+|find_\w+)", text, re.MULTILINE)
    if not sections:
        sections = re.findall(r"`(research_\w+|fetch_\w+|find_\w+)`", text)
    sections = list(dict.fromkeys(sections))
    return claimed, sections


def get_help_md_count() -> int:
    path = ROOT / "docs" / "help.md"
    if not path.exists():
        return 0
    text = path.read_text()
    match = re.search(r"Tool Catalog \((\d+)", text)
    return int(match.group(1)) if match else 0


def get_claude_md_count() -> int:
    path = ROOT / "CLAUDE.md"
    if not path.exists():
        return 0
    text = path.read_text()
    match = re.search(r"(\d+) research tools", text)
    return int(match.group(1)) if match else 0


def main() -> int:
    errors = 0

    print("=== Loom Completeness Verification ===\n")

    tools = get_registered_tools()
    actual = len(tools)
    print(f"Registered tools (create_app): {actual}")

    ref_claimed, ref_sections = get_tools_reference_count()
    print(f"tools-reference.md claims: {ref_claimed} tools, {len(ref_sections)} documented sections")

    help_count = get_help_md_count()
    print(f"help.md claims: {help_count} tools")

    claude_count = get_claude_md_count()
    print(f"CLAUDE.md claims: {claude_count} tools")

    print()

    if ref_claimed != actual:
        print(f"FAIL: tools-reference.md says {ref_claimed}, actual is {actual}")
        errors += 1
    else:
        print(f"PASS: tools-reference.md count matches ({actual})")

    if help_count != actual:
        print(f"FAIL: help.md says {help_count}, actual is {actual}")
        errors += 1
    else:
        print(f"PASS: help.md count matches ({actual})")

    if claude_count != actual:
        print(f"FAIL: CLAUDE.md says {claude_count}, actual is {actual}")
        errors += 1
    else:
        print(f"PASS: CLAUDE.md count matches ({actual})")

    missing_from_ref = [t for t in tools if t not in ref_sections]
    if missing_from_ref:
        print(f"\nFAIL: {len(missing_from_ref)} tools missing from tools-reference.md:")
        for t in missing_from_ref:
            print(f"  - {t}")
        errors += 1
    else:
        print(f"\nPASS: All {actual} tools documented in tools-reference.md")

    print(f"\n{'FAILED' if errors else 'PASSED'}: {errors} issues found")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
