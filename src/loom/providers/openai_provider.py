"""OpenAI provider for Loom.

Uses the OpenAI API at https://api.openai.com/v1 or a custom base_url.
Supports JSON schema responses via response_format parameter.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

logger = logging.getLogger("loom.llm")


class OpenAIProvider(LLMProvider):
    """OpenAI provider using gpt-4/gpt-5 models.

    Attributes:
        name: "openai"
        default_model: "gpt-5-mini"
    """

    name = "openai"
    default_model = "gpt-5-mini"

    def __init__(self) -> None:
        """Initialize OpenAI provider."""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.client: Any = None
        self._import_failed = False

    def _get_client(self) -> Any:
        """Lazy-initialize OpenAI client."""
        if self.client is None:
            if self._import_failed:
                raise ImportError("openai package not available")
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                logger.error("openai package not installed: %s", e)
                self._import_failed = True
                raise

            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60.0,
            )
        return self.client

    def available(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.api_key)

    async def close(self) -> None:
        """Close the OpenAI client."""
        if self.client is not None:
            await self.client.close()
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
        """Send chat messages to OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema dict (OpenAI-style)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        model = model or self.default_model
        client = self._get_client()
        start = time.time()

        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add response_format if provided
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error("OpenAI error: %s", str(e)[:200])
            raise

        latency_ms = int((time.time() - start) * 1000)

        # Extract response data
        text = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason

        # Token counts
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

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
    ) -> list[list[float]]:
        """Generate embeddings via OpenAI.

        Args:
            texts: List of text strings
            model: Embedding model (default: text-embedding-3-small)

        Returns:
            List of embedding vectors
        """
        model = model or "text-embedding-3-small"
        client = self._get_client()
        start = time.time()

        try:
            response = await client.embeddings.create(
                model=model,
                input=texts,
            )
        except Exception as e:
            logger.error("OpenAI embeddings error: %s", str(e)[:200])
            raise

        latency_ms = int((time.time() - start) * 1000)

        # Extract embeddings (ordered same as input)
        embeddings = [item.embedding for item in response.data]

        logger.info(
            "llm_embed_ok provider=%s model=%s texts=%d latency=%dms",
            self.name,
            model,
            len(texts),
            latency_ms,
        )

        return embeddings
