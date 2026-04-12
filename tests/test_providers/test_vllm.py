"""Unit tests for VllmLocalProvider."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

pytest.importorskip("loom.providers.vllm_local")

from loom.providers.vllm_local import VllmLocalProvider


@pytest.fixture(autouse=True)
def clean_vllm_env():
    old_val = os.environ.pop("VLLM_LOCAL_URL", None)
    yield
    if old_val:
        os.environ["VLLM_LOCAL_URL"] = old_val
    else:
        os.environ.pop("VLLM_LOCAL_URL", None)


class TestVllmLocalProvider:
    def test_available_endpoint_reachable(self) -> None:
        provider = VllmLocalProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.Client") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.return_value = mock_response
            mock_client_class.return_value = mock_instance
            assert provider.available() is True

    def test_unavailable_endpoint_unreachable(self) -> None:
        provider = VllmLocalProvider()
        with patch("httpx.Client") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.__enter__.return_value.get.side_effect = ConnectionError()
            mock_client_class.return_value = mock_instance
            assert provider.available() is False

    def test_provider_metadata(self) -> None:
        provider = VllmLocalProvider()
        assert provider.name == "vllm"
        assert provider.default_model == "mimo_v2_flash"
        assert provider.base_url == "http://localhost:9001/v1"
        os.environ["VLLM_LOCAL_URL"] = "http://custom:9001/v1"
        assert VllmLocalProvider().base_url == "http://custom:9001/v1"

    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self) -> None:
        provider = VllmLocalProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25},
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        with patch.object(provider, "_get_client", return_value=mock_client):
            response = await provider.chat(
                messages=[{"role": "user", "content": "test"}],
                model="mimo_v2_flash",
            )
        assert response.text == "Hello"
        assert response.model == "mimo_v2_flash"
        assert response.input_tokens == 15
        assert response.output_tokens == 25
        assert response.provider == "vllm"

    @pytest.mark.asyncio
    async def test_chat_uses_default_model(self) -> None:
        provider = VllmLocalProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.chat(messages=[{"role": "user", "content": "test"}], model=None)
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["model"] == "mimo_v2_flash"

    @pytest.mark.asyncio
    async def test_chat_handles_timeout(self) -> None:
        provider = VllmLocalProvider()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(httpx.TimeoutException):
                await provider.chat(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_embed_returns_vectors(self) -> None:
        provider = VllmLocalProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}],
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        with patch.object(provider, "_get_client", return_value=mock_client):
            embeddings = await provider.embed(texts=["text1", "text2"])
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        provider = VllmLocalProvider()
        await provider.close()
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        provider.client = mock_client
        await provider.close()
        mock_client.aclose.assert_called_once()
        assert provider.client is None
