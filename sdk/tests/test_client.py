"""Tests for Loom SDK client."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom_sdk import LoomClient, LoomClientError
from loom_sdk.models import SearchResponse, FetchResult


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = LoomClient("http://127.0.0.1:8787")
    assert client.server_url == "http://127.0.0.1:8787"
    assert client.api_key is None
    assert client.timeout == 300.0
    await client.close()


@pytest.mark.asyncio
async def test_client_with_api_key():
    """Test client with API key."""
    client = LoomClient("http://127.0.0.1:8787", api_key="test-key")
    assert client.api_key == "test-key"
    await client.close()


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    async with LoomClient("http://127.0.0.1:8787") as client:
        assert client is not None


@pytest.mark.asyncio
async def test_search_parsing():
    """Test search result parsing."""
    client = LoomClient()

    # Mock the _call_tool method
    mock_response = {
        "provider": "exa",
        "query": "test query",
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "snippet": "Test snippet",
            }
        ],
    }

    with patch.object(client, "_call_tool", new_callable=AsyncMock) as mock_tool:
        mock_tool.return_value = mock_response

        results = await client.search("test query", provider="exa", n=10)

        assert isinstance(results, SearchResponse)
        assert results.query == "test query"
        assert len(results.results) == 1
        assert results.results[0].title == "Test Result"

    await client.close()


@pytest.mark.asyncio
async def test_fetch_parsing():
    """Test fetch result parsing."""
    client = LoomClient()

    mock_response = {
        "status_code": 200,
        "content": "Test content",
        "encoding": "utf-8",
    }

    with patch.object(client, "_call_tool", new_callable=AsyncMock) as mock_tool:
        mock_tool.return_value = mock_response

        result = await client.fetch("https://example.com")

        assert isinstance(result, FetchResult)
        assert result.status_code == 200
        assert result.content == "Test content"

    await client.close()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling."""
    client = LoomClient()

    with patch.object(client, "_call_tool", new_callable=AsyncMock) as mock_tool:
        mock_tool.side_effect = LoomClientError("Test error")

        with pytest.raises(LoomClientError):
            await client.search("test")

    await client.close()


def test_models_validation():
    """Test model validation."""
    from loom_sdk.models import SearchResult, HealthCheckResponse

    # Valid SearchResult
    result = SearchResult(
        title="Test",
        url="https://example.com",
        snippet="Test snippet",
    )
    assert result.title == "Test"

    # Valid HealthCheckResponse
    health = HealthCheckResponse(
        status="healthy",
        version="0.1.0",
    )
    assert health.status == "healthy"
