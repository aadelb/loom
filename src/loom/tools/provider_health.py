"""Provider health monitoring tools — track LLM and search provider availability."""

from __future__ import annotations

import os
from collections import deque
from datetime import UTC, datetime
from typing import Any, Literal

# Health tracking: bounded deque per provider
_HISTORY: dict[str, deque[dict[str, Any]]] = {}
_MAX_EVENTS = 1000

# Provider config keys
_KEYS = {
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

# Provider capability scores
_SCORES = {
    "groq": {"speed": 95, "accuracy": 75, "reasoning": 70},
    "nvidia_nim": {"speed": 85, "accuracy": 75, "reasoning": 70},
    "deepseek": {"speed": 60, "accuracy": 85, "reasoning": 95},
    "gemini": {"speed": 80, "accuracy": 88, "reasoning": 85},
    "moonshot": {"speed": 75, "accuracy": 80, "reasoning": 80},
    "openai": {"speed": 70, "accuracy": 95, "reasoning": 90},
    "anthropic": {"speed": 65, "accuracy": 95, "reasoning": 95},
    "exa": {"speed": 85, "accuracy": 80, "reasoning": 0},
    "tavily": {"speed": 80, "accuracy": 75, "reasoning": 0},
    "brave": {"speed": 90, "accuracy": 70, "reasoning": 0},
}

# Task type preferences
_TASKS = {
    "general": ["groq", "openai", "anthropic", "gemini", "moonshot"],
    "reasoning": ["deepseek", "openai", "anthropic", "gemini"],
    "code": ["groq", "openai", "anthropic", "deepseek"],
    "creative": ["openai", "anthropic", "gemini", "moonshot"],
    "fast": ["groq", "nvidia_nim", "brave", "tavily", "exa"],
    "cheap": ["nvidia_nim", "anthropic", "openai", "gemini", "deepseek"],
    "accurate": ["openai", "anthropic", "deepseek", "gemini", "moonshot"],
}


def _get_history(provider: str) -> deque[dict[str, Any]]:
    """Get or create history deque for provider."""
    if provider not in _HISTORY:
        _HISTORY[provider] = deque(maxlen=_MAX_EVENTS)
    return _HISTORY[provider]


def _check_provider(provider: str) -> tuple[bool, bool]:
    """Check if provider is configured with valid key format."""
    key_env = _KEYS.get(provider)
    if not key_env:
        return False, False
    key = os.environ.get(key_env, "").strip()
    if not key:
        return False, False
    valid = 16 <= len(key) <= 256 and all(c.isalnum() or c in "-_." for c in key)
    return True, valid


async def research_provider_ping(provider: str = "all") -> dict[str, Any]:
    """Quick availability check for providers. Returns config status + API key format validity."""
    try:
        if provider != "all" and provider not in _KEYS:
            return {"error": f"invalid provider: {provider}", "valid_providers": list(_KEYS.keys())}
        providers_list = list(_KEYS.keys()) if provider == "all" else [provider]
        result = []
        healthy = 0
        for p in providers_list:
            configured, valid = _check_provider(p)
            status = "available" if configured and valid else "not_configured" if not configured else "invalid_key"
            if status == "available":
                healthy += 1
            result.append({"name": p, "configured": configured, "key_valid_format": valid, "status": status})
        return {"providers": result, "healthy_count": healthy, "total": len(providers_list)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_provider_ping"}


async def research_provider_history(provider: str = "", hours: int = 24) -> dict[str, Any]:
    """Show provider health history with uptime percentage and avg response time."""
    try:
        if not provider or provider not in _KEYS:
            return {"error": "invalid provider", "events": [], "uptime_pct": 0.0, "avg_response_ms": 0.0}
        history = _get_history(provider)
        if not history:
            return {"provider": provider, "events": [], "uptime_pct": 0.0, "avg_response_ms": 0.0}
        cutoff = datetime.now(UTC).timestamp() - (hours * 3600)
        recent = [e for e in history if isinstance(e.get("timestamp"), (int, float)) and e.get("timestamp", 0) > cutoff]
        available = sum(1 for e in recent if e.get("status") == "available")
        uptime_pct = (available / len(recent) * 100) if recent else 0.0
        response_times = [e.get("response_time_ms", 0) for e in recent if "response_time_ms" in e and e.get("response_time_ms") is not None]
        avg_ms = sum(response_times) / len(response_times) if response_times else 0.0
        return {
            "provider": provider,
            "events": [{"timestamp": datetime.fromtimestamp(e.get("timestamp", 0), UTC).isoformat(), "status": e.get("status"), "response_time_ms": e.get("response_time_ms", 0)} for e in recent[-100:]],
            "uptime_pct": round(uptime_pct, 2),
            "avg_response_ms": round(avg_ms, 1),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_provider_history"}


async def research_provider_recommend(task_type: str = "general") -> dict[str, Any]:
    """Recommend best provider for task type based on availability and capability."""
    try:
        if task_type not in _TASKS:
            return {"error": f"unknown task_type: {task_type}", "valid_types": list(_TASKS.keys())}
        candidates = _TASKS[task_type]
        scored = []
        for p in candidates:
            configured, valid = _check_provider(p)
            if not (configured and valid):
                continue
            scores = _SCORES.get(p, {})
            if task_type == "reasoning":
                score = scores.get("reasoning", 0) * 1.5 + scores.get("accuracy", 0)
            elif task_type == "code":
                score = scores.get("accuracy", 0) + scores.get("reasoning", 0) * 0.5
            elif task_type == "fast":
                score = scores.get("speed", 0) * 1.5
            elif task_type == "cheap":
                score = scores.get("accuracy", 0) * 0.5  # Lower cost providers tend to be less accurate
            elif task_type == "accurate":
                score = scores.get("accuracy", 0) + scores.get("reasoning", 0)
            else:  # general, creative
                score = (scores.get("accuracy", 0) + scores.get("speed", 0)) / 2
            scored.append((p, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        if not scored:
            return {"error": "no providers configured", "task_type": task_type}
        return {"task_type": task_type, "recommended": scored[0][0], "alternatives": [p for p, _ in scored[1:3]], "reasoning": f"Best provider for {task_type} tasks"}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_provider_recommend"}


def record_health_event(provider: str, status: str, response_time_ms: int = 0) -> None:
    """Record provider health event (called by monitoring systems)."""
    history = _get_history(provider)
    history.append({"timestamp": datetime.now(UTC).timestamp(), "status": status, "response_time_ms": response_time_ms})
