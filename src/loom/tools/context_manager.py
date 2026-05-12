"""Research Context Manager — session and persistent state management.

Maintains state across tool calls with dual scopes:
- session: In-memory context (fast, ephemeral)
- persistent: Saved to ~/.loom/context.json (survives restarts)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.context_manager")

# ─── Module state ────────────────────────────────────────────────────────────
_session_context: dict[str, dict[str, Any]] = {}
_context_file = Path.home() / ".loom" / "context.json"

# Lazy lock for thread-safe session context access
_context_lock: asyncio.Lock | None = None


def _get_context_lock() -> asyncio.Lock:
    """Get or create the context lock (lazy initialization)."""
    global _context_lock
    if _context_lock is None:
        _context_lock = asyncio.Lock()
    return _context_lock


def _load_persistent_context() -> dict[str, Any]:
    """Load persistent context from disk, return {} if missing."""
    if not _context_file.exists():
        return {}
    try:
        with open(_context_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("context_load_failed error=%s", e)
        return {}


def _save_persistent_context(context: dict[str, Any]) -> None:
    """Save context to ~/.loom/context.json atomically."""
    _context_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _context_file.parent / f"{_context_file.name}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2)
        tmp_path.replace(_context_file)
        logger.debug("context_saved path=%s", _context_file)
    except OSError as e:
        logger.error("context_save_failed error=%s", e)


@handle_tool_errors("research_context_set")
async def research_context_set(
    key: str,
    value: str,
    scope: Literal["session", "persistent"] = "session",
) -> dict[str, Any]:
    """Set a context variable.

    Args:
        key: Variable name (alphanumeric, underscore, hyphen)
        value: Variable value (string, max 10000 chars)
        scope: "session" (memory) or "persistent" (disk)

    Returns:
        {key, scope, set: True, set_at}
    """
    try:
        if not key or len(key) > 256:
            return {"error": "key must be 1-256 chars"}
        if not isinstance(value, str) or len(value) > 10000:
            return {"error": "value must be string, max 10000 chars"}

        now = datetime.now(UTC).isoformat()

        if scope == "session":
            async with _get_context_lock():
                _session_context[key] = {"value": value, "set_at": now}
            logger.info("context_set_session key=%s", key)
            return {"key": key, "scope": "session", "set": True, "set_at": now}

        elif scope == "persistent":
            context = _load_persistent_context()
            context[key] = {"value": value, "set_at": now}
            _save_persistent_context(context)
            logger.info("context_set_persistent key=%s", key)
            return {"key": key, "scope": "persistent", "set": True, "set_at": now}

        return {"error": f"invalid scope: {scope}"}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_context_set"}


@handle_tool_errors("research_context_get")
async def research_context_get(key: str = "") -> dict[str, Any]:
    """Get context variable(s).

    Args:
        key: Specific key to retrieve (empty = all context)

    Returns:
        {key, value, scope, set_at} or {context: dict} if key empty
    """
    try:
        # Merge session + persistent for retrieval
        async with _get_context_lock():
            merged = {}
            persistent = _load_persistent_context()
            merged.update(persistent)
            merged.update(_session_context)

        if not key:
            # Return all context (stripped of metadata)
            result = {k: v.get("value") for k, v in merged.items()}
            logger.info("context_get_all count=%d", len(result))
            return {"context": result, "total": len(result)}

        if key in merged:
            entry = merged[key]
            logger.info("context_get_found key=%s", key)
            return {
                "key": key,
                "value": entry.get("value"),
                "scope": "persistent" if key in persistent else "session",
                "set_at": entry.get("set_at"),
            }

        logger.info("context_get_not_found key=%s", key)
        return {"key": key, "found": False}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_context_get"}


@handle_tool_errors("research_context_clear")
async def research_context_clear(
    scope: Literal["session", "persistent", "all"] = "session",
) -> dict[str, Any]:
    """Clear context variables.

    Args:
        scope: "session" (memory), "persistent" (disk), or "all" (both)

    Returns:
        {cleared: int, scope}
    """
    try:
        if scope in ("session", "all"):
            async with _get_context_lock():
                cleared_session = len(_session_context)
                _session_context.clear()
            logger.info("context_clear_session cleared=%d", cleared_session)
        else:
            cleared_session = 0

        if scope in ("persistent", "all"):
            persistent = _load_persistent_context()
            cleared_persistent = len(persistent)
            _save_persistent_context({})
            logger.info("context_clear_persistent cleared=%d", cleared_persistent)
        else:
            cleared_persistent = 0

        total_cleared = cleared_session + cleared_persistent
        return {"cleared": total_cleared, "scope": scope}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_context_clear"}
