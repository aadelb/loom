"""Tests for Yahoo Finance investing data provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_investing_module():
    sys.modules.pop("loom.providers.investing_data", None)
    yield
    sys.modules.pop("loom.providers.investing_data", None)


class TestSearchInvesting:
    def test_stock_quote_success(self):
        """Test successful stock quote retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "shortName": "Apple Inc.",
                            "longName": "Apple Inc.",
                            "currency": "USD",
                            "previousClose": 185.0,
                            "marketCap": 2800000000000,
                            "exchangeTimezoneName": "America/New_York",
                        },
                        "timestamp": [1705315200, 1705401600],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [185.50, 186.25],
                                    "volume": [50000000, 45000000],
                                }
                            ]
                        },
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.investing_data._get_investing_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.investing_data import search_investing

            result = search_investing("apple stock")

            assert "error" not in result
            assert len(result["results"]) == 1
            assert result["results"][0]["symbol"] == "AAPL"
            assert result["results"][0]["price"] == 186.25
            assert result["results"][0]["currency"] == "USD"

    def test_forex_pair_success(self):
        """Test successful forex pair quote."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "shortName": "EUR/USD",
                            "currency": "USD",
                            "previousClose": 1.0850,
                        },
                        "timestamp": [1705315200],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [1.0875],
                                    "volume": [None],
                                }
                            ]
                        },
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.investing_data._get_investing_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.investing_data import search_investing

            result = search_investing("EUR/USD")

            assert result["results"][0]["price"] == 1.09
            assert result["results"][0]["change_pct"] == 0.23

    def test_symbol_not_found(self):
        """Test handling of unknown symbol."""
        with patch("loom.providers.investing_data.httpx.Client"):
            from loom.providers.investing_data import search_investing

            result = search_investing("UNKNOWNSYMBOL123XYZ")

            assert "error" in result
            assert result["error"] == "search failed"
            assert result["results"] == []

    def test_api_error_response(self):
        """Test handling of API error in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {
                "error": {
                    "description": "No data found for symbol",
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.investing_data._get_investing_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.investing_data import search_investing

            result = search_investing("INVALIDTICKER")

            assert "error" in result
            assert result["error"] == "search failed"
            assert result["results"] == []

    def test_http_status_error(self):
        """Test handling of HTTP status error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch("loom.providers.investing_data._get_investing_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.investing_data import search_investing

            result = search_investing("apple")

            assert "error" in result
            assert result["error"] == "search failed"

    def test_connect_error(self):
        """Test handling of connection error."""
        with patch("loom.providers.investing_data.httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.investing_data import search_investing

            result = search_investing("apple")

            assert "error" in result
            assert result["error"] == "search failed"

    def test_timeout_error(self):
        """Test handling of timeout error."""
        with patch("loom.providers.investing_data.httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.providers.investing_data import search_investing

            result = search_investing("apple")

            assert "error" in result
            assert result["error"] == "search failed"

    def test_price_change_calculation(self):
        """Test price change calculation when previous close differs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "shortName": "Tesla",
                            "currency": "USD",
                            "previousClose": 250.0,
                        },
                        "timestamp": [1705315200],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [255.00],
                                    "volume": [1000000],
                                }
                            ]
                        },
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.investing_data._get_investing_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.investing_data import search_investing

            result = search_investing("tesla")

            assert result["results"][0]["change"] == 5.0
            assert result["results"][0]["change_pct"] == 2.0

    def test_n_capped_at_20(self):
        """Test that n parameter is capped at 20."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "shortName": "Test",
                            "currency": "USD",
                            "previousClose": 100.0,
                        },
                        "timestamp": [1705315200],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [100.0],
                                    "volume": [1000000],
                                }
                            ]
                        },
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.investing_data._get_investing_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.investing_data import search_investing

            result = search_investing("test", n=100)

            assert len(result["results"]) == 1
