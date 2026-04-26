"""Tests for Binance crypto data provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_binance_module():
    sys.modules.pop("loom.providers.binance_data", None)
    yield
    sys.modules.pop("loom.providers.binance_data", None)


class TestSearchBinance:
    def test_single_crypto_success(self):
        """Test successful search for single cryptocurrency."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "BTCUSDT",
            "lastPrice": "45000.50",
            "volume": "1000000",
            "quoteAssetVolume": "45000000000",
            "priceChange": "1000.00",
            "priceChangePercent": "2.27",
            "highPrice": "45500.00",
            "lowPrice": "43500.00",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("bitcoin")

            assert "error" not in result
            assert len(result["results"]) == 1
            assert result["results"][0]["symbol"] == "BTCUSDT"
            assert result["results"][0]["price"] == 45000.50
            assert result["results"][0]["price_change_pct"] == 2.27

    def test_ethereum_search(self):
        """Test search for Ethereum by name."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "ETHUSDT",
            "lastPrice": "2500.00",
            "volume": "500000",
            "quoteAssetVolume": "1250000000",
            "priceChange": "50.00",
            "priceChangePercent": "2.04",
            "highPrice": "2550.00",
            "lowPrice": "2450.00",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("ethereum")

            assert result["results"][0]["symbol"] == "ETHUSDT"
            assert result["results"][0]["price"] == 2500.0

    def test_unknown_cryptocurrency(self):
        """Test query with unknown cryptocurrency (formats to pair and attempts API)."""
        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
            )
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("unknowntoken123")

            assert "error" in result
            assert result["results"] == []

    def test_top_crypto_query(self):
        """Test search for top cryptocurrencies by volume."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "symbol": "BTCUSDT",
                "lastPrice": "45000.00",
                "volume": "1000000",
                "quoteAssetVolume": "45000000000",
                "priceChange": "1000.00",
                "priceChangePercent": "2.27",
                "highPrice": "45500.00",
                "lowPrice": "43500.00",
            },
            {
                "symbol": "ETHUSDT",
                "lastPrice": "2500.00",
                "volume": "500000",
                "quoteAssetVolume": "1250000000",
                "priceChange": "50.00",
                "priceChangePercent": "2.04",
                "highPrice": "2550.00",
                "lowPrice": "2450.00",
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("top cryptocurrencies", n=5)

            assert "results" in result
            assert len(result["results"]) == 2
            assert result["results"][0]["symbol"] == "BTCUSDT"

    def test_http_error_400_invalid_symbol(self):
        """Test handling of HTTP 400 for invalid symbol."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("INVALIDPAIR")

            assert "error" in result

    def test_http_error_500(self):
        """Test handling of HTTP 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("bitcoin")

            assert "error" in result

    def test_connection_error(self):
        """Test handling of connection error."""
        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = httpx.ConnectError("Network error")
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("bitcoin")

            assert "error" in result

    def test_price_change_rounding(self):
        """Test that price change percentage is rounded to 2 decimals."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "BTCUSDT",
            "lastPrice": "45000.00",
            "volume": "1000000",
            "quoteAssetVolume": "45000000000",
            "priceChange": "1234.56",
            "priceChangePercent": "2.8792945612",
            "highPrice": "46234.56",
            "lowPrice": "43765.44",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("loom.providers.binance_data.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.__exit__.return_value = False
            mock_client_cls.return_value = mock_instance

            from loom.providers.binance_data import search_binance

            result = search_binance("bitcoin")

            assert result["results"][0]["price_change_pct"] == 2.88
