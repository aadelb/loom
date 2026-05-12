"""Tool function introspection utilities.

Discovers registered tool functions and extracts metadata (signatures,
docstrings, parameter info) for the help system and tool recommender.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Callable, get_type_hints

logger = logging.getLogger("loom.tool_introspection")


def get_tool_signature(func: Callable) -> dict[str, Any]:
    """Extract a tool function's signature as a dict.

    Returns:
        {
            "name": "research_foo",
            "async": True,
            "params": [{"name": "query", "type": "str", "default": None, "required": True}, ...],
            "return_type": "dict[str, Any]",
            "docstring": "First line of docstring",
        }
    """
    sig = inspect.signature(func)

    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    params: list[dict[str, Any]] = []
    for name, param in sig.parameters.items():
        p: dict[str, Any] = {"name": name}

        # Type
        if name in hints:
            p["type"] = _type_to_str(hints[name])
        elif param.annotation != inspect.Parameter.empty:
            p["type"] = _type_to_str(param.annotation)
        else:
            p["type"] = "Any"

        # Default
        if param.default != inspect.Parameter.empty:
            p["default"] = param.default
            p["required"] = False
        else:
            p["default"] = None
            p["required"] = True

        params.append(p)

    return_type = _type_to_str(hints.get("return", "Any"))

    doc = inspect.getdoc(func) or ""
    first_line = doc.split("\n")[0] if doc else ""

    return {
        "name": func.__name__,
        "async": inspect.iscoroutinefunction(func),
        "params": params,
        "return_type": return_type,
        "docstring": first_line,
    }


def get_tool_params(func: Callable) -> list[str]:
    """Get parameter names for a tool function (excluding self/cls)."""
    sig = inspect.signature(func)
    return [
        name for name, p in sig.parameters.items()
        if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]


def get_tool_docstring(func: Callable, *, max_length: int = 200) -> str:
    """Get the first line of a tool's docstring."""
    doc = inspect.getdoc(func) or ""
    first_line = doc.split("\n")[0]
    if len(first_line) > max_length:
        first_line = first_line[:max_length - 3] + "..."
    return first_line


def is_tool_async(func: Callable) -> bool:
    """Check if a tool function is async."""
    return inspect.iscoroutinefunction(func)


def _type_to_str(annotation: Any) -> str:
    """Convert a type annotation to a readable string."""
    if annotation == "Any" or annotation is None:
        return "Any"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation).replace("typing.", "")
