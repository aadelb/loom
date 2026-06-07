"""Tool RAG — Dynamic tool retrieval by semantic query.

With 1006 tools, you can't pass all schemas to an LLM. This tool
takes a natural language query and returns the top-K most relevant
tools using keyword matching and description similarity.

From Gemini's recommendation: "You cannot pass 1000 tool schemas in
a single LLM context window. You need a semantic search mechanism to
retrieve and inject only the top-K relevant tools per query."

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
import re
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.tool_rag")

_TOOL_CATEGORIES = {
    "price": ["price_extract", "price_compare", "price_live", "price_history", "uae_price", "moet_prices"],
    "security": ["pentest", "vulnerability", "exploit", "cve", "bandit", "security", "owasp"],
    "social": ["facebook", "linkedin", "twitter", "instagram", "social", "sherlock", "maigret"],
    "research": ["deep", "search", "fetch", "spider", "markdown", "github"],
    "llm": ["llm_answer", "llm_chat", "llm_query", "prompt_reframe", "auto_reframe"],
    "scoring": ["hcs_score", "stealth_score", "executability", "quality", "attack_score"],
    "adversarial": ["jailbreak", "bypass", "reframe", "crescendo", "daisy_chain", "full_spectrum"],
    "osint": ["osint", "sherlock", "maigret", "holehe", "breach", "leak"],
    "dark": ["tor", "darkweb", "onion", "ahmia", "dark_forum"],
    "infrastructure": ["billing", "webhook", "workflow", "pipeline", "deploy"],
}


_TOOL_CACHE: dict[str, str] = {}


async def _get_all_tools() -> dict[str, str]:
    """Get tool names by scanning registered functions in server modules."""
    global _TOOL_CACHE
    if _TOOL_CACHE:
        return _TOOL_CACHE

    try:
        import importlib
        from pathlib import Path
        tool_dir = Path(__file__).parent.parent / "tools"
        for py_file in tool_dir.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                content = py_file.read_text(errors="ignore")[:5000]
                funcs = re.findall(r'async def (research_\w+)\(', content)
                for func_name in funcs:
                    doc_match = re.search(rf'async def {func_name}\([^)]*\)[^:]*:\s*"""([^"]+)', content)
                    doc = doc_match.group(1)[:150] if doc_match else ""
                    _TOOL_CACHE[func_name] = doc
            except Exception:
                pass
    except Exception:
        pass

    if not _TOOL_CACHE:
        for cat, tools in _TOOL_CATEGORIES.items():
            for t in tools:
                _TOOL_CACHE[f"research_{t}"] = f"{cat} tool"

    return _TOOL_CACHE


def _score_tool_relevance(query: str, tool_name: str, description: str) -> float:
    """Score how relevant a tool is to a query using keyword matching."""
    query_lower = query.lower()
    name_lower = tool_name.lower()
    desc_lower = description.lower()

    score = 0.0

    query_words = set(re.findall(r'\w+', query_lower))
    name_words = set(re.findall(r'\w+', name_lower))
    desc_words = set(re.findall(r'\w+', desc_lower))

    name_overlap = query_words & name_words
    score += len(name_overlap) * 3.0

    desc_overlap = query_words & desc_words
    score += len(desc_overlap) * 1.0

    for category, keywords in _TOOL_CATEGORIES.items():
        if any(kw in query_lower for kw in keywords):
            if any(kw in name_lower for kw in keywords):
                score += 5.0
                break

    if any(w in name_lower for w in query_words):
        score += 2.0

    return score


@handle_tool_errors("research_tool_recommend")
async def research_tool_recommend(
    query: str,
    top_k: int = 10,
    include_descriptions: bool = True,
) -> dict[str, Any]:
    """Find the most relevant Loom tools for a given task/query.

    Searches 1006 tools by keyword matching and category detection.
    Returns top-K most relevant tools with descriptions.

    Use this when you need to know which Loom tool to use for a task.

    Args:
        query: Natural language description of what you want to do.
        top_k: Number of tools to return (default 10, max 50).
        include_descriptions: Include tool descriptions (default True).

    Returns:
        Dict with query, matched tools ranked by relevance,
        detected categories, and total tools searched.
    """
    top_k = min(max(1, top_k), 50)

    all_tools = await _get_all_tools()
    if not all_tools:
        return {"error": "Could not fetch tool list", "query": query}

    scored = []
    for name, desc in all_tools.items():
        score = _score_tool_relevance(query, name, desc)
        if score > 0:
            scored.append((name, desc, score))

    scored.sort(key=lambda x: -x[2])

    detected_categories = []
    query_lower = query.lower()
    for cat, keywords in _TOOL_CATEGORIES.items():
        if any(kw in query_lower for kw in keywords):
            detected_categories.append(cat)

    results = []
    for name, desc, score in scored[:top_k]:
        entry = {"tool": name, "relevance": round(score, 1)}
        if include_descriptions:
            entry["description"] = desc[:150]
        results.append(entry)

    return {
        "query": query[:200],
        "total_tools_searched": len(all_tools),
        "matches_found": len(scored),
        "detected_categories": detected_categories,
        "recommended_tools": results,
    }
