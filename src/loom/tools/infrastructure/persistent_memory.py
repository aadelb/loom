"""Persistent memory storage for research findings across sessions.

Stores findings in SQLite with auto-extracted entities/tags, enabling
permanent recall and session-agnostic knowledge accumulation.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.persistent_memory")
_MEMORY_DB = Path.home() / ".loom" / "memory" / "persistent.db"


def _init_memory_db() -> None:
    """Initialize persistent memory SQLite schema."""
    _MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(_MEMORY_DB)) as conn:
        c = conn.cursor()
        c.execute(
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_topic ON memories(topic)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        conn.commit()


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
def research_remember(
    content: str, topic: str = "", session_id: str = "", importance: float = 0.5
) -> dict[str, object]:
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

    _init_memory_db()
    importance = max(0.0, min(1.0, importance))
    entities = _extract_entities(content)
    tags = ",".join(entities[:10]) if entities else ""

    try:
        with sqlite3.connect(str(_MEMORY_DB)) as conn:
            c = conn.cursor()
            now = datetime.now(UTC).isoformat()
            c.execute(
                "INSERT INTO memories (content, topic, session_id, importance, entities_json, tags, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (content, topic or "", session_id or "", importance, json.dumps(entities), tags, now),
            )
            conn.commit()
            memory_id = c.lastrowid
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
def research_recall(
    query: str, top_k: int = 10, topic: str = ""
) -> dict[str, object]:
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

    _init_memory_db()
    top_k = max(1, min(top_k, 100))

    try:
        with sqlite3.connect(str(_MEMORY_DB)) as conn:
            c = conn.cursor()

            # Build query with optional topic filter
            where_clause = "WHERE (content LIKE ? OR tags LIKE ?)"
            params = [f"%{query}%", f"%{query}%"]
            if topic:
                where_clause += " AND topic = ?"
                params.append(topic)

            c.execute(
                "SELECT id, content, topic, importance, tags, created_at FROM memories "
                f"{where_clause} ORDER BY importance DESC, created_at DESC LIMIT ?",
                params + [top_k],
            )
            results = [
                {
                    "id": row[0],
                    "content": row[1][:500],  # Truncate to 500 chars
                    "topic": row[2],
                    "importance": row[3],
                    "tags": row[4].split(",") if row[4] else [],
                    "created_at": row[5],
                }
                for row in c.fetchall()
            ]

            c.execute("SELECT COUNT(*) FROM memories")
            count_row = c.fetchone()
            total = count_row[0] if count_row else 0

        logger.info("Memory recall: query=%s results=%d", query, len(results))
        return {"results": results, "total_memories": total, "query": query}
    except Exception as e:
        logger.error("Memory recall failed: %s", e)
        return {"results": [], "error": str(e)}


@handle_tool_errors("research_memory_stats")
def research_memory_stats() -> dict[str, object]:
    """Return persistent memory statistics.

    Returns:
        {total_memories: int, topics: list[str], oldest: str, newest: str, size_mb: float}
    """
    _init_memory_db()

    try:
        with sqlite3.connect(str(_MEMORY_DB)) as conn:
            c = conn.cursor()

            c.execute("SELECT COUNT(*) FROM memories")
            count_row = c.fetchone()
            total = count_row[0] if count_row else 0

            c.execute("SELECT DISTINCT topic FROM memories WHERE topic IS NOT NULL AND topic != '' ORDER BY topic")
            topics = [row[0] for row in c.fetchall()]

            c.execute("SELECT MIN(created_at), MAX(created_at) FROM memories")
            dates_row = c.fetchone()
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
