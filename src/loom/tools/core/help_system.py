"""Help system for Loom tools — tool discovery, documentation, and assistance."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import re
from functools import lru_cache
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.tool_introspection import get_tool_signature, get_tool_docstring, is_tool_async
    _INTROSPECTION_AVAILABLE = True
except ImportError:
    _INTROSPECTION_AVAILABLE = False

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

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


@lru_cache(maxsize=1)
def _get_all_tools() -> dict[str, dict[str, Any]]:
    """Discover all research_* and tool_* functions from loom.tools modules.

    Returns:
        Dict mapping tool_name -> {module, function, docstring, signature, is_async}
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

    # Scan *.py files in tools/ directory AND subdirectories (except reframe_strategies/)
    skip_dirs = {"reframe_strategies", "__pycache__"}
    py_files = sorted(tools_dir.glob("*.py"))
    for subdir in sorted(tools_dir.iterdir()):
        if subdir.is_dir() and subdir.name not in skip_dirs:
            py_files.extend(sorted(subdir.glob("*.py")))

    for py_file in py_files:
        module_name = py_file.stem
        if module_name.startswith("_") or module_name == "help_system":
            continue

        # Build import path: loom.tools.module or loom.tools.subdir.module
        rel = py_file.relative_to(tools_dir)
        if len(rel.parts) == 1:
            import_path = f"loom.tools.{module_name}"
        else:
            import_path = f"loom.tools.{rel.parent.name}.{module_name}"

        try:
            mod = importlib.import_module(import_path)
        except ImportError as e:
            logger.debug(f"Failed to import {import_path}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error importing {import_path}: {e}")
            continue

        # Extract all research_* and tool_* functions (both sync and async)
        for name, obj in inspect.getmembers(mod):
            if not (name.startswith("research_") or name.startswith("tool_")):
                continue

            is_async = inspect.iscoroutinefunction(obj)
            is_sync = inspect.isfunction(obj)

            if not (is_sync or is_async):
                continue

            # Use tool_introspection if available
            if _INTROSPECTION_AVAILABLE:
                try:
                    sig_info = get_tool_signature(obj)
                    docstring = sig_info.get("docstring", inspect.getdoc(obj) or "No documentation available.")
                    signature = str(inspect.signature(obj))
                except Exception:
                    # Fallback to inspect
                    docstring = inspect.getdoc(obj) or "No documentation available."
                    signature = str(inspect.signature(obj))
            else:
                docstring = inspect.getdoc(obj) or "No documentation available."
                signature = str(inspect.signature(obj))

            tools[name] = {
                "module": module_name,
                "function": name,
                "docstring": docstring,
                "signature": signature,
                "is_async": is_async,
            }

    return tools


def _format_annotation(annotation: Any) -> str:
    """Format a type annotation for readable display.

    Args:
        annotation: The annotation object from inspect.Parameter

    Returns:
        Human-readable type string
    """
    if annotation == inspect.Parameter.empty:
        return "Any"

    # Handle common types
    if hasattr(annotation, "__origin__"):
        origin = annotation.__origin__
        if origin is list:
            args = getattr(annotation, "__args__", ())
            if args:
                return f"list[{_format_annotation(args[0])}]"
            return "list"
        elif origin is dict:
            args = getattr(annotation, "__args__", ())
            if len(args) >= 2:
                return f"dict[{_format_annotation(args[0])}, {_format_annotation(args[1])}]"
            return "dict"
        elif origin is tuple:
            args = getattr(annotation, "__args__", ())
            if args:
                formatted = ", ".join(_format_annotation(arg) for arg in args)
                return f"tuple[{formatted}]"
            return "tuple"

    # Handle Union/Optional
    type_str = str(annotation)
    if "Union" in type_str:
        return type_str.replace("typing.Union", "Union").replace("typing.", "")
    if "Optional" in type_str:
        return type_str.replace("typing.Optional", "Optional").replace("typing.", "")

    # Simple types
    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation).replace("typing.", "").replace("<class '", "").replace("'>", "")


def _parse_docstring_params(docstring: str) -> dict[str, str]:
    """Extract parameter descriptions from docstring.

    Supports Google-style and Sphinx-style docstrings.

    Args:
        docstring: The docstring to parse

    Returns:
        Dict mapping param_name -> description
    """
    if not docstring:
        return {}

    params_dict = {}
    lines = docstring.split("\n")
    in_args_section = False
    current_param = None
    current_desc = []

    for line in lines:
        # Google-style: "Args:"
        if line.strip() in ("Args:", "Arguments:"):
            in_args_section = True
            continue

        # Sphinx-style: ":param name: description"
        param_match = re.match(r":param\s+(\w+):\s*(.*)", line)
        if param_match:
            if current_param:
                params_dict[current_param] = " ".join(current_desc).strip()
            current_param = param_match.group(1)
            current_desc = [param_match.group(2)]
            continue

        if in_args_section:
            stripped = line.strip()

            # End of Args section (new section starts)
            if stripped and not line.startswith(" "):
                in_args_section = False
                continue

            # Google-style: "    param_name: description"
            if stripped and not line.startswith("        "):
                match = re.match(r"(\w+)\s*:\s*(.*)", stripped)
                if match:
                    if current_param:
                        params_dict[current_param] = " ".join(current_desc).strip()
                    current_param = match.group(1)
                    current_desc = [match.group(2)]
                elif current_param:
                    # Continuation of previous param description
                    current_desc.append(stripped)

    # Save last param
    if current_param:
        params_dict[current_param] = " ".join(current_desc).strip()

    return params_dict


def _get_tool_params(tool_name: str) -> dict[str, Any]:
    """Extract parameter information for a specific tool.

    Args:
        tool_name: Name of the tool (e.g., "research_fetch")

    Returns:
        Dict with parameter details: {param_name -> {type, default, description, is_async}}
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

    # Use tool_introspection if available
    if _INTROSPECTION_AVAILABLE:
        try:
            sig_info = get_tool_signature(func)
            params_list = sig_info.get("params", [])
        except Exception:
            # Fallback to inspect
            sig = inspect.signature(func)
            params_list = []
            for param_name, param in sig.parameters.items():
                if param_name not in ("self", "cls"):
                    params_list.append({
                        "name": param_name,
                        "annotation": param.annotation,
                        "default": param.default,
                    })
    else:
        sig = inspect.signature(func)
        params_list = []
        for param_name, param in sig.parameters.items():
            if param_name not in ("self", "cls"):
                params_list.append({
                    "name": param_name,
                    "annotation": param.annotation,
                    "default": param.default,
                })

    params = {}

    # Parse docstring for parameter descriptions
    docstring_params = _parse_docstring_params(tool_info["docstring"])

    for item in params_list:
        param_name = item.get("name")
        if not param_name:
            continue

        param_annotation = item.get("annotation", inspect.Parameter.empty)
        param_default = item.get("default", inspect.Parameter.empty)
        param_desc = docstring_params.get(param_name, "See docstring for details")

        params[param_name] = {
            "type": _format_annotation(param_annotation),
            "default": (
                str(param_default)
                if param_default != inspect.Parameter.empty
                else "Required"
            ),
            "description": param_desc,
        }

    return params


def _categorize_tool(tool_name: str) -> str:
    """Determine the category of a tool based on its name.

    Uses exact word boundary matching to avoid false positives.

    Args:
        tool_name: Name of the tool

    Returns:
        Category string (e.g., "research", "analysis", "security")
    """
    tool_lower = tool_name.lower()

    for category, patterns in TOOL_CATEGORIES.items():
        for pattern in patterns:
            # Use word boundary matching to avoid substring false positives
            # e.g., "fetch" should match "research_fetch" but not "prefetch"
            if re.search(rf"\b{re.escape(pattern)}\b", tool_lower):
                return category

    return "other"


@handle_tool_errors("research_help")
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
    try:
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
            "is_async": tool_info["is_async"],
            "documentation": tool_info["docstring"],
            "parameters": params,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_help"}


@handle_tool_errors("research_tools_list")
def research_tools_list(category: str = "") -> dict[str, Any]:
    """List Loom tools filtered by category.

    Available categories: research, analysis, security, infrastructure, darkweb,
    cache, sessions, config, utility, other

    Args:
        category: Filter tools by category (empty = all)

    Returns:
        Dict with filtered tool list.
    """
    try:
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
    except Exception as exc:
        return {"error": str(exc), "tool": "research_tools_list"}


def tool_help(tool_name: str = "") -> list[TextContent]:
    """MCP wrapper for research_help."""
    result = research_help(tool_name)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_tools_list(category: str = "") -> list[TextContent]:
    """MCP wrapper for research_tools_list."""
    result = research_tools_list(category)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
