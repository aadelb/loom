"""Tests for shared http_helpers module."""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from loom.http_helpers import fetch_json, fetch_text, fetch_bytes


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


def _mock_response(status_code=200, json_data=None, text="", content=b""):
    resp = AsyncMock()
    resp.status_code = status_code
    resp.json = lambda: json_data
    resp.text = text
    resp.content = content
    return resp


class TestFetchJson:
    @pytest.mark.asyncio
    async def test_success(self, mock_client):
        mock_client.get.return_value = _mock_response(200, json_data={"key": "value"})
        result = await fetch_json(mock_client, "https://example.com/api")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_non_200_returns_none(self, mock_client):
        mock_client.get.return_value = _mock_response(404)
        result = await fetch_json(mock_client, "https://example.com/missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, mock_client):
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        result = await fetch_json(mock_client, "https://slow.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_none(self, mock_client):
        mock_client.get.side_effect = httpx.ConnectError("refused")
        result = await fetch_json(mock_client, "https://down.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_custom_headers(self, mock_client):
        mock_client.get.return_value = _mock_response(200, json_data={})
        await fetch_json(mock_client, "https://api.example.com", headers={"X-Key": "abc"})
        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs.get("headers") == {"X-Key": "abc"}

    @pytest.mark.asyncio
    async def test_custom_params(self, mock_client):
        mock_client.get.return_value = _mock_response(200, json_data=[1, 2])
        result = await fetch_json(mock_client, "https://api.example.com", params={"q": "test"})
        assert result == [1, 2]

    @pytest.mark.asyncio
    async def test_custom_timeout(self, mock_client):
        mock_client.get.return_value = _mock_response(200, json_data={})
        await fetch_json(mock_client, "https://example.com", timeout=5.0)
        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs.get("timeout") == 5.0


class TestFetchText:
    @pytest.mark.asyncio
    async def test_success(self, mock_client):
        mock_client.get.return_value = _mock_response(200, text="Hello World")
        result = await fetch_text(mock_client, "https://example.com")
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_non_200_returns_empty(self, mock_client):
        mock_client.get.return_value = _mock_response(500, text="error")
        result = await fetch_text(mock_client, "https://example.com")
        assert result == ""

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self, mock_client):
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        result = await fetch_text(mock_client, "https://slow.example.com")
        assert result == ""

    @pytest.mark.asyncio
    async def test_connection_error_returns_empty(self, mock_client):
        mock_client.get.side_effect = httpx.ConnectError("refused")
        result = await fetch_text(mock_client, "https://down.example.com")
        assert result == ""


class TestFetchBytes:
    @pytest.mark.asyncio
    async def test_success(self, mock_client):
        mock_client.get.return_value = _mock_response(200, content=b"\x89PNG")
        result = await fetch_bytes(mock_client, "https://example.com/image.png")
        assert result == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_non_200_returns_empty_bytes(self, mock_client):
        mock_client.get.return_value = _mock_response(403, content=b"forbidden")
        result = await fetch_bytes(mock_client, "https://example.com/secret")
        assert result == b""

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_bytes(self, mock_client):
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        result = await fetch_bytes(mock_client, "https://slow.example.com")
        assert result == b""
