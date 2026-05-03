"""Smart Search Router — Dynamically route queries to optimal tools via keyword indexing."""

from __future__ import annotations

import ast
import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.smart_router")
_TOOL_INDEX: dict[str, set[str]] = {}
_INDEX_LOCK = asyncio.Lock()


def _build_tool_index() -> dict[str, set[str]]:
    """Build {keyword: {tool_names}} index from all tool docstrings via AST."""
    index: dict[str, set[str]] = defaultdict(set)
    tools_dir = Path(__file__).parent

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name in ("smart_router.py", "__init__.py"):
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

            # Tokenize first line: lowercase, split on non-alphanumeric, filter short
            first_line = doc.split("\n")[0].lower()
            tokens = {t for t in first_line.replace("_", " ").replace("-", " ").split()
                     if len(t) > 2 and t.isalnum()}

            for token in tokens:
                index[token].add(node.name)

    return dict(index)


def _get_tool_index() -> dict[str, set[str]]:
    """Get cached index, build if empty."""
    global _TOOL_INDEX
    if not _TOOL_INDEX:
        _TOOL_INDEX = _build_tool_index()
        logger.info(f"Tool index: {len(_TOOL_INDEX)} keywords, {sum(len(v) for v in _TOOL_INDEX.values())} refs")
    return _TOOL_INDEX


async def research_route_query(query: str, intent: str = "auto") -> dict[str, Any]:
    """Route query to optimal tools via keyword matching against all tool docstrings.

    Tokenizes query, matches against tool index, scores by match count.
    Returns top tool with confidence and alternatives.
    """
    if not query or not isinstance(query, str):
        return {"query": query, "error": "Query must be a non-empty string",
                "recommended_tools": [], "confidence": 0.0}

    query_clean = query.strip().lower()
    tool_index = _get_tool_index()

    # Tokenize query
    query_tokens = {t for t in query_clean.replace("_", " ").replace("-", " ").split()
                   if len(t) > 2 and t.isalnum()}

    if not query_tokens:
        return {"query": query_clean, "error": "Query too short/no keywords",
                "recommended_tools": [], "confidence": 0.0}

    # Score tools by keyword match count
    tool_scores: dict[str, int] = defaultdict(int)
    for token in query_tokens:
        for tool in tool_index.get(token, set()):
            tool_scores[tool] += 1

    if not tool_scores:
        return {"query": query_clean, "detected_intent": "no_match",
                "recommended_tools": [], "confidence": 0.0,
                "routing_reason": "No tools matched query keywords"}

    sorted_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)
    top_tool, top_score = sorted_tools[0]
    confidence = round(min(top_score / len(query_tokens), 1.0), 2)

    return {
        "query": query_clean,
        "detected_intent": "auto",
        "recommended_tools": [top_tool],
        "alternative_tools": [t for t, _ in sorted_tools[1:4]],
        "confidence": confidence,
        "routing_reason": f"Matched {top_score}/{len(query_tokens)} keywords",
        "match_breakdown": {t: s for t, s in sorted_tools[:5]},
    }


async def research_route_batch(queries: list[str]) -> dict[str, Any]:
    """Route multiple queries with aggregated statistics."""
    if not queries or not isinstance(queries, list):
        return {"error": "Queries must be non-empty list", "routes": [], "total_queries": 0}

    routes, tool_counts = [], {}
    for query in queries:
        if isinstance(query, str) and query.strip():
            route = await research_route_query(query)
            routes.append(route)
            for tool in route.get("recommended_tools", []):
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

    top_tool = max(tool_counts, key=tool_counts.get) if tool_counts else "mixed"
    return {
        "routes": routes,
        "tool_distribution": dict(sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)),
        "total_queries": len(routes),
        "recommendation_summary": f"Routed {len(routes)} queries to {len(tool_counts)} tools. Most: {top_tool}",
    }


async def research_router_rebuild() -> dict[str, Any]:
    """Force rebuild tool index (call when new tools added)."""
    global _TOOL_INDEX
    async with _INDEX_LOCK:
        _TOOL_INDEX = {}
    idx = _get_tool_index()
    return {
        "status": "rebuilt",
        "keywords": len(idx),
        "tool_references": sum(len(v) for v in idx.values()),
        "message": f"Index rebuilt with {len(idx)} keywords",
    }
