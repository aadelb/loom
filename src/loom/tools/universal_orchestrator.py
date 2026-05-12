"""Universal Smart Orchestrator — Auto-discovers and executes optimal tools."""
from __future__ import annotations

import ast
import asyncio
import importlib
import inspect
import logging
import re
import time
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.universal_orchestrator")
_TOOL_INDEX: dict[str, dict[str, Any]] | None = None
_INDEX_BUILD_TIME: float = 0.0

# Import smart_router with fallback
try:
    from . import smart_router

    _SMART_ROUTER_AVAILABLE = True
except ImportError:
    _SMART_ROUTER_AVAILABLE = False
    logger.warning("smart_router not available; orchestrator will skip router pre-filter")

# Import semantic_router with fallback
try:
    from . import semantic_router

    _SEMANTIC_ROUTER_AVAILABLE = True
except ImportError:
    _SEMANTIC_ROUTER_AVAILABLE = False
    logger.warning("semantic_router not available; orchestrator will skip semantic pre-filter")

# Import tool_discovery with fallback
try:
    from . import tool_discovery

    _TOOL_DISCOVERY_AVAILABLE = True
except ImportError:
    _TOOL_DISCOVERY_AVAILABLE = False
    logger.warning("tool_discovery not available; orchestrator will skip follow-up suggestions")

# Import capability_matrix with fallback
try:
    from . import capability_matrix

    _CAPABILITY_MATRIX_AVAILABLE = True
except ImportError:
    _CAPABILITY_MATRIX_AVAILABLE = False
    logger.warning("capability_matrix not available; orchestrator will skip capability boost")


def _build_tool_index() -> dict[str, dict[str, Any]]:
    """Scan tools directory and build index of all research_* functions."""
    global _TOOL_INDEX, _INDEX_BUILD_TIME
    if _TOOL_INDEX is not None and (time.time() - _INDEX_BUILD_TIME) < 3600:
        return _TOOL_INDEX
    _TOOL_INDEX = {}
    for tool_file in sorted(Path(__file__).parent.glob("*.py")):
        if tool_file.name.startswith("_"):
            continue
        try:
            tree = ast.parse(tool_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("research_"):
                    docstring = (ast.get_docstring(node) or "").split("\n")[0]
                    params = [
                        arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")
                    ]
                    _TOOL_INDEX[node.name] = {
                        "module": tool_file.stem,
                        "docstring": docstring,
                        "params": params,
                        "is_async": True,
                    }
        except Exception as e:
            logger.debug("parse_error module=%s error=%s", tool_file.stem, str(e))
    _INDEX_BUILD_TIME = time.time()
    return _TOOL_INDEX


def _infer_query_category(query: str) -> str:
    """Infer primary category from query keywords.

    Maps query keywords to tool categories (fetch, search, analyze, generate, etc.)
    Returns the most likely category based on keyword matches.
    """
    query_lower = query.lower()

    category_keywords = {
        "fetch": ["fetch", "scrape", "download", "extract", "crawl", "pull"],
        "search": ["search", "find", "look for", "discover", "query", "seek"],
        "analyze": [
            "analyze",
            "analyze",
            "detect",
            "check",
            "assess",
            "evaluate",
            "score",
            "profile",
        ],
        "generate": ["generate", "create", "synthesize", "compose", "write", "build"],
        "adversarial": ["attack", "jailbreak", "exploit", "bypass", "reframe", "manipulate"],
        "monitor": ["monitor", "track", "watch", "drift", "pressure", "detect change"],
        "output": ["report", "export", "render", "format", "dashboard", "display"],
        "llm": ["llm", "model", "embedding", "summarize", "translate", "chat"],
        "transform": ["transform", "convert", "encode", "decode", "parse", "process"],
        "infrastructure": ["config", "session", "cache", "deploy", "health", "auth"],
    }

    best_category = "search"  # default fallback
    max_matches = 0

    for category, keywords in category_keywords.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        if matches > max_matches:
            max_matches = matches
            best_category = category

    return best_category


async def _build_capability_boost_map(category: str) -> dict[str, float]:
    """Build a map of tool -> boost_factor based on capability matrix ratings.

    Args:
        category: The inferred query category (e.g., 'search', 'analyze')

    Returns:
        Dict mapping tool names to boost factors (0-3)
    """
    if not _CAPABILITY_MATRIX_AVAILABLE:
        return {}

    try:
        matrix = await capability_matrix.research_capability_matrix(category=category)
        boost_map: dict[str, float] = {}

        tools_in_category = matrix.get("matrix", [])
        for tool_info in tools_in_category:
            tool_name = tool_info.get("tool", "")
            if not tool_name:
                continue

            # Boost based on category match (tools in their primary category get +3)
            if tool_info.get("category") == category:
                boost_map[tool_name] = 3.0
            # Tools with similar capabilities get +1.5
            else:
                boost_map[tool_name] = 1.5

        logger.debug(
            "capability_boost_map category=%s tools_boosted=%d", category, len(boost_map)
        )
        return boost_map
    except Exception as e:
        logger.warning("capability_boost_map failed: %s", str(e))
        return {}


def _score_tool_relevance(query: str, tool_name: str, tool_info: dict[str, Any]) -> float:
    """Score tool relevance: name_matches * 3 + docstring_matches."""
    keywords = re.findall(r"\b\w{3,}\b", query.lower())
    name_lower = tool_name.lower().replace("research_", "")
    name_score = sum(3 for kw in keywords if kw in name_lower)
    docstring_lower = tool_info.get("docstring", "").lower()
    return min(100, name_score + sum(1 for kw in keywords if kw in docstring_lower))


async def _auto_generate_params(
    tool_name: str, tool_info: dict[str, Any], query: str
) -> dict[str, Any]:
    """Auto-generate minimal parameters for tool."""
    params: dict[str, Any] = {}
    url = re.search(r"https?://[^\s]+|www\.[^\s]+", query)
    for param in tool_info.get("params", []):
        if param in ("query", "prompt", "text", "input_text"):
            params[param] = query
        elif param == "url" and url:
            params[param] = url.group(0)
        elif param == "tool_name":
            params[param] = tool_name
    return params


async def _execute_tool(
    tool_name: str, tool_info: dict[str, Any], params: dict[str, Any], timeout_sec: float = 10.0
) -> dict[str, Any]:
    """Dynamically import and execute a single tool."""
    start_time = time.time()
    try:
        module = importlib.import_module(f"loom.tools.{tool_info['module']}")
        tool_func = getattr(module, tool_name, None)
        if tool_func is None:
            return {
                "tool": tool_name,
                "success": False,
                "error": "tool_not_found",
                "duration_ms": (time.time() - start_time) * 1000,
            }
        result = (
            await asyncio.wait_for(tool_func(**params), timeout=timeout_sec)
            if inspect.iscoroutinefunction(tool_func)
            else await asyncio.to_thread(tool_func, **params)
        )
        return {
            "tool": tool_name,
            "success": True,
            "result": result,
            "duration_ms": (time.time() - start_time) * 1000,
        }
    except asyncio.TimeoutError:
        return {
            "tool": tool_name,
            "success": False,
            "error": f"timeout {timeout_sec}s",
            "duration_ms": (time.time() - start_time) * 1000,
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "success": False,
            "error": f"{type(e).__name__}: {str(e)[:100]}",
            "duration_ms": (time.time() - start_time) * 1000,
        }


_ORCHESTRATOR_BLACKLIST = frozenset(
    {
        "research_orchestrate_smart",
        "research_do_expert",
        "research_full_pipeline",
        "research_semantic_route",
        "research_semantic_batch_route",
        "research_semantic_router_rebuild",
    }
)

@handle_tool_errors("research_orchestrate_smart")

async def research_orchestrate_smart(
    query: str, max_tools: int = 3, strategy: str = "auto"
) -> dict[str, Any]:
    """Auto-discover, score, and execute optimal tools for ANY query.

    Uses semantic similarity (60%) combined with keyword matching (40%) for
    intelligent tool selection. Falls back gracefully if semantic embeddings
    unavailable.

    Args:
        query: Natural language query (min 3 chars)
        max_tools: Maximum number of tools to select (1-25)
        strategy: "auto" (pick 1), "parallel" (top-K), or "sequential"

    Returns:
        Dict with query, tools_discovered, tools_selected, results, aggregated_summary,
        router_confidence, inferred_category, capability_boosts_applied, suggested_next_tools,
        semantic_scores, total_duration_ms
    """
    if not query or len(query.strip()) < 3:
        return {"error": "query too short (min 3 chars)", "query": query}
    max_tools = max(1, min(max_tools, 25))
    total_start = time.time()

    tool_index = _build_tool_index()
    if not tool_index:
        return {
            "error": "no_tools_discovered",
            "query": query,
            "total_duration_ms": (time.time() - total_start) * 1000,
        }

    # Infer query category for capability matrix
    inferred_category = _infer_query_category(query)

    # Build capability boost map from matrix
    capability_boost_map = await _build_capability_boost_map(inferred_category)

    # Step 1: Semantic pre-filtering (initial candidates via embeddings)
    semantic_scores: dict[str, float] = {}
    semantic_candidates: set[str] = set()
    semantic_embedding_method = "none"
    if _SEMANTIC_ROUTER_AVAILABLE:
        try:
            semantic_result = await semantic_router.research_semantic_route(query, top_k=10)
            semantic_embedding_method = semantic_result.get("embedding_method", "none")
            recommended = semantic_result.get("recommended_tools", [])
            for tool_info in recommended:
                tool_name = tool_info.get("tool", "")
                similarity = tool_info.get("similarity", 0.0)
                if tool_name:
                    semantic_scores[tool_name] = similarity
                    semantic_candidates.add(tool_name)
            logger.debug(
                "semantic_prefilter query=%s method=%s candidates=%d",
                query[:50],
                semantic_embedding_method,
                len(semantic_candidates),
            )
        except Exception as e:
            logger.warning("semantic_router prefilter failed: %s", str(e))

    # Step 2: Smart keyword routing (alternative pre-filtering)
    router_confidence = 0.0
    router_candidates: set[str] = set()
    if _SMART_ROUTER_AVAILABLE and not semantic_candidates:
        try:
            route_result = await smart_router.research_route_query(query)
            router_confidence = route_result.get("confidence", 0.0)
            router_candidates = set(route_result.get("recommended_tools", []))
            router_candidates.update(route_result.get("alternative_tools", []))
            logger.debug(
                "router_prefilter query=%s confidence=%.2f candidates=%d",
                query[:50],
                router_confidence,
                len(router_candidates),
            )
        except Exception as e:
            logger.warning("smart_router prefilter failed: %s", str(e))

    # Determine effective candidates (prefer semantic, fallback to keyword)
    effective_candidates = semantic_candidates or router_candidates

    # Score all tools with base relevance
    scored = [
        (n, _score_tool_relevance(query, n, i), i)
        for n, i in tool_index.items()
        if n not in _ORCHESTRATOR_BLACKLIST
    ]

    # Apply semantic similarity boost: 60% semantic score normalized to 0-10
    if semantic_scores:
        scored = [
            (n, s + (semantic_scores.get(n, 0.0) * 10 * 0.6), i) for n, s, i in scored
        ]

    # Apply keyword-based router bonus: +2 for candidates (40% weight equivalent)
    if effective_candidates and (router_confidence > 0.7 or semantic_candidates):
        scored = [
            (n, s + (2 if n in effective_candidates else 0), i) for n, s, i in scored
        ]

    # Apply capability boost: +0 to +3 for tools in optimal category
    if capability_boost_map:
        scored = [(n, s + capability_boost_map.get(n, 0), i) for n, s, i in scored]

    scored = sorted([(n, s, i) for n, s, i in scored if s > 0], key=lambda x: x[1], reverse=True)

    selected_count = 1 if strategy == "auto" else min(max_tools, len(scored))
    selected = scored[:selected_count]

    if not selected:
        return {
            "query": query,
            "tools_discovered": len(tool_index),
            "tools_selected": [],
            "results": [],
            "warning": "no_relevant_tools_found",
            "router_confidence": router_confidence,
            "inferred_category": inferred_category,
            "capability_boosts_applied": len(capability_boost_map),
            "semantic_scores": semantic_scores,
            "semantic_embedding_method": semantic_embedding_method,
            "total_duration_ms": (time.time() - total_start) * 1000,
        }

    selections = [
        {
            "name": n,
            "relevance_score": s,
            "params_used": await _auto_generate_params(n, i, query),
        }
        for n, s, i in selected
    ]

    tasks = [
        _execute_tool(s["name"], tool_index[s["name"]], s["params_used"]) for s in selections
    ]
    results = (
        await asyncio.gather(*tasks, return_exceptions=True)
        if strategy == "parallel"
        else [await t for t in tasks]
    )
    results = [
        r if isinstance(r, dict) else {"tool": "unknown", "success": False, "error": str(r)}
        for r in results
    ]

    successful = [r for r in results if r.get("success")]

    # Discover follow-up tools
    suggested_next_tools: list[str] = []
    if _TOOL_DISCOVERY_AVAILABLE:
        try:
            discover_result = await tool_discovery.research_discover(query=query, detailed=False)
            tools_list = (
                discover_result.get("tools", []) if isinstance(discover_result, dict) else []
            )
            suggested_next_tools = [
                t.get("name", "") for t in tools_list[:5] if t.get("name")
            ][:5]
            logger.debug("discovery suggested %d follow-up tools", len(suggested_next_tools))
        except Exception as e:
            logger.debug("tool_discovery failed: %s", str(e))

    return {
        "query": query,
        "tools_discovered": len(tool_index),
        "tools_selected": selections,
        "results": results,
        "aggregated_summary": {
            "total_executed": len(results),
            "total_succeeded": len(successful),
            "total_failed": len(results) - len(successful),
            "execution_strategy": strategy,
        },
        "router_confidence": router_confidence,
        "inferred_category": inferred_category,
        "capability_boosts_applied": len(capability_boost_map),
        "semantic_scores": semantic_scores,
        "semantic_embedding_method": semantic_embedding_method,
        "suggested_next_tools": suggested_next_tools,
        "total_duration_ms": (time.time() - total_start) * 1000,
    }
