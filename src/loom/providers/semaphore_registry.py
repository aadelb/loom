"""Provider semaphore registry.

Centralized management of asyncio.Semaphore instances for rate-limiting
concurrent requests to external providers. Each provider gets one shared
semaphore, created lazily on first access.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("loom.providers.semaphore_registry")

_semaphores: dict[str, asyncio.Semaphore] = {}

# Default concurrency limits per provider
DEFAULT_LIMITS: dict[str, int] = {
    "groq": 30,
    "nvidia_nim": 12,
    "deepseek": 10,
    "gemini": 10,
    "moonshot": 10,
    "openai": 20,
    "anthropic": 10,
    "vllm": 50,
    "exa": 10,
    "tavily": 10,
    "firecrawl": 5,
    "brave": 10,
    "ddgs": 5,
}


def get_semaphore(provider: str, *, max_concurrent: int | None = None) -> asyncio.Semaphore:
    """Get or create a semaphore for a provider.

    Args:
        provider: Provider name (e.g., "groq", "nvidia_nim")
        max_concurrent: Override default concurrency limit
    """
    if provider not in _semaphores:
        limit = max_concurrent or DEFAULT_LIMITS.get(provider, 10)
        _semaphores[provider] = asyncio.Semaphore(limit)
        logger.debug("semaphore_created provider=%s limit=%d", provider, limit)
    return _semaphores[provider]


def reset(provider: str | None = None) -> None:
    """Reset semaphore(s) — primarily for testing."""
    if provider:
        _semaphores.pop(provider, None)
    else:
        _semaphores.clear()


def active_providers() -> dict[str, int]:
    """Return active providers and their semaphore values."""
    return {name: sem._value for name, sem in _semaphores.items()}
