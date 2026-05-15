"""Config hot-reload tools for Loom — watch config.json for changes.

Provides three MCP tools for monitoring and reacting to config file changes:
- research_config_watch: Start watching config.json
- research_config_check: Check if config has changed and reload if needed
- research_config_diff: Show what changed between old and new config
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.config import _resolve_path, load_config, get_config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

logger = logging.getLogger("loom.tools.config_reload")

# ─── Module state ────────────────────────────────────────────────────────────
_watch_state: dict[str, Any] = {
    "watching": False,
    "config_path": None,
    "last_mtime": None,
    "last_config": None,
}


@handle_tool_errors("research_config_watch")
def research_config_watch(config_path: str | None = None) -> dict[str, Any]:
    """Start watching config.json for modifications.

    Stores file modification time (mtime) in module state. Returns current
    watch status and config file location.

    Args:
        config_path: Optional explicit config path (default: resolved from env/cwd)

    Returns:
        Dict with keys: watching, config_path, last_modified (ISO format)
    """
    if not _CONFIG_AVAILABLE:
        return {"watching": False, "error": "loom.config module not available"}

    global _watch_state

    cfg_path = _resolve_path(config_path)

    if not cfg_path.exists():
        logger.warning("config_watch_file_not_found path=%s", cfg_path)
        return {
            "watching": False,
            "error": f"config file not found: {cfg_path}",
            "config_path": str(cfg_path),
        }

    try:
        current_mtime = cfg_path.stat().st_mtime
        current_config = dict(get_config())  # Snapshot current config

        _watch_state.update(
            {
                "watching": True,
                "config_path": str(cfg_path),
                "last_mtime": current_mtime,
                "last_config": current_config,
            }
        )

        logger.info("config_watch_started path=%s mtime=%s", cfg_path, current_mtime)

        return {
            "watching": True,
            "config_path": str(cfg_path),
            "last_modified": current_mtime,
        }
    except OSError as e:
        logger.error("config_watch_failed path=%s error=%s", cfg_path, e)
        return {"watching": False, "error": str(e), "config_path": str(cfg_path)}


@handle_tool_errors("research_config_check")
def research_config_check(config_path: str | None = None) -> dict[str, Any]:
    """Check if config has changed since watch started and reload if needed.

    Compares current file mtime against stored mtime. If changed, reloads
    config and returns new values (top-level keys only).

    Args:
        config_path: Optional explicit config path (default: from watch state)

    Returns:
        Dict with keys: changed, reloaded, current_settings (top-level keys)
    """
    if not _CONFIG_AVAILABLE:
        return {"changed": False, "reloaded": False, "error": "loom.config module not available"}

    global _watch_state

    if config_path:
        cfg_path = _resolve_path(config_path)
    elif _watch_state.get("config_path"):
        cfg_path = Path(_watch_state["config_path"])
    else:
        cfg_path = _resolve_path(None)

    if not cfg_path.exists():
        return {
            "changed": False,
            "reloaded": False,
            "error": f"config file not found: {cfg_path}",
        }

    try:
        current_mtime = cfg_path.stat().st_mtime
        last_mtime = _watch_state.get("last_mtime")

        if last_mtime is None:
            # First check, initialize state
            _watch_state["last_mtime"] = current_mtime
            _watch_state["last_config"] = dict(get_config())
            return {
                "changed": False,
                "reloaded": False,
                "current_settings": dict(get_config()),
            }

        has_changed = current_mtime != last_mtime

        if has_changed:
            new_config = load_config(cfg_path)
            _watch_state["last_mtime"] = current_mtime
            _watch_state["last_config"] = dict(new_config)
            logger.info("config_reloaded path=%s", cfg_path)
            return {
                "changed": True,
                "reloaded": True,
                "current_settings": dict(new_config),
            }
        else:
            return {
                "changed": False,
                "reloaded": False,
                "current_settings": dict(get_config()),
            }
    except OSError as e:
        logger.error("config_check_failed path=%s error=%s", cfg_path, e)
        return {"changed": False, "reloaded": False, "error": str(e)}


@handle_tool_errors("research_config_diff")
def research_config_diff(key: str = "") -> dict[str, Any]:
    """Show what changed between old and new config.

    If key is provided, shows only that key's old vs new value.
    Otherwise, lists all changes.

    Args:
        key: Optional config key to inspect (default: all changes)

    Returns:
        Dict with keys: changes (list of {key, old_value, new_value}), unchanged_count
    """
    if not _CONFIG_AVAILABLE:
        return {"changes": [], "error": "loom.config module not available"}
    try:
        old_config = _watch_state.get("last_config", {})
        current_config = dict(get_config())

        if not old_config:
            return {"changes": [], "unchanged_count": len(current_config)}

        changes = []

        # If key specified, only compare that key
        if key:
            old_val = old_config.get(key)
            new_val = current_config.get(key)
            if old_val != new_val:
                changes.append({"key": key, "old_value": old_val, "new_value": new_val})
            return {"changes": changes, "unchanged_count": 1 if old_val == new_val else 0}

        # Compare all keys
        all_keys = set(old_config.keys()) | set(current_config.keys())
        unchanged_count = 0

        for k in sorted(all_keys):
            old_val = old_config.get(k)
            new_val = current_config.get(k)
            if old_val != new_val:
                changes.append({"key": k, "old_value": old_val, "new_value": new_val})
            else:
                unchanged_count += 1

        logger.info("config_diff changes=%d unchanged=%d", len(changes), unchanged_count)

        return {"changes": changes, "unchanged_count": unchanged_count}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_config_diff"}
