"""NVIDIA NIM provider for Loom.

Uses the OpenAI-compatible API at https://integrate.api.nvidia.com/v1
with global rate limiting (12 parallel requests by default).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

logger = logging.getLogger("loom.llm")

# Global semaphore for NVIDIA NIM rate limiting
_NIM_SEMAPHORE: asyncio.Semaphore | None = None


def _get_nim_semaphore(max_parallel: int = 12) -> asyncio.Semaphore:
    """Get or create the global NVIDIA NIM semaphore."""
    global _NIM_SEMAPHORE
    if _NIM_SEMAPHORE is None:
        _NIM_SEMAPHORE = asyncio.Semaphore(max_parallel)
    return _NIM_SEMAPHORE


class NvidiaNimProvider(LLMProvider):
    """NVIDIA NIM provider using OpenAI-compatible API.

    Attributes:
        name: "nvidia"
        default_model: "meta/llama-4-maverick-17b-128e-instruct"
    """

    name = "nvidia"
    default_model = "meta/llama-4-maverick-17b-128e-instruct"

    def __init__(self, max_parallel: int = 12) -> None:
        """Initialize NVIDIA NIM provider.

        Args:
            max_parallel: Max concurrent requests (default 12 per NVIDIA free tier)
        """
        self.endpoint = os.environ.get("NVIDIA_NIM_ENDPOINT", "https://integrate.api.nvidia.com/v1")
        self.api_key = os.environ.get("NVIDIA_NIM_API_KEY", "")
        self.semaphore = _get_nim_semaphore(max_parallel)
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0),
            )
        return self.client

    def available(self) -> bool:
        """Check if NVIDIA NIM is configured with a non-empty key.

        Rejects whitespace-only keys so `available()` does not lie and cause
        a 401 at the API boundary (cross-review CRITICAL #2).
        """
        return bool(self.api_key and self.api_key.strip())

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

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
        """Send chat messages to NVIDIA NIM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (NIM doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        model = model or self.default_model
        async with self.semaphore:
            return await self._chat_impl(
                messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )

    async def _chat_impl(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: int,  # noqa: ASYNC109
    ) -> LLMResponse:
        """Internal chat implementation."""
        client = await self._get_client()
        start = time.time()

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = await client.post(
                "/chat/completions",
                json=payload,
                timeout=float(timeout),
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("NVIDIA NIM timeout after %.1fs", time.time() - start)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "NVIDIA NIM error: %d %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise

        data = response.json()
        latency_ms = int((time.time() - start) * 1000)

        # Extract response data
        choice = data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")

        # Token counts
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Cost estimation
        cost_usd = _estimate_cost(self.name, model, input_tokens, output_tokens)

        logger.info(
            "llm_call_ok provider=%s model=%s latency=%dms tokens=%d/%d cost=$%.5f",
            self.name,
            model,
            latency_ms,
            input_tokens,
            output_tokens,
            cost_usd,
        )

        return LLMResponse(
            text=text,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider=self.name,
            finish_reason=finish_reason,
        )

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        timeout: int = 60,  # noqa: ASYNC109  # legacy kwarg threaded through to httpx/openai SDK
    ) -> list[list[float]]:
        """Generate embeddings via NVIDIA NIM.

        The NVIDIA NIM free tier at integrate.api.nvidia.com does NOT support
        the /v1/embeddings endpoint (it only supports /v1/chat/completions).
        This method raises NotImplementedError to cascade to the next provider
        in the chain (OpenAI, Anthropic, or vLLM).

        Args:
            texts: List of text strings (unused, method will raise)
            model: Embedding model (unused, method will raise)
            timeout: Per-call timeout in seconds (unused)

        Returns:
            Never returns; always raises NotImplementedError

        Raises:
            NotImplementedError: Always, as NVIDIA NIM free tier has no embeddings API
        """
        raise NotImplementedError(
            "NVIDIA NIM free tier does not support embeddings. "
            "Use OpenAI, Anthropic, vLLM, or another provider with embedding support."
        )
