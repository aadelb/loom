"""Anthropic provider for Loom.

Uses the Anthropic Messages API for Claude models.
Anthropic SDK is optional and provider gracefully degrades if not installed.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

# Strip provider key prefixes from error messages (HIGH #5)
_KEY_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]{10,}|sk-[A-Za-z0-9_\-]{10,}|nvapi-[A-Za-z0-9_\-]{10,})"
)


def _sanitize(msg: str) -> str:
    """Redact API keys from an error string."""
    return _KEY_RE.sub("[REDACTED_KEY]", msg)

logger = logging.getLogger("loom.llm")


class AnthropicProvider(LLMProvider):
    """Anthropic provider using Claude models.

    Attributes:
        name: "anthropic"
        default_model: "claude-fable-5" (released Jun 9 2026; Mythos-class, 1M ctx)
    """

    name = "anthropic"
    default_model = "claude-fable-5"

    def __init__(self) -> None:
        """Initialize Anthropic provider."""
        # The primary ANTHROPIC_API_KEY is currently invalid (401); prefer the valid
        # alternates that are present in the environment, falling back in order.
        self.api_key = (
            os.environ.get("ANTHROPIC_API_KEY_GENERAL")
            or os.environ.get("ANTHROPIC_API_KEY_ALT")
            or os.environ.get("ANTHROPIC_API_KEY_OPUS")
            or os.environ.get("ANTHROPIC_API_KEY")
            or ""
        )
        self.client: Any = None
        self._import_failed = False
        self._import_error: str | None = None

    def _get_client(self) -> Any:
        """Lazy-initialize Anthropic client."""
        if self.client is None:
            if self._import_failed:
                raise ImportError(self._import_error or "anthropic package not available")
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                logger.warning("anthropic package not installed: %s", e)
                self._import_failed = True
                self._import_error = str(e)
                raise

            self.client = AsyncAnthropic(api_key=self.api_key)
        return self.client

    def available(self) -> bool:
        """Check if Anthropic is configured with a non-empty key AND importable.

        Rejects whitespace-only keys so `available()` cannot falsely advertise
        readiness (cross-review CRITICAL #2).
        """
        if not self.api_key or not self.api_key.strip():
            return False
        # Try importing to check if package is available
        try:
            from anthropic import AsyncAnthropic  # noqa: F401

            return True
        except ImportError:
            logger.debug("anthropic package not available")
            return False

    async def close(self) -> None:
        """Close the Anthropic client."""
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
        """Send chat messages to Anthropic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (Anthropic doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        # Validate timeout to prevent abuse (HIGH #8)
        timeout = max(1, min(int(timeout), 600))
        if not model or not model.startswith(("claude", "anthropic")):
            model = self.default_model
        client = self._get_client()
        start = time.time()

        # Anthropic deprecated `temperature` for all Claude 4.x models (including
        # opus-4-8, sonnet-4-6, fable-5, mythos-5). Omit it for any claude-*-4* model.
        _ml = model.lower()
        _no_temp = (
            "fable-5" in _ml or "mythos-5" in _ml
            or ("claude" in _ml and "-4" in _ml)
        )
        try:
            create_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
                "timeout": float(timeout),
            }
            if not _no_temp:
                create_kwargs["temperature"] = temperature
            response = await client.messages.create(**create_kwargs)
        except Exception as e:
            safe = _sanitize(str(e))[:200]
            logger.error("Anthropic error: %s", safe)
            raise RuntimeError(safe) from None

        latency_ms = int((time.time() - start) * 1000)

        # Extract response data
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        finish_reason = response.stop_reason

        # Token counts (Anthropic provides usage directly)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

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
        """Anthropic does not support embeddings.

        Args:
            texts: List of text strings (unused)
            model: Embedding model (unused)

        Returns:
            Empty list (not supported)

        Raises:
            NotImplementedError: Always, as Anthropic has no embedding API.
        """
        raise NotImplementedError(
            "Anthropic does not provide embedding APIs. Use NVIDIA NIM or OpenAI."
        )
