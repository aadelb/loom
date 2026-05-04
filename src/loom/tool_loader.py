"""Lazy-loading tool loader for deferred MCP tool imports.

This module provides a LazyToolLoader class that allows registering tool functions
without importing them immediately. Tools are imported on first access (lazy loading),
reducing startup time from importing all 567+ modules to importing only on first use.

Supports statistics tracking, error handling, and caching of loaded functions.

Example:
    >>> loader = LazyToolLoader()
    >>> loader.register("research_fetch", "loom.tools.fetch", "research_fetch")
    >>> fetch_func = loader.load("research_fetch")  # Import happens here
    >>> stats = loader.get_load_stats()
    >>> print(stats)
    {'loaded_count': 1, 'failed_count': 0, 'avg_load_time_ms': 45.2}
"""

from __future__ import annotations

import importlib
import logging
import time
from typing import Any, Callable

log = logging.getLogger("loom.tool_loader")


class LazyToolLoader:
    """Lazy-load MCP tool functions on first access.

    Defers module imports until tools are actually used, reducing startup time
    and memory footprint. Caches loaded functions for reuse.

    Attributes:
        _registry: Dict mapping tool name to (module_path, func_name) tuple
        _cache: Dict mapping tool name to loaded function
        _load_times: Dict mapping tool name to load time in milliseconds
        _failed: Set of tool names that failed to load
    """

    def __init__(self) -> None:
        """Initialize the lazy tool loader."""
        self._registry: dict[str, tuple[str, str]] = {}
        self._cache: dict[str, Callable[..., Any]] = {}
        self._load_times: dict[str, float] = {}
        self._failed: set[str] = set()

    def register(
        self,
        tool_name: str,
        module_path: str,
        func_name: str,
    ) -> None:
        """Register a tool without importing it.

        Args:
            tool_name: Name of the tool (e.g., "research_fetch")
            module_path: Full module import path (e.g., "loom.tools.fetch")
            func_name: Name of the function in the module (e.g., "research_fetch")

        Raises:
            ValueError: If tool_name is already registered
        """
        if tool_name in self._registry:
            msg = f"Tool {tool_name} already registered"
            raise ValueError(msg)

        self._registry[tool_name] = (module_path, func_name)
        log.debug("tool_registered tool_name=%s module_path=%s func_name=%s",
                  tool_name, module_path, func_name)

    def load(self, tool_name: str) -> Callable[..., Any]:
        """Load a tool function by name, importing on first access.

        Caches the loaded function for subsequent calls. If the tool has already
        been loaded, returns the cached function without re-importing.

        Args:
            tool_name: Name of the tool to load

        Returns:
            The loaded function

        Raises:
            KeyError: If tool_name not registered
            ImportError: If module cannot be imported
            AttributeError: If function not found in module
        """
        # Return cached function if already loaded
        if tool_name in self._cache:
            return self._cache[tool_name]

        # Fail fast if previous load failed
        if tool_name in self._failed:
            msg = f"Tool {tool_name} previously failed to load"
            raise ImportError(msg)

        if tool_name not in self._registry:
            msg = f"Tool {tool_name} not registered"
            raise KeyError(msg)

        module_path, func_name = self._registry[tool_name]

        # Measure import time
        start_time = time.time()

        try:
            # Import the module
            module = importlib.import_module(module_path)
            load_time_ms = (time.time() - start_time) * 1000

            # Get the function from the module
            func = getattr(module, func_name)

            if not callable(func):
                msg = f"Attribute {func_name} in {module_path} is not callable"
                raise AttributeError(msg)

            # Cache the function and load time
            self._cache[tool_name] = func
            self._load_times[tool_name] = load_time_ms

            log.info("tool_loaded tool_name=%s module_path=%s load_time_ms=%.2f",
                     tool_name, module_path, load_time_ms)

            return func

        except (ImportError, AttributeError) as e:
            # Mark as failed and log error
            self._failed.add(tool_name)
            load_time_ms = (time.time() - start_time) * 1000

            log.error(
                "tool_load_failed tool_name=%s module_path=%s func_name=%s "
                "error=%s load_time_ms=%.2f",
                tool_name, module_path, func_name, str(e), load_time_ms
            )
            raise

    def is_loaded(self, tool_name: str) -> bool:
        """Check if a tool has been successfully loaded.

        Args:
            tool_name: Name of the tool

        Returns:
            True if the tool is in the cache, False otherwise
        """
        return tool_name in self._cache

    def get_all_registered(self) -> list[str]:
        """Get list of all registered tool names.

        Returns:
            List of tool names in registration order
        """
        return list(self._registry.keys())

    def get_load_stats(self) -> dict[str, Any]:
        """Get statistics about tool loading.

        Returns:
            Dict with:
            - loaded_count: Number of successfully loaded tools
            - failed_count: Number of tools that failed to load
            - registered_count: Total number of registered tools
            - avg_load_time_ms: Average load time for successful loads
            - load_times_by_tool: Dict mapping tool name to load time
            - failed_tools: List of tool names that failed
        """
        loaded_count = len(self._cache)
        failed_count = len(self._failed)
        registered_count = len(self._registry)

        # Calculate average load time (only for successful loads)
        load_times = list(self._load_times.values())
        avg_load_time_ms = (
            sum(load_times) / len(load_times) if load_times else 0.0
        )

        return {
            "loaded_count": loaded_count,
            "failed_count": failed_count,
            "registered_count": registered_count,
            "avg_load_time_ms": round(avg_load_time_ms, 2),
            "load_times_by_tool": dict(self._load_times),
            "failed_tools": list(self._failed),
        }

    def get_load_time(self, tool_name: str) -> float | None:
        """Get the load time for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Load time in milliseconds, or None if not loaded
        """
        return self._load_times.get(tool_name)

    def unload(self, tool_name: str) -> None:
        """Unload a tool from cache (for testing/resource management).

        Note: This does NOT remove the tool from the registry, so it can be
        reloaded again via load().

        Args:
            tool_name: Name of the tool to unload

        Raises:
            KeyError: If tool_name not in cache
        """
        if tool_name not in self._cache:
            msg = f"Tool {tool_name} not in cache"
            raise KeyError(msg)

        del self._cache[tool_name]
        log.debug("tool_unloaded tool_name=%s", tool_name)

    def reset(self) -> None:
        """Clear all cached functions and statistics.

        Note: This does NOT clear the registry, so all tools remain registered.
        """
        self._cache.clear()
        self._load_times.clear()
        self._failed.clear()
        log.debug("tool_loader_reset")


# Module-level singleton instance
_default_loader: LazyToolLoader | None = None


def get_loader() -> LazyToolLoader:
    """Get the default LazyToolLoader instance (singleton).

    Returns:
        The default LazyToolLoader instance
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = LazyToolLoader()
    return _default_loader
