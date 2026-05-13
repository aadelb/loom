"""Tests for Moonshot/Kimi provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest

from loom.providers.base import LLMResponse


@pytest.fixture(autouse=True)
def _clear_moonshot_module():
    sys.modules.pop("loom.providers.moonshot_provider", None)
    yield
    sys.modules.pop("loom.providers.moonshot_provider", None)


@pytest.mark.asyncio
class TestMoonshotProvider:
    async def test_available_with_key(self):
        """Test available() returns True with valid API key."""
        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk-test123"}):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            assert provider.available() is True

    async def test_available_without_key(self):
        """Test available() returns False without API key."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            assert provider.available() is False

    async def test_available_with_whitespace_key(self):
        """Test available() returns False with whitespace-only key."""
        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "\t\n"}):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            assert provider.available() is False

    async def test_chat_success(self):
        """Test successful chat call with mocked httpx."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Hello from Kimi!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            messages = [{"role": "user", "content": "Hi Kimi"}]

            result = await provider.chat(messages)

            assert isinstance(result, LLMResponse)
            assert result.text == "Hello from Kimi!"
            assert result.provider == "moonshot"
            assert result.model == "kimi-k2-0711-preview"
            assert result.input_tokens == 12
            assert result.output_tokens == 4
            assert result.finish_reason == "stop"

            await provider.close()

    async def test_chat_with_custom_model(self):
        """Test chat with custom model override."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "response"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ) as mock_post:
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            messages = [{"role": "user", "content": "test"}]

            result = await provider.chat(messages, model="kimi-k2")

            assert result.model == "kimi-k2"

            await provider.close()

    async def test_chat_timeout(self):
        """Test chat call with timeout exception."""
        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.TimeoutException):
                await provider.chat(messages)

            await provider.close()

    async def test_chat_http_error_401(self):
        """Test chat call with 401 unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "invalid"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat(messages)

            await provider.close()

    async def test_chat_http_error_500(self):
        """Test chat call with 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat(messages)

            await provider.close()

    async def test_close(self):
        """Test closing the provider."""
        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            await provider.close()
            assert provider._client is None

    async def test_embed_not_implemented(self):
        """Test that embed raises NotImplementedError."""
        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}):
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()

            with pytest.raises(NotImplementedError):
                await provider.embed(["text"])

            await provider.close()

    async def test_default_timeout_120s(self):
        """Test that default timeout is 120 seconds."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "test"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ) as mock_post:
            from loom.providers.moonshot_provider import MoonshotProvider

            provider = MoonshotProvider()
            messages = [{"role": "user", "content": "test"}]

            await provider.chat(messages)

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["timeout"] == 120.0

            await provider.close()
