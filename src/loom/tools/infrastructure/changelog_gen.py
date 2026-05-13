"""Changelog generator from git history."""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any

import logging
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.changelog_gen")


def _run_git(cmd: list[str]) -> str:
    """Run git command and return stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=".")
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        logger.error("Git error: %s", e)
        return ""


def _parse_type(msg: str) -> str:
    """Extract commit type from conventional commit message."""
    m = re.match(r"^(\w+)(?:\([^)]*\))?:", msg)
    return m.group(1).lower() if m else "other"


def _since_to_arg(since: str) -> str:
    """Convert since parameter to git --since argument."""
    if since == "last_tag":
        tag = _run_git(["git", "describe", "--tags", "--abbrev=0"])
        return tag or "1 month ago"
    if since.endswith("d") and len(since) > 1 and since[:-1].isdigit():
        days = int(since[:-1])
        return (datetime.now(UTC) - timedelta(days=days)).isoformat()
    return since if re.match(r"^\d{4}-\d{2}-\d{2}", since) else (datetime.now(UTC) - timedelta(days=7)).isoformat()


@handle_tool_errors("research_changelog_generate")
async def research_changelog_generate(
    since: str = "7d",
    format: str = "markdown",
) -> dict[str, Any]:
    """Generate changelog from git log with conventional commit parsing.

    Args:
        since: Time period ("7d", "30d", "last_tag", or ISO date)
        format: Output format ("markdown")

    Returns:
        Dict with: changelog, period, commits_count, by_type
    """
    try:
        since_arg = _since_to_arg(since)
        log_output = _run_git(["git", "log", f"--since={since_arg}", '--pretty=format:%H|%an|%ad|%s', "--date=iso"])

        if not log_output:
            return {"changelog": "No commits found.", "period": since, "commits_count": 0, "by_type": {}}

        by_type: dict[str, list[str]] = {}
        commits_count = 0

        for line in log_output.split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue

            commit_type = _parse_type(parts[3])
            by_type.setdefault(commit_type, []).append(parts[3])
            commits_count += 1

        # Generate markdown changelog
        lines = ["# Changelog\n"]
        type_labels = {"feat": "Features", "fix": "Bug Fixes", "refactor": "Refactoring", "test": "Tests", "docs": "Documentation"}
        for ctype in ["feat", "fix", "refactor", "test", "docs", "other"]:
            if ctype in by_type:
                label = type_labels.get(ctype, ctype.capitalize())
                lines.append(f"\n## {label}\n")
                lines.extend(f"- {msg}" for msg in by_type[ctype])

        return {
            "changelog": "\n".join(lines),
            "period": since,
            "commits_count": commits_count,
            "by_type": {k: len(v) for k, v in by_type.items()},
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_changelog_generate"}


@handle_tool_errors("research_changelog_stats")
async def research_changelog_stats(days: int = 30) -> dict[str, Any]:
    """Get git statistics for the project.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with project stats: commits, files, insertions, deletions, authors, frequency
    """
    try:
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        commits_output = _run_git(["git", "log", f"--since={since}", "--oneline"])
        total_commits = len([l for l in commits_output.split("\n") if l.strip()])

        diffstat_output = _run_git(["git", "log", f"--since={since}", "--numstat", "--pretty="])
        insertions = deletions = files_changed = 0
        for line in diffstat_output.split("\n"):
            try:
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    insertions += int(parts[0])
                    deletions += int(parts[1])
                    files_changed += 1
            except (ValueError, IndexError):
                pass

        authors_output = _run_git(["git", "log", f"--since={since}", "--pretty=format:%an"])
        author_counts = {}
        for author in authors_output.split("\n"):
            if author.strip():
                author_counts[author] = author_counts.get(author, 0) + 1
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        days_output = _run_git(["git", "log", f"--since={since}", "--pretty=format:%ad", "--date=short"])
        day_counts = {}
        for date in days_output.split("\n"):
            if date.strip():
                day_counts[date] = day_counts.get(date, 0) + 1
        most_active = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else None

        return {
            "total_commits": total_commits,
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
            "top_authors": [{"author": a, "commits": c} for a, c in top_authors],
            "most_active_day": most_active,
            "commit_frequency_per_day": round(total_commits / max(days, 1), 2),
            "period_days": days,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_changelog_stats"}
