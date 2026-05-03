"""API key rotation and validation system."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import logging
import os
import re
import time
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.key_rotation")

KEY_MAP = {"groq": "GROQ_API_KEY", "nvidia": "NVIDIA_NIM_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "gemini": "GOOGLE_AI_KEY", "moonshot": "MOONSHOT_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "exa": "EXA_API_KEY", "tavily": "TAVILY_API_KEY", "brave": "BRAVE_API_KEY"}
HEALTH = {"groq": ("https://api.groq.com/openai/v1/models", "GET"), "deepseek": ("https://api.deepseek.com/models", "GET"), "gemini": ("https://generativelanguage.googleapis.com/v1beta/models?key={key}", "GET"), "moonshot": ("https://api.moonshot.cn/v1/models", "GET"), "openai": ("https://api.openai.com/v1/models", "GET"), "anthropic": ("https://api.anthropic.com/v1/models", "GET")}
PATTERNS = {"groq": r"^gsk_[a-zA-Z0-9]{40,}$", "deepseek": r"^sk_[a-zA-Z0-9]{40,}$", "gemini": r"^[a-zA-Z0-9_-]{39,}$", "moonshot": r"^sk_[a-zA-Z0-9]{40,}$", "openai": r"^sk_[a-zA-Z0-9]{40,}$", "anthropic": r"^sk_ant_[a-zA-Z0-9]{40,}$"}
_md = {}
_md_lock = asyncio.Lock()
_last_rotation: dict[str, float] = {}
_rotation_lock = asyncio.Lock()


async def research_key_status() -> dict[str, Any]:
    """Check status of all configured API keys."""
    p = []
    for n, e in KEY_MAP.items():
        v = os.environ.get(e, "").strip()
        c = bool(v)
        vf = c and (n not in PATTERNS or bool(re.match(PATTERNS[n], v)))
        async with _md_lock:
            m = _md.get(n, {})
        s = "unconfigured" if not c else ("invalid_format" if not vf else ("degraded" if m.get("error_count", 0) > 0 else "healthy"))
        p.append({"name": n, "configured": c, "valid_format": vf, "last_used": m.get("last_used"), "last_error": m.get("last_error"), "error_count": m.get("error_count", 0), "status": s})
    return {"providers": p, "healthy_count": sum(1 for x in p if x["status"] == "healthy"), "total_count": len(p), "timestamp": datetime.now(UTC).isoformat()}


async def research_key_rotate(provider: str, new_key: str) -> dict[str, Any]:
    """Hot-swap an API key without restart."""
    if provider not in KEY_MAP:
        raise ValueError(f"Unknown provider: {provider}")

    # Fix 3: Validate key format
    new_key = new_key.strip()
    if not new_key or len(new_key) < 8 or len(new_key) > 256:
        raise ValueError(f"Invalid key length: must be 8-256 characters, got {len(new_key)}")

    # Fix 2: Rate limiting on key rotation
    async with _rotation_lock:
        last_rotation_time = _last_rotation.get(provider, 0)
        current_time = time.time()
        if current_time - last_rotation_time < 60:
            seconds_remaining = 60 - (current_time - last_rotation_time)
            raise ValueError(
                f"Key rotation rate limited for {provider}. "
                f"Wait {seconds_remaining:.1f} more seconds before rotating again."
            )
        _last_rotation[provider] = current_time

    e = KEY_MAP[provider]
    o = os.environ.get(e, "")
    os.environ[e] = new_key
    _clear_cache(provider)

    # Fix 4: Protect _md mutations with lock
    async with _md_lock:
        if provider not in _md:
            _md[provider] = {}
        _md[provider]["last_rotated"] = datetime.now(UTC).isoformat()
        _md[provider]["rotation_count"] = _md[provider].get("rotation_count", 0) + 1

    # Fix 1: Use hash of key instead of exposing first 8 chars
    old_key_hash = hashlib.sha256(o.encode()).hexdigest()[:8] if o else "not_set"
    new_key_hash = hashlib.sha256(new_key.encode()).hexdigest()[:8]

    return {
        "provider": provider,
        "rotated": True,
        "previous_key_identifier": old_key_hash,
        "new_key_identifier": new_key_hash,
        "timestamp": datetime.now(UTC).isoformat()
    }


async def research_key_test(provider: str) -> dict[str, Any]:
    """Test if an API key is valid via health check."""
    if provider not in KEY_MAP:
        raise ValueError(f"Unknown provider: {provider}")
    k = os.environ.get(KEY_MAP[provider], "").strip()
    if not k:
        return {"provider": provider, "valid": False, "response_time_ms": 0, "error": "Key not configured"}
    if provider not in HEALTH:
        return {"provider": provider, "valid": True, "response_time_ms": 0, "error": None}
    u, m = HEALTH[provider]
    u = u.format(key=k) if "{key}" in u else u
    st = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            h = {} if provider == "gemini" else {"Authorization": f"Bearer {k}"}
            r = await c.request(m, u, headers=h)
        e = int((time.time() - st) * 1000)
        if r.status_code == 200:
            await _use(provider)
            return {"provider": provider, "valid": True, "response_time_ms": e, "error": None}
        elif r.status_code in (401, 403):
            await _err(provider, f"HTTP {r.status_code}")
            return {"provider": provider, "valid": False, "response_time_ms": e, "error": f"Auth: {r.status_code}"}
        else:
            await _err(provider, f"HTTP {r.status_code}")
            return {"provider": provider, "valid": False, "response_time_ms": e, "error": f"HTTP {r.status_code}"}
    except asyncio.TimeoutError:
        await _err(provider, "Timeout")
        return {"provider": provider, "valid": False, "response_time_ms": int((time.time() - st) * 1000), "error": "Timeout"}
    except Exception as ex:
        await _err(provider, str(ex))
        return {"provider": provider, "valid": False, "response_time_ms": int((time.time() - st) * 1000), "error": str(ex)}


def _clear_cache(p: str) -> None:
    """Clear cached provider instance."""
    mods = {"groq": "loom.providers.groq_provider", "nvidia": "loom.providers.nvidia_nim", "deepseek": "loom.providers.deepseek_provider", "gemini": "loom.providers.gemini_provider", "moonshot": "loom.providers.moonshot_provider", "openai": "loom.providers.openai_provider", "anthropic": "loom.providers.anthropic_provider"}
    try:
        if n := mods.get(p):
            m = importlib.import_module(n)
            if hasattr(m, "_instance"):
                m._instance = None
    except ImportError:
        pass


async def _use(p: str) -> None:
    """Record key usage."""
    async with _md_lock:
        if p not in _md:
            _md[p] = {}
        _md[p]["last_used"] = datetime.now(UTC).isoformat()
        _md[p]["error_count"] = 0


async def _err(p: str, e: str) -> None:
    """Record key error."""
    async with _md_lock:
        if p not in _md:
            _md[p] = {}
        _md[p]["last_error"] = datetime.now(UTC).isoformat()
        _md[p]["error_count"] = _md[p].get("error_count", 0) + 1
    logger.warning(f"Key error for {p}: {e}")
