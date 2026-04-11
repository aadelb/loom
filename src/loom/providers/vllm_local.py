"""Local vLLM provider for Loom.

Uses a local vLLM instance (e.g. on Hetzner GPU) via OpenAI-compatible API.
Defaults to http://localhost:9001/v1 but can be overridden with VLLM_LOCAL_URL.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

logger = logging.getLogger("loom.llm")


class VllmLocalProvider(LLMProvider):
    """Local vLLM provider using OpenAI-compatible API.

    Attributes:
        name: "vllm"
        default_model: "mimo_v2_flash"
    """

    name = "vllm"
    default_model = "mimo_v2_flash"

    def __init__(self) -> None:
        """Initialize local vLLM provider."""
        self.base_url = os.environ.get("VLLM_LOCAL_URL", "http://localhost:9001/v1")
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(60.0),
            )
        return self.client

    def available(self) -> bool:
        """Check if vLLM endpoint is reachable.

        Performs a quick ping to /models endpoint with 2s timeout.
        """
        try:
            import httpx

            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception:
            logger.debug("vLLM endpoint %s not reachable", self.base_url)
            return False

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
        """Send chat messages to local vLLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (vLLM doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        model = model or self.default_model
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
            logger.error("vLLM timeout after %.1fs", time.time() - start)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "vLLM error: %d %s",
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

        # Cost estimation (local vLLM is free)
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
        timeout: int = 60,
    ) -> list[list[float]]:
        """Generate embeddings via local vLLM.

        Args:
            texts: List of text strings
            model: Embedding model (provider-specific)
            timeout: Per-call timeout in seconds (cross-review HIGH #6)

        Returns:
            List of embedding vectors
        """
        model = model or self.default_model
        client = await self._get_client()
        start = time.time()

        payload = {
            "model": model,
            "input": texts,
        }

        try:
            response = await client.post(
                "/embeddings",
                json=payload,
                timeout=float(timeout),
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("vLLM embeddings timeout")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("vLLM embeddings error: %d", e.response.status_code)
            raise

        data = response.json()
        latency_ms = int((time.time() - start) * 1000)

        # Extract embeddings
        embeddings = []
        for item in data.get("data", []):
            embeddings.append(item.get("embedding", []))

        logger.info(
            "llm_embed_ok provider=%s model=%s texts=%d latency=%dms",
            self.name,
            model,
            len(texts),
            latency_ms,
        )

        return embeddings
