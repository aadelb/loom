"""Tests for onion discovery tool."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestOnionDiscover:
    """Test research_onion_discover tool."""

    @pytest.mark.asyncio
    async def test_ahmia_fetch_success(self):
        """Test successful Ahmia API response."""
        from loom.tools.onion_discover import _fetch_ahmia

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
            <a href="https://example.onion">Example Onion</a>
            <a href="http://test.onion/path">Test</a>
        </body>
        </html>
        """

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_ahmia(mock_client, "test query")

        assert len(results) == 2
        assert any(r["url"] == "https://example.onion" for r in results)
        assert any(r["source"] == "ahmia" for r in results)

    @pytest.mark.asyncio
    async def test_ahmia_fetch_failure(self):
        """Test Ahmia API failure."""
        from loom.tools.onion_discover import _fetch_ahmia

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

        results = await _fetch_ahmia(mock_client, "test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_darksearch_fetch_success(self):
        """Test successful DarkSearch API response."""
        from loom.tools.onion_discover import _fetch_darksearch

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "data": [
                    {
                        "url": "https://market.onion",
                        "title": "Market",
                        "description": "Dark market",
                    },
                    {
                        "url": "https://forum.onion",
                        "title": "Forum",
                        "description": "Discussion forum",
                    },
                ]
            }
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_darksearch(mock_client, "test query")

        assert len(results) == 2
        assert any(r["url"] == "https://market.onion" for r in results)
        assert any(r["source"] == "darksearch" for r in results)

    @pytest.mark.asyncio
    async def test_darksearch_no_onion_urls(self):
        """Test DarkSearch with no .onion URLs."""
        from loom.tools.onion_discover import _fetch_darksearch

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "data": [
                    {
                        "url": "https://example.com",
                        "title": "Regular site",
                        "description": "Not onion",
                    }
                ]
            }
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_darksearch(mock_client, "test query")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_intelx_fetch_success(self):
        """Test successful IntelX API response."""
        from loom.tools.onion_discover import _fetch_intelx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "selectors": [
                    {"selector": "dark.onion"},
                    {"selector": "secure.onion"},
                ]
            }
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        results = await _fetch_intelx(mock_client, "test query")

        assert len(results) == 2
        assert any(r["url"] == "dark.onion" for r in results)
        assert any(r["source"] == "intelx" for r in results)

    @pytest.mark.asyncio
    async def test_ct_onion_certs_success(self):
        """Test successful Certificate Transparency fetch."""
        from loom.tools.onion_discover import _fetch_ct_onion_certs

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "test.onion\n*.test.onion"},
                {"name_value": "example.onion"},
            ]
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_ct_onion_certs(mock_client)

        assert len(results) >= 2
        assert any(r["source"] == "certificate_transparency" for r in results)
        assert any(".onion" in r["url"] for r in results)

    @pytest.mark.asyncio
    async def test_ct_deduplication(self):
        """Test that CT deduplicates URLs."""
        from loom.tools.onion_discover import _fetch_ct_onion_certs

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "test.onion"},
                {"name_value": "test.onion"},
            ]
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_ct_onion_certs(mock_client)

        # Should have only one unique entry despite two inputs
        unique_urls = {r["url"] for r in results}
        assert len(unique_urls) == 1

    @pytest.mark.asyncio
    async def test_reddit_onions_fetch_success(self):
        """Test successful Reddit fetch."""
        from loom.tools.onion_discover import _fetch_reddit_onions

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "New onion site - https://newsite.onion",
                                "selftext": "Check this out at https://mirror.onion",
                            }
                        }
                    ]
                }
            }
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_reddit_onions(mock_client, "test query")

        assert len(results) == 2
        assert any(r["source"] == "reddit_onions" for r in results)

    @pytest.mark.asyncio
    async def test_reddit_onions_no_urls(self):
        """Test Reddit fetch with no onion URLs."""
        from loom.tools.onion_discover import _fetch_reddit_onions

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "Regular post",
                                "selftext": "No onion URLs here",
                            }
                        }
                    ]
                }
            }
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_reddit_onions(mock_client, "test query")

        assert len(results) == 0

    def test_research_onion_discover_return_keys(self):
        """Test research_onion_discover returns correct keys."""
        from loom.tools.onion_discover import research_onion_discover

        # This test will call the actual function with httpx mocked
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=404, json=lambda: {}))
            mock_client_class.return_value = mock_client

            result = research_onion_discover("test")

            # Check that all expected keys are present
            assert "query" in result
            assert "sources_checked" in result
            assert "onion_urls_found" in result
            assert "total_unique" in result

            # Check data types
            assert isinstance(result["query"], str)
            assert isinstance(result["sources_checked"], list)
            assert isinstance(result["onion_urls_found"], list)
            assert isinstance(result["total_unique"], int)

    def test_research_onion_discover_max_results_validation(self):
        """Test research_onion_discover respects max_results bounds."""
        from loom.tools.onion_discover import research_onion_discover

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=404, json=lambda: {}))
            mock_client_class.return_value = mock_client

            # Test with max_results at boundary
            result = research_onion_discover("test", max_results=100)
            assert isinstance(result["total_unique"], int)
            assert result["total_unique"] <= 100


class TestOnionDiscoverEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON."""
        from loom.tools.onion_discover import _fetch_darksearch

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(side_effect=ValueError("Invalid JSON"))

        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_darksearch(mock_client, "test")

        assert results == []

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        from loom.tools.onion_discover import _fetch_ahmia

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=TimeoutError("Request timeout"))

        results = await _fetch_ahmia(mock_client, "test")

        assert results == []

    @pytest.mark.asyncio
    async def test_http_404_response(self):
        """Test handling of 404 responses."""
        from loom.tools.onion_discover import _fetch_ahmia

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = ""

        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_ahmia(mock_client, "test")

        assert results == []

    @pytest.mark.asyncio
    async def test_non_dict_response(self):
        """Test handling of non-dict JSON responses."""
        from loom.tools.onion_discover import _fetch_darksearch

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[])  # List instead of dict

        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_darksearch(mock_client, "test")

        assert results == []

    @pytest.mark.asyncio
    async def test_invalid_onion_format_filtering(self):
        """Test that invalid .onion URLs are filtered."""
        from loom.tools.onion_discover import _fetch_darksearch

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "data": [
                    {"url": "https://valid.onion", "title": "", "description": ""},
                    {"url": "https://example.com", "title": "", "description": ""},
                    {"url": "https://another.onion", "title": "", "description": ""},
                ]
            }
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await _fetch_darksearch(mock_client, "test")

        assert all(".onion" in r["url"] for r in results)
        assert len(results) == 2
