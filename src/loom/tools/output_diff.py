"""Output diff comparator for tracking tool output changes over time."""

from __future__ import annotations

import difflib
import logging
from typing import Any

logger = logging.getLogger("loom.tools.output_diff")
_output_history: dict[str, tuple[str, str]] = {}


async def research_diff_compare(text_a: str, text_b: str, context_lines: int = 3) -> dict[str, Any]:
    """Compare two text outputs and show unified diff."""
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(lines_a, lines_b, lineterm="", n=context_lines))
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    unchanged = len(lines_a) - removed
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    similarity_pct = round(matcher.ratio() * 100, 2)
    summary = f"Lines added: {added}, removed: {removed}, unchanged: {unchanged}"
    if similarity_pct == 100:
        summary = "Outputs are identical"
    elif similarity_pct >= 95:
        summary += " (near-identical)"
    elif similarity_pct >= 80:
        summary += " (mostly similar)"
    elif similarity_pct < 50:
        summary += " (significantly different)"
    return {
        "lines_added": added,
        "lines_removed": removed,
        "lines_unchanged": unchanged,
        "similarity_pct": similarity_pct,
        "diff": "\n".join(diff_lines),
        "summary": summary,
    }


async def research_diff_track(tool_name: str, output: str, run_id: str = "") -> dict[str, Any]:
    """Track a tool's output over time to detect drift."""
    previous = _output_history.get(tool_name)
    _output_history[tool_name] = (output, run_id)
    if previous is None:
        return {
            "tool": tool_name,
            "changed": False,
            "previous_run_id": None,
            "similarity_pct": 100.0,
            "changes_summary": "Initial baseline recorded",
            "drift_detected": False,
        }
    previous_output, previous_run_id = previous
    matcher = difflib.SequenceMatcher(None, previous_output, output)
    similarity_pct = round(matcher.ratio() * 100, 2)
    changed = similarity_pct < 100
    drift_detected = similarity_pct < 80 if changed else False
    if not changed:
        changes_summary = "No changes detected"
    elif similarity_pct >= 95:
        changes_summary = "Minor changes detected"
    elif similarity_pct >= 80:
        changes_summary = "Moderate changes detected"
    else:
        changes_summary = "Significant changes detected (drift warning)"
    return {
        "tool": tool_name,
        "changed": changed,
        "previous_run_id": previous_run_id,
        "similarity_pct": similarity_pct,
        "changes_summary": changes_summary,
        "drift_detected": drift_detected,
    }
