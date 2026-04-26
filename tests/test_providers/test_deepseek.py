"""Tests for DeepSeek provider."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.providers.base import LLMResponse


@pytest.fixture(autouse=True)
def _clear_deepseek_module():
    sys.modules.pop("loom.providers.deepseek_provider", None)
    yield
    sys.modules.pop("loom.providers.deepseek_provider", None)


@pytest.mark.asyncio
class TestDeepSeekProvider:
    async def test_available_with_key(self):
        """Test available() returns True with valid API key."""
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test123"}):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            assert provider.available() is True

    async def test_available_without_key(self):
        """Test available() returns False without API key."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            assert provider.available() is False

    async def test_available_with_whitespace_key(self):
        """Test available() returns False with whitespace-only key."""
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "  \n"}):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            assert provider.available() is False

    async def test_chat_success(self):
        """Test successful chat call with mocked httpx."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "choices": [
                    {
                        "message": {"content": "I am DeepSeek AI assistant."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 8,
                },
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test123"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            messages = [{"role": "user", "content": "Who are you?"}]

            result = await provider.chat(messages)

            assert isinstance(result, LLMResponse)
            assert result.text == "I am DeepSeek AI assistant."
            assert result.provider == "deepseek"
            assert result.model == "deepseek-chat"
            assert result.input_tokens == 15
            assert result.output_tokens == 8

            await provider.close()

    async def test_chat_with_custom_model(self):
        """Test chat with custom model override."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "choices": [
                    {"message": {"content": "test"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            messages = [{"role": "user", "content": "test"}]

            result = await provider.chat(messages, model="deepseek-reasoning")

            assert result.model == "deepseek-reasoning"

            await provider.close()

    async def test_chat_timeout(self):
        """Test chat call with timeout exception."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test123"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(httpx.TimeoutException):
                await provider.chat(messages)

            await provider.close()

    async def test_chat_http_error_401(self):
        """Test chat call with 401 unauthorized error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "invalid"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat(messages)

            await provider.close()

    async def test_chat_http_error_429(self):
        """Test chat call with rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limited", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient",
            return_value=mock_client,
        ):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat(messages)

            await provider.close()

    async def test_close(self):
        """Test closing the provider."""
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test123"}):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
            await provider.close()
            assert provider.client is None

    async def test_embed_not_implemented(self):
        """Test that embed raises NotImplementedError."""
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk_test123"}):
            from loom.providers.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()

            with pytest.raises(NotImplementedError):
                await provider.embed(["text1", "text2"])

            await provider.close()
