"""Feature flags system for Loom MCP server.

Supports both Redis-backed (distributed) and in-memory (local) flag storage.
Loads initial state from LOOM_FEATURE_FLAGS environment variable (comma-separated
list of enabled flags at startup).

Public API:
    FeatureFlags           Main class for flag management
    get_feature_flags()    Singleton accessor
    research_feature_flags MCP tool: list/enable/disable flags
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal

logger = logging.getLogger("loom.feature_flags")

# Default flag configuration
DEFAULT_FLAGS: dict[str, bool] = {
    "token_economy": False,  # Opt-in billing
    "auto_model_routing": True,
    "refusal_auto_reframe": True,
    "content_sanitizer": True,
    "per_tool_rate_limit": True,
    "lazy_loading": False,
    "batch_queue": True,
    "experimental_privacy_tools": False,
}

# Global singleton instance
_instance: FeatureFlags | None = None


class FeatureFlags:
    """Feature flag manager with optional Redis backing.

    Maintains a dict of feature flags with boolean values.
    Attempts to use Redis for distributed state, falls back to in-memory dict.
    """

    def __init__(self) -> None:
        """Initialize feature flags from defaults + environment variable."""
        self._flags: dict[str, bool] = dict(DEFAULT_FLAGS)
        self._redis_available = False
        self._redis_client: Any = None

        # Try to import and connect to Redis
        try:
            import redis

            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self._redis_client = redis.from_url(redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
                # Test connection
                self._redis_client.ping()
                self._redis_available = True
                logger.info("feature_flags_redis_connected redis_url=%s", redis_url)
                # Load from Redis
                self._load_from_redis()
            else:
                logger.debug("feature_flags_redis_not_configured REDIS_URL not set")
        except ImportError:
            logger.debug("feature_flags_redis_unavailable redis module not installed")
        except Exception as e:
            logger.warning("feature_flags_redis_connection_failed error=%s", e)

        # Load from environment variable (overrides defaults and Redis)
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load enabled flags from LOOM_FEATURE_FLAGS environment variable.

        Expected format: comma-separated flag names (e.g. "token_economy,lazy_loading")
        """
        env_flags = os.getenv("LOOM_FEATURE_FLAGS", "")
        if not env_flags:
            return

        enabled_flags = [f.strip() for f in env_flags.split(",") if f.strip()]
        for flag in enabled_flags:
            if flag in self._flags:
                self._flags[flag] = True
                logger.debug("feature_flag_enabled_from_env flag=%s", flag)
            else:
                logger.warning("feature_flag_unknown_from_env flag=%s", flag)

    def _load_from_redis(self) -> None:
        """Load all flags from Redis (if available)."""
        if not self._redis_available or not self._redis_client:
            return

        try:
            key = "loom:feature_flags"
            raw = self._redis_client.get(key)
            if raw:
                loaded = json.loads(raw)
                self._flags.update(loaded)
                logger.debug("feature_flags_loaded_from_redis count=%d", len(loaded))
        except Exception as e:
            logger.warning("feature_flags_redis_load_failed error=%s", e)

    def _save_to_redis(self) -> None:
        """Persist flags to Redis (if available)."""
        if not self._redis_available or not self._redis_client:
            return

        try:
            key = "loom:feature_flags"
            self._redis_client.set(key, json.dumps(self._flags))
            logger.debug("feature_flags_saved_to_redis count=%d", len(self._flags))
        except Exception as e:
            logger.warning("feature_flags_redis_save_failed error=%s", e)

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: Name of the flag to check.

        Returns:
            True if flag is enabled, False if disabled or unknown.
        """
        return self._flags.get(flag_name, False)

    def enable(self, flag_name: str) -> bool:
        """Enable a feature flag.

        Args:
            flag_name: Name of the flag to enable.

        Returns:
            True if flag was enabled (or already enabled), False if unknown.
        """
        if flag_name not in self._flags:
            logger.warning("feature_flag_unknown flag=%s action=enable", flag_name)
            return False

        if not self._flags[flag_name]:
            self._flags[flag_name] = True
            self._save_to_redis()
            logger.info("feature_flag_enabled flag=%s", flag_name)

        return True

    def disable(self, flag_name: str) -> bool:
        """Disable a feature flag.

        Args:
            flag_name: Name of the flag to disable.

        Returns:
            True if flag was disabled (or already disabled), False if unknown.
        """
        if flag_name not in self._flags:
            logger.warning("feature_flag_unknown flag=%s action=disable", flag_name)
            return False

        if self._flags[flag_name]:
            self._flags[flag_name] = False
            self._save_to_redis()
            logger.info("feature_flag_disabled flag=%s", flag_name)

        return True

    def list_all(self) -> dict[str, bool]:
        """Return all feature flags and their current state.

        Returns:
            Dict mapping flag names to boolean values.
        """
        return dict(self._flags)

    def reset_to_defaults(self) -> dict[str, bool]:
        """Reset all flags to their default values.

        Returns:
            Dict of flags after reset.
        """
        self._flags = dict(DEFAULT_FLAGS)
        self._save_to_redis()
        logger.info("feature_flags_reset_to_defaults")
        return dict(self._flags)


def get_feature_flags() -> FeatureFlags:
    """Get or create the global feature flags singleton."""
    global _instance
    if _instance is None:
        _instance = FeatureFlags()
    return _instance


# ─── MCP Tool ───────────────────────────────────────────────────────────────────


def research_feature_flags(
    action: Literal["list", "enable", "disable"] = "list",
    flag: str | None = None,
) -> dict[str, Any]:
    """Manage feature flags.

    Args:
        action: Action to perform ("list", "enable", or "disable").
        flag: Flag name (required for "enable" and "disable" actions).

    Returns:
        Dict with action results or error message.

        For "list": returns {"flags": {...}, "timestamp": "..."}
        For "enable"/"disable": returns {"flag": "...", "enabled": bool, "timestamp": "..."}
                               or {"error": "..."} on failure
    """
    ff = get_feature_flags()

    if action == "list":
        return {
            "action": "list",
            "flags": ff.list_all(),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    if action == "enable":
        if not flag:
            return {"error": 'flag parameter required for "enable" action'}
        success = ff.enable(flag)
        if not success:
            return {"error": f"unknown flag: {flag}"}
        return {
            "action": "enable",
            "flag": flag,
            "enabled": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    if action == "disable":
        if not flag:
            return {"error": 'flag parameter required for "disable" action'}
        success = ff.disable(flag)
        if not success:
            return {"error": f"unknown flag: {flag}"}
        return {
            "action": "disable",
            "flag": flag,
            "enabled": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return {"error": f"unknown action: {action}. Must be 'list', 'enable', or 'disable'."}
