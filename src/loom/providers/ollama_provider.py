"""Ollama provider for local abliterated models.

Connects to a local Ollama instance running abliterated (uncensored) models.
These models have safety filters removed and will comply with any request.

Available models:
  - mannix/llama3.1-8b-abliterated (4.7GB, fastest, proven uncensored)
  - qwen3.5-abliterated (2.7GB, 4.2B params, Huihui abliteration)
  - gemma4-abliterated (5.2GB, 7.5B params, Huihui abliteration, slower on CPU)

Usage:
  Set OLLAMA_URL env var (default: http://localhost:11434/v1)
  Set OLLAMA_DEFAULT_MODEL (default: mannix/llama3.1-8b-abliterated)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

logger = logging.getLogger("loom.llm.ollama")

_AVAILABLE_MODELS = [
    "gemma3n-8b-abliterated",
    "mannix/llama3.1-8b-abliterated",
    "qwen3.5-abliterated",
    "qwen3-coder-30b-abliterated",
    "qwen35-9b-abliterated",
    "qwen35-35b-abliterated",
    "gemma4-26b-abliterated",
]


class OllamaProvider(LLMProvider):
    """Local Ollama provider for abliterated (uncensored) models.

    Attributes:
        name: "ollama"
        default_model: from OLLAMA_DEFAULT_MODEL env or mannix/llama3.1-8b-abliterated
    """

    name = "ollama"
    default_model = os.environ.get(
        "OLLAMA_DEFAULT_MODEL", "gemma3n-8b-abliterated"
    )

    def __init__(self) -> None:
        raw = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1")
        self.base_url = raw.rstrip("/")
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))
        return self.client

    def available(self) -> bool:
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception:
            logger.debug("Ollama endpoint %s not reachable", self.base_url)
            return False

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> LLMResponse:
        """Send chat to local Ollama.

        Args:
            messages: Chat messages
            model: Model name (one of available abliterated models)
            max_tokens: Max response tokens
            temperature: Sampling temperature
            response_format: Optional JSON mode
            timeout: Timeout in seconds (CPU inference is slow, default 300s)

        Returns:
            LLMResponse
        """
        timeout = max(1, min(int(timeout), 600))
        model = model or self.default_model
        if not any(m in model for m in ("abliterated", "mannix", "llama3", "qwen3", "gemma3n")):
            model = self.default_model
        client = await self._get_client()
        start = time.time()

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=float(timeout),
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("Ollama timeout after %.1fs model=%s", time.time() - start, model)
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Ollama error: %d %s", e.response.status_code, e.response.text[:200])
            raise

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            raise RuntimeError(f"Invalid JSON from Ollama: {response.text[:200]}")

        latency_ms = int((time.time() - start) * 1000)

        choice = data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        cost_usd = 0.0

        logger.info(
            "llm_call_ok provider=%s model=%s latency=%dms tokens=%d/%d",
            self.name,
            model,
            latency_ms,
            input_tokens,
            output_tokens,
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
        timeout: int = 120,
    ) -> list[list[float]]:
        """Generate embeddings via Ollama (if model supports it)."""
        timeout = max(1, min(int(timeout), 600))
        model = model or self.default_model
        client = await self._get_client()

        payload = {
            "model": model,
            "input": texts,
        }

        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                timeout=float(timeout),
            )
            response.raise_for_status()
        except Exception:
            logger.warning("Ollama embeddings not supported for model=%s", model)
            return []

        data = response.json()
        return [item.get("embedding", []) for item in data.get("data", [])]
