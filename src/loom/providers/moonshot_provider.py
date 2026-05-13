"""Moonshot/Kimi provider for Loom.

Uses the OpenAI-compatible API at https://api.moonshot.cn/v1.
Kimi K2 models are also available via NVIDIA NIM.
"""

from __future__ import annotations

from typing import Any

from loom.providers.llm_openai_compat import OpenAICompatProvider


class MoonshotProvider(OpenAICompatProvider):
    """Moonshot/Kimi provider using OpenAI-compatible API.

    Attributes:
        PROVIDER_NAME: "moonshot"
        DEFAULT_MODEL: "kimi-k2-0711-preview"
        TIMEOUT_SECONDS: 120.0 (Moonshot needs longer timeouts)
    """

    PROVIDER_NAME = "moonshot"
    ENV_KEY = "MOONSHOT_API_KEY"
    BASE_URL = "https://api.moonshot.cn/v1"
    DEFAULT_MODEL = "kimi-k2-0711-preview"
    ENV_ENDPOINT_KEY = "MOONSHOT_ENDPOINT"
    SUPPORTS_EMBED = False
    COST_INPUT_PER_M = 0.33
    COST_OUTPUT_PER_M = 0.66
    TIMEOUT_SECONDS = 120.0

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        timeout: int = 120,  # noqa: ASYNC109
    ):
        """Send chat messages to Moonshot.

        Uses 120s default timeout instead of 60s due to Moonshot's longer response times.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (not supported)
            timeout: Per-call timeout in seconds (default 120s)

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        return await super().chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            timeout=timeout,
        )
