# Adding Custom LLM Providers

This guide walks through adding a new LLM provider to Loom's provider cascade system.

## Architecture Overview

Loom's LLM provider system uses a cascading fallback pattern:

1. **Base class:** `loom.providers.base.LLMProvider` (abstract)
2. **Implementations:** `nvidia_nim.py`, `openai_provider.py`, `anthropic_provider.py`, `vllm_local.py`
3. **Registry:** `loom.providers.__init__.py` exports all providers
4. **Cascade:** `LLM_PROVIDER_CASCADE` config (env var or `config.json`) lists providers in order; first available is used

When you call a tool like `research_llm_chat`, Loom tries each provider in the cascade list until one succeeds (is available and not rate-limited).

## Create a Custom Provider

### Step 1: Understand the Base Class

```python
# loom/providers/base.py

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: dict = None,
    ) -> LLMResponse:
        """Generate a response from a list of messages."""

    @abstractmethod
    async def embed(
        self,
        text: str | list[str],
        model: str = None,
    ) -> dict:
        """Generate embeddings."""

    @abstractmethod
    async def available(self) -> bool:
        """Check if the provider is available (API key set, endpoint reachable)."""

    async def close(self) -> None:
        """Clean up resources (http client, etc.)."""
```

### Step 2: Implement Your Provider

Example: custom provider using an OpenAI-compatible endpoint.

**File:** `loom/providers/custom_provider.py`

```python
"""Custom OpenAI-compatible LLM provider."""

from __future__ import annotations

import httpx
import logging
from dataclasses import dataclass
from typing import Any

from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost

logger = logging.getLogger("loom.providers.custom")


class CustomProvider(LLMProvider):
    """Custom provider using an OpenAI-compatible API."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        default_model: str = "custom-model-7b",
    ):
        """
        Args:
            endpoint_url: Base URL of the API (e.g., "https://api.custom.com/v1")
            api_key: API key for authentication
            default_model: Default model ID to use if not specified in chat()
        """
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def available(self) -> bool:
        """Check if the endpoint is reachable and API key is valid."""
        if not self.api_key:
            logger.warning("CUSTOM_API_KEY not set")
            return False

        try:
            # Ping the /models endpoint (OpenAI-compatible)
            response = await self.http_client.get(
                f"{self.endpoint_url}/models",
                timeout=2.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Custom provider unavailable: {e}")
            return False

    async def chat(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: dict = None,
    ) -> LLMResponse:
        """Generate a chat response."""
        if not model:
            model = self.default_model

        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add JSON schema if requested (OpenAI-compatible)
            if response_format:
                payload["response_format"] = response_format

            response = await self.http_client.post(
                f"{self.endpoint_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            # Parse OpenAI-compatible response
            output_text = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason", "stop")

            # Token counts (may not be available; default to 0)
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # Estimate cost
            cost = _estimate_cost("custom", model, input_tokens, output_tokens)

            return LLMResponse(
                text=output_text,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=int(response.elapsed.total_seconds() * 1000),
                provider="custom",
                finish_reason=finish_reason,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Custom provider error: {e.response.text}")
            raise Exception(f"Custom provider failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in custom provider: {e}")
            raise

    async def embed(
        self,
        text: str | list[str],
        model: str = None,
    ) -> dict:
        """Generate embeddings (if supported)."""
        # If your endpoint doesn't support embeddings, raise NotImplementedError
        raise NotImplementedError("Custom provider does not support embeddings")

    async def close(self) -> None:
        """Clean up HTTP client."""
        await self.http_client.aclose()
```

### Step 3: Register the Provider

Edit `loom/providers/__init__.py` to export your provider:

```python
"""LLM provider registry and cascade."""

from loom.providers.custom_provider import CustomProvider
from loom.providers.nvidia_nim import NVIDIANIMProvider
from loom.providers.openai_provider import OpenAIProvider
from loom.providers.anthropic_provider import AnthropicProvider
from loom.providers.vllm_local import VLLMLocalProvider

__all__ = [
    "CustomProvider",
    "NVIDIANIMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "VLLMLocalProvider",
]

# Available provider implementations
PROVIDERS = {
    "custom": CustomProvider,
    "nvidia": NVIDIANIMProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "vllm": VLLMLocalProvider,
}
```

### Step 4: Add Configuration

Update `loom.config.ConfigModel` to include custom provider env vars (optional, if your provider needs additional config):

```python
# In loom/config.py

class ConfigModel(BaseModel):
    # ... existing fields ...

    CUSTOM_API_KEY: str = Field(
        default="",
        description="API key for custom provider",
    )
    CUSTOM_ENDPOINT_URL: str = Field(
        default="https://api.custom.com/v1",
        description="Endpoint URL for custom provider",
    )
    CUSTOM_MODEL: str = Field(
        default="custom-model-7b",
        description="Default model for custom provider",
    )
```

### Step 5: Wire It Into the Cascade

The cascade is read from `LLM_PROVIDER_CASCADE` (env var or config.json). Update your `.env`:

```bash
LLM_PROVIDER_CASCADE=custom,nvidia,openai
CUSTOM_API_KEY=your_custom_api_key
CUSTOM_ENDPOINT_URL=https://api.custom.com/v1
CUSTOM_MODEL=custom-model-7b
```

Or set it at runtime:

```python
research_config_set("LLM_PROVIDER_CASCADE", "custom,nvidia,openai")
```

### Step 6: Test It

Create a test file: `tests/test_providers/test_custom_provider.py`

```python
"""Tests for custom provider."""

import pytest
import httpx
from loom.providers.custom_provider import CustomProvider

# Mock HTTP responses
@pytest.fixture
def mock_transport():
    """Mock HTTP transport for testing."""
    responses = {
        "https://api.custom.com/v1/models": httpx.Response(
            status_code=200,
            json={"data": [{"id": "custom-model-7b"}]},
        ),
        "https://api.custom.com/v1/chat/completions": httpx.Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {"content": "Hello, world!"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                },
            },
        ),
    }

    def transport_handler(request):
        url = str(request.url)
        if url in responses:
            return responses[url]
        raise httpx.RequestNotFound(f"No mock for {url}")

    return httpx.MockTransport(transport_handler)


@pytest.mark.asyncio
async def test_custom_provider_available(mock_transport):
    """Test availability check."""
    provider = CustomProvider(
        endpoint_url="https://api.custom.com/v1",
        api_key="test_key",
    )
    provider.http_client = httpx.AsyncClient(transport=mock_transport)

    is_available = await provider.available()
    assert is_available is True


@pytest.mark.asyncio
async def test_custom_provider_chat(mock_transport):
    """Test chat response."""
    provider = CustomProvider(
        endpoint_url="https://api.custom.com/v1",
        api_key="test_key",
    )
    provider.http_client = httpx.AsyncClient(transport=mock_transport)

    response = await provider.chat(
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert response.text == "Hello, world!"
    assert response.model == "custom-model-7b"
    assert response.input_tokens == 10
    assert response.output_tokens == 5
    assert response.provider == "custom"
```

Run the test:

```bash
pytest tests/test_providers/test_custom_provider.py -v
```

## Cost Estimation

If your provider has a different pricing model, override `_estimate_cost` in the base module:

```python
# In loom/providers/base.py, extend _estimate_cost():

if provider == "custom" or "custom" in model.lower():
    # Custom pricing: $0.01 per 1K input tokens, $0.02 per 1K output
    in_cost = (input_tokens / 1000) * 0.01
    out_cost = (output_tokens / 1000) * 0.02
    return in_cost + out_cost
```

Or if your provider is free:

```python
if provider == "custom":
    return 0.0  # Free (self-hosted or sponsored)
```

## Integration Test

Add your provider to the cascade and test the full flow:

```bash
# .env
CUSTOM_API_KEY=test_key
LLM_PROVIDER_CASCADE=custom,nvidia,openai

# Run a research task
python -c "
from loom import client
result = client.research_llm_chat(
    messages=[{'role': 'user', 'content': 'Hello'}],
    model='custom-model-7b',
)
print(result)
"
```

## Examples

### Self-Hosted vLLM (Already Built-In)

The vLLM provider demonstrates a self-hosted OpenAI-compatible endpoint:

- File: `loom/providers/vllm_local.py`
- Cost: Free (your hardware)
- Endpoint: `http://localhost:9001/v1` (customizable)

### Groq (Example to Add)

To add Groq:

1. Create `loom/providers/groq_provider.py`
2. Implement chat() using the Groq Python SDK or HTTP API
3. Register in `__init__.py`
4. Add env vars: `GROQ_API_KEY`
5. Test and add to CI

## Security Considerations

- **API keys:** Store in environment variables, never commit to git
- **HTTP validation:** Validate URLs before making requests
- **Error messages:** Don't leak API keys in error logs
- **Timeout:** Set reasonable timeouts (30 seconds is typical) to avoid hanging requests

## Related Documentation

- [docs/providers/nvidia-nim.md](../providers/nvidia-nim.md) — NVIDIA NIM provider reference
- [docs/providers/openai.md](../providers/openai.md) — OpenAI provider reference
- [docs/providers/local-vllm.md](../providers/local-vllm.md) — Local vLLM reference
