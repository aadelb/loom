"""Unified rate limiting for external API calls.

Provides token bucket rate limiting that can be shared across
tools hitting the same external service.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("loom.rate_limit_manager")


@dataclass
class TokenBucket:
    """Token bucket rate limiter."""

    rate: float  # tokens per second
    capacity: float  # max tokens
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0) -> None:
        """Acquire tokens, waiting if necessary."""
        async with self._get_lock():
            self._refill()
            while self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self.rate
                await asyncio.sleep(min(wait_time, 1.0))
                self._refill()
            self._tokens -= tokens

    @property
    def available(self) -> float:
        """Current available tokens."""
        self._refill()
        return self._tokens


_limiters: dict[str, TokenBucket] = {}

DEFAULT_RATES: dict[str, tuple[float, float]] = {
    # (tokens_per_second, capacity)
    "groq": (30.0, 30.0),
    "nvidia_nim": (5.0, 12.0),
    "deepseek": (5.0, 10.0),
    "gemini": (5.0, 10.0),
    "openai": (10.0, 20.0),
    "anthropic": (5.0, 10.0),
    "exa": (5.0, 10.0),
    "tavily": (5.0, 10.0),
    "brave": (5.0, 10.0),
}


def get_limiter(service: str) -> TokenBucket:
    """Get or create a rate limiter for a service."""
    if service not in _limiters:
        rate, capacity = DEFAULT_RATES.get(service, (5.0, 10.0))
        _limiters[service] = TokenBucket(rate=rate, capacity=capacity)
    return _limiters[service]


async def throttle(service: str, tokens: float = 1.0) -> None:
    """Wait until rate limit allows the request."""
    limiter = get_limiter(service)
    await limiter.acquire(tokens)


def reset(service: str | None = None) -> None:
    """Reset limiter(s) — for testing."""
    if service:
        _limiters.pop(service, None)
    else:
        _limiters.clear()
