"""Google Gemini provider for Loom.

Uses the REST API at https://generativelanguage.googleapis.com/v1beta
with global rate limiting (15 parallel requests by default).
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

logger = logging.getLogger("loom.llm")

# Global semaphore for Gemini rate limiting
_GEMINI_SEMAPHORE: asyncio.Semaphore | None = None


def _get_gemini_semaphore(max_parallel: int = 15) -> asyncio.Semaphore:
    """Get or create the global Gemini semaphore."""
    global _GEMINI_SEMAPHORE
    if _GEMINI_SEMAPHORE is None:
        _GEMINI_SEMAPHORE = asyncio.Semaphore(max_parallel)
    return _GEMINI_SEMAPHORE


class GeminiProvider(LLMProvider):
    """Google Gemini provider using REST API.

    Attributes:
        name: "gemini"
        default_model: "gemini-2.0-flash"
    """

    name = "gemini"
    default_model = "gemini-2.0-flash"

    def __init__(self, max_parallel: int = 15) -> None:
        """Initialize Gemini provider.

        Args:
            max_parallel: Max concurrent requests (default 15)
        """
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta"
        self.api_key = os.environ.get("GOOGLE_AI_KEY", "") or os.environ.get("GOOGLE_AI_KEY_1", "")
        self.semaphore = _get_gemini_semaphore(max_parallel)
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
            )
        return self.client

    def available(self) -> bool:
        """Check if Gemini is configured with a non-empty key.

        Rejects whitespace-only keys so `available()` does not lie and cause
        a 401 at the API boundary.
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
        """Send chat messages to Gemini.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (Gemini doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        # Validate timeout to prevent abuse
        timeout = max(1, min(int(timeout), 600))
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

        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Map user role from OpenAI format; system messages are typically ignored by Gemini
            gemini_role = "user" if role in ("user", "system") else "model"
            contents.append(
                {
                    "role": gemini_role,
                    "parts": [{"text": content}],
                }
            )

        # Build request body
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        # Construct URL without API key (moved to header)
        url = f"{self.endpoint}/models/{model}:generateContent"

        # Set API key via x-goog-api-key header (Google's recommended approach)
        headers = {"x-goog-api-key": self.api_key}

        try:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=float(timeout),
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("Gemini timeout after %.1fs", time.time() - start)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Gemini error: %d %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise

        try:
            data = await response.json()
        except (json.JSONDecodeError, ValueError):
            raise RuntimeError(f"Invalid JSON from gemini: {response.text[:200]}")

        latency_ms = int((time.time() - start) * 1000)

        # Extract response data
        text = ""
        finish_reason = None
        if data.get("candidates"):
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if parts and "text" in parts[0]:
                    text = parts[0]["text"]
            if "finishReason" in candidate:
                finish_reason = candidate["finishReason"]

        # Token counts from usageMetadata
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

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
        timeout: int = 60,  # noqa: ASYNC109
    ) -> list[list[float]]:
        """Gemini does not support embeddings via this API.

        Args:
            texts: List of text strings (unused)
            model: Embedding model (unused)
            timeout: Per-call timeout in seconds (unused)

        Raises:
            NotImplementedError: Gemini embeddings are not implemented
        """
        raise NotImplementedError("Gemini embeddings are not implemented")
