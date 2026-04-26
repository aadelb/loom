"""Tests for CoinDesk news search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_coindesk_module():
    sys.modules.pop("loom.providers.coindesk_search", None)
    yield
    sys.modules.pop("loom.providers.coindesk_search", None)


class TestSearchCoinDeskNews:
    def test_bitcoin_price_query_no_auth_required(self):
        """Test that Bitcoin price queries work without API key."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "bpi": {
                "USD": {
                    "rate_float": 45000.50,
                    "rate": "45,000.50",
                }
            },
            "time": {"updated": "Jan 15, 2024"},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {}, clear=True), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("bitcoin price")

            assert "error" not in result
            assert len(result["results"]) == 1
            assert result["results"][0]["symbol"] == "BTC"
            assert result["results"][0]["price"] == 45000.50

    def test_btc_price_query(self):
        """Test query with BTC abbreviation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "bpi": {
                "USD": {
                    "rate_float": 46000.0,
                    "rate": "46,000.00",
                }
            },
            "time": {"updated": "Jan 15, 2024"},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("btc price")

            assert result["results"][0]["price"] == 46000.0

    def test_news_search_missing_api_key(self):
        """Test news search without API key (still attempts API call)."""
        with patch.dict("os.environ", {}, clear=True), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
            )
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("cryptocurrency news")

            assert "error" in result
            assert result["results"] == []

    def test_news_search_success(self):
        """Test successful news article search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "article1",
                    "title": "Bitcoin Reaches New High",
                    "description": "Bitcoin crosses $45k",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "id": "article2",
                    "title": "Ethereum Update",
                    "description": "ETH 2.0 progress",
                    "created_at": "2024-01-15T09:00:00Z",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINDESK_API_KEY": "test-key"}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("crypto news", n=10)

            assert "error" not in result
            assert len(result["results"]) == 2
            assert result["results"][0]["title"] == "Bitcoin Reaches New High"
            assert result["results"][0]["snippet"] == "Bitcoin crosses $45k"

    def test_news_snippet_truncation(self):
        """Test that news snippet is truncated to 500 chars."""
        long_description = "x" * 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "article1",
                    "title": "News",
                    "description": long_description,
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINDESK_API_KEY": "key"}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("test")

            assert len(result["results"][0]["snippet"]) == 500

    def test_http_error_401(self):
        """Test handling of HTTP 401 unauthorized for news search."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"COINDESK_API_KEY": "invalid"}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("news query")

            assert "error" in result
            assert result["results"] == []

    def test_http_error_price_query(self):
        """Test handling of HTTP error in price query."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("bitcoin price")

            assert "error" in result
            assert result["results"] == []

    def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"COINDESK_API_KEY": "key"}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("DNS failed")
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("crypto news")

            assert "search failed" in result["error"]

    def test_empty_brief_handling(self):
        """Test handling of articles with missing description."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "article1",
                    "title": "News",
                    "description": None,
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINDESK_API_KEY": "key"}), patch(
            "loom.providers.coindesk_search._get_coindesk_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("news")

            assert result["results"][0]["snippet"] == ""
