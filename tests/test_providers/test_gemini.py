"""Tests for Google Gemini provider."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.providers.base import LLMResponse


@pytest.fixture(autouse=True)
def _clear_gemini_module():
    sys.modules.pop("loom.providers.gemini_provider", None)
    yield
    sys.modules.pop("loom.providers.gemini_provider", None)


@pytest.mark.asyncio
class TestGeminiProvider:
    async def test_available_with_key(self):
        """Test available() returns True with valid API key."""
        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test123"}):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            assert provider.available() is True

    async def test_available_without_key(self):
        """Test available() returns False without API key."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            assert provider.available() is False

    async def test_available_with_fallback_key(self):
        """Test available() with GOOGLE_AI_KEY_1 fallback."""
        with patch.dict("os.environ", {"GOOGLE_AI_KEY_1": "AIzaSy_fallback"}):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            assert provider.available() is True

    async def test_chat_success_message_format_conversion(self):
        """Test chat with correct OpenAI-to-Gemini message format conversion."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "This is Gemini response."}],
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 20,
                "candidatesTokenCount": 10,
            },
        }

        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ) as mock_post:
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]

            result = await provider.chat(messages)

            assert isinstance(result, LLMResponse)
            assert result.text == "This is Gemini response."
            assert result.provider == "gemini"
            assert result.input_tokens == 20
            assert result.output_tokens == 10

            await provider.close()

    async def test_chat_system_message_mapped_to_user(self):
        """Test that system messages are mapped to user role."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Response"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 1,
            },
        }

        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ) as mock_post:
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            messages = [{"role": "system", "content": "You are helpful."}]

            result = await provider.chat(messages)

            # Verify the message was sent with correct format
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["contents"][0]["role"] == "user"
            assert payload["contents"][0]["parts"][0]["text"] == "You are helpful."

            await provider.close()

    async def test_chat_timeout(self):
        """Test chat call with timeout exception."""
        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test"}), patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.TimeoutException):
                await provider.chat(messages)

            await provider.close()

    async def test_chat_http_error_401(self):
        """Test chat call with 401 error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "invalid"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            messages = [{"role": "user", "content": "test"}]

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat(messages)

            await provider.close()

    async def test_close(self):
        """Test closing the provider."""
        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test"}):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            await provider.close()
            assert provider.client is None

    async def test_embed_not_implemented(self):
        """Test that embed raises NotImplementedError."""
        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test"}):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()

            with pytest.raises(NotImplementedError):
                await provider.embed(["text"])

            await provider.close()

    async def test_chat_with_empty_candidates(self):
        """Test chat response with empty candidates list."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "candidates": [],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 0,
            },
        }

        with patch.dict("os.environ", {"GOOGLE_AI_KEY": "AIzaSy_test"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.providers.gemini_provider import GeminiProvider

            provider = GeminiProvider()
            messages = [{"role": "user", "content": "test"}]

            result = await provider.chat(messages)

            assert result.text == ""
            assert result.finish_reason is None

            await provider.close()
