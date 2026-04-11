"""Base LLM provider interface and response model.

Defines the abstract LLMProvider class and LLMResponse dataclass for
all provider implementations (NVIDIA NIM, OpenAI, Anthropic, vLLM).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("loom.llm")


@dataclass
class LLMResponse:
    """Response from an LLM provider call.

    Attributes:
        text: Generated text response
        model: Model identifier used (provider/model)
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        cost_usd: Estimated USD cost of this call
        latency_ms: Wall-clock latency in milliseconds
        provider: Provider name (nvidia, openai, anthropic, vllm)
        finish_reason: Why generation stopped (stop, length, error, etc.)
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    provider: str
    finish_reason: str | None = None


def _estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for an LLM call.

    Cost table per model (as of Apr 2025):
    - NVIDIA NIM: free tier (integrate.api.nvidia.com)
    - OpenAI gpt-5-mini: $0.60/M in, $2.40/M out
    - Anthropic claude-opus-4-6: $15/M in, $75/M out
    - Local vLLM: free (self-hosted)

    Args:
        provider: Provider name
        model: Model identifier
        input_tokens: Input token count
        output_tokens: Output token count

    Returns:
        Estimated USD cost (float)
    """
    # NVIDIA NIM is free tier
    if provider == "nvidia" or "nvidia" in model.lower():
        return 0.0

    # Local vLLM is free (self-hosted)
    if provider == "vllm" or "vllm" in model.lower():
        return 0.0

    # OpenAI pricing
    if provider == "openai" or "openai" in model.lower() or "gpt-" in model.lower():
        # gpt-5-mini is the reference; other models scale accordingly
        if "gpt-5-mini" in model.lower() or "gpt-5.2-mini" in model.lower():
            in_cost = (input_tokens / 1_000_000) * 0.60
            out_cost = (output_tokens / 1_000_000) * 2.40
            return in_cost + out_cost
        # gpt-4o pricing tier (approximation for gpt-5)
        if "gpt-5" in model.lower() or "gpt-5.2" in model.lower():
            in_cost = (input_tokens / 1_000_000) * 0.60
            out_cost = (output_tokens / 1_000_000) * 2.40
            return in_cost + out_cost
        # GPT-4 pricing
        if "gpt-4" in model.lower():
            in_cost = (input_tokens / 1_000_000) * 0.03
            out_cost = (output_tokens / 1_000_000) * 0.06
            return in_cost + out_cost
        # GPT-3.5 pricing
        in_cost = (input_tokens / 1_000_000) * 0.0005
        out_cost = (output_tokens / 1_000_000) * 0.0015
        return in_cost + out_cost

    # Anthropic pricing
    if provider == "anthropic" or "claude" in model.lower():
        if "opus-4-6" in model.lower() or "opus-4" in model.lower():
            in_cost = (input_tokens / 1_000_000) * 15.0
            out_cost = (output_tokens / 1_000_000) * 75.0
            return in_cost + out_cost
        # Fallback: assume Sonnet pricing
        in_cost = (input_tokens / 1_000_000) * 3.0
        out_cost = (output_tokens / 1_000_000) * 15.0
        return in_cost + out_cost

    # Default: free
    return 0.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Subclasses must implement chat() and embed() with async/await for
    network calls. All methods should handle timeouts, API errors, and
    provider-specific quirks.

    Class Attributes:
        name: Provider identifier (e.g. "nvidia", "openai", "anthropic", "vllm")
        default_model: Default model if not specified by caller
    """

    name: str = ""
    default_model: str = ""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        timeout: int = 60,  # noqa: ASYNC109
    ) -> LLMResponse:
        """Send messages to the LLM and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses self.default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature (0-2)
            response_format: Optional JSON schema for structured output
                e.g. {"type": "json_schema", "json_schema": {...}}
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, model, token counts, cost, latency

        Raises:
            httpx.TimeoutException: Call exceeded timeout
            httpx.HTTPStatusError: API returned 4xx or 5xx
            ValueError: Invalid arguments or API unavailable
        """
        ...

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings
            model: Model override (uses self.default_model if None)

        Returns:
            List of embedding vectors (each a list[float])

        Raises:
            httpx.TimeoutException: Call exceeded timeout
            httpx.HTTPStatusError: API returned 4xx or 5xx
            ValueError: Invalid arguments or API unavailable
        """
        ...

    @abstractmethod
    def available(self) -> bool:
        """Check if provider is configured and reachable.

        Returns:
            True if provider has required env vars and is not in a
            known-broken state. Does NOT perform a network ping
            (that happens on first actual call).
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (e.g. close HTTP client connections).

        Called when the provider is being shut down. Subclasses may
        keep a persistent httpx.AsyncClient and close it here.
        """
        ...
