"""Unit tests for AnthropicProvider."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("loom.providers.anthropic_provider")

from loom.providers.anthropic_provider import AnthropicProvider


@pytest.fixture(autouse=True)
def clean_anthropic_env():
    old_val = os.environ.pop("ANTHROPIC_API_KEY", None)
    yield
    if old_val:
        os.environ["ANTHROPIC_API_KEY"] = old_val
    else:
        os.environ.pop("ANTHROPIC_API_KEY", None)


class TestAnthropicProvider:
    def test_available_with_key(self) -> None:
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        provider = AnthropicProvider()
        try:
            from anthropic import AsyncAnthropic  # noqa: F401
            assert provider.available() is True
        except ImportError:
            assert provider.available() is False

    def test_unavailable_without_key(self) -> None:
        provider = AnthropicProvider()
        assert provider.available() is False
        os.environ["ANTHROPIC_API_KEY"] = ""
        assert AnthropicProvider().available() is False
        os.environ["ANTHROPIC_API_KEY"] = "   "
        assert AnthropicProvider().available() is False

    def test_provider_metadata(self) -> None:
        provider = AnthropicProvider()
        assert provider.name == "anthropic"
        assert provider.default_model == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self) -> None:
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        provider = AnthropicProvider()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        with patch.object(provider, "_get_client", return_value=mock_client):
            response = await provider.chat(
                messages=[{"role": "user", "content": "test"}],
                model="claude-opus-4-6",
            )
        assert response.text == "Hello"
        assert response.model == "claude-opus-4-6"
        assert response.input_tokens == 10
        assert response.output_tokens == 20
        assert response.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_chat_uses_default_model(self) -> None:
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        provider = AnthropicProvider()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="test")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 1
        mock_response.usage.output_tokens = 1
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.chat(messages=[{"role": "user", "content": "test"}], model=None)
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_embed_raises_not_implemented(self) -> None:
        provider = AnthropicProvider()
        with pytest.raises(NotImplementedError) as exc:
            await provider.embed(texts=["test"])
        assert "Anthropic does not provide embedding" in str(exc.value)

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        provider = AnthropicProvider()
        await provider.close()
        close_called = False

        async def mock_close():
            nonlocal close_called
            close_called = True

        mock_client = AsyncMock()
        mock_client.close = mock_close
        provider.client = mock_client
        await provider.close()
        assert close_called and provider.client is None
