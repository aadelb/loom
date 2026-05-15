"""Research Journal — track findings over time with JSONL storage."""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from loom.error_responses import handle_tool_errors
try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text: str, max_chars: int = 500, *, suffix: str = "...") -> str:
        """Fallback truncate if text_utils unavailable."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix

logger = logging.getLogger("loom.tools.research_journal")
VALID_CATEGORIES = {"finding", "hypothesis", "experiment", "insight", "todo", "milestone"}

def _journal_dir() -> Path:
    d = Path.home() / ".loom" / "journal"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _month_file(dt: datetime | None = None) -> Path:
    if dt is None:
        dt = datetime.now(UTC)
    return _journal_dir() / f"{dt.strftime('%Y-%m')}.jsonl"


def _write_journal_entry(month_file: Path, entry: dict[str, Any]) -> None:
    """Write journal entry to file (blocking I/O)."""
    with open(month_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _search_journal_entries(query: str, category: str, limit: int) -> tuple[list[dict[str, Any]], int]:
    """Search journal entries (blocking I/O).

    Args:
        query: search query string
        category: category filter
        limit: max entries to return

    Returns:
        Tuple of (entries, total count)
    """
    journal_dir = _journal_dir()
    entries = []
    if not journal_dir.exists():
        return [], 0

    for month_file in sorted(journal_dir.glob("*.jsonl")):
        try:
            with open(month_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if category != "all" and entry.get("category") != category:
                        continue
                    if query:
                        query_lower = query.lower()
                        if not (query_lower in entry.get("title", "").lower() or query_lower in entry.get("content", "").lower() or any(query_lower in tag.lower() for tag in entry.get("tags", []))):
                            continue
                    entries.append(entry)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("journal_read_failed", file=month_file, error=str(e))

    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    for entry in entries[:limit]:
        content = entry.get("content", "")
        entry["preview"] = truncate(content, 150) + ("..." if len(content) > 150 else "")

    return entries[:limit], len(entries)


def _read_journal_timeline(months: int) -> tuple[list[dict[str, Any]], int, int]:
    """Read and aggregate journal timeline (blocking I/O).

    Args:
        months: number of months to include

    Returns:
        Tuple of (timeline, total_entries, active_weeks)
    """
    journal_dir = _journal_dir()
    entries_by_week: dict[str, list[dict]] = {}
    if not journal_dir.exists():
        return [], 0, 0

    for month_file in sorted(journal_dir.glob("*.jsonl")):
        try:
            with open(month_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    try:
                        dt = datetime.fromisoformat(entry.get("timestamp", ""))
                        week = dt.strftime("%G-W%V")
                        if week not in entries_by_week:
                            entries_by_week[week] = []
                        entries_by_week[week].append(entry)
                    except ValueError:
                        logger.warning("invalid_timestamp", entry_id=entry.get("id"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("journal_read_failed", file=month_file, error=str(e))

    cutoff = datetime.now(UTC) - timedelta(days=months * 30)
    timeline, total = [], 0
    for week in sorted(entries_by_week.keys(), reverse=True):
        entries = entries_by_week[week]
        if entries and entries[0].get("timestamp"):
            try:
                if datetime.fromisoformat(entries[0]["timestamp"]) < cutoff:
                    continue
            except ValueError:
                pass
        cats = {}
        for e in entries:
            cat = e.get("category", "unknown")
            cats[cat] = cats.get(cat, 0) + 1
        highlights = [e["title"] for e in sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)[:3]]
        timeline.append({"week": week, "entries_count": len(entries), "categories": cats, "highlights": highlights})
        total += len(entries)

    active_weeks = len(timeline)
    return timeline[:52], total, active_weeks


@handle_tool_errors("research_journal_add")
async def research_journal_add(title: str, content: str, tags: list[str] | None = None, category: str = "finding") -> dict[str, Any]:
    """Add entry to journal. Categories: finding, hypothesis, experiment, insight, todo, milestone."""
    try:
        if category not in VALID_CATEGORIES:
            return {"error": f"Invalid category '{category}'", "entry_id": None}
        if not title or not title.strip():
            return {"error": "Title empty", "entry_id": None}

        entry_id = str(uuid4())[:8]
        now = datetime.now(UTC)
        entry = {
            "id": entry_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "category": category,
            "timestamp": now.isoformat(),
        }

        try:
            # Run blocking file I/O in executor
            await asyncio.to_thread(_write_journal_entry, _month_file(now), entry)
            logger.info("journal_entry_added", entry_id=entry_id, category=category)
        except OSError as e:
            logger.error("journal_write_failed", error=str(e))
            return {"error": f"Write failed: {e}", "entry_id": None}

        return {
            "entry_id": entry_id,
            "title": title,
            "category": category,
            "timestamp": entry["timestamp"],
        }
    except Exception as exc:
        logger.error("journal_add_error: %s", exc)
        return {"error": str(exc), "tool": "research_journal_add"}


@handle_tool_errors("research_journal_search")
async def research_journal_search(query: str = "", category: str = "all", limit: int = 20) -> dict[str, Any]:
    """Search journal entries by query and/or category. Returns {entries, total}."""
    try:
        # Run blocking file I/O in executor
        entries, total = await asyncio.to_thread(_search_journal_entries, query, category, limit)
        return {"entries": entries, "total": total}
    except Exception as exc:
        logger.error("journal_search_error: %s", exc)
        return {"error": str(exc), "tool": "research_journal_search"}


@handle_tool_errors("research_journal_timeline")
async def research_journal_timeline(months: int = 3) -> dict[str, Any]:
    """Timeline aggregated by week. Returns {timeline, total_entries, active_weeks}."""
    try:
        # Run blocking file I/O in executor
        timeline, total_entries, active_weeks = await asyncio.to_thread(_read_journal_timeline, months)
        return {
            "timeline": timeline,
            "total_entries": total_entries,
            "active_weeks": active_weeks,
        }
    except Exception as exc:
        logger.error("journal_timeline_error: %s", exc)
        return {"error": str(exc), "tool": "research_journal_timeline"}
