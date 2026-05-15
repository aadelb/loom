"""Secret Manager for API key validation, rotation, and expiration tracking.

Provides centralized management of API keys for all LLM and search providers:
- Format validation (prefix check, length, base64 validity)
- Rotation without server restart
- Expiration tracking and alerts
- Last-used timestamp monitoring
- Health status reporting

Public API:
    SecretManager               Manager class (singleton)
    get_secret_manager()        Get or create singleton instance
    research_secret_health()    MCP tool: return key health status
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from threading import Lock

logger = logging.getLogger("loom.secret_manager")

# Key configuration: provider_name -> (env_var, prefix, min_length, rotation_supported)
KEY_CONFIGS: dict[str, dict[str, Any]] = {
    # LLM Providers (8 total)
    "groq": {
        "env_var": "GROQ_API_KEY",
        "prefix": "gsk_",
        "min_length": 20,
        "rotation_supported": True,
        "description": "Groq API key for LLM inference",
    },
    "nvidia_nim": {
        "env_var": "NVIDIA_NIM_API_KEY",
        "prefix": "nvapi-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "NVIDIA NIM free tier API key",
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
        "prefix": "sk-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "DeepSeek API key",
    },
    "gemini": {
        "env_var": "GOOGLE_AI_KEY",
        "prefix": "AIzaSy",
        "min_length": 30,
        "rotation_supported": True,
        "description": "Google Gemini API key",
    },
    "moonshot": {
        "env_var": "MOONSHOT_API_KEY",
        "prefix": "sk-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "Moonshot (Kimi) API key",
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "prefix": "sk-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "OpenAI API key",
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "prefix": "sk-ant-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "Anthropic Claude API key",
    },
    "vllm": {
        "env_var": "VLLM_ENDPOINT",
        "prefix": "http",
        "min_length": 10,
        "rotation_supported": False,
        "description": "Local vLLM endpoint URL",
    },
    # Search Providers (6 key-required, 5 always-available)
    "exa": {
        "env_var": "EXA_API_KEY",
        "prefix": "exa-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "Exa semantic search API key",
    },
    "tavily": {
        "env_var": "TAVILY_API_KEY",
        "prefix": "tvly-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "Tavily search API key",
    },
    "firecrawl": {
        "env_var": "FIRECRAWL_API_KEY",
        "prefix": "fc-",
        "min_length": 20,
        "rotation_supported": True,
        "description": "Firecrawl API key",
    },
    "brave": {
        "env_var": "BRAVE_API_KEY",
        "prefix": "BSA",
        "min_length": 10,
        "rotation_supported": True,
        "description": "Brave search API key",
    },
    "newsapi": {
        "env_var": "NEWS_API_KEY",
        "prefix": "",
        "min_length": 20,
        "rotation_supported": True,
        "description": "NewsAPI key",
    },
    "coinmarketcap": {
        "env_var": "COINMARKETCAP_API_KEY",
        "prefix": "",
        "min_length": 20,
        "rotation_supported": True,
        "description": "CoinMarketCap API key",
    },
}

# Always-available providers (no key required)
ALWAYS_AVAILABLE: set[str] = {"ddgs", "arxiv", "wikipedia", "hackernews", "reddit"}


class SecretManager:
    """Centralized API key management with validation and rotation.

    Provides:
    - Format validation (prefix, length, base64 check)
    - In-memory rotation (no restart required)
    - Last-used timestamp tracking
    - Expiration alerting (>7 days without use)
    - Health status reporting
    """

    def __init__(self) -> None:
        """Initialize the SecretManager singleton."""
        self._lock = Lock()
        self._keys: dict[str, Optional[str]] = {}  # provider -> key value
        self._last_used: dict[str, Optional[datetime]] = {}  # provider -> last_used timestamp
        self._validated: dict[str, bool] = {}  # provider -> validation result
        self._validation_errors: dict[str, str] = {}  # provider -> error message

        # Load all keys from environment
        self._load_keys_from_env()

        # Initial validation
        self.validate_all_keys()

    def _load_keys_from_env(self) -> None:
        """Load all configured keys from environment variables."""
        for provider_name, config in KEY_CONFIGS.items():
            env_var = config["env_var"]
            value = os.environ.get(env_var, "").strip()
            self._keys[provider_name] = value if value else None
            self._last_used[provider_name] = None  # Initialize timestamps

    def _is_valid_base64(self, value: str) -> bool:
        """Check if a string is valid base64.

        Args:
            value: String to check

        Returns:
            True if valid base64-like, False otherwise
        """
        # Only check if value has padding or is pure alphanumeric
        if not value:
            return False
        # Most API keys are alphanumeric + hyphens/underscores
        return bool(re.match(r"^[a-zA-Z0-9_\-/.]+$", value))

    def validate_key(self, provider: str) -> dict[str, Any]:
        """Validate a single API key.

        Args:
            provider: Provider name (e.g., "groq", "exa")

        Returns:
            Dict with:
            - valid: bool
            - present: bool
            - error: str | None
            - format_check: bool
            - length_check: bool
            - prefix_check: bool | None
        """
        if provider not in KEY_CONFIGS:
            return {
                "valid": False,
                "present": False,
                "error": f"Unknown provider: {provider}",
                "format_check": False,
                "length_check": False,
                "prefix_check": None,
            }

        config = KEY_CONFIGS[provider]
        key = self._keys.get(provider)

        # Check presence
        if not key:
            self._validated[provider] = False
            self._validation_errors[provider] = "Key not present in environment"
            return {
                "valid": False,
                "present": False,
                "error": "Key not present",
                "format_check": False,
                "length_check": False,
                "prefix_check": None,
            }

        # Check length
        min_length = config.get("min_length", 10)
        length_check = len(key) >= min_length
        if not length_check:
            self._validated[provider] = False
            self._validation_errors[provider] = (
                f"Key length {len(key)} < {min_length} minimum"
            )
            return {
                "valid": False,
                "present": True,
                "error": f"Key too short ({len(key)} < {min_length})",
                "format_check": False,
                "length_check": False,
                "prefix_check": None,
            }

        # Check prefix (if configured)
        prefix = config.get("prefix", "")
        prefix_check = None
        if prefix:
            prefix_check = key.startswith(prefix)
            if not prefix_check:
                self._validated[provider] = False
                self._validation_errors[provider] = (
                    f"Key does not start with expected prefix '{prefix}'"
                )
                return {
                    "valid": False,
                    "present": True,
                    "error": f"Invalid prefix (expected '{prefix}')",
                    "format_check": self._is_valid_base64(key),
                    "length_check": True,
                    "prefix_check": False,
                }

        # Check base64 validity (alphanumeric + hyphens/underscores)
        format_check = self._is_valid_base64(key)
        if not format_check:
            self._validated[provider] = False
            self._validation_errors[provider] = "Key contains invalid characters"
            return {
                "valid": False,
                "present": True,
                "error": "Invalid character in key",
                "format_check": False,
                "length_check": True,
                "prefix_check": prefix_check,
            }

        # All checks passed
        self._validated[provider] = True
        self._validation_errors[provider] = ""
        return {
            "valid": True,
            "present": True,
            "error": None,
            "format_check": True,
            "length_check": True,
            "prefix_check": prefix_check,
        }

    def validate_all_keys(self) -> dict[str, dict[str, Any]]:
        """Validate all configured API keys.

        Returns:
            Dict mapping provider_name -> validation_result
        """
        with self._lock:
            results: dict[str, dict[str, Any]] = {}
            for provider in KEY_CONFIGS:
                results[provider] = self.validate_key(provider)

            # Log summary
            valid_count = sum(1 for r in results.values() if r["valid"])
            present_count = sum(1 for r in results.values() if r["present"])
            logger.info(
                "validate_all_keys total_providers=%d valid=%d present=%d",
                len(results),
                valid_count,
                present_count,
            )

            return results

    def get_key(self, provider: str) -> Optional[str]:
        """Get current API key for a provider.

        Args:
            provider: Provider name

        Returns:
            API key string or None if not found/invalid
        """
        with self._lock:
            # Update last-used timestamp
            if provider in self._keys and self._keys[provider]:
                self._last_used[provider] = datetime.now(UTC)

            return self._keys.get(provider)

    def rotate_key(self, provider: str, new_key: str) -> bool:
        """Rotate API key for a provider without restart.

        Args:
            provider: Provider name
            new_key: New API key value

        Returns:
            True if rotation successful, False otherwise
        """
        if provider not in KEY_CONFIGS:
            logger.warning("rotate_key unknown_provider provider=%s", provider)
            return False

        config = KEY_CONFIGS[provider]
        if not config.get("rotation_supported", False):
            logger.warning(
                "rotate_key rotation_not_supported provider=%s", provider
            )
            return False

        with self._lock:
            old_key = self._keys.get(provider, "")
            self._keys[provider] = new_key
            self._last_used[provider] = datetime.now(UTC)

            # Validate new key
            validation = self.validate_key(provider)
            if not validation["valid"]:
                # Revert on validation failure
                self._keys[provider] = old_key
                logger.error(
                    "rotate_key validation_failed provider=%s error=%s",
                    provider,
                    validation.get("error"),
                )
                return False

            logger.info(
                "rotate_key_success provider=%s key_length=%d",
                provider,
                len(new_key) if new_key else 0,
            )
            return True

    def get_expiry(self, provider: str) -> Optional[datetime]:
        """Get estimated key expiration date (tracking only).

        Note: Most API providers don't publish expiration dates.
        This tracks last-used timestamp to alert on stale keys.

        Args:
            provider: Provider name

        Returns:
            None (expiration date tracking not yet implemented for most providers)
        """
        # Placeholder for future expiration tracking
        # Could be extended to store expiration dates per provider
        return None

    def get_last_used(self, provider: str) -> Optional[datetime]:
        """Get last-used timestamp for a key.

        Args:
            provider: Provider name

        Returns:
            Last-used datetime or None
        """
        with self._lock:
            return self._last_used.get(provider)

    def get_health(self) -> dict[str, Any]:
        """Get overall key health status.

        Returns:
            Dict with:
            - overall_status: "healthy", "degraded", or "unhealthy"
            - valid_keys: Number of valid keys present
            - missing_keys: Number of missing keys
            - stale_keys: List of keys not used in >7 days
            - providers: Dict of provider details
            - timestamp: ISO 8601 timestamp
        """
        with self._lock:
            results: dict[str, dict[str, Any]] = {}
            valid_count = 0
            missing_count = 0
            stale_keys: list[str] = []
            stale_threshold = timedelta(days=7)
            now = datetime.now(UTC)

            for provider in KEY_CONFIGS:
                validation = self._validated.get(provider, False)
                last_used = self._last_used.get(provider)
                is_stale = False

                if not self._keys.get(provider):
                    missing_count += 1
                    status = "missing"
                elif not validation:
                    status = "invalid"
                else:
                    valid_count += 1
                    # Check for staleness
                    if last_used and (now - last_used) > stale_threshold:
                        is_stale = True
                        stale_keys.append(provider)
                        status = "stale"
                    else:
                        status = "valid"

                results[provider] = {
                    "status": status,
                    "present": bool(self._keys.get(provider)),
                    "valid": validation,
                    "last_used": last_used.isoformat() if last_used else None,
                    "error": self._validation_errors.get(provider, ""),
                }

            # Overall status determination
            if valid_count == 0:
                overall_status = "unhealthy"
            elif stale_keys or missing_count > 0:
                overall_status = "degraded"
            else:
                overall_status = "healthy"

            # Log alerts for stale keys
            for provider in stale_keys:
                logger.warning(
                    "stale_key_alert provider=%s days_since_use=%d",
                    provider,
                    (now - self._last_used.get(provider, now)).days,
                )

            return {
                "overall_status": overall_status,
                "valid_keys": valid_count,
                "missing_keys": missing_count,
                "stale_keys": stale_keys,
                "stale_threshold_days": 7,
                "total_providers": len(KEY_CONFIGS),
                "providers": results,
                "always_available": sorted(ALWAYS_AVAILABLE),
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Singleton instance
_manager: Optional[SecretManager] = None
_manager_lock = Lock()


def get_secret_manager() -> SecretManager:
    """Get or create the SecretManager singleton.

    Returns:
        SecretManager instance
    """
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = SecretManager()
    return _manager


async def research_secret_health() -> dict[str, Any]:
    """MCP tool: Return API key health status for all providers.

    Provides visibility into:
    - Which keys are present vs missing
    - Format validation results
    - Last successful use timestamp
    - Stale key alerts (>7 days unused)

    Returns:
        Dict with:
        - overall_status: "healthy", "degraded", or "unhealthy"
        - valid_keys: Count of valid keys
        - missing_keys: Count of missing keys
        - stale_keys: List of keys not used in >7 days
        - providers: Dict of provider health details
        - timestamp: ISO 8601 timestamp
    """
    manager = get_secret_manager()
    health = manager.get_health()

    return {
        "overall_status": health["overall_status"],
        "valid_keys": health["valid_keys"],
        "missing_keys": health["missing_keys"],
        "stale_keys": health["stale_keys"],
        "stale_threshold_days": health["stale_threshold_days"],
        "total_providers": health["total_providers"],
        "providers": health["providers"],
        "always_available": health["always_available"],
        "timestamp": health["timestamp"],
    }
