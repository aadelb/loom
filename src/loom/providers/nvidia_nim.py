"""NVIDIA NIM provider for Loom.

Uses the OpenAI-compatible API at https://integrate.api.nvidia.com/v1
with global rate limiting (12 parallel requests by default).
"""

from __future__ import annotations

from typing import Any

from loom.providers.llm_openai_compat import OpenAICompatProvider


class NvidiaNimProvider(OpenAICompatProvider):
    """NVIDIA NIM provider using OpenAI-compatible API.

    Attributes:
        PROVIDER_NAME: "nvidia"
        DEFAULT_MODEL: "meta/llama-4-maverick-17b-128e-instruct"
        SEMAPHORE_SIZE: 12 (NVIDIA free tier limit)
        SUPPORTS_EMBED: True (via /embeddings endpoint)
    """

    PROVIDER_NAME = "nvidia"
    ENV_KEY = "NVIDIA_NIM_API_KEY"
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    DEFAULT_MODEL = "meta/llama-4-maverick-17b-128e-instruct"
    ENV_ENDPOINT_KEY = "NVIDIA_NIM_ENDPOINT"
    SUPPORTS_EMBED = True
    COST_INPUT_PER_M = 0.0  # NVIDIA NIM is free tier
    COST_OUTPUT_PER_M = 0.0
    SEMAPHORE_SIZE = 12

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
        """Send chat messages to NVIDIA NIM.

        NIM-specific model validation: accepts namespace-prefixed models
        (meta/, nvidia/, mistral/).

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model override (uses default_model if None)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            response_format: JSON schema (NIM doesn't support this natively)
            timeout: Per-call timeout in seconds

        Returns:
            LLMResponse with text, tokens, cost, latency
        """
        # Validate timeout to prevent abuse
        timeout = max(1, min(int(timeout), 600))
        # Use provider's own default if passed model isn't an NIM-compatible model
        # NIM models are namespaced like "meta/llama-4-maverick-17b-128e-instruct"
        if model and not model.startswith(("meta/", "nvidia/", "mistral/")):
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

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        timeout: int = 60,  # noqa: ASYNC109
    ) -> list[list[float]]:
        """Generate embeddings via NVIDIA NIM.

        Uses NIM's /v1/embeddings endpoint with input_type parameter.
        Default model: nvidia/nv-embedqa-e5-v5 (1024 dims, free tier).

        Args:
            texts: List of text strings to embed
            model: Embedding model (default: nvidia/nv-embedqa-e5-v5)
            timeout: Per-call timeout in seconds

        Returns:
            List of embedding vectors
        """
        model = model or "nvidia/nv-embedqa-e5-v5"
        client = self._get_client()

        payload: dict[str, Any] = {
            "model": model,
            "input": texts,
            "input_type": "query",
            "encoding_format": "float",
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
        except Exception as exc:
            import logging

            logger = logging.getLogger("loom.providers.nvidia_nim")
            logger.error("NVIDIA NIM embeddings error: %s", exc)
            raise
