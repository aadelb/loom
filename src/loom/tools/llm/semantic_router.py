"""Semantic Tool Router — Intelligent tool matching via sentence-transformers embeddings.

Uses all-MiniLM-L6-v2 to embed tool descriptions and queries, then performs cosine
similarity matching. Automatically falls back to TF-IDF (sklearn) and then keyword
matching if higher-order libraries unavailable.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.semantic_router")

# ── Lazy imports with fallbacks ──
_SENTENCE_TRANSFORMERS_AVAILABLE = False
_SKLEARN_AVAILABLE = False
_EMBEDDING_MODEL = None
_TFIDF_VECTORIZER = None
_TOOL_EMBEDDINGS: np.ndarray | None = None
_TOOL_NAMES: list[str] | None = None
_TOOL_DESCRIPTIONS: dict[str, str] = {}
_ROUTER_LOCK: asyncio.Lock | None = None
_CACHE_PATH = Path.home() / ".cache" / "loom" / "tool_embeddings.npy"
_TOOL_CACHE_PATH = Path.home() / ".cache" / "loom" / "tool_names.npy"

try:
    from sentence_transformers import SentenceTransformer

    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    _SKLEARN_AVAILABLE = True
except ImportError:
    pass


def _get_router_lock() -> asyncio.Lock:
    """Get or create the router lock."""
    global _ROUTER_LOCK
    if _ROUTER_LOCK is None:
        _ROUTER_LOCK = asyncio.Lock()
    return _ROUTER_LOCK


def _extract_tool_descriptions() -> dict[str, str]:
    """Extract all tool descriptions from docstrings via AST."""
    descriptions: dict[str, str] = {}
    tools_dir = Path(__file__).parent

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name in ("semantic_router.py", "smart_router.py", "__init__.py"):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            doc = ast.get_docstring(node)
            if not doc:
                continue

            descriptions[node.name] = doc.split("\n")[0]

    return descriptions


async def _load_sentence_transformers_model() -> Any:
    """Lazily load sentence-transformers model on first use."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    if not _SENTENCE_TRANSFORMERS_AVAILABLE:
        return None

    try:
        _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
        return _EMBEDDING_MODEL
    except Exception as e:
        logger.warning("Failed to load sentence-transformers: %s", str(e))
        return None


async def _embed_texts_sentence_transformers(texts: list[str]) -> np.ndarray:
    """Embed texts using sentence-transformers."""
    model = await _load_sentence_transformers_model()
    if model is None:
        raise RuntimeError("sentence-transformers model not available")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings


async def _embed_texts_sklearn(texts: list[str]) -> np.ndarray:
    """Embed texts using TF-IDF + sklearn."""
    global _TFIDF_VECTORIZER

    if not _SKLEARN_AVAILABLE:
        raise RuntimeError("sklearn not available")

    if _TFIDF_VECTORIZER is None:
        _TFIDF_VECTORIZER = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
        _TFIDF_VECTORIZER.fit(texts)

    embeddings = _TFIDF_VECTORIZER.transform(texts).toarray()
    return embeddings


async def _build_tool_embeddings() -> tuple[np.ndarray, list[str]]:
    """Build and cache embeddings for all tools."""
    global _TOOL_EMBEDDINGS, _TOOL_NAMES, _TOOL_DESCRIPTIONS

    async with _get_router_lock():
        if _TOOL_EMBEDDINGS is not None and _TOOL_NAMES is not None:
            return _TOOL_EMBEDDINGS, _TOOL_NAMES

        # Extract tool descriptions
        if not _TOOL_DESCRIPTIONS:
            _TOOL_DESCRIPTIONS.update(_extract_tool_descriptions())

        if not _TOOL_DESCRIPTIONS:
            logger.warning("No tools found")
            return np.array([]), []

        tool_names = sorted(_TOOL_DESCRIPTIONS.keys())
        descriptions = [_TOOL_DESCRIPTIONS[name] for name in tool_names]

        # Try to load cached embeddings
        if _CACHE_PATH.exists() and _TOOL_CACHE_PATH.exists():
            try:
                cached_embeddings = np.load(str(_CACHE_PATH), allow_pickle=False)
                cached_names = np.load(str(_TOOL_CACHE_PATH), allow_pickle=True).tolist()
                if cached_names == tool_names and cached_embeddings.shape[0] == len(tool_names):
                    _TOOL_EMBEDDINGS = cached_embeddings
                    _TOOL_NAMES = cached_names
                    logger.info(
                        "Loaded cached tool embeddings: %d tools, shape %s",
                        len(tool_names),
                        cached_embeddings.shape,
                    )
                    return _TOOL_EMBEDDINGS, _TOOL_NAMES
            except Exception as e:
                logger.warning("Failed to load cached embeddings: %s", str(e))

        # Generate new embeddings (try sentence-transformers first, then sklearn)
        embeddings = None
        embedding_method = "none"

        if _SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                embeddings = await _embed_texts_sentence_transformers(descriptions)
                embedding_method = "sentence-transformers"
                logger.info(
                    "Generated embeddings via sentence-transformers: %d tools, shape %s",
                    len(tool_names),
                    embeddings.shape,
                )
            except Exception as e:
                logger.warning("sentence-transformers embedding failed: %s", str(e))
                embeddings = None

        if embeddings is None and _SKLEARN_AVAILABLE:
            try:
                embeddings = await _embed_texts_sklearn(descriptions)
                embedding_method = "sklearn-tfidf"
                logger.info(
                    "Generated embeddings via sklearn TF-IDF: %d tools, shape %s",
                    len(tool_names),
                    embeddings.shape,
                )
            except Exception as e:
                logger.warning("sklearn TF-IDF embedding failed: %s", str(e))
                embeddings = None

        if embeddings is None:
            logger.warning("No embedding backend available; returning empty")
            return np.array([]), []

        # Cache embeddings to disk
        try:
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            np.save(str(_CACHE_PATH), embeddings, allow_pickle=False)
            np.save(str(_TOOL_CACHE_PATH), np.array(tool_names, dtype=object), allow_pickle=True)
            logger.info("Cached embeddings to %s", _CACHE_PATH)
        except Exception as e:
            logger.warning("Failed to cache embeddings: %s", str(e))

        _TOOL_EMBEDDINGS = embeddings
        _TOOL_NAMES = tool_names
        return _TOOL_EMBEDDINGS, _TOOL_NAMES


async def _similarity_search(query_embedding: np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
    """Find top-K tools by cosine similarity."""
    if _TOOL_EMBEDDINGS is None or _TOOL_NAMES is None:
        return []

    if not _SKLEARN_AVAILABLE:
        return []

    if len(query_embedding.shape) == 1:
        query_embedding = query_embedding.reshape(1, -1)

    similarities = cosine_similarity(query_embedding, _TOOL_EMBEDDINGS)[0]
    top_indices = np.argsort(-similarities)[:top_k]

    return [
        (_TOOL_NAMES[i], float(similarities[i])) for i in top_indices if similarities[i] > 0.0
    ]


def _keyword_fallback(query: str, top_k: int = 5) -> list[tuple[str, float]]:
    """Fallback keyword-based matching when embeddings unavailable."""
    if not _TOOL_DESCRIPTIONS:
        return []

    query_lower = query.lower()
    query_tokens = {t for t in query_lower.replace("_", " ").replace("-", " ").split()
                   if len(t) > 2 and t.isalnum()}

    if not query_tokens:
        return []

    scores: dict[str, float] = {}
    for tool_name, desc in _TOOL_DESCRIPTIONS.items():
        desc_lower = desc.lower()
        match_count = sum(1 for token in query_tokens if token in desc_lower)
        if match_count > 0:
            scores[tool_name] = match_count / len(query_tokens)

    sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_tools[:top_k]


@handle_tool_errors("research_semantic_route")
async def research_semantic_route(query: str, top_k: int = 5) -> dict[str, Any]:
    """Route query to optimal tools via semantic embeddings.

    Uses sentence-transformers to embed query and tool descriptions, then finds
    top-K most similar tools via cosine similarity. Falls back to TF-IDF and
    keyword matching if higher-order libraries unavailable.

    Args:
        query: Natural language query describing tools needed
        top_k: Maximum number of tools to return (1-25)

    Returns:
        Dict with recommended tools, similarity scores, embedding method used
    """
    try:
        if not query or not isinstance(query, str):
            return {
                "query": query,
                "error": "Query must be a non-empty string",
                "recommended_tools": [],
                "embedding_method": "none",
            }

        query = query.strip()
        if len(query) < 2:
            return {
                "query": query,
                "error": "Query too short (min 2 chars)",
                "recommended_tools": [],
                "embedding_method": "none",
            }

        top_k = max(1, min(top_k, 25))

        # Build embeddings if not already done
        embeddings, tool_names = await _build_tool_embeddings()
        if embeddings is None or len(tool_names) == 0:
            logger.warning("No embeddings available; using keyword fallback")
            results = _keyword_fallback(query, top_k)
            return {
                "query": query,
                "recommended_tools": [
                    {"tool": name, "similarity": float(score)} for name, score in results
                ],
                "embedding_method": "keyword_fallback",
                "total_tools": len(_TOOL_DESCRIPTIONS),
            }

        # Embed query
        embedding_method = "none"
        query_embedding = None

        if _SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                query_embedding = await _embed_texts_sentence_transformers([query])
                embedding_method = "sentence-transformers"
            except Exception as e:
                logger.warning("Query embedding failed with sentence-transformers: %s", str(e))

        if query_embedding is None and _SKLEARN_AVAILABLE:
            try:
                query_embedding = await _embed_texts_sklearn([query])
                embedding_method = "sklearn-tfidf"
            except Exception as e:
                logger.warning("Query embedding failed with sklearn: %s", str(e))

        if query_embedding is None:
            logger.warning("Could not embed query; using keyword fallback")
            results = _keyword_fallback(query, top_k)
            return {
                "query": query,
                "recommended_tools": [
                    {"tool": name, "similarity": float(score)} for name, score in results
                ],
                "embedding_method": "keyword_fallback",
                "total_tools": len(_TOOL_DESCRIPTIONS),
            }

        # Search for similar tools
        results = await _similarity_search(query_embedding, top_k)

        return {
            "query": query,
            "recommended_tools": [
                {"tool": name, "similarity": float(score)} for name, score in results
            ],
            "embedding_method": embedding_method,
            "total_tools": len(_TOOL_DESCRIPTIONS),
            "embedding_dims": int(query_embedding.shape[-1]),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_semantic_route"}


@handle_tool_errors("research_semantic_batch_route")
async def research_semantic_batch_route(
    queries: list[str], top_k: int = 5
) -> dict[str, Any]:
    """Route multiple queries with aggregated statistics.

    Args:
        queries: List of natural language queries
        top_k: Maximum tools per query

    Returns:
        Dict with routes for each query and aggregated statistics
    """
    try:
        if not queries or not isinstance(queries, list):
            return {"error": "Queries must be non-empty list", "routes": [], "total_queries": 0}

        routes = []
        tool_counts: dict[str, int] = {}

        for query in queries:
            if isinstance(query, str) and query.strip():
                route = await research_semantic_route(query, top_k)
                routes.append(route)
                for tool_info in route.get("recommended_tools", []):
                    tool_name = tool_info.get("tool", "")
                    if tool_name:
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        top_tool = max(tool_counts, key=tool_counts.get) if tool_counts else "mixed"

        return {
            "routes": routes,
            "tool_distribution": dict(
                sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
            ),
            "total_queries": len(routes),
            "recommendation_summary": f"Routed {len(routes)} queries to {len(tool_counts)} tools. Most: {top_tool}",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_semantic_batch_route"}


@handle_tool_errors("research_semantic_router_rebuild")
async def research_semantic_router_rebuild() -> dict[str, Any]:
    """Force rebuild semantic embeddings (call when new tools added).

    Returns:
        Dict with rebuild status and statistics
    """
    try:
        global _TOOL_EMBEDDINGS, _TOOL_NAMES, _TOOL_DESCRIPTIONS

        async with _get_router_lock():
            _TOOL_EMBEDDINGS = None
            _TOOL_NAMES = None
            _TOOL_DESCRIPTIONS = {}

        embeddings, tool_names = await _build_tool_embeddings()

        return {
            "status": "rebuilt",
            "tools": len(tool_names),
            "embedding_dims": int(embeddings.shape[-1]) if embeddings.shape[0] > 0 else 0,
            "cache_path": str(_CACHE_PATH),
            "message": f"Rebuilt embeddings for {len(tool_names)} tools",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_semantic_router_rebuild"}
