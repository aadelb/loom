"""Tool discovery service for Loom MCP server.

Provides rich API endpoints for users to discover, search, browse,
and understand all 923+ tools, their parameters, capabilities,
and example usage.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.tool_discovery")

_catalog: dict[str, Any] | None = None
_search_index: list[tuple[str, str, str]] | None = None  # (name, text, category)

CATEGORY_LABELS = {
    "search_scraping": "Search & Web Scraping",
    "llm": "LLM & AI",
    "adversarial": "Adversarial & Red Team",
    "security": "Security & Vulnerability",
    "osint": "OSINT & Intelligence",
    "contact_intelligence": "Contact Intelligence",
    "legal": "Legal & Compliance",
    "infrastructure": "Infrastructure & Monitoring",
    "privacy": "Privacy & Anti-Forensics",
    "career": "Career Intelligence",
    "crypto": "Cryptocurrency & Blockchain",
    "github": "GitHub & Code",
    "orchestration": "Orchestration & Pipelines",
    "research": "Research & Analysis",
    "other": "Other",
}

TASK_KEYWORDS: dict[str, list[str]] = {
    "search_scraping": [
        "search", "scrape", "fetch", "crawl", "spider", "download",
        "web", "url", "page", "site", "browse", "extract html",
    ],
    "llm": [
        "llm", "ai", "gpt", "chat", "summarize", "translate", "classify",
        "embed", "generate", "prompt", "model", "ask", "answer",
    ],
    "adversarial": [
        "attack", "jailbreak", "red team", "reframe", "bypass", "hcs",
        "stealth", "adversarial", "prompt injection", "safety test",
    ],
    "security": [
        "cve", "vulnerability", "pentest", "security", "ssl", "cert",
        "whois", "dns", "port scan", "header", "exploit",
    ],
    "osint": [
        "osint", "recon", "intelligence", "sherlock", "maigret", "shodan",
        "threat", "investigate", "tracking", "surveillance",
    ],
    "contact_intelligence": [
        "email", "phone", "contact", "verify email", "lookup phone",
        "holehe", "person", "find contact",
    ],
    "legal": [
        "uae", "dubai", "labor law", "visa", "rera", "trade license",
        "legal", "compliance", "regulation",
    ],
    "infrastructure": [
        "health", "monitor", "metric", "config", "cache", "backup",
        "deploy", "status", "scheduler", "billing", "audit",
    ],
    "privacy": [
        "privacy", "fingerprint", "steganography", "forensic", "anonymous",
        "anti-forensic", "usb", "wipe", "tracking",
    ],
    "career": [
        "career", "job", "salary", "resume", "interview", "hiring",
        "linkedin", "company", "employer",
    ],
    "crypto": [
        "crypto", "bitcoin", "ethereum", "blockchain", "wallet", "token",
        "defi", "nft", "transaction",
    ],
    "github": [
        "github", "repo", "code search", "commit", "pull request",
        "issue", "git", "repository",
    ],
    "orchestration": [
        "pipeline", "orchestrate", "workflow", "chain", "batch",
        "smart", "brain", "automate", "multi-step",
    ],
    "research": [
        "research", "analyze", "fact check", "knowledge", "pdf",
        "rss", "text analysis", "sentiment", "citation",
    ],
}


def _load_catalog() -> dict[str, Any]:
    global _catalog, _search_index
    if _catalog is not None:
        return _catalog

    catalog_paths = [
        Path("/opt/loom-v3/docs/TOOL_CATALOG.json"),
        Path(__file__).parent.parent.parent / "docs" / "TOOL_CATALOG.json",
    ]

    for path in catalog_paths:
        if path.exists():
            with open(path) as f:
                _catalog = json.load(f)
            log.info("tool_catalog_loaded path=%s tools=%d", path, len(_catalog.get("tools", {})))
            _build_search_index()
            return _catalog

    log.warning("tool_catalog_not_found checked=%s", [str(p) for p in catalog_paths])
    _catalog = {"tools": {}, "metadata": {}}
    return _catalog


def _build_search_index() -> None:
    global _search_index
    if _catalog is None:
        return
    _search_index = []
    for name, t in _catalog.get("tools", {}).items():
        desc = t.get("description", "")
        params = " ".join(t.get("parameters", {}).keys())
        returns = t.get("returns", "")
        text = f"{name} {desc} {params} {returns}".lower()
        category = t.get("category", "other")
        _search_index.append((name, text, category))


def _score_match(query_terms: list[str], text: str) -> float:
    score = 0.0
    for term in query_terms:
        if term in text:
            score += 1.0
            if text.startswith(term) or f" {term}" in text:
                score += 0.5
    return score


def get_overview() -> dict[str, Any]:
    """High-level overview of all available tools and capabilities."""
    cat = _load_catalog()
    tools = cat.get("tools", {})

    by_category: dict[str, int] = defaultdict(int)
    async_count = 0
    total_params = 0

    for t in tools.values():
        by_category[t.get("category", "other")] += 1
        if t.get("async"):
            async_count += 1
        total_params += len(t.get("parameters", {}))

    categories = []
    for cat_id in sorted(by_category, key=lambda c: -by_category[c]):
        categories.append({
            "id": cat_id,
            "label": CATEGORY_LABELS.get(cat_id, cat_id.replace("_", " ").title()),
            "tool_count": by_category[cat_id],
        })

    return {
        "service": "Loom MCP Research Server",
        "total_tools": len(tools),
        "total_parameters": total_params,
        "async_tools": async_count,
        "sync_tools": len(tools) - async_count,
        "categories": categories,
        "api_base": "/api/v1",
        "endpoints": {
            "overview": "GET /api/v1/discover",
            "search": "GET /api/v1/discover/search?q=<query>&limit=20",
            "categories": "GET /api/v1/discover/categories",
            "category_detail": "GET /api/v1/discover/category/<name>",
            "tool_detail": "GET /api/v1/discover/tool/<name>",
            "suggest": "GET /api/v1/discover/suggest?task=<description>",
            "examples": "GET /api/v1/discover/examples/<name>",
        },
        "quick_start": {
            "search_web": {
                "tool": "research_search",
                "call": "POST /api/v1/tools/research_search",
                "body": {"query": "your search query", "n": 10},
            },
            "fetch_url": {
                "tool": "research_fetch",
                "call": "POST /api/v1/tools/research_fetch",
                "body": {"url": "https://example.com"},
            },
            "ask_llm": {
                "tool": "research_llm_chat",
                "call": "POST /api/v1/tools/research_llm_chat",
                "body": {"messages": [{"role": "user", "content": "Hello"}]},
            },
        },
    }


def search_tools(query: str, limit: int = 20, category: str | None = None) -> dict[str, Any]:
    """Full-text search across tool names, descriptions, and parameters."""
    _load_catalog()
    if _search_index is None:
        return {"query": query, "results": [], "total": 0}

    query_lower = query.lower().strip()
    terms = query_lower.split()

    scored: list[tuple[float, str]] = []
    for name, text, cat in _search_index:
        if category and cat != category:
            continue

        score = _score_match(terms, text)

        if query_lower in name:
            score += 3.0
        if name.startswith(f"research_{query_lower}"):
            score += 2.0

        ratio = SequenceMatcher(None, query_lower, name.replace("research_", "")).ratio()
        score += ratio * 1.5

        if score > 0.3:
            scored.append((score, name))

    scored.sort(key=lambda x: -x[0])
    top = scored[:limit]

    tools = _catalog.get("tools", {}) if _catalog else {}
    results = []
    for score, name in top:
        t = tools.get(name, {})
        params = t.get("parameters", {})
        required = [p for p, info in params.items() if info.get("required")]
        results.append({
            "name": name,
            "description": t.get("description", "")[:200],
            "category": CATEGORY_LABELS.get(t.get("category", ""), t.get("category", "")),
            "required_params": required,
            "param_count": len(params),
            "is_async": t.get("async", False),
            "relevance_score": round(score, 2),
        })

    return {
        "query": query,
        "results": results,
        "total": len(results),
        "searched": len(_search_index),
    }


def list_categories() -> dict[str, Any]:
    """List all tool categories with descriptions and representative tools."""
    cat = _load_catalog()
    tools = cat.get("tools", {})

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, t in sorted(tools.items()):
        by_category[t.get("category", "other")].append({"name": name, "description": t.get("description", "")[:120]})

    categories = []
    for cat_id in sorted(by_category, key=lambda c: -len(by_category[c])):
        tool_list = by_category[cat_id]
        categories.append({
            "id": cat_id,
            "label": CATEGORY_LABELS.get(cat_id, cat_id.replace("_", " ").title()),
            "tool_count": len(tool_list),
            "sample_tools": [t["name"] for t in tool_list[:5]],
            "keywords": TASK_KEYWORDS.get(cat_id, []),
        })

    return {"categories": categories, "total_categories": len(categories)}


def get_category_tools(category_id: str) -> dict[str, Any]:
    """Get all tools in a category with summaries."""
    cat = _load_catalog()
    tools = cat.get("tools", {})

    matching = []
    for name, t in sorted(tools.items()):
        if t.get("category", "other") == category_id:
            params = t.get("parameters", {})
            required = [p for p, info in params.items() if info.get("required")]
            matching.append({
                "name": name,
                "description": t.get("description", "")[:200],
                "required_params": required,
                "optional_params": [p for p in params if p not in required],
                "is_async": t.get("async", False),
            })

    return {
        "category": category_id,
        "label": CATEGORY_LABELS.get(category_id, category_id.replace("_", " ").title()),
        "tool_count": len(matching),
        "tools": matching,
    }


def get_tool_detail(tool_name: str) -> dict[str, Any]:
    """Deep detail for a single tool: params, types, defaults, examples, output schema."""
    cat = _load_catalog()
    tools = cat.get("tools", {})

    if tool_name not in tools:
        close = _find_similar_names(tool_name, list(tools.keys()), max_results=5)
        return {"error": f"Tool '{tool_name}' not found", "did_you_mean": close}

    t = tools[tool_name]
    params = t.get("parameters", {})
    test_params = t.get("test_params", {})
    output = t.get("output_sample") or {}

    param_details = []
    for pname, pinfo in params.items():
        detail: dict[str, Any] = {
            "name": pname,
            "type": pinfo.get("type", "str"),
            "required": pinfo.get("required", False),
            "default": pinfo.get("default"),
            "description": pinfo.get("description", t.get("args_documentation", {}).get(pname, "")),
        }
        if pname in test_params:
            detail["example_value"] = test_params[pname]
        param_details.append(detail)

    curl_body = json.dumps(test_params, default=str) if test_params else "{}"
    curl_example = (
        f"curl -X POST http://127.0.0.1:8788/api/v1/tools/{tool_name} \\\n"
        f"  -H 'Content-Type: application/json' \\\n"
        f"  -d '{curl_body}'"
    )

    mcp_example = {
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": test_params},
    }

    related = _find_related_tools(tool_name, t.get("category", "other"), t.get("description", ""))

    result: dict[str, Any] = {
        "name": tool_name,
        "description": t.get("description", ""),
        "full_docstring": t.get("full_docstring", ""),
        "category": t.get("category", "other"),
        "category_label": CATEGORY_LABELS.get(t.get("category", ""), ""),
        "is_async": t.get("async", False),
        "parameters": param_details,
        "required_params": [p["name"] for p in param_details if p["required"]],
        "optional_params": [p["name"] for p in param_details if not p["required"]],
        "example_call": {
            "rest_api": curl_example,
            "mcp": mcp_example,
            "test_params": test_params,
        },
        "returns": t.get("returns", ""),
        "related_tools": related,
    }

    if output:
        result["output_info"] = {
            "tested": output.get("success", False),
            "output_keys": output.get("output_keys", []),
            "output_schema": output.get("output_schema", {}),
        }

    return result


def get_tool_examples(tool_name: str) -> dict[str, Any]:
    """Get example calls and expected output for a tool."""
    cat = _load_catalog()
    tools = cat.get("tools", {})

    if tool_name not in tools:
        close = _find_similar_names(tool_name, list(tools.keys()), max_results=5)
        return {"error": f"Tool '{tool_name}' not found", "did_you_mean": close}

    t = tools[tool_name]
    params = t.get("parameters", {})
    test_params = t.get("test_params", {})
    output = t.get("output_sample") or {}

    examples = []

    if test_params:
        examples.append({
            "label": "Basic call with test parameters",
            "params": test_params,
            "curl": (
                f"curl -X POST http://127.0.0.1:8788/api/v1/tools/{tool_name} "
                f"-H 'Content-Type: application/json' "
                f"-d '{json.dumps(test_params, default=str)}'"
            ),
        })

    required = {p: info for p, info in params.items() if info.get("required")}
    if required:
        minimal = {}
        for pname, pinfo in required.items():
            if pname in test_params:
                minimal[pname] = test_params[pname]
            else:
                minimal[pname] = _default_for_type(pinfo.get("type", "str"))
        examples.append({
            "label": "Minimal call (required params only)",
            "params": minimal,
            "curl": (
                f"curl -X POST http://127.0.0.1:8788/api/v1/tools/{tool_name} "
                f"-H 'Content-Type: application/json' "
                f"-d '{json.dumps(minimal, default=str)}'"
            ),
        })

    result: dict[str, Any] = {
        "name": tool_name,
        "examples": examples,
        "parameter_guide": [],
    }

    for pname, pinfo in params.items():
        guide_entry: dict[str, Any] = {
            "param": pname,
            "type": pinfo.get("type", "str"),
            "required": pinfo.get("required", False),
        }
        if pinfo.get("default") is not None:
            guide_entry["default"] = pinfo["default"]
        desc = pinfo.get("description", "")
        if desc:
            guide_entry["description"] = desc
        if pname in test_params:
            guide_entry["example"] = test_params[pname]
        result["parameter_guide"].append(guide_entry)

    if output and output.get("success"):
        result["expected_output"] = {
            "keys": output.get("output_keys", []),
            "schema": output.get("output_schema", {}),
        }

    return result


def suggest_tools(task: str, limit: int = 10) -> dict[str, Any]:
    """Given a user task description, suggest the best tools to use."""
    _load_catalog()
    if _catalog is None:
        return {"task": task, "suggestions": []}

    task_lower = task.lower().strip()
    tools = _catalog.get("tools", {})

    category_scores: dict[str, float] = defaultdict(float)
    for cat_id, keywords in TASK_KEYWORDS.items():
        for kw in keywords:
            if kw in task_lower:
                category_scores[cat_id] += 1.0

    top_categories = sorted(category_scores, key=lambda c: -category_scores[c])[:3]

    candidates: list[tuple[float, str, dict[str, Any]]] = []
    task_terms = task_lower.split()

    for name, t in tools.items():
        score = 0.0
        cat = t.get("category", "other")
        desc = t.get("description", "").lower()

        if cat in top_categories:
            score += category_scores[cat] * 2.0

        for term in task_terms:
            if len(term) < 3:
                continue
            if term in name:
                score += 3.0
            if term in desc:
                score += 1.0

        clean_name = name.replace("research_", "").replace("_", " ")
        for term in task_terms:
            if len(term) >= 3 and term in clean_name:
                score += 2.0

        if score > 1.0:
            params = t.get("parameters", {})
            required = [p for p, info in params.items() if info.get("required")]
            candidates.append((score, name, {
                "name": name,
                "description": t.get("description", "")[:200],
                "category": CATEGORY_LABELS.get(cat, cat),
                "required_params": required,
                "relevance_score": round(score, 1),
                "how_to_call": f"POST /api/v1/tools/{name}",
                "example_body": t.get("test_params", {}),
            }))

    candidates.sort(key=lambda x: -x[0])
    suggestions = [c[2] for c in candidates[:limit]]

    return {
        "task": task,
        "suggestions": suggestions,
        "matched_categories": [
            {"id": c, "label": CATEGORY_LABELS.get(c, c), "score": round(category_scores[c], 1)}
            for c in top_categories if category_scores.get(c, 0) > 0
        ],
        "tip": "Use GET /api/v1/discover/tool/<name> for full details on any suggested tool.",
    }


def _find_similar_names(query: str, names: list[str], max_results: int = 5) -> list[str]:
    scored = []
    q = query.lower().replace("research_", "")
    for name in names:
        n = name.replace("research_", "")
        ratio = SequenceMatcher(None, q, n).ratio()
        if ratio > 0.4 or q in n:
            scored.append((ratio + (1.0 if q in n else 0.0), name))
    scored.sort(key=lambda x: -x[0])
    return [name for _, name in scored[:max_results]]


def _find_related_tools(tool_name: str, category: str, description: str) -> list[str]:
    if _catalog is None:
        return []
    tools = _catalog.get("tools", {})
    base = tool_name.replace("research_", "")
    parts = set(base.split("_"))
    related = []

    for name, t in tools.items():
        if name == tool_name:
            continue
        if t.get("category") == category:
            other_base = name.replace("research_", "")
            other_parts = set(other_base.split("_"))
            overlap = len(parts & other_parts)
            if overlap >= 1:
                related.append((overlap, name))

    related.sort(key=lambda x: -x[0])
    return [name for _, name in related[:8]]


def _default_for_type(type_str: str) -> Any:
    type_lower = type_str.lower()
    if "int" in type_lower:
        return 5
    if "float" in type_lower:
        return 0.5
    if "bool" in type_lower:
        return True
    if "list" in type_lower:
        return ["example"]
    if "dict" in type_lower:
        return {}
    return "example"
