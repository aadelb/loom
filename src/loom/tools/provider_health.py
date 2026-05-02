"""Provider health monitoring tools — track LLM and search provider availability.

Monitors 10 providers: groq, nvidia_nim, deepseek, gemini, moonshot, openai,
anthropic, exa, tavily, brave. Tracks uptime, response times, and recommends
best provider for specific task types.
"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

logger_name = "loom.tools.provider_health"

# Module-level health history (max 1000 events per provider)
_HEALTH_HISTORY: dict[str, deque[dict[str, Any]]] = {}
_MAX_EVENTS = 1000

# Provider metadata for recommendations
_PROVIDER_TRAITS = {
    "groq": {"speed": 95, "cost": 90, "accuracy": 75, "reasoning": 70},
    "nvidia_nim": {"speed": 85, "cost": 100, "accuracy": 75, "reasoning": 70},
    "deepseek": {"speed": 60, "cost": 70, "accuracy": 85, "reasoning": 95},
    "gemini": {"speed": 80, "cost": 60, "accuracy": 88, "reasoning": 85},
    "moonshot": {"speed": 75, "cost": 70, "accuracy": 80, "reasoning": 80},
    "openai": {"speed": 70, "cost": 30, "accuracy": 95, "reasoning": 90},
    "anthropic": {"speed": 65, "cost": 20, "accuracy": 95, "reasoning": 95},
    "exa": {"speed": 85, "cost": 50, "accuracy": 80, "reasoning": 0},
    "tavily": {"speed": 80, "cost": 60, "accuracy": 75, "reasoning": 0},
    "brave": {"speed": 90, "cost": 100, "accuracy": 70, "reasoning": 0},
}

_TASK_PREFERENCES = {
    "general": ["groq", "openai", "anthropic", "gemini", "moonshot"],
    "reasoning": ["deepseek", "openai", "anthropic", "gemini"],
    "code": ["groq", "openai", "anthropic", "deepseek"],
    "creative": ["openai", "anthropic", "gemini", "moonshot"],
    "fast": ["groq", "nvidia_nim", "brave", "tavily", "exa"],
    "cheap": ["nvidia_nim", "anthropic", "openai", "gemini", "deepseek"],
    "accurate": ["openai", "anthropic", "deepseek", "gemini", "moonshot"],
}


@dataclass(frozen=True)
class ProviderStatus:
    """Single provider status snapshot."""

    name: str
    configured: bool
    key_valid_format: bool
    status: Literal["available", "not_configured", "invalid_key"]


def _get_history(provider: str) -> deque[dict[str, Any]]:
    """Get or create health history deque for a provider."""
    if provider not in _HEALTH_HISTORY:
        _HEALTH_HISTORY[provider] = deque(maxlen=_MAX_EVENTS)
    return _HEALTH_HISTORY[provider]


def _check_provider_configured(provider: str) -> tuple[bool, bool]:
    """Check if provider is configured and has valid-format key.

    Returns:
        (configured, key_valid_format)
    """
    key_map = {
        "groq": "GROQ_API_KEY",
        "nvidia_nim": "NVIDIA_NIM_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GOOGLE_AI_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "exa": "EXA_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "brave": "BRAVE_API_KEY",
    }

    env_key = key_map.get(provider)
    if not env_key:
        return False, False

    api_key = os.environ.get(env_key, "").strip()
    if not api_key:
        return False, False

    # Basic format validation: key should be 16+ chars, alphanumeric/dash/underscore
    is_valid_format = (
        len(api_key) >= 16 and all(c.isalnum() or c in "-_" for c in api_key)
    )
    return True, is_valid_format


async def research_provider_ping(provider: str = "all") -> dict[str, Any]:
    """Quick availability check for providers.

    Args:
        provider: Provider name or "all" for all providers

    Returns:
        Dict with keys: providers (list), healthy_count, total
    """
    all_providers = [
        "groq",
        "nvidia_nim",
        "deepseek",
        "gemini",
        "moonshot",
        "openai",
        "anthropic",
        "exa",
        "tavily",
        "brave",
    ]
    providers_to_check = (
        all_providers if provider == "all" else [provider]
        if provider in all_providers
        else []
    )

    result_providers = []
    healthy_count = 0

    for p in providers_to_check:
        configured, key_valid = _check_provider_configured(p)
        status = (
            "available"
            if configured and key_valid
            else "not_configured"
            if not configured
            else "invalid_key"
        )
        is_healthy = status == "available"
        if is_healthy:
            healthy_count += 1

        result_providers.append(
            {
                "name": p,
                "configured": configured,
                "key_valid_format": key_valid,
                "status": status,
            }
        )

    return {
        "providers": result_providers,
        "healthy_count": healthy_count,
        "total": len(providers_to_check),
    }


async def research_provider_history(
    provider: str = "", hours: int = 24
) -> dict[str, Any]:
    """Show provider health history from module-level tracking.

    Args:
        provider: Provider name (required)
        hours: Look back this many hours (default 24)

    Returns:
        Dict with keys: provider, events (list), uptime_pct, avg_response_ms
    """
    if not provider:
        return {"error": "provider name required", "events": [], "uptime_pct": 0.0}

    history = _get_history(provider)
    if not history:
        return {
            "provider": provider,
            "events": [],
            "uptime_pct": 0.0,
            "avg_response_ms": 0.0,
        }

    # Filter by time window
    cutoff = datetime.now(UTC).timestamp() - (hours * 3600)
    recent_events = [e for e in history if e.get("timestamp", 0) > cutoff]

    # Calculate uptime
    available_count = sum(1 for e in recent_events if e.get("status") == "available")
    uptime_pct = (
        (available_count / len(recent_events) * 100) if recent_events else 0.0
    )

    # Calculate avg response time
    response_times = [
        e.get("response_time_ms", 0)
        for e in recent_events
        if e.get("response_time_ms")
    ]
    avg_response_ms = sum(response_times) / len(response_times) if response_times else 0

    return {
        "provider": provider,
        "events": [
            {
                "timestamp": datetime.fromtimestamp(e.get("timestamp", 0), UTC).isoformat(),
                "status": e.get("status", "unknown"),
                "response_time_ms": e.get("response_time_ms", 0),
            }
            for e in recent_events[-100:]  # Last 100 events
        ],
        "uptime_pct": round(uptime_pct, 2),
        "avg_response_ms": round(avg_response_ms, 1),
    }


async def research_provider_recommend(task_type: str = "general") -> dict[str, Any]:
    """Recommend best provider for a task type.

    Args:
        task_type: One of: general, reasoning, code, creative, fast, cheap, accurate

    Returns:
        Dict with keys: task_type, recommended, alternatives, reasoning
    """
    if task_type not in _TASK_PREFERENCES:
        return {
            "error": f"unknown task_type: {task_type}",
            "valid_types": list(_TASK_PREFERENCES.keys()),
        }

    candidates = _TASK_PREFERENCES[task_type]
    scored = []

    for p in candidates:
        configured, key_valid = _check_provider_configured(p)
        if not (configured and key_valid):
            continue

        # Score based on task type preferences and provider traits
        traits = _PROVIDER_TRAITS.get(p, {})
        score = 0.0

        if task_type == "general":
            score = (traits.get("accuracy", 0) + traits.get("speed", 0)) / 2
        elif task_type == "reasoning":
            score = traits.get("reasoning", 0) * 1.5 + traits.get("accuracy", 0)
        elif task_type == "code":
            score = traits.get("accuracy", 0) + traits.get("reasoning", 0) * 0.5
        elif task_type == "creative":
            score = (traits.get("accuracy", 0) + traits.get("cost", 0)) / 2
        elif task_type == "fast":
            score = traits.get("speed", 0) * 1.5
        elif task_type == "cheap":
            score = traits.get("cost", 0) * 1.5
        elif task_type == "accurate":
            score = traits.get("accuracy", 0) + traits.get("reasoning", 0)

        scored.append((p, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    if not scored:
        return {
            "error": "no providers configured for this task type",
            "task_type": task_type,
        }

    recommended = scored[0][0]
    alternatives = [p for p, _ in scored[1:3]]

    reasoning_map = {
        "general": "Balanced speed and accuracy",
        "reasoning": "Best reasoning capability",
        "code": "Strong accuracy and reasoning for code generation",
        "creative": "Optimized for creative and novel output",
        "fast": "Fastest response times",
        "cheap": "Lowest cost per request",
        "accurate": "Highest accuracy and reliability",
    }

    return {
        "task_type": task_type,
        "recommended": recommended,
        "alternatives": alternatives,
        "reasoning": reasoning_map.get(task_type, ""),
    }


def record_health_event(
    provider: str, status: str, response_time_ms: int = 0
) -> None:
    """Record a health event for a provider (called by monitoring systems).

    Args:
        provider: Provider name
        status: 'available' or 'error' or 'timeout'
        response_time_ms: Response time in milliseconds
    """
    history = _get_history(provider)
    history.append(
        {
            "timestamp": datetime.now(UTC).timestamp(),
            "status": status,
            "response_time_ms": response_time_ms,
        }
    )
