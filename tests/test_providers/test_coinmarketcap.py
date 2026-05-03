"""Tests for CoinMarketCap crypto search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_coinmarketcap_module():
    sys.modules.pop("loom.providers.coinmarketcap", None)
    yield
    sys.modules.pop("loom.providers.coinmarketcap", None)



pytestmark = pytest.mark.asyncio
class TestSearchCrypto:
    async def test_missing_api_key(self):
        """Test returns error when COINMARKETCAP_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("bitcoin")

            assert result["error"] == "COINMARKETCAP_API_KEY not set"
            assert result["results"] == []

    async def test_success_known_crypto(self):
        """Test successful search for known cryptocurrency."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "BTC": {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "quote": {
                        "USD": {
                            "price": 45000.50,
                            "market_cap": 900000000000,
                            "volume_24h": 30000000000,
                            "percent_change_24h": 2.5,
                        }
                    },
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "test-key"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("bitcoin")

            assert "error" not in result
            assert len(result["results"]) == 1
            assert result["results"][0]["symbol"] == "BTC"
            assert result["results"][0]["name"] == "Bitcoin"
            assert result["results"][0]["price_usd"] == 45000.50
            assert result["query"] == "bitcoin"

    async def test_success_top_cryptos(self):
        """Test successful search for top cryptocurrencies by market cap."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "quote": {
                        "USD": {
                            "price": 45000.0,
                            "market_cap": 900000000000,
                            "volume_24h": 30000000000,
                            "percent_change_24h": 2.5,
                        }
                    },
                },
                {
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "quote": {
                        "USD": {
                            "price": 2500.0,
                            "market_cap": 300000000000,
                            "volume_24h": 15000000000,
                            "percent_change_24h": 1.5,
                        }
                    },
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "key"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("top cryptos", n=5)

            assert len(result["results"]) == 2
            assert result["results"][0]["symbol"] == "BTC"
            assert result["results"][1]["symbol"] == "ETH"

    async def test_case_insensitive_matching(self):
        """Test that query matching is case-insensitive."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "ETH": {
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "quote": {"USD": {"price": 2500.0}},
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "key"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("ETHEREUM")

            assert result["results"][0]["symbol"] == "ETH"

    async def test_http_error_401(self):
        """Test handling of HTTP 401 unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "invalid"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("bitcoin")

            assert "error" in result
            assert result["results"] == []

    async def test_http_error_429(self):
        """Test handling of HTTP 429 rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limited", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "key"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("bitcoin")

            assert "error" in result

    async def test_unknown_crypto(self):
        """Test behavior with unknown cryptocurrency."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "key"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("unknowntoken123")

            assert result["results"] == []

    async def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"COINMARKETCAP_API_KEY": "key"}), patch(
            "loom.providers.coinmarketcap._get_cmc_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("Network error")
            mock_get_client.return_value = mock_client

            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto("bitcoin")

            assert "search failed" in result["error"]
