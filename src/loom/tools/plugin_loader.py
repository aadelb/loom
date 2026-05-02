"""Dynamic plugin loader for external Loom tool modules."""

from __future__ import annotations

import importlib.util
import inspect
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_plugins: dict[str, dict[str, Any]] = {}


async def research_plugin_load(path: str) -> dict[str, Any]:
    """Load a Python file as a Loom plugin.

    Validates that the file exists, is a .py file, and contains research_*
    async functions. Stores plugin metadata and makes tools available.

    Args:
        path: Absolute path to .py plugin file

    Returns:
        {loaded: bool, path: str, tools_found: list[str], plugin_id: str, error?: str}
    """
    plugin_path = Path(path)

    # Validate file exists
    if not plugin_path.exists():
        return {
            "loaded": False,
            "path": path,
            "tools_found": [],
            "error": "File does not exist",
        }

    # Validate .py extension
    if plugin_path.suffix != ".py":
        return {
            "loaded": False,
            "path": path,
            "tools_found": [],
            "error": "File must be .py extension",
        }

    try:
        # Load module from file
        spec = importlib.util.spec_from_file_location(
            f"loom_plugin_{uuid.uuid4().hex[:8]}", plugin_path
        )
        if spec is None or spec.loader is None:
            return {
                "loaded": False,
                "path": path,
                "tools_found": [],
                "error": "Failed to create module spec",
            }

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract research_* async functions
        tools = []
        for name, obj in inspect.getmembers(module):
            if name.startswith("research_") and inspect.iscoroutinefunction(obj):
                tools.append(name)

        if not tools:
            return {
                "loaded": False,
                "path": path,
                "tools_found": [],
                "error": "No research_* async functions found",
            }

        # Store plugin metadata
        plugin_id = f"plugin_{uuid.uuid4().hex[:12]}"
        _plugins[plugin_id] = {
            "id": plugin_id,
            "path": str(plugin_path.resolve()),
            "module_name": module.__name__,
            "module": module,
            "tools": tools,
            "loaded_at": datetime.utcnow().isoformat(),
        }

        return {
            "loaded": True,
            "path": str(plugin_path.resolve()),
            "tools_found": tools,
            "plugin_id": plugin_id,
        }

    except Exception as e:
        return {
            "loaded": False,
            "path": path,
            "tools_found": [],
            "error": str(e),
        }


async def research_plugin_list() -> dict[str, Any]:
    """List all loaded plugins with their metadata.

    Returns:
        {plugins: list[{id, path, tools, loaded_at}], total: int}
    """
    plugins = [
        {
            "id": meta["id"],
            "path": meta["path"],
            "tools": meta["tools"],
            "loaded_at": meta["loaded_at"],
        }
        for meta in _plugins.values()
    ]

    return {
        "plugins": plugins,
        "total": len(plugins),
    }


async def research_plugin_unload(plugin_id: str) -> dict[str, Any]:
    """Remove plugin from registry.

    Args:
        plugin_id: Plugin ID returned from research_plugin_load

    Returns:
        {unloaded: bool, plugin_id: str, error?: str}
    """
    if plugin_id not in _plugins:
        return {
            "unloaded": False,
            "plugin_id": plugin_id,
            "error": f"Plugin {plugin_id} not found",
        }

    try:
        del _plugins[plugin_id]
        return {
            "unloaded": True,
            "plugin_id": plugin_id,
        }
    except Exception as e:
        return {
            "unloaded": False,
            "plugin_id": plugin_id,
            "error": str(e),
        }
