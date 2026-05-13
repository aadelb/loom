"""Knowledge Base search tool — store and query accumulated research data."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import aiosqlite

logger = logging.getLogger("loom.tools.knowledge_base")


def _get_kb_path() -> Path:
    path = Path.home() / ".loom" / "knowledge_base.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def _init_kb() -> None:
    async with aiosqlite.connect(_get_kb_path()) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS knowledge (
            id TEXT PRIMARY KEY, key TEXT NOT NULL UNIQUE, content TEXT NOT NULL,
            category TEXT NOT NULL, tags JSON, created TEXT NOT NULL, updated TEXT NOT NULL)""")
        await db.commit()


@handle_tool_errors("research_kb_store")
async def research_kb_store(
    key: str, content: str, category: str = "general", tags: list[str] | None = None,
) -> dict[str, str]:
    """Store knowledge in the base."""
    try:
        await _init_kb()
        kb_id, now = str(uuid4()), datetime.now(UTC).isoformat()
        async with aiosqlite.connect(_get_kb_path()) as db:
            try:
                await db.execute(
                    "INSERT INTO knowledge (id, key, content, category, tags, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (kb_id, key, content, category, json.dumps(tags or []), now, now),
                )
                await db.commit()
                logger.info("kb_stored kb_id=%s key=%s category=%s", kb_id, key, category)
                return {"stored": True, "kb_id": kb_id, "key": key, "category": category}
            except aiosqlite.IntegrityError:
                cursor = await db.execute(
                    "SELECT id FROM knowledge WHERE key=?",
                    (key,),
                )
                existing_id = (await cursor.fetchone())[0]
                await db.execute("UPDATE knowledge SET content=?, category=?, tags=?, updated=? WHERE key=?",
                    (content, category, json.dumps(tags or []), now, key),)
                await db.commit()
                logger.info("kb_updated key=%s category=%s", key, category)
                return {"stored": True, "kb_id": existing_id, "key": key, "category": category}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_kb_store"}


@handle_tool_errors("research_kb_search")
async def research_kb_search(query: str, category: str = "all", limit: int = 20,) -> dict:
    """Search knowledge base matching query against key + content."""
    try:
        await _init_kb()
        pattern = f"%{query}%"
        async with aiosqlite.connect(_get_kb_path()) as db:
            if category == "all":
                cursor = await db.execute(
                    "SELECT id, key, content, category, tags, created FROM knowledge WHERE key LIKE ? OR content LIKE ? ORDER BY created DESC LIMIT ?",
                    (pattern, pattern, limit),)
            else:
                cursor = await db.execute(
                    "SELECT id, key, content, category, tags, created FROM knowledge WHERE (key LIKE ? OR content LIKE ?) AND category = ? ORDER BY created DESC LIMIT ?",
                    (pattern, pattern, category, limit),)
            rows = await cursor.fetchall()
        results = []
        for kb_id, key, content, cat, tags_json, created in rows:
            preview = (content[:200] + "...") if len(content) > 200 else content
            results.append({
                "kb_id": kb_id, "key": key, "content_preview": preview, "category": cat,
                "tags": json.loads(tags_json) if tags_json else [], "created": created,
                "relevance": 0.95 if key.lower() == query.lower() else 0.85,
            })
        logger.info("kb_search query=%s category=%s results=%d", query, category, len(results))
        return {"results": results, "total": len(results)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_kb_search"}


@handle_tool_errors("research_kb_stats")
async def research_kb_stats() -> dict:
    """Return knowledge base statistics."""
    try:
        await _init_kb()
        db_path = _get_kb_path()
        async with aiosqlite.connect(db_path) as db:
            total = (await (await db.execute("SELECT COUNT(*) FROM knowledge")).fetchone())[0]
            categories = {r[0]: r[1] for r in await (await db.execute(
                "SELECT category, COUNT(*) FROM knowledge GROUP BY category")).fetchall()}
            recent = [{"kb_id": r[0], "key": r[1], "category": r[2], "created": r[3]}
                for r in await (await db.execute(
                    "SELECT id, key, category, created FROM knowledge ORDER BY created DESC LIMIT 10")).fetchall()]
        size_kb = db_path.stat().st_size / 1024 if db_path.exists() else 0
        logger.info("kb_stats total=%d categories=%d", total, len(categories))
        return {"total_entries": total, "categories": categories, "recent_additions": recent, "total_size_kb": round(size_kb, 2)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_kb_stats"}
