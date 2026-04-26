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
            "httpx.Client"
        ) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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

        with patch.dict("os.environ", {}), patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("btc price")

            assert result["results"][0]["price"] == 46000.0

    def test_news_search_missing_api_key(self):
        """Test news search returns error when API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("cryptocurrency news")

            assert result["error"] == "COINDESK_API_KEY not set"
            assert result["results"] == []

    def test_news_search_success(self):
        """Test successful news article search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "headline": "Bitcoin Reaches New High",
                    "brief": "Bitcoin crosses $45k",
                    "link": "https://coindesk.com/article1",
                    "published_at": "2024-01-15T10:00:00Z",
                    "author": "John Doe",
                },
                {
                    "headline": "Ethereum Update",
                    "brief": "ETH 2.0 progress",
                    "link": "https://coindesk.com/article2",
                    "published_at": "2024-01-15T09:00:00Z",
                    "author": "Jane Smith",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINDESK_API_KEY": "test-key"}), patch(
            "httpx.Client"
        ) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("crypto news", n=10)

            assert "error" not in result
            assert len(result["results"]) == 2
            assert result["results"][0]["title"] == "Bitcoin Reaches New High"
            assert result["results"][0]["snippet"] == "Bitcoin crosses $45k"
            assert result["results"][0]["author"] == "John Doe"

    def test_news_snippet_truncation(self):
        """Test that news snippet is truncated to 500 chars."""
        long_brief = "x" * 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "headline": "News",
                    "brief": long_brief,
                    "link": "https://example.com",
                    "published_at": "2024-01-15T10:00:00Z",
                    "author": "Test",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINDESK_API_KEY": "key"}), patch(
            "httpx.Client"
        ) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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
            "httpx.Client"
        ) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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

        with patch.dict("os.environ", {}), patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("bitcoin price")

            assert "error" in result
            assert result["results"] == []

    def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"COINDESK_API_KEY": "key"}), patch(
            "httpx.Client"
        ) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = httpx.ConnectError("DNS failed")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("crypto news")

            assert "search failed" in result["error"]

    def test_empty_brief_handling(self):
        """Test handling of articles with missing brief."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "headline": "News",
                    "brief": None,
                    "link": "https://example.com",
                    "published_at": "2024-01-15T10:00:00Z",
                    "author": "Test",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINDESK_API_KEY": "key"}), patch(
            "httpx.Client"
        ) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news("news")

            assert result["results"][0]["snippet"] == ""
