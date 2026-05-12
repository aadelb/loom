"""Typed configuration accessors for loom.config.

Wraps loom.config.get_config() with domain-specific accessor functions.
"""

from __future__ import annotations

import os
from typing import Any


def _cfg() -> dict[str, Any]:
    """Get global config dict (lazy import to avoid circular deps)."""
    from loom.config import get_config

    return get_config()


# Network Timeouts
def external_timeout() -> float:
    return float(_cfg().get("EXTERNAL_TIMEOUT_SECS", 30))


def llm_timeout() -> float:
    return float(_cfg().get("LLM_TIMEOUT_SECS", 120))


def fetch_timeout() -> float:
    return float(_cfg().get("FETCH_TIMEOUT_SECS", 20))


# Limits
def max_chars() -> int:
    return int(_cfg().get("MAX_CHARS_HARD_CAP", 200_000))


def max_spider_urls() -> int:
    return int(_cfg().get("MAX_SPIDER_URLS", 100))


def max_search_results() -> int:
    return int(_cfg().get("MAX_SEARCH_RESULTS", 10))


def spider_concurrency() -> int:
    return int(_cfg().get("SPIDER_CONCURRENCY", 10))


# LLM
def llm_cascade_order() -> list[str]:
    return _cfg().get(
        "LLM_CASCADE_ORDER",
        ["groq", "nvidia", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm"],
    )


def default_llm_model() -> str:
    return str(_cfg().get("LLM_DEFAULT_CHAT_MODEL", ""))


def default_embed_model() -> str:
    return str(_cfg().get("LLM_DEFAULT_EMBED_MODEL", ""))


def default_temperature() -> float:
    return float(_cfg().get("DEFAULT_TEMPERATURE", 0.7))


def llm_max_parallel() -> int:
    return int(_cfg().get("LLM_MAX_PARALLEL", 12))


# Features
def tor_enabled() -> bool:
    return bool(_cfg().get("TOR_ENABLED", False))


def cache_enabled() -> bool:
    return bool(_cfg().get("CACHE_ENABLED", True))


def debug_mode() -> bool:
    return bool(_cfg().get("DEBUG", False) or os.environ.get("LOOM_DEBUG"))


def fetch_auto_escalate() -> bool:
    return bool(_cfg().get("FETCH_AUTO_ESCALATE", True))


# Paths
def cache_dir() -> str:
    path = _cfg().get("CACHE_DIR", "~/.cache/loom")
    return os.path.expanduser(str(path))


def sessions_dir() -> str:
    path = _cfg().get("SESSION_DIR", "~/.loom/sessions")
    return os.path.expanduser(str(path))
