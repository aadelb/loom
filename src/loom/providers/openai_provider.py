"""OpenAI provider for Loom.

Uses the OpenAI API at https://api.openai.com/v1 or a custom base_url.
Supports JSON schema responses via response_format parameter.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

# Local helper — keeps provider self-contained even if tools/llm.py is not loaded.
_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{10,}|nvapi-[A-Za-z0-9_\-]{10,})")


def _sanitize(msg: str) -> str:
    """Strip provider API key prefixes from an error message (HIGH #5)."""
    return _KEY_RE.sub("[REDACTED_KEY]", msg)

logger = logging.getLogger("loom.llm")


class OpenAIProvider(LLMProvider):
    """OpenAI provider using gpt-4/gpt-5 models.

    Attributes:
        name: "openai"
        default_model: "gpt-5-mini"
    """

    name = "openai"
    default_model = "gpt-4o-mini"

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
        """Check if OpenAI is configured with a non-empty key.

        Rejects whitespace-only keys so `available()` cannot falsely advertise
        readiness and leak the key in a 401 traceback (cross-review CRITICAL #2).
        """
        return bool(self.api_key and self.api_key.strip())

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
        # Validate timeout to prevent abuse (HIGH #8)
        timeout = max(1, min(int(timeout), 600))
        if not model or model.startswith(("meta/", "accounts/")):
            model = self.default_model
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        client = self._get_client()
        start = time.time()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            # Thread per-call timeout through to the OpenAI SDK (HIGH #8).
            "timeout": float(timeout),
        }
        # Newer models (o3, o4, gpt-5) use max_completion_tokens, no temperature
        if model and any(x in model for x in ("o3", "o4", "gpt-5")):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature

        # Add response_format if provided
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as e:
            # Sanitize API key patterns out of the error message before logging
            # or re-raising (HIGH #5).
            safe = _sanitize(str(e))[:200]
            logger.error("OpenAI error: %s", safe)
            raise RuntimeError(safe) from None

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
        timeout: int = 60,  # noqa: ASYNC109  # legacy kwarg threaded through to httpx/openai SDK
    ) -> list[list[float]]:
        """Generate embeddings via OpenAI.

        Args:
            texts: List of text strings
            model: Embedding model (default: text-embedding-3-small)
            timeout: Per-call timeout in seconds (HIGH #6/8)

        Returns:
            List of embedding vectors
        """
        # Validate timeout to prevent abuse (HIGH #6)
        timeout = max(1, min(int(timeout), 600))
        model = model or "text-embedding-3-small"
        client = self._get_client()
        start = time.time()

        try:
            response = await client.embeddings.create(
                model=model,
                input=texts,
                timeout=float(timeout),
            )
        except Exception as e:
            safe = _sanitize(str(e))[:200]
            logger.error("OpenAI embeddings error: %s", safe)
            raise RuntimeError(safe) from None

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
