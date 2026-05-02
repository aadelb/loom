"""Help system for Loom tools — tool discovery, documentation, and assistance."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
from typing import Any

from mcp.types import TextContent

logger = logging.getLogger("loom.tools.help_system")

# Tool categories mapping (category -> list of module patterns)
TOOL_CATEGORIES = {
    "research": [
        "fetch",
        "spider",
        "markdown",
        "search",
        "deep",
        "github",
    ],
    "analysis": [
        "fact_checker",
        "knowledge_graph",
        "trend_predictor",
        "sentiment",
        "bias_lens",
        "stylometry",
    ],
    "security": [
        "ai_safety",
        "breach_check",
        "cert_analyzer",
        "cve_lookup",
        "vuln_intel",
        "crypto_trace",
    ],
    "infrastructure": [
        "vastai",
        "billing",
        "deploy",
        "metrics",
        "observability",
    ],
    "darkweb": [
        "dark_forum",
        "onion_discover",
        "leak_scan",
        "darkweb",
    ],
    "cache": [
        "cache",
        "semantic_cache",
    ],
    "sessions": [
        "session",
    ],
    "config": [
        "config",
    ],
    "utility": [
        "error",
        "output",
        "notifications",
        "audit",
    ],
}


def _get_all_tools() -> dict[str, dict[str, Any]]:
    """Discover all research_* and tool_* functions from loom.tools modules.

    Returns:
        Dict mapping tool_name -> {module, function, docstring, signature}
    """
    tools = {}

    # Import all tool modules
    try:
        import loom.tools as tools_module
        tool_modules_path = tools_module.__path__[0]
    except (AttributeError, IndexError):
        return tools

    import pathlib

    tools_dir = pathlib.Path(tool_modules_path)

    for py_file in sorted(tools_dir.glob("*.py")):
        module_name = py_file.stem
        if module_name.startswith("_") or module_name == "help_system":
            continue

        try:
            mod = importlib.import_module(f"loom.tools.{module_name}")
        except (ImportError, Exception) as e:
            logger.debug(f"Failed to import loom.tools.{module_name}: {e}")
            continue

        # Extract all research_* and tool_* functions
        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("research_") or name.startswith("tool_"):
                tools[name] = {
                    "module": module_name,
                    "function": name,
                    "docstring": inspect.getdoc(obj) or "No documentation available.",
                    "signature": str(inspect.signature(obj)),
                }

    return tools


def _get_tool_params(tool_name: str) -> dict[str, Any]:
    """Extract parameter information for a specific tool.

    Args:
        tool_name: Name of the tool (e.g., "research_fetch")

    Returns:
        Dict with parameter details: {param_name -> {type, default, description}}
    """
    tools = _get_all_tools()

    if tool_name not in tools:
        return {}

    tool_info = tools[tool_name]
    module_name = tool_info["module"]

    try:
        mod = importlib.import_module(f"loom.tools.{module_name}")
        func = getattr(mod, tool_name)
    except (ImportError, AttributeError):
        return {}

    sig = inspect.signature(func)
    params = {}

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        params[param_name] = {
            "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
            "default": (
                str(param.default)
                if param.default != inspect.Parameter.empty
                else "Required"
            ),
            "description": "See docstring for details",
        }

    return params


def _categorize_tool(tool_name: str) -> str:
    """Determine the category of a tool based on its name.

    Args:
        tool_name: Name of the tool

    Returns:
        Category string (e.g., "research", "analysis", "security")
    """
    for category, patterns in TOOL_CATEGORIES.items():
        for pattern in patterns:
            if pattern in tool_name.lower():
                return category

    return "other"


def research_help(tool_name: str = "") -> dict[str, Any]:
    """Get help documentation for Loom tools.

    Call with empty tool_name to list all tools.
    Call with a specific tool_name to get full documentation for that tool.

    Args:
        tool_name: Name of the tool to get help for (e.g., "research_fetch")
                   If empty, returns list of all tools.

    Returns:
        Dict with tool list or detailed documentation.
    """
    all_tools = _get_all_tools()

    if not tool_name:
        # Return list of all tools grouped by category
        categorized = {}

        for tool_name, tool_info in sorted(all_tools.items()):
            category = _categorize_tool(tool_name)
            if category not in categorized:
                categorized[category] = []

            # Extract first line of docstring as summary
            summary = tool_info["docstring"].split("\n")[0]
            categorized[category].append(
                {
                    "name": tool_name,
                    "summary": summary,
                    "module": tool_info["module"],
                }
            )

        return {
            "status": "success",
            "total_tools": len(all_tools),
            "categories": categorized,
            "instruction": "Call research_help with tool_name='research_fetch' for full documentation",
        }

    # Return full documentation for specific tool
    if tool_name not in all_tools:
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' not found",
            "suggestion": "Call research_help() with no arguments to list all available tools",
        }

    tool_info = all_tools[tool_name]
    params = _get_tool_params(tool_name)

    return {
        "status": "success",
        "tool_name": tool_name,
        "module": tool_info["module"],
        "category": _categorize_tool(tool_name),
        "signature": tool_info["signature"],
        "documentation": tool_info["docstring"],
        "parameters": params,
    }


def research_tools_list(category: str = "") -> dict[str, Any]:
    """List Loom tools filtered by category.

    Available categories: research, analysis, security, infrastructure, darkweb,
    cache, sessions, config, utility, other

    Args:
        category: Filter tools by category (empty = all)

    Returns:
        Dict with filtered tool list.
    """
    all_tools = _get_all_tools()

    if not category:
        # Return all categories
        categorized = {}

        for tool_name, tool_info in sorted(all_tools.items()):
            cat = _categorize_tool(tool_name)
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(tool_name)

        return {
            "status": "success",
            "total_tools": len(all_tools),
            "categories": {k: len(v) for k, v in categorized.items()},
            "tools_by_category": categorized,
        }

    # Filter by specific category
    category_lower = category.lower()
    filtered = {}

    for tool_name, tool_info in sorted(all_tools.items()):
        if _categorize_tool(tool_name).lower() == category_lower:
            summary = tool_info["docstring"].split("\n")[0]
            filtered[tool_name] = summary

    return {
        "status": "success",
        "category": category,
        "count": len(filtered),
        "tools": filtered,
    }


def tool_help(tool_name: str = "") -> list[TextContent]:
    """MCP wrapper for research_help."""
    result = research_help(tool_name)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_tools_list(category: str = "") -> list[TextContent]:
    """MCP wrapper for research_tools_list."""
    result = research_tools_list(category)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
