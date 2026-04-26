"""Tests for Groq provider."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.providers.base import LLMResponse


@pytest.fixture(autouse=True)
def _clear_groq_module():
    sys.modules.pop("loom.providers.groq_provider", None)
    yield
    sys.modules.pop("loom.providers.groq_provider", None)


@pytest.mark.asyncio
class TestGroqProvider:
    async def test_available_with_key(self):
        """Test available() returns True with valid API key."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            assert provider.available() is True

    async def test_available_without_key(self):
        """Test available() returns False without API key."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            assert provider.available() is False

    async def test_available_with_whitespace_key(self):
        """Test available() returns False with whitespace-only key."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "   "}):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            assert provider.available() is False

    async def test_chat_success(self):
        """Test successful chat call with mocked httpx."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
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
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            messages = [{"role": "user", "content": "Hello"}]

            result = await provider.chat(messages)

            assert isinstance(result, LLMResponse)
            assert result.text == "Hello, world!"
            assert result.provider == "groq"
            assert result.input_tokens == 10
            assert result.output_tokens == 5

            await provider.close()

    async def test_chat_timeout(self):
        """Test chat call with timeout exception."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(httpx.TimeoutException):
                await provider.chat(messages)

            await provider.close()

    async def test_chat_http_error(self):
        """Test chat call with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.dict("os.environ", {"GROQ_API_KEY": "invalid"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat(messages)

            await provider.close()

    async def test_close(self):
        """Test closing the provider."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            await provider.close()
            assert provider.client is None

    async def test_embed_not_implemented(self):
        """Test that embed raises NotImplementedError."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()

            with pytest.raises(NotImplementedError):
                await provider.embed(["test text"])

            await provider.close()

    async def test_timeout_validation(self):
        """Test that timeout is clamped to valid range."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "choices": [{"message": {"content": "test"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test123"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.groq_provider import GroqProvider

            provider = GroqProvider()
            messages = [{"role": "user", "content": "test"}]

            await provider.chat(messages, timeout=1000)

            # Verify timeout was clamped to 600
            call_kwargs = mock_client.post.call_args.kwargs
            assert call_kwargs["timeout"] == 600.0

            await provider.close()
