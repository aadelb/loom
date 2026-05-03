"""Auto-discovery decorator system for tool registration.

This module provides a decorator-based approach to register MCP tools,
eliminating the need for manual registration in server.py.

Usage:
    from loom.tool_registry import loom_tool

    @loom_tool(category="intelligence", description="Search social graphs")
    async def research_social_graph(query: str, depth: int = 2) -> dict:
        ...

The registry discovers all decorated functions and can inject them into
the FastMCP server via register_all_with_mcp().
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger("loom.tool_registry")

# Type variables for generic function handling
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")

# Global registry: {tool_name: tool_info}
_REGISTRY: dict[str, dict[str, Any]] = {}

# Lock for thread-safe registry updates
_REGISTRY_LOCK = asyncio.Lock()


class ToolInfo:
    """Metadata about a registered tool."""

    __slots__ = ("func", "category", "description", "module", "is_async", "name")

    def __init__(
        self,
        func: Callable[..., Any],
        category: str,
        description: str,
        module: str,
        is_async: bool,
        name: str,
    ) -> None:
        self.func = func
        self.category = category
        self.description = description
        self.module = module
        self.is_async = is_async
        self.name = name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "func": self.func,
            "category": self.category,
            "description": self.description,
            "module": self.module,
            "is_async": self.is_async,
            "name": self.name,
        }


def loom_tool(
    category: str = "research",
    description: str = "",
) -> Callable[[F], F]:
    """Decorator to register a function as an MCP tool.

    Args:
        category: Tool category (e.g., "intelligence", "research", "analysis")
        description: Human-readable tool description

    Returns:
        Decorator function that registers the tool and returns the original function

    Example:
        @loom_tool(category="intelligence", description="Search social graphs")
        async def research_social_graph(query: str, depth: int = 2) -> dict:
            ...
    """

    def decorator(func: F) -> F:
        """Inner decorator that captures and registers the function."""
        tool_name = func.__name__
        module = func.__module__
        is_async = asyncio.iscoroutinefunction(func)

        # Create tool info
        tool_info = ToolInfo(
            func=func,
            category=category,
            description=description,
            module=module,
            is_async=is_async,
            name=tool_name,
        )

        # Register in global registry
        _REGISTRY[tool_name] = tool_info.to_dict()

        logger.debug(
            "Registered tool",
            extra={
                "tool_name": tool_name,
                "category": category,
                "module": module,
                "is_async": is_async,
            },
        )

        # Return original function unchanged
        return func

    return decorator


def get_all_registered_tools() -> dict[str, dict[str, Any]]:
    """Get all registered tools from the global registry.

    Returns:
        Dictionary mapping tool names to tool info dicts

    Example:
        tools = get_all_registered_tools()
        for name, info in tools.items():
            print(f"{name}: {info['description']}")
    """
    return _REGISTRY.copy()


def get_tools_by_category(category: str) -> dict[str, dict[str, Any]]:
    """Get all tools in a specific category.

    Args:
        category: Category name to filter by

    Returns:
        Dictionary of tools matching the category
    """
    return {
        name: info for name, info in _REGISTRY.items() if info["category"] == category
    }


def get_registered_tool(tool_name: str) -> dict[str, Any] | None:
    """Get a specific registered tool by name.

    Args:
        tool_name: Name of the tool to retrieve

    Returns:
        Tool info dict or None if not found
    """
    return _REGISTRY.get(tool_name)


def discover_tools(tools_dir: Path) -> int:
    """Auto-import all tool modules to trigger decorators.

    Scans a directory for .py files and imports them, which causes
    any @loom_tool decorated functions to self-register.

    Args:
        tools_dir: Path to the tools directory

    Returns:
        Number of modules imported

    Raises:
        ImportError: If a module fails to import
        ValueError: If tools_dir does not exist

    Example:
        from pathlib import Path
        count = discover_tools(Path("src/loom/tools"))
        print(f"Discovered {count} tool modules")
    """
    if not tools_dir.exists():
        raise ValueError(f"Tools directory does not exist: {tools_dir}")

    if not tools_dir.is_dir():
        raise ValueError(f"Path is not a directory: {tools_dir}")

    imported = 0
    errors: list[tuple[str, Exception]] = []

    for py_file in sorted(tools_dir.glob("*.py")):
        # Skip private/internal modules
        if py_file.name.startswith("_"):
            continue

        module_name = py_file.stem
        full_module = f"loom.tools.{module_name}"

        try:
            importlib.import_module(full_module)
            imported += 1
            logger.debug(f"Imported tool module: {full_module}")
        except ImportError as e:
            errors.append((full_module, e))
            logger.warning(f"Failed to import {full_module}: {e}")
        except Exception as e:
            errors.append((full_module, e))
            logger.error(f"Unexpected error importing {full_module}: {e}")

    if errors:
        logger.info(
            f"Tool discovery complete with {len(errors)} import error(s)",
            extra={"total_imported": imported, "errors": len(errors)},
        )

    return imported


def register_all_with_mcp(
    mcp: Any,
    wrap_tool: Callable[[Callable[..., Any]], Callable[..., Any]],
) -> int:
    """Register all discovered tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance
        wrap_tool: Wrapper function from server.py that handles tool execution

    Returns:
        Number of tools registered

    Example:
        from mcp.server import FastMCP
        mcp = FastMCP("loom")
        from loom.server import _wrap_tool
        count = register_all_with_mcp(mcp, _wrap_tool)
        print(f"Registered {count} tools")
    """
    registered = 0

    for tool_name, tool_info in _REGISTRY.items():
        try:
            func = tool_info["func"]
            # Register with FastMCP
            mcp.tool()(wrap_tool(func))
            registered += 1
            logger.debug(f"Registered {tool_name} with MCP")
        except Exception as e:
            logger.error(f"Failed to register tool {tool_name}: {e}")

    logger.info(f"Registered {registered}/{len(_REGISTRY)} tools with MCP")
    return registered


def get_registry_stats() -> dict[str, Any]:
    """Get statistics about registered tools.

    Returns:
        Dictionary containing registry statistics

    Example:
        stats = get_registry_stats()
        print(f"Total tools: {stats['total']}")
        print(f"By category: {stats['by_category']}")
    """
    categories: dict[str, int] = {}
    async_count = 0

    for tool_info in _REGISTRY.values():
        category = tool_info["category"]
        categories[category] = categories.get(category, 0) + 1

        if tool_info["is_async"]:
            async_count += 1

    return {
        "total": len(_REGISTRY),
        "async": async_count,
        "sync": len(_REGISTRY) - async_count,
        "by_category": categories,
        "categories": sorted(categories.keys()),
    }


def validate_registry() -> tuple[bool, list[str]]:
    """Validate registry integrity.

    Returns:
        Tuple of (is_valid, error_messages)

    Checks:
        - All tools have required fields
        - No duplicate tool names
        - All functions are callable
        - Async detection matches actual function signature
    """
    errors: list[str] = []

    for tool_name, tool_info in _REGISTRY.items():
        # Check required fields
        required = {"func", "category", "description", "module", "is_async", "name"}
        missing = required - set(tool_info.keys())
        if missing:
            errors.append(f"{tool_name}: missing fields {missing}")

        # Check callable
        if not callable(tool_info.get("func")):
            errors.append(f"{tool_name}: not callable")

        # Check async detection
        is_async_detected = asyncio.iscoroutinefunction(tool_info.get("func"))
        is_async_stored = tool_info.get("is_async", False)
        if is_async_detected != is_async_stored:
            errors.append(
                f"{tool_name}: async mismatch "
                f"(detected={is_async_detected}, stored={is_async_stored})"
            )

    return len(errors) == 0, errors


def clear_registry() -> None:
    """Clear all registered tools.

    WARNING: This is a destructive operation used primarily for testing.
    """
    global _REGISTRY
    _REGISTRY.clear()
    logger.warning("Tool registry cleared")


def print_registry(stream: Any = None) -> None:
    """Print a formatted summary of the registry.

    Args:
        stream: Output stream (default: stdout)
    """
    if not _REGISTRY:
        print("Registry is empty", file=stream)
        return

    stats = get_registry_stats()
    print(f"\n=== Loom Tool Registry ===", file=stream)
    print(f"Total: {stats['total']} tools", file=stream)
    print(f"Async: {stats['async']}, Sync: {stats['sync']}", file=stream)
    print(f"\nBy Category:", file=stream)
    for category, count in sorted(stats["by_category"].items()):
        print(f"  {category}: {count}", file=stream)

    print(f"\nTools:", file=stream)
    for tool_name, tool_info in sorted(_REGISTRY.items()):
        async_marker = "async" if tool_info["is_async"] else "sync"
        print(
            f"  {tool_name:<40} ({async_marker:>5}) - {tool_info['category']:<15}",
            file=stream,
        )
        if tool_info["description"]:
            print(f"    {tool_info['description']}", file=stream)
