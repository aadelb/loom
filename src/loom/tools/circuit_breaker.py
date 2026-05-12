"""Circuit Breaker pattern for external API calls.

Prevents cascading failures when providers go down.
If a provider fails N times, "open" the circuit and skip it for cooldown.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.circuit_breaker")
PROVIDERS = {"groq", "nvidia_nim", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm",
             "exa", "tavily", "firecrawl", "brave", "ddgs"}

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

_lock: asyncio.Lock | None = None
CIRCUITS = {p: {"state": CircuitState.CLOSED, "failures": 0, "last_failure": None, "opened_at": None} for p in PROVIDERS}
FAILURE_THRESHOLD, COOLDOWN_SECONDS = 5, 60


def _get_lock() -> asyncio.Lock:
    """Get or create the circuit breaker lock."""
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


@handle_tool_errors("research_breaker_status")
async def research_breaker_status() -> dict[str, Any]:
    """Show circuit breaker state: {circuits: [{provider, state, failures, last_failure, cooldown_remaining_s}]}"""
    try:
        async with _get_lock():
            now, circuits = time.time(), []
            for provider, circuit in sorted(CIRCUITS.items()):
                cooldown = 0
                if circuit["state"] == CircuitState.OPEN and circuit["opened_at"]:
                    cooldown = max(0, COOLDOWN_SECONDS - (now - circuit["opened_at"]))
                    if cooldown <= 0:
                        circuit["state"] = CircuitState.HALF_OPEN
                circuits.append({
                    "provider": provider, "state": circuit["state"].value, "failures": circuit["failures"],
                    "last_failure": circuit["last_failure"], "cooldown_remaining_s": round(cooldown, 1),
                })
            return {"circuits": circuits}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_breaker_status"}

@handle_tool_errors("research_breaker_trip")
async def research_breaker_trip(provider: str, error: str = "") -> dict[str, Any]:
    """Record failure for provider. Open circuit if failures >= threshold (5).
    Returns: {provider, state, failures, threshold, tripped: bool}"""
    try:
        if provider not in CIRCUITS:
            return {"provider": provider, "state": "unknown", "error": f"Unknown provider: {provider}"}
        async with _get_lock():
            circuit = CIRCUITS[provider]
            circuit["failures"] += 1
            circuit["last_failure"] = datetime.now(UTC).isoformat()
            tripped = False
            if circuit["failures"] >= FAILURE_THRESHOLD and circuit["state"] == CircuitState.CLOSED:
                circuit["state"] = CircuitState.OPEN
                circuit["opened_at"] = time.time()
                tripped = True
                logger.warning("circuit_opened provider=%s failures=%d error=%s", provider, circuit["failures"], error)
            return {
                "provider": provider, "state": circuit["state"].value, "failures": circuit["failures"],
                "threshold": FAILURE_THRESHOLD, "tripped": tripped, "error": error,
            }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_breaker_trip"}

@handle_tool_errors("research_breaker_reset")
async def research_breaker_reset(provider: str = "all") -> dict[str, Any]:
    """Manually reset circuit(s) to CLOSED.
    Returns: {reset: list[str], new_state: "closed", count: int}"""
    try:
        async with _get_lock():
            reset_list = []
            providers = list(CIRCUITS.keys()) if provider == "all" else ([provider] if provider in CIRCUITS else [])
            for prov in providers:
                CIRCUITS[prov]["state"] = CircuitState.CLOSED
                CIRCUITS[prov]["failures"] = 0
                CIRCUITS[prov]["last_failure"] = None
                CIRCUITS[prov]["opened_at"] = None
                reset_list.append(prov)
            return {"reset": reset_list, "new_state": "closed", "count": len(reset_list)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_breaker_reset"}
