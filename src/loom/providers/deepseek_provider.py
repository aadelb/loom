"""DeepSeek provider for Loom.

Uses the OpenAI-compatible API at https://api.deepseek.com/v1
with global rate limiting (10 parallel requests by default).
"""

from __future__ import annotations

from typing import Any

from loom.providers.llm_openai_compat import OpenAICompatProvider


class DeepSeekProvider(OpenAICompatProvider):
    """DeepSeek provider using OpenAI-compatible API.

    Attributes:
        PROVIDER_NAME: "deepseek"
        DEFAULT_MODEL: "deepseek-chat"
        SEMAPHORE_SIZE: 10
    """

    PROVIDER_NAME = "deepseek"
    ENV_KEY = "DEEPSEEK_API_KEY"
    BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    ENV_ENDPOINT_KEY = "DEEPSEEK_ENDPOINT"
    SUPPORTS_EMBED = False
    COST_INPUT_PER_M = 0.14
    COST_OUTPUT_PER_M = 0.28
    SEMAPHORE_SIZE = 10

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        timeout: int = 60,  # noqa: ASYNC109
    ):
        """Send chat messages to DeepSeek.

        DeepSeek-specific model validation: only accepts known DeepSeek models
        (deepseek-chat, deepseek-reasoning, deepseek-reasoner).

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (DeepSeek doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        # Validate timeout to prevent abuse
        timeout = max(1, min(int(timeout), 600))
        # Use provider's own default if passed model isn't a DeepSeek-compatible model
        DEEPSEEK_MODELS = {"deepseek-chat", "deepseek-reasoning", "deepseek-reasoner"}
        if model and "/" in model:
            model = self.default_model
        elif model and model not in DEEPSEEK_MODELS:
            model = self.default_model
        model = model or self.default_model

        return await super().chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            timeout=timeout,
        )
