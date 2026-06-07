"""Unified Knowledge Query — semantic search across ALL Qdrant collections.

Searches 37M+ vectors across 19 collections with auto-routing based on
query type. Groups collections by vector dimension and searches the most
relevant group.

Collection families:
- 384-dim (MiniLM): HCS10 gold (206), ChromaDB tactics (70K), docs_all, consultation
- 768-dim: almahba (6.2K), global_rag (17.5K)
- 1024-dim (E5): code (14.4M+7M), docs_v4 (5.5M)

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.knowledge_query")

QDRANT_URL = "http://localhost:6333"

_COLLECTIONS_384 = [
    ("ummro_hcs10_responses", "HCS10 gold-standard responses"),
    ("ummro_chromadb_migrated", "SFT training, DPO pairs, tactics, Pangea"),
    ("ummro_docs_all", "General documentation"),
    ("consultation_knowledge", "Consultation and advisory knowledge"),
]

_COLLECTIONS_768 = [
    ("almahba_knowledge", "Business knowledge base"),
    ("global_rag", "Global RAG knowledge"),
]

_COLLECTIONS_1024 = [
    ("ummro_code_e5", "Code patterns (14.4M)"),
    ("ummro_docs_v4", "Documentation (5.5M)"),
]

_QUERY_ROUTING = {
    "tactics": ["ummro_chromadb_migrated", "ummro_hcs10_responses"],
    "strategy": ["ummro_chromadb_migrated", "ummro_hcs10_responses"],
    "code": ["ummro_code_e5"],
    "documentation": ["ummro_docs_v4", "ummro_docs_all"],
    "business": ["almahba_knowledge", "global_rag"],
    "gold": ["ummro_hcs10_responses"],
    "training": ["ummro_chromadb_migrated"],
}


def _embed_384(texts: list[str]) -> list[list[float]]:
    """Embed with MiniLM-L6-v2 (384-dim)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


async def _search_collection(
    collection: str,
    vector: list[float],
    limit: int = 5,
    score_threshold: float = 0.3,
) -> list[dict]:
    """Search a single Qdrant collection."""
    import aiohttp

    body = {
        "vector": vector,
        "limit": limit,
        "score_threshold": score_threshold,
        "with_payload": True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{QDRANT_URL}/collections/{collection}/points/search",
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = data.get("result", [])
                return [
                    {
                        "collection": collection,
                        "score": round(r.get("score", 0), 4),
                        "id": r.get("id"),
                        "text": (
                            r.get("payload", {}).get("text", "")
                            or r.get("payload", {}).get("best_response_preview", "")
                            or r.get("payload", {}).get("content", "")
                            or str(r.get("payload", {}))[:300]
                        )[:500],
                        "metadata": {
                            k: v for k, v in r.get("payload", {}).items()
                            if k not in ("text", "content", "best_response_preview", "vector")
                            and isinstance(v, (str, int, float, bool))
                        },
                    }
                    for r in results
                ]
    except Exception as e:
        logger.debug("search_failed collection=%s: %s", collection, str(e)[:80])
        return []


def _detect_query_domain(query: str) -> list[str]:
    """Detect which collections to search based on query keywords."""
    query_lower = query.lower()

    for domain, collections in _QUERY_ROUTING.items():
        if domain in query_lower:
            return collections

    if any(kw in query_lower for kw in ["hack", "exploit", "bypass", "jailbreak", "attack", "reframe"]):
        return ["ummro_chromadb_migrated", "ummro_hcs10_responses"]
    if any(kw in query_lower for kw in ["python", "function", "class", "import", "def ", "async"]):
        return ["ummro_code_e5"]
    if any(kw in query_lower for kw in ["how to", "guide", "tutorial", "documentation"]):
        return ["ummro_docs_v4", "ummro_docs_all"]

    return ["ummro_chromadb_migrated", "ummro_hcs10_responses", "ummro_docs_all"]


@handle_tool_errors("research_knowledge_query")
async def research_knowledge_query(
    query: str,
    collections: list[str] | None = None,
    limit: int = 10,
    min_score: float = 0.3,
) -> dict[str, Any]:
    """Unified semantic search across ALL Qdrant knowledge collections.

    Auto-routes query to the most relevant collections based on content.
    Currently searches 384-dim collections (HCS10 gold, ChromaDB tactics,
    docs, consultation) using MiniLM-L6-v2 embeddings.

    Args:
        query: Search query text.
        collections: Explicit collection names to search (auto-detect if None).
        limit: Max results per collection (default 10, max 50).
        min_score: Minimum cosine similarity threshold (default 0.3).

    Returns:
        Dict with results ranked by score, collections searched,
        query routing info, and total matches found.
    """
    if isinstance(query, list):
        query = " ".join(str(x) for x in query)
    if isinstance(query, dict):
        query = str(query)

    limit = min(max(1, limit), 50)

    target_collections = collections or _detect_query_domain(query)

    supported_384 = {c for c, _ in _COLLECTIONS_384}
    searchable = [c for c in target_collections if c in supported_384]

    if not searchable:
        searchable = ["ummro_chromadb_migrated", "ummro_hcs10_responses"]

    vectors = await asyncio.to_thread(_embed_384, [query])
    if not vectors or not vectors[0]:
        return {"error": "embedding_failed", "query": query}

    vector = vectors[0]

    all_results = []
    for collection in searchable:
        results = await _search_collection(
            collection, vector, limit=limit, score_threshold=min_score,
        )
        all_results.extend(results)

    all_results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "query": query[:100],
        "collections_searched": searchable,
        "routing_reason": "auto" if not collections else "explicit",
        "total_results": len(all_results),
        "results": all_results[:limit],
    }
