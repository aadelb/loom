"""Groq provider for Loom.

Uses the OpenAI-compatible API at https://api.groq.com/openai/v1
with global rate limiting (30 parallel requests by default).
"""

from __future__ import annotations

from typing import Any

from loom.providers.llm_openai_compat import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    """Groq provider using OpenAI-compatible API.

    Attributes:
        PROVIDER_NAME: "groq"
        DEFAULT_MODEL: "llama-3.3-70b-versatile"
        SEMAPHORE_SIZE: 30 (Groq is very fast)
    """

    PROVIDER_NAME = "groq"
    ENV_KEY = "GROQ_API_KEY"
    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    ENV_ENDPOINT_KEY = "GROQ_ENDPOINT"
    SUPPORTS_EMBED = False
    COST_INPUT_PER_M = 0.59
    COST_OUTPUT_PER_M = 0.79
    SEMAPHORE_SIZE = 30

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
        """Send chat messages to Groq.

        Groq-specific model validation: rejects non-Groq models and cross-provider models.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (Groq doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        # Validate timeout to prevent abuse
        timeout = max(1, min(int(timeout), 600))
        # Use provider's own default if passed model isn't a Groq-compatible model
        GROQ_MODELS = {
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "llama-guard-3-8b",
        }
        if model and "/" in model:
            model = self.default_model
        elif model and model not in GROQ_MODELS:
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
