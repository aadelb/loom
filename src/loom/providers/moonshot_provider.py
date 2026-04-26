"""Moonshot/Kimi provider for Loom.

Uses the OpenAI-compatible API at https://api.moonshot.cn/v1.
Kimi K2 models are also available via NVIDIA NIM.
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

_MOONSHOT_SEMAPHORE: asyncio.Semaphore | None = None


def _get_moonshot_semaphore(max_parallel: int = 10) -> asyncio.Semaphore:
    global _MOONSHOT_SEMAPHORE
    if _MOONSHOT_SEMAPHORE is None:
        _MOONSHOT_SEMAPHORE = asyncio.Semaphore(max_parallel)
    return _MOONSHOT_SEMAPHORE


class MoonshotProvider(LLMProvider):
    """Moonshot/Kimi provider using OpenAI-compatible API."""

    name = "moonshot"
    default_model = "kimi-k2-0711-preview"

    def __init__(self, max_parallel: int = 10) -> None:
        self.endpoint = os.environ.get(
            "MOONSHOT_ENDPOINT", "https://api.moonshot.cn/v1"
        )
        self.api_key = os.environ.get("MOONSHOT_API_KEY", "")
        self.semaphore = _get_moonshot_semaphore(max_parallel)
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0),
            )
        return self.client

    def available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def close(self) -> None:
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
        timeout: int = 120,  # noqa: ASYNC109
    ) -> LLMResponse:
        model = model or self.default_model
        async with self.semaphore:
            client = await self._get_client()
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
                logger.error("Moonshot timeout after %.1fs", time.time() - start)
                raise
            except httpx.HTTPStatusError as e:
                logger.error("Moonshot error: %d %s", e.response.status_code, e.response.text[:200])
                raise

            data = response.json()
            latency_ms = int((time.time() - start) * 1000)

            choice = data.get("choices", [{}])[0]
            text = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason")

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            cost_usd = _estimate_cost(self.name, model, input_tokens, output_tokens)

            logger.info(
                "llm_call_ok provider=%s model=%s latency=%dms tokens=%d/%d cost=$%.5f",
                self.name, model, latency_ms, input_tokens, output_tokens, cost_usd,
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
        raise NotImplementedError("Moonshot does not support embeddings")
