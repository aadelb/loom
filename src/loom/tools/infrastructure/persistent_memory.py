"""Persistent memory storage for research findings across sessions.

Stores findings in SQLite with auto-extracted entities/tags, enabling
permanent recall and session-agnostic knowledge accumulation.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from loom.error_responses import handle_tool_errors

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """Fallback clamp if score_utils unavailable."""
        return max(lo, min(hi, v))

logger = logging.getLogger("loom.tools.persistent_memory")
_MEMORY_DB = Path.home() / ".loom" / "memory" / "persistent.db"


async def _init_memory_db() -> None:
    """Initialize persistent memory SQLite schema."""
    _MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(_MEMORY_DB)) as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS memories ("
            "id INTEGER PRIMARY KEY, "
            "content TEXT NOT NULL, "
            "topic TEXT, "
            "session_id TEXT, "
            "importance REAL DEFAULT 0.5, "
            "entities_json TEXT, "
            "tags TEXT, "
            "created_at TEXT)"
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON memories(topic)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        await conn.commit()


def _extract_entities(content: str) -> list[str]:
    """Auto-extract potential entities (capitalized words, URLs, emails)."""
    entities = []
    # Capitalized phrases (person/org names)
    entities.extend(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content))
    # URLs
    entities.extend(re.findall(r"https?://\S+", content))
    # Email addresses
    entities.extend(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content))
    return list(set(entities))[:20]  # Deduplicate, limit to 20


@handle_tool_errors("research_remember")
async def research_remember(
    content: str, topic: str = "", session_id: str = "", importance: float = 0.5
) -> dict[str, Any]:
    """Store research finding permanently in persistent memory.

    Args:
        content: Research finding text to store
        topic: Topic/category (e.g., 'threat_intel', 'privacy_research')
        session_id: Optional session identifier for context
        importance: Importance score 0.0-1.0 (default 0.5)

    Returns:
        {stored: bool, memory_id: int, topic: str, entities_extracted: list[str]}
    """
    if not content or not content.strip():
        return {"stored": False, "error": "content cannot be empty"}

    await _init_memory_db()
    importance = clamp(importance, 0.0, 1.0)
    entities = _extract_entities(content)
    tags = ",".join(entities[:10]) if entities else ""

    try:
        async with aiosqlite.connect(str(_MEMORY_DB)) as conn:
            now = datetime.now(UTC).isoformat()
            cursor = await conn.execute(
                "INSERT INTO memories (content, topic, session_id, importance, entities_json, tags, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (content, topic or "", session_id or "", importance, json.dumps(entities), tags, now),
            )
            await conn.commit()
            memory_id = cursor.lastrowid
        logger.info("Memory stored: id=%d topic=%s entities=%d", memory_id, topic, len(entities))
        return {
            "stored": True,
            "memory_id": memory_id,
            "topic": topic,
            "entities_extracted": entities,
        }
    except Exception as e:
        logger.error("Memory store failed: %s", e)
        return {"stored": False, "error": str(e)}


@handle_tool_errors("research_recall")
async def research_recall(
    query: str, top_k: int = 10, topic: str = ""
) -> dict[str, Any]:
    """Search persistent memory using LIKE matching.

    Args:
        query: Search query (matched against content and tags)
        top_k: Maximum results to return (default 10)
        topic: Optional topic filter

    Returns:
        {results: list[dict], total_memories: int, query: str}
    """
    if not query or not query.strip():
        return {"results": [], "total_memories": 0, "query": query}

    await _init_memory_db()
    top_k = max(1, min(top_k, 100))

    try:
        async with aiosqlite.connect(str(_MEMORY_DB)) as conn:
            # Build query with optional topic filter
            where_clause = "WHERE (content LIKE ? OR tags LIKE ?)"
            params = [f"%{query}%", f"%{query}%"]
            if topic:
                where_clause += " AND topic = ?"
                params.append(topic)

            cursor = await conn.execute(
                "SELECT id, content, topic, importance, tags, created_at FROM memories "
                f"{where_clause} ORDER BY importance DESC, created_at DESC LIMIT ?",
                params + [top_k],
            )
            rows = await cursor.fetchall()
            results = [
                {
                    "id": row[0],
                    "content": row[1][:500],  # Truncate to 500 chars
                    "topic": row[2],
                    "importance": row[3],
                    "tags": row[4].split(",") if row[4] else [],
                    "created_at": row[5],
                }
                for row in rows
            ]

            count_cursor = await conn.execute("SELECT COUNT(*) FROM memories")
            count_row = await count_cursor.fetchone()
            total = count_row[0] if count_row else 0

        logger.info("Memory recall: query=%s results=%d", query, len(results))
        return {"results": results, "total_memories": total, "query": query}
    except Exception as e:
        logger.error("Memory recall failed: %s", e)
        return {"results": [], "error": str(e)}


@handle_tool_errors("research_memory_stats")
async def research_memory_stats() -> dict[str, Any]:
    """Return persistent memory statistics.

    Returns:
        {total_memories: int, topics: list[str], oldest: str, newest: str, size_mb: float}
    """
    await _init_memory_db()

    try:
        async with aiosqlite.connect(str(_MEMORY_DB)) as conn:
            count_cursor = await conn.execute("SELECT COUNT(*) FROM memories")
            count_row = await count_cursor.fetchone()
            total = count_row[0] if count_row else 0

            topics_cursor = await conn.execute("SELECT DISTINCT topic FROM memories WHERE topic IS NOT NULL AND topic != '' ORDER BY topic")
            topics = [row[0] for row in await topics_cursor.fetchall()]

            dates_cursor = await conn.execute("SELECT MIN(created_at), MAX(created_at) FROM memories")
            dates_row = await dates_cursor.fetchone()
            oldest, newest = (dates_row if dates_row else (None, None))

        # Get file size
        size_mb = _MEMORY_DB.stat().st_size / (1024 * 1024) if _MEMORY_DB.exists() else 0

        logger.info("Memory stats: total=%d topics=%d size=%.2f MB", total, len(topics), size_mb)
        return {
            "total_memories": total,
            "topics": topics,
            "oldest": oldest or "",
            "newest": newest or "",
            "size_mb": round(size_mb, 2),
        }
    except Exception as e:
        logger.error("Memory stats failed: %s", e)
        return {"error": str(e)}
