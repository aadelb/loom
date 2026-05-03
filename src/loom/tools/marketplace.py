"""Loom Marketplace tools for buying/selling custom modules, strategies, templates."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import aiosqlite

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.marketplace")

# Marketplace database path
_MARKETPLACE_DB = Path.home() / ".loom" / "marketplace.db"


async def _get_db() -> aiosqlite.Connection:
    """Get or create marketplace database connection."""
    _MARKETPLACE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(_MARKETPLACE_DB))
    await conn.execute("PRAGMA journal_mode=WAL")
    await _init_db(conn)
    return conn


async def _init_db(conn: aiosqlite.Connection) -> None:
    """Initialize marketplace tables if they don't exist."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price_credits INTEGER NOT NULL,
            author TEXT NOT NULL,
            downloads INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            created TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_category ON listings(category)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_created ON listings(created DESC)"
    )
    await conn.commit()


async def research_marketplace_list(
    category: str = "all",
    sort_by: str = "popular",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Browse marketplace listings.

    Args:
        category: Filter by "strategy", "tool", "template", "dataset", "pipeline", or "all"
        sort_by: Sort by "popular", "newest", "price_low", "price_high", or "rating"
        page: Page number (1-indexed)
        limit: Results per page (1-100)

    Returns:
        Dict with listings, total count, and pagination info
    """
    if category not in ("strategy", "tool", "template", "dataset", "pipeline", "all"):
        return {"error": f"Invalid category: {category}"}
    if sort_by not in ("popular", "newest", "price_low", "price_high", "rating"):
        return {"error": f"Invalid sort_by: {sort_by}"}
    if not (1 <= page <= 1000) or not (1 <= limit <= 100):
        return {"error": "Invalid page or limit"}

    async with await _get_db() as conn:
        # Build query
        where_clause = "" if category == "all" else f"WHERE category = ?"
        order_map = {
            "popular": "downloads DESC",
            "newest": "created DESC",
            "price_low": "price_credits ASC",
            "price_high": "price_credits DESC",
            "rating": "rating DESC",
        }
        order_clause = order_map[sort_by]

        # Count total
        count_sql = f"SELECT COUNT(*) FROM listings {where_clause}"
        cursor = await conn.execute(count_sql, () if category == "all" else (category,))
        total = (await cursor.fetchone())[0]

        # Fetch page
        offset = (page - 1) * limit
        query_sql = (
            f"SELECT id, name, category, price_credits, author, downloads, rating "
            f"FROM listings {where_clause} ORDER BY {order_clause} LIMIT ? OFFSET ?"
        )
        params = (limit, offset) if category == "all" else (category, limit, offset)
        cursor = await conn.execute(query_sql, params)
        rows = await cursor.fetchall()

        listings = [
            {
                "id": r[0],
                "name": r[1],
                "category": r[2],
                "price": r[3],
                "author": r[4],
                "downloads": r[5],
                "rating": r[6],
            }
            for r in rows
        ]

        return {
            "listings": listings,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }


async def research_marketplace_publish(
    name: str,
    category: str,
    description: str,
    content: str,
    price_credits: int = 0,
    author: str = "anonymous",
) -> dict[str, Any]:
    """Publish a custom module/strategy/template to the marketplace.

    Args:
        name: Listing name
        category: "strategy", "tool", "template", "dataset", or "pipeline"
        description: Short description
        content: Full content (JSON-serialized)
        price_credits: Price in credits (0 for free)
        author: Author name

    Returns:
        Dict with listing_id, status, and details
    """
    if category not in ("strategy", "tool", "template", "dataset", "pipeline"):
        return {"error": f"Invalid category: {category}"}
    if not (0 <= price_credits <= 1000000):
        return {"error": "price_credits must be 0-1000000"}
    if len(name) < 3 or len(name) > 200:
        return {"error": "name must be 3-200 chars"}
    if len(description) < 10 or len(description) > 2000:
        return {"error": "description must be 10-2000 chars"}
    if len(author) < 1 or len(author) > 100:
        return {"error": "author must be 1-100 chars"}

    listing_id = str(uuid4())
    now = datetime.now(UTC).isoformat()

    async with await _get_db() as conn:
        await conn.execute(
            "INSERT INTO listings "
            "(id, name, category, description, price_credits, author, downloads, rating, created, content) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0.0, ?, ?)",
            (listing_id, name, category, description, price_credits, author, now, content),
        )
        await conn.commit()

        return {
            "listing_id": listing_id,
            "name": name,
            "category": category,
            "price": price_credits,
            "author": author,
            "status": "published",
            "created": now,
        }


async def research_marketplace_download(
    listing_id: str,
) -> dict[str, Any]:
    """Download/acquire a marketplace item.

    Args:
        listing_id: ID of the listing to download

    Returns:
        Dict with listing details, content, and download timestamp
    """
    if not listing_id or len(listing_id) > 100:
        return {"error": "Invalid listing_id"}

    async with await _get_db() as conn:
        cursor = await conn.execute(
            "SELECT id, name, category, content, downloads FROM listings WHERE id = ?",
            (listing_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return {"error": "Listing not found"}

        listing_id_result, name, category, content, downloads = row

        # Increment downloads
        await conn.execute(
            "UPDATE listings SET downloads = downloads + 1 WHERE id = ?",
            (listing_id,),
        )
        await conn.commit()

        return {
            "listing_id": listing_id_result,
            "name": name,
            "category": category,
            "content": content,
            "downloaded_at": datetime.now(UTC).isoformat(),
            "download_count": downloads + 1,
        }
