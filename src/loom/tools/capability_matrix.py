"""Tool Capability Matrix — Analyze and query 220+ tools by input/output type."""

from __future__ import annotations

import ast
import asyncio
import logging
import pathlib
from typing import Any

logger = logging.getLogger("loom.tools.capability_matrix")

# Module-level cache: populated on first query
_MATRIX_CACHE: dict[str, Any] | None = None
_MATRIX_LOCK = asyncio.Lock()

_CATEGORIES_MAP = {
    "fetch": ["fetch", "spider", "scrape", "stealth", "camoufox", "botasaurus"],
    "search": ["search", "deep", "query", "semantic"],
    "analyze": ["score", "detect", "check", "analyze", "assess", "profile", "audit"],
    "generate": ["generate", "create", "synthesize", "compose", "extract"],
    "adversarial": ["reframe", "attack", "jailbreak", "exploit", "craft", "bypass"],
    "monitor": ["monitor", "track", "watch", "drift", "pressure", "alert"],
    "output": ["export", "report", "render", "format", "dashboard"],
    "llm": ["llm", "model", "embed", "summarize", "translate", "chat"],
    "transform": ["transform", "convert", "encode", "decode", "parse"],
    "infrastructure": ["config", "session", "cache", "deploy", "health", "auth"],
}

_INPUT_MAPPINGS = {
    "url": "url",
    "urls": "url",
    "query": "text",
    "prompt": "text",
    "text": "text",
    "message": "text",
    "model": "model_name",
    "provider": "provider",
    "data": "data",
    "target": "url",
    "input": "text",
}


def _infer_category(module_name: str, docstring: str | None) -> str:
    """Infer tool category from module name and docstring."""
    combined = f"{module_name} {docstring or ''}".lower()
    for category, keywords in _CATEGORIES_MAP.items():
        if any(kw in combined for kw in keywords):
            return category
    return "other"


def _infer_input_types(params: list[str]) -> list[str]:
    """Infer input types from parameter names."""
    types = []
    for param in params:
        param_lower = param.lower()
        mapped = _INPUT_MAPPINGS.get(param_lower, param_lower)
        if mapped not in types:
            types.append(mapped)
    return types


def _has_network_imports(node: ast.Module) -> bool:
    """Check if module imports network libraries."""
    network_libs = {"httpx", "aiohttp", "requests", "socket", "urllib"}
    for item in ast.walk(node):
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(item, ast.Import):
                names = [alias.name for alias in item.names]
            else:
                names = [item.module] if item.module else []
            for name in names:
                if any(lib in name for lib in network_libs):
                    return True
    return False


def _has_llm_imports(node: ast.Module) -> bool:
    """Check if module imports LLM providers."""
    llm_libs = {"openai", "anthropic", "groq", "google", "deepseek", "moonshot", "nvidia"}
    for item in ast.walk(node):
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(item, ast.Import):
                names = [alias.name for alias in item.names]
            else:
                names = [item.module] if item.module else []
            for name in names:
                if any(lib in name.lower() for lib in llm_libs):
                    return True
    return False


def _parse_tool_functions(tool_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Parse all research_* functions from tool files."""
    tools = []

    if not tool_dir.exists():
        return tools

    for py_file in sorted(tool_dir.glob("*.py")):
        if py_file.name in ("__init__.py", "capability_matrix.py"):
            continue

        try:
            with open(py_file, "r") as f:
                content = f.read()
            tree = ast.parse(content)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", py_file.name, e)
            continue

        module_name = py_file.stem
        module_docstring = ast.get_docstring(tree) or ""
        has_network = _has_network_imports(tree)
        has_llm = _has_llm_imports(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("research_"):
                docstring = ast.get_docstring(node) or ""
                params = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
                params = [p for p in params if not p.startswith("_")]

                input_types = _infer_input_types(params)
                category = _infer_category(module_name, docstring)

                speed = "fast"
                if has_network and has_llm:
                    speed = "slow"
                elif has_network:
                    speed = "medium"

                requires_network = has_network or has_llm

                tools.append({
                    "tool": node.name,
                    "module": module_name,
                    "input_types": input_types,
                    "category": category,
                    "requires_network": requires_network,
                    "speed": speed,
                    "docstring": docstring[:100] if docstring else "",
                })

    return tools


def _build_matrix() -> dict[str, Any]:
    """Build capability matrix from all tool files."""
    tool_dir = pathlib.Path(__file__).parent
    tools = _parse_tool_functions(tool_dir)

    # Aggregate by category
    category_counts = {}
    for tool in tools:
        cat = tool["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total_tools": len(tools),
        "categories": category_counts,
        "matrix": tools,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
    }


async def research_capability_matrix(category: str = "all") -> dict[str, Any]:
    """Analyze all tool functions by input/output type.

    Scans src/loom/tools/*.py via AST, classifies each research_* function by:
    - input_types: inferred from parameter names
    - category: fetch, search, analyze, generate, adversarial, monitor, output, llm, etc.
    - requires_network: True if module imports network/LLM libraries
    - speed: fast (no network), medium (network only), slow (network + LLM)

    Args:
        category: Filter by category ('all', 'fetch', 'search', 'analyze', etc.)

    Returns:
        Dict with total_tools, categories count, and full matrix
    """
    try:
        global _MATRIX_CACHE

        if _MATRIX_CACHE is None:
            async with _MATRIX_LOCK:
                if _MATRIX_CACHE is None:
                    _MATRIX_CACHE = _build_matrix()

        result = {
            "total_tools": _MATRIX_CACHE["total_tools"],
            "categories": _MATRIX_CACHE["categories"],
        }

        if category == "all":
            result["matrix"] = _MATRIX_CACHE["matrix"]
        else:
            result["matrix"] = [
                t for t in _MATRIX_CACHE["matrix"]
                if t["category"] == category
            ]
            result["total_matching"] = len(result["matrix"])

        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_capability_matrix"}


async def research_find_tools_by_capability(
    input_type: str = "",
    category: str = "",
    requires_network: bool | None = None,
    speed: str = "",
) -> dict[str, Any]:
    """Filter capability matrix by input type, category, network requirement, or speed.

    Args:
        input_type: Filter by input (url, text, model_name, provider, data, etc.)
        category: Filter by category (fetch, search, analyze, generate, etc.)
        requires_network: Filter by network requirement (True/False/None for any)
        speed: Filter by speed (fast, medium, slow)

    Returns:
        Dict with filters_applied, matching_tools, and total_matches
    """
    try:
        global _MATRIX_CACHE

        if _MATRIX_CACHE is None:
            async with _MATRIX_LOCK:
                if _MATRIX_CACHE is None:
                    _MATRIX_CACHE = _build_matrix()

        matching = _MATRIX_CACHE["matrix"]
        filters = {}

        if input_type:
            matching = [t for t in matching if input_type in t["input_types"]]
            filters["input_type"] = input_type

        if category:
            matching = [t for t in matching if t["category"] == category]
            filters["category"] = category

        if requires_network is not None:
            matching = [t for t in matching if t["requires_network"] == requires_network]
            filters["requires_network"] = requires_network

        if speed:
            matching = [t for t in matching if t["speed"] == speed]
            filters["speed"] = speed

        return {
            "filters_applied": filters,
            "total_matches": len(matching),
            "matching_tools": [
                {
                    "tool": t["tool"],
                    "module": t["module"],
                    "input_types": t["input_types"],
                    "category": t["category"],
                }
                for t in matching
            ],
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_find_tools_by_capability"}
