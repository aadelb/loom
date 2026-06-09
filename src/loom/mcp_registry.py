"""MCP server registry with atomic JSON persistence.

Provides functions to manage a registry of external MCP servers that Loom can
discover and route to. Registry is stored as JSON in ~/.loom/mcp_servers.json
with atomic write semantics (uuid tmp → os.replace) to prevent corruption
from concurrent writes.

Registry schema:
  {
    "server_name": {
      "url": "http://...",
      "transport": "streamable-http",
      "enabled": true,
      "status": "reachable|unreachable|unknown",
      "last_check_ts": "2026-06-09T15:30:45.123Z",
      "last_check_latency_ms": 42,
      "tool_count": 15,
      "error": null
    },
    ...
  }
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.mcp_registry")


def get_registry_path() -> Path:
    """Get the MCP server registry file path (~/.loom/mcp_servers.json)."""
    loom_dir = Path("~/.loom").expanduser()
    loom_dir.mkdir(parents=True, exist_ok=True)
    return loom_dir / "mcp_servers.json"


def load_registry() -> dict[str, dict[str, Any]]:
    """Load the MCP server registry from disk.

    Returns:
        Dict mapping server name → server entry dict. Returns {} if file
        doesn't exist or is malformed.
    """
    path = get_registry_path()
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            log.warning("registry_corrupted: not a dict")
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        log.warning("registry_load_failed: %s", e)
        return {}


def save_registry(registry: dict[str, dict[str, Any]]) -> None:
    """Save the MCP server registry to disk with atomic writes.

    Uses a temporary file + os.replace to ensure atomicity and prevent
    corruption from concurrent writes.

    Args:
        registry: Dict mapping server name → server entry dict

    Raises:
        OSError: if write fails after retries
    """
    path = get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: uuid tmp → os.replace
    tmp_path = path.parent / f".{path.name}.{uuid.uuid4().hex[:8]}"
    try:
        with open(tmp_path, "w") as f:
            json.dump(registry, f, indent=2, default=str)
        os.replace(tmp_path, path)
        log.debug("registry_saved path=%s", path)
    except Exception as e:
        log.error("registry_save_failed: %s", e)
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def validate_registry_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Validate a registry entry has required keys.

    Ensures the entry conforms to the schema and fills in defaults for
    optional status fields.

    Args:
        entry: Entry dict from the registry

    Returns:
        Validated entry dict

    Raises:
        ValueError: if required keys are missing
    """
    required = {"url", "transport", "enabled"}
    missing = required - set(entry.keys())
    if missing:
        raise ValueError(f"entry missing required keys: {missing}")

    # Ensure status fields exist (with defaults if missing)
    return {
        **entry,
        "status": entry.get("status", "unknown"),
        "last_check_ts": entry.get("last_check_ts"),
        "last_check_latency_ms": entry.get("last_check_latency_ms"),
        "tool_count": entry.get("tool_count"),
        "error": entry.get("error"),
    }


def get_registry_entry(name: str) -> dict[str, Any] | None:
    """Get a single registry entry by name.

    Args:
        name: Server name

    Returns:
        Entry dict if found, None otherwise
    """
    registry = load_registry()
    return registry.get(name)


def set_registry_entry(name: str, entry: dict[str, Any]) -> None:
    """Set or update a registry entry (immutable update).

    Loads current registry, updates/adds the entry, and saves atomically.
    This ensures immutability — we never modify in-place.

    Args:
        name: Server name
        entry: Entry dict with url, transport, enabled, etc.

    Raises:
        ValueError: if entry is invalid
    """
    validated = validate_registry_entry(entry)
    registry = load_registry()
    registry[name] = validated
    save_registry(registry)


def delete_registry_entry(name: str) -> None:
    """Delete a registry entry (immutable delete).

    Loads current registry, removes the entry, and saves atomically.

    Args:
        name: Server name
    """
    registry = load_registry()
    registry.pop(name, None)
    save_registry(registry)


def update_registry_entry(name: str, updates: dict[str, Any]) -> None:
    """Update specific fields of a registry entry (immutable update).

    Loads current registry, updates specified fields, and saves atomically.
    Only updates keys present in `updates`; other fields are preserved.

    Args:
        name: Server name
        updates: Dict of fields to update

    Raises:
        ValueError: if server doesn't exist
    """
    registry = load_registry()
    if name not in registry:
        raise ValueError(f"server '{name}' not found")

    # Immutable update: create new dict with updates merged in
    entry = {**registry[name], **updates}
    validated = validate_registry_entry(entry)
    registry[name] = validated
    save_registry(registry)


def format_registry_entry(name: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Format a registry entry for display (adds name, computed fields).

    Args:
        name: Server name
        entry: Entry dict

    Returns:
        Formatted dict suitable for JSON response
    """
    return {
        "name": name,
        "url": entry.get("url", ""),
        "transport": entry.get("transport", "streamable-http"),
        "enabled": entry.get("enabled", True),
        "status": entry.get("status", "unknown"),
        "last_check_ts": entry.get("last_check_ts"),
        "last_check_latency_ms": entry.get("last_check_latency_ms"),
        "tool_count": entry.get("tool_count"),
        "error": entry.get("error"),
    }
