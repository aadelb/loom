"""OpenAI-compatible base provider.

Base class for LLM providers using the OpenAI API format (/v1/chat/completions).
Eliminates ~300 lines of duplicated code across Groq, NVIDIA NIM, DeepSeek,
Moonshot, and OpenAI providers.

Subclasses must override PROVIDER_NAME, ENV_KEY, BASE_URL, DEFAULT_MODEL,
SUPPORTS_EMBED, COST_INPUT_PER_M, and COST_OUTPUT_PER_M.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import httpx

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

logger = logging.getLogger("loom.providers.openai_compat")


class OpenAICompatProvider(LLMProvider):
    """Base class for OpenAI-compatible API providers.

    Subclasses MUST override class attributes:
    - PROVIDER_NAME: Provider identifier (e.g. "groq", "nvidia", "deepseek")
    - ENV_KEY: Environment variable for API key (e.g. "GROQ_API_KEY")
    - BASE_URL: API endpoint (e.g. "https://api.groq.com/openai/v1")
    - DEFAULT_MODEL: Default model name
    - SUPPORTS_EMBED: Whether embeddings endpoint is available
    - COST_INPUT_PER_M: Cost per 1M input tokens
    - COST_OUTPUT_PER_M: Cost per 1M output tokens

    Optional overrides:
    - SEMAPHORE_SIZE: Max concurrent requests (default 10)
    - TIMEOUT_SECONDS: Default request timeout (default 60)
    """

    # Subclasses MUST override these
    PROVIDER_NAME: str = "openai_compat"
    ENV_KEY: str = ""
    BASE_URL: str = ""
    DEFAULT_MODEL: str = ""
    SUPPORTS_EMBED: bool = False
    COST_INPUT_PER_M: float = 0.0
    COST_OUTPUT_PER_M: float = 0.0

    # Optional overrides
    SEMAPHORE_SIZE: int = 10
    TIMEOUT_SECONDS: float = 60.0
    ENV_ENDPOINT_KEY: str | None = None  # e.g. "GROQ_ENDPOINT"

    # Semaphores per subclass (keyed by PROVIDER_NAME)
    _semaphores: dict[str, asyncio.Semaphore] = {}

    def __init__(self, model: str | None = None, max_parallel: int | None = None) -> None:
        """Initialize OpenAI-compatible provider.

        Args:
            model: Override default model name
            max_parallel: Override semaphore size (default SEMAPHORE_SIZE)
        """
        self.name = self.PROVIDER_NAME
        self.default_model = model or self.DEFAULT_MODEL
        self._api_key = os.environ.get(self.ENV_KEY, "")
        self._client: httpx.AsyncClient | None = None

        # Set up semaphore for rate limiting
        size = max_parallel or self.SEMAPHORE_SIZE
        if self.PROVIDER_NAME not in self._semaphores:
            self._semaphores[self.PROVIDER_NAME] = asyncio.Semaphore(size)
        self._semaphore = self._semaphores[self.PROVIDER_NAME]

        # Allow endpoint override via env var (e.g. GROQ_ENDPOINT)
        if self.ENV_ENDPOINT_KEY:
            self._base_url = os.environ.get(self.ENV_ENDPOINT_KEY, self.BASE_URL)
        else:
            self._base_url = self.BASE_URL

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.TIMEOUT_SECONDS),
            )
        return self._client

    def available(self) -> bool:
        """Check if provider is configured with a non-empty API key."""
        return bool(self._api_key and self._api_key.strip())

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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
        """Send chat messages to the OpenAI-compatible API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (ignored by some providers)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        timeout = max(1, min(int(timeout), 600))
        model = model or self.default_model

        async with self._semaphore:
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
        client = self._get_client()
        start = time.time()

        payload: dict[str, Any] = {
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
            logger.error(
                "%s timeout after %.1fs", self.PROVIDER_NAME, time.time() - start
            )
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "%s error: %d %s",
                self.PROVIDER_NAME,
                e.response.status_code,
                e.response.text[:200],
            )
            raise

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(
                f"Invalid JSON from {self.PROVIDER_NAME}: {str(e)[:100]}"
            ) from e

        latency_ms = int((time.time() - start) * 1000)

        # Extract response data
        choice = data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")

        # Token counts
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Cost estimation using base class helper
        cost_usd = _estimate_cost(
            self.PROVIDER_NAME, model, input_tokens, output_tokens
        )

        logger.info(
            "llm_call_ok provider=%s model=%s latency=%dms tokens=%d/%d cost=$%.5f",
            self.PROVIDER_NAME,
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
            provider=self.PROVIDER_NAME,
            finish_reason=finish_reason,
        )

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        timeout: int = 60,  # noqa: ASYNC109
    ) -> list[list[float]]:
        """Generate embeddings via OpenAI-compatible API.

        Args:
            texts: List of text strings
            model: Embedding model (default: provider-specific)
            timeout: Per-call timeout in seconds

        Returns:
            List of embedding vectors

        Raises:
            NotImplementedError: If provider doesn't support embeddings
        """
        if not self.SUPPORTS_EMBED:
            raise NotImplementedError(
                f"{self.PROVIDER_NAME} does not support embeddings"
            )

        timeout = max(1, min(int(timeout), 600))
        model = model or self.default_model
        client = self._get_client()

        payload: dict[str, Any] = {
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
            data = response.json()
            return [item["embedding"] for item in data.get("data", [])]
        except Exception as e:
            logger.error(
                "%s embeddings error: %s", self.PROVIDER_NAME, str(e)[:200]
            )
            raise
