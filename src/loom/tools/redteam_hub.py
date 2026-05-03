"""Red Team Hub — collaborative multi-researcher platform for sharing findings.

Tools:
    research_hub_share — Share a finding with the team
    research_hub_feed — Get the team feed of recent findings
    research_hub_vote — Upvote/downvote a finding
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiosqlite

logger = logging.getLogger("loom.tools.redteam_hub")
HUB_DB = Path.home() / ".loom" / "hub.db"


async def _init_db() -> aiosqlite.Connection:
    """Initialize SQLite connection with schema."""
    HUB_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(HUB_DB))
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS findings ("
        "id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL, "
        "content TEXT NOT NULL, tags TEXT, visibility TEXT NOT NULL, "
        "author TEXT NOT NULL, created TEXT NOT NULL, votes INTEGER DEFAULT 0)"
    )
    await conn.commit()
    return conn


async def research_hub_share(
    finding_type: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
    visibility: str = "team",
) -> dict[str, Any]:
    """Share a finding with the team.

    Args:
        finding_type: 'exploit', 'strategy', 'defense', 'insight', 'question'
        title: Brief title
        content: Full content
        tags: Optional tags
        visibility: 'private', 'team', 'public'
    """
    if finding_type not in ("exploit", "strategy", "defense", "insight", "question"):
        return {"success": False, "error": f"Invalid finding_type: {finding_type}"}
    if visibility not in ("private", "team", "public"):
        return {"success": False, "error": f"Invalid visibility: {visibility}"}

    finding_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()

    try:
        async with await _init_db() as conn:
            await conn.execute(
                "INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (finding_id, finding_type, title, content, json.dumps(tags or []), visibility, "anonymous", timestamp),
            )
            await conn.commit()
        logger.info("hub_share", finding_id=finding_id, type=finding_type)
        return {"success": True, "finding_id": finding_id, "type": finding_type, "title": title, "visibility": visibility, "timestamp": timestamp}
    except Exception as e:
        logger.error("hub_share_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def research_hub_feed(
    type_filter: str = "all",
    limit: int = 20,
) -> dict[str, Any]:
    """Get team feed of recent findings.

    Args:
        type_filter: 'all' or specific type
        limit: Max findings (max 100)
    """
    limit = min(limit, 100)
    try:
        async with await _init_db() as conn:
            query = "SELECT id, type, title, tags, author, created, votes FROM findings WHERE visibility IN ('team', 'public')"
            params: list[Any] = []
            if type_filter != "all":
                query += " AND type = ?"
                params.append(type_filter)
            query += " ORDER BY created DESC LIMIT ?"
            params.append(limit)

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        findings = [{
            "id": r[0], "type": r[1], "title": r[2], "tags": json.loads(r[3]) if r[3] else [],
            "author": r[4], "created": r[5], "votes": r[6],
        } for r in rows]
        return {"findings": findings, "total": len(findings), "type_filter": type_filter}
    except Exception as e:
        logger.error("hub_feed_failed", error=str(e))
        return {"findings": [], "total": 0, "error": str(e)}


async def research_hub_vote(
    finding_id: str,
    vote: int = 1,
) -> dict[str, Any]:
    """Upvote (1) or downvote (-1) a finding.

    Args:
        finding_id: Finding ID
        vote: 1 for upvote, -1 for downvote
    """
    if vote not in (1, -1):
        return {"success": False, "error": "vote must be 1 or -1"}

    try:
        async with await _init_db() as conn:
            cursor = await conn.execute("SELECT votes FROM findings WHERE id = ?", (finding_id,))
            row = await cursor.fetchone()
            if not row:
                return {"success": False, "error": f"Finding {finding_id} not found"}
            new_votes = row[0] + vote
            await conn.execute("UPDATE findings SET votes = ? WHERE id = ?", (new_votes, finding_id))
            await conn.commit()
        logger.info("hub_vote", finding_id=finding_id, vote=vote, new_count=new_votes)
        return {"success": True, "finding_id": finding_id, "new_vote_count": new_votes}
    except Exception as e:
        logger.error("hub_vote_failed", error=str(e))
        return {"success": False, "error": str(e)}
