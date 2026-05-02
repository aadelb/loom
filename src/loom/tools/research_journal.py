"""Research Journal — track findings over time with JSONL storage."""
from __future__ import annotations
import json, logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

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

async def research_journal_add(title: str, content: str, tags: list[str] | None = None, category: str = "finding") -> dict[str, Any]:
    """Add entry to journal. Categories: finding, hypothesis, experiment, insight, todo, milestone."""
    if category not in VALID_CATEGORIES:
        return {"error": f"Invalid category '{category}'", "entry_id": None}
    if not title or not title.strip():
        return {"error": "Title empty", "entry_id": None}
    entry_id = str(uuid4())[:8]
    now = datetime.now(UTC)
    entry = {"id": entry_id, "title": title, "content": content, "tags": tags or [], "category": category, "timestamp": now.isoformat()}
    try:
        with open(_month_file(now), "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("journal_entry_added", entry_id=entry_id, category=category)
    except OSError as e:
        logger.error("journal_write_failed", error=str(e))
        return {"error": f"Write failed: {e}", "entry_id": None}
    return {"entry_id": entry_id, "title": title, "category": category, "timestamp": entry["timestamp"]}

async def research_journal_search(query: str = "", category: str = "all", limit: int = 20) -> dict[str, Any]:
    """Search journal entries by query and/or category. Returns {entries, total}."""
    journal_dir = _journal_dir()
    entries = []
    if not journal_dir.exists():
        return {"entries": [], "total": 0}
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
        entry["preview"] = entry.get("content", "")[:150] + "..."
    return {"entries": entries[:limit], "total": len(entries)}

async def research_journal_timeline(months: int = 3) -> dict[str, Any]:
    """Timeline aggregated by week. Returns {timeline, total_entries, active_weeks}."""
    journal_dir = _journal_dir()
    entries_by_week: dict[str, list[dict]] = {}
    if not journal_dir.exists():
        return {"timeline": [], "total_entries": 0, "active_weeks": 0}
    for month_file in sorted(journal_dir.glob("*.jsonl")):
        try:
            with open(month_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    try:
                        dt = datetime.fromisoformat(entry.get("timestamp", ""))
                        week = dt.strftime("%Y-W%V")
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
    return {"timeline": timeline[:52], "total_entries": total, "active_weeks": len(timeline)}
