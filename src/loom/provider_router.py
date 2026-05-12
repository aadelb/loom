"""LLM provider routing and cascade logic.

Centralizes provider selection, availability checking, and cascade order.
Used by llm.py and multi_llm.py to determine which LLM provider to use.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from loom.config import CONFIG, load_config

logger = logging.getLogger("loom.provider_router")

DEFAULT_CASCADE: list[str] = [
    "groq",
    "nvidia",
    "deepseek",
    "gemini",
    "moonshot",
    "openai",
    "anthropic",
    "vllm",
]

PROVIDER_ENV_KEYS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_NIM_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GOOGLE_AI_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "vllm": "VLLM_ENDPOINT",
}


def is_provider_available(provider: str) -> bool:
    """Check if a provider has credentials configured."""
    env_key = PROVIDER_ENV_KEYS.get(provider, "")
    return bool(env_key and os.environ.get(env_key, "").strip())


def get_available_providers(cascade: list[str] | None = None) -> list[str]:
    """Return list of providers with credentials configured."""
    order = cascade or _get_cascade_order()
    return [p for p in order if is_provider_available(p)]


def _get_cascade_order() -> list[str]:
    """Get cascade order from config or default."""
    if not CONFIG:
        load_config()
    return CONFIG.get("LLM_CASCADE_ORDER", DEFAULT_CASCADE)


def select_provider(
    *,
    preferred: str | None = None,
    cascade: list[str] | None = None,
    exclude: set[str] | None = None,
) -> str | None:
    """Select the best available provider.

    Args:
        preferred: Try this provider first
        cascade: Custom cascade order
        exclude: Providers to skip (recently failed)

    Returns:
        Provider name or None
    """
    exclude = exclude or set()
    if preferred and preferred not in exclude and is_provider_available(preferred):
        return preferred
    for provider in get_available_providers(cascade):
        if provider not in exclude:
            return provider
    return None


def get_provider_config(provider: str) -> dict[str, Any]:
    """Get configuration status for a specific provider."""
    env_key = PROVIDER_ENV_KEYS.get(provider, "")
    return {
        "provider": provider,
        "env_key": env_key,
        "available": is_provider_available(provider),
        "api_key_set": bool(os.environ.get(env_key, "")),
    }


def cascade_status() -> list[dict[str, Any]]:
    """Return status of all providers in cascade order."""
    return [get_provider_config(p) for p in DEFAULT_CASCADE]
