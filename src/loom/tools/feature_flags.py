"""Feature flags system for toggling tools on/off without redeployment."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.feature_flags")

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
        FLAGS_FILE.write_text(json.dumps(flags, indent=2))


def _load_flags() -> dict[str, Any]:
    """Load flags from file."""
    _ensure_flags_file()
    return json.loads(FLAGS_FILE.read_text())


def _save_flags(flags: dict[str, Any]) -> None:
    """Save flags to file atomically."""
    _ensure_flags_file()
    tmp = FLAGS_FILE.with_stem(FLAGS_FILE.stem + ".tmp")
    tmp.write_text(json.dumps(flags, indent=2))
    tmp.replace(FLAGS_FILE)


async def research_flag_check(flag_name: str) -> dict[str, Any]:
    """Check if a feature flag is enabled.

    Args:
        flag_name: Name of the flag to check

    Returns:
        Dict with flag status: {flag, enabled, description, last_toggled}
    """
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


async def research_flag_toggle(flag_name: str, enabled: bool, description: str = "") -> dict[str, Any]:
    """Enable or disable a feature flag.

    Args:
        flag_name: Name of the flag to toggle
        enabled: New enabled state
        description: Optional description of the change

    Returns:
        Dict with result: {flag, enabled, toggled_at, description}
    """
    flags = _load_flags()
    if flag_name not in flags:
        return {"error": f"flag '{flag_name}' not found", "available": list(flags.keys())}

    now = datetime.now(UTC).isoformat()
    flags[flag_name]["enabled"] = enabled
    if description:
        flags[flag_name]["description"] = description
    flags[flag_name]["last_toggled"] = now

    _save_flags(flags)
    logger.info("flag_toggled", flag=flag_name, enabled=enabled, timestamp=now)

    return {
        "flag": flag_name,
        "enabled": enabled,
        "toggled_at": now,
        "description": flags[flag_name].get("description", ""),
    }


async def research_flag_list() -> dict[str, Any]:
    """List all feature flags and their status.

    Returns:
        Dict with flags array and summary counts
    """
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
