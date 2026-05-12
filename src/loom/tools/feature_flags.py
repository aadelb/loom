"""Feature flags system for toggling tools on/off without redeployment."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.feature_flags")


class FlagCheckResponse(TypedDict, total=False):
    """Typed response for flag check operations."""
    flag: str
    enabled: bool
    description: str
    last_toggled: str | None
    error: str
    available: list[str]


class FlagToggleResponse(TypedDict, total=False):
    """Typed response for flag toggle operations."""
    flag: str
    enabled: bool
    toggled_at: str
    description: str
    error: str
    available: list[str]


class FlagListResponse(TypedDict, total=False):
    """Typed response for flag list operations."""
    flags: list[dict[str, Any]]
    total: int
    enabled_count: int
    disabled_count: int
    error: str

# Default feature flags
DEFAULT_FLAGS = {
    "dark_web_enrichment": True,
    "cli_fallback": True,
    "dspy_decomposition": True,
    "auto_escalation": True,
}

FLAGS_FILE = Path.home() / ".loom" / "feature_flags.json"


def _ensure_flags_file() -> None:
    """Create feature flags file with defaults if missing."""
    FLAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FLAGS_FILE.exists():
        flags = {name: {"enabled": enabled, "description": "", "last_toggled": None}
                 for name, enabled in DEFAULT_FLAGS.items()}
        try:
            _write_flags_atomic(flags)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to initialize flags file: {e}", exc_info=True)
            raise


def _load_flags() -> dict[str, Any]:
    """Load flags from file with validation."""
    _ensure_flags_file()
    try:
        content = FLAGS_FILE.read_text()
        flags = json.loads(content)
        if not isinstance(flags, dict):
            raise ValueError("Flags file must contain a JSON object")
        return flags
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in flags file: {e}", exc_info=True)
        raise


def _write_flags_atomic(flags: dict[str, Any]) -> None:
    """Write flags to file atomically with fsync.

    Uses atomic rename pattern: write temp file, fsync, then rename.
    """
    FLAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FLAGS_FILE.with_stem(FLAGS_FILE.stem + f".tmp.{os.getpid()}")
    try:
        # Write to temp file
        tmp.write_text(json.dumps(flags, indent=2))
        # Fsync to ensure data is written to disk
        with tmp.open("r") as f:
            os.fsync(f.fileno())
        # Atomic rename
        os.replace(str(tmp), str(FLAGS_FILE))
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write flags atomically: {e}", exc_info=True)
        if tmp.exists():
            tmp.unlink()
        raise


def _save_flags(flags: dict[str, Any]) -> None:
    """Save flags to file atomically."""
    _write_flags_atomic(flags)


@handle_tool_errors("research_flag_check")
def research_flag_check(flag_name: str) -> FlagCheckResponse:
    """Check if a feature flag is enabled.

    Args:
        flag_name: Name of the flag to check

    Returns:
        Dict with flag status: {flag, enabled, description, last_toggled}
    """
    try:
        flags = _load_flags()
        if flag_name not in flags:
            return {"error": f"flag '{flag_name}' not found", "available": list(flags.keys())}

        flag_data = flags[flag_name]
        return {
            "flag": flag_name,
            "enabled": flag_data["enabled"],
            "description": flag_data.get("description", ""),
            "last_toggled": flag_data.get("last_toggled"),
        }
    except Exception as exc:
        logger.error(f"Error checking flag '{flag_name}': {exc}", exc_info=True)
        return {"error": str(exc)}


@handle_tool_errors("research_flag_toggle")
def research_flag_toggle(flag_name: str, enabled: bool, description: str = "") -> FlagToggleResponse:
    """Enable or disable a feature flag.

    Args:
        flag_name: Name of the flag to toggle
        enabled: New enabled state
        description: Optional description of the change

    Returns:
        Dict with result: {flag, enabled, toggled_at, description}
    """
    try:
        flags = _load_flags()
        if flag_name not in flags:
            return {"error": f"flag '{flag_name}' not found", "available": list(flags.keys())}

        now = datetime.now(UTC).isoformat()
        flags[flag_name]["enabled"] = enabled
        if description:
            flags[flag_name]["description"] = description
        flags[flag_name]["last_toggled"] = now

        _save_flags(flags)
        logger.info(f"flag_toggled: {flag_name}={enabled} at {now}")

        return {
            "flag": flag_name,
            "enabled": enabled,
            "toggled_at": now,
            "description": flags[flag_name].get("description", ""),
        }
    except Exception as exc:
        logger.error(f"Error toggling flag '{flag_name}': {exc}", exc_info=True)
        return {"error": str(exc)}


@handle_tool_errors("research_flag_list")
def research_flag_list() -> FlagListResponse:
    """List all feature flags and their status.

    Returns:
        Dict with flags array and summary counts
    """
    try:
        flags = _load_flags()
        flags_list = [
            {
                "name": name,
                "enabled": data["enabled"],
                "description": data.get("description", ""),
                "last_toggled": data.get("last_toggled"),
            }
            for name, data in sorted(flags.items())
        ]

        enabled_count = sum(1 for f in flags_list if f["enabled"])
        disabled_count = len(flags_list) - enabled_count

        return {
            "flags": flags_list,
            "total": len(flags_list),
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
        }
    except Exception as exc:
        logger.error(f"Error listing flags: {exc}", exc_info=True)
        return {"error": str(exc)}
