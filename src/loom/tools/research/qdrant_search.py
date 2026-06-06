"""Qdrant vector search tool — search 37M+ vectors across 18 collections.

Enables semantic search over code (21M vectors), docs (11M vectors),
and HCS=10 gold standard responses for quality improvement.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.qdrant_search")

QDRANT_URL = "http://localhost:6333"

_COLLECTION_MAP = {
    "code": "ummro_code_e5",
    "code_v2": "ummro_code_e5v2",
    "docs": "ummro_docs_v4",
    "docs_splade": "ummro_docs_splade",
    "code_legacy": "ummro_code",
    "rag": "global_rag",
    "knowledge": "almahba_knowledge",
    "hcs10": "ummro_hcs10_responses",
    "all_docs": "ummro_docs_all",
    "consultation": "consultation_knowledge",
}

_COLLECTION_DIMS = {
    "ummro_code_e5": 1024,
    "ummro_code_e5v2": 1024,
    "ummro_docs_v4": 1024,
    "ummro_code": 1024,
    "ummro_code_v4": 1024,
    "ummro_docs": 1024,
    "ummro_docs_1024": 1024,
    "global_rag": 768,
    "almahba_knowledge": 768,
    "ummro_local": 768,
    "ummro_hcs10_responses": 384,
    "ummro_docs_all": 768,
    "consultation_knowledge": 768,
    "deepsearcher_cart": 768,
}


async def _get_collection_info(collection: str) -> dict[str, Any]:
    """Get collection metadata from Qdrant."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{QDRANT_URL}/collections/{collection}") as resp:
            data = await resp.json()
            return data.get("result", {})


async def _scroll_points(
    collection: str,
    limit: int = 10,
    offset: int | None = None,
    with_payload: bool = True,
    with_vector: bool = False,
    filter_conditions: dict | None = None,
) -> dict[str, Any]:
    """Scroll through points in a collection."""
    import aiohttp

    body: dict[str, Any] = {
        "limit": limit,
        "with_payload": with_payload,
        "with_vector": with_vector,
    }
    if offset is not None:
        body["offset"] = offset
    if filter_conditions:
        body["filter"] = filter_conditions

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{QDRANT_URL}/collections/{collection}/points/scroll",
            json=body,
        ) as resp:
            return await resp.json()


async def _search_similar(
    collection: str,
    vector: list[float],
    limit: int = 5,
    score_threshold: float = 0.5,
) -> dict[str, Any]:
    """Search for similar vectors in a collection."""
    import aiohttp

    body = {
        "vector": vector,
        "limit": limit,
        "score_threshold": score_threshold,
        "with_payload": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{QDRANT_URL}/collections/{collection}/points/search",
            json=body,
        ) as resp:
            return await resp.json()


@handle_tool_errors("research_qdrant_collections")
async def research_qdrant_collections() -> dict[str, Any]:
    """List all Qdrant collections with point counts and metadata.

    Returns:
        Dict with collections list, total points, and per-collection stats.
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{QDRANT_URL}/collections") as resp:
            data = await resp.json()

    collections = data.get("result", {}).get("collections", [])
    stats = []
    total_points = 0

    for col in collections:
        name = col["name"]
        try:
            info = await _get_collection_info(name)
            points = info.get("points_count", 0)
            status = info.get("status", "unknown")
            vectors_config = info.get("config", {}).get("params", {}).get("vectors", {})
            dim = vectors_config.get("size", 0)
            distance = vectors_config.get("distance", "unknown")

            stats.append({
                "name": name,
                "points": points,
                "dimension": dim,
                "distance": distance,
                "status": status,
            })
            total_points += points
        except Exception as e:
            stats.append({"name": name, "error": str(e)})

    return {
        "total_collections": len(collections),
        "total_points": total_points,
        "collections": stats,
    }


@handle_tool_errors("research_qdrant_browse")
async def research_qdrant_browse(
    collection: str = "docs",
    limit: int = 5,
    offset: int = 0,
) -> dict[str, Any]:
    """Browse points in a Qdrant collection with payload metadata.

    Args:
        collection: Collection alias (code, docs, hcs10, rag, knowledge) or full name.
        limit: Number of points to return (max 100).
        offset: Starting offset for pagination.

    Returns:
        Dict with points, their payloads, and pagination info.
    """
    resolved = _COLLECTION_MAP.get(collection, collection)
    limit = min(max(1, limit), 100)

    result = await _scroll_points(
        resolved,
        limit=limit,
        offset=offset if offset > 0 else None,
    )

    points = result.get("result", {}).get("points", [])
    next_offset = result.get("result", {}).get("next_page_offset")

    return {
        "collection": resolved,
        "points_returned": len(points),
        "next_offset": next_offset,
        "points": [
            {
                "id": p.get("id"),
                "payload": p.get("payload", {}),
            }
            for p in points
        ],
    }


@handle_tool_errors("research_qdrant_hcs10")
async def research_qdrant_hcs10(
    limit: int = 10,
    tactic: str = "",
    mold: str = "",
) -> dict[str, Any]:
    """Browse HCS=10 gold standard responses — known-good bypass responses.

    Args:
        limit: Number of responses to return.
        tactic: Filter by tactic (darvo, reverse_psychology, etc).
        mold: Filter by mold/template type.

    Returns:
        Dict with HCS=10 responses, their metadata, and preview text.
    """
    filter_conditions = None
    if tactic or mold:
        must = []
        if tactic:
            must.append({"key": "tactic", "match": {"value": tactic}})
        if mold:
            must.append({"key": "mold", "match": {"value": mold}})
        filter_conditions = {"must": must}

    result = await _scroll_points(
        "ummro_hcs10_responses",
        limit=min(max(1, limit), 36),
        filter_conditions=filter_conditions,
    )

    points = result.get("result", {}).get("points", [])

    return {
        "total_hcs10": 36,
        "returned": len(points),
        "responses": [
            {
                "id": p.get("id"),
                "model": p.get("payload", {}).get("model_id", ""),
                "mold": p.get("payload", {}).get("mold", ""),
                "tactic": p.get("payload", {}).get("tactic", ""),
                "linguistic_mode": p.get("payload", {}).get("linguistic_mode", ""),
                "cascade_depth": p.get("payload", {}).get("cascade_depth", 0),
                "strategy": p.get("payload", {}).get("terminal_strategy", ""),
                "preview": p.get("payload", {}).get("best_response_preview", "")[:300],
            }
            for p in points
        ],
    }


@handle_tool_errors("research_qdrant_count")
async def research_qdrant_count(
    collection: str = "docs",
) -> dict[str, Any]:
    """Get point count for a Qdrant collection.

    Args:
        collection: Collection alias or full name.

    Returns:
        Dict with collection name and point count.
    """
    resolved = _COLLECTION_MAP.get(collection, collection)
    info = await _get_collection_info(resolved)

    return {
        "collection": resolved,
        "points_count": info.get("points_count", 0),
        "status": info.get("status", "unknown"),
        "dimension": info.get("config", {}).get("params", {}).get("vectors", {}).get("size", 0),
    }
