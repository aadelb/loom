"""CoinMarketCap cryptocurrency research provider (REST API via httpx)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.coinmarketcap")

_CMC_LISTINGS_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
_CMC_QUOTES_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

# Module-level client for connection pooling
_cmc_client: httpx.Client | None = None

# Common cryptocurrency symbols/names for matching
_KNOWN_CRYPTOS = {
    "btc": "BTC",
    "bitcoin": "BTC",
    "eth": "ETH",
    "ethereum": "ETH",
    "bnb": "BNB",
    "binance": "BNB",
    "ada": "ADA",
    "cardano": "ADA",
    "xrp": "XRP",
    "ripple": "XRP",
    "sol": "SOL",
    "solana": "SOL",
    "doge": "DOGE",
    "dogecoin": "DOGE",
    "ltc": "LTC",
    "litecoin": "LTC",
    "usdt": "USDT",
    "usdc": "USDC",
    "link": "LINK",
    "chainlink": "LINK",
}


def _get_cmc_client() -> httpx.Client:
    """Get or create CoinMarketCap client with connection pooling."""
    global _cmc_client
    if _cmc_client is None:
        _cmc_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
    return _cmc_client


def search_crypto(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search for cryptocurrency data using CoinMarketCap API.

    Searches against known crypto symbols/names and fetches current price,
    market cap, volume, and 24h change data.

    Args:
        query: search query (e.g., "bitcoin", "BTC", "ethereum")
        n: max number of results (for trending, matched cryptos)
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list containing crypto data.
    """
    api_key = os.environ.get("COINMARKETCAP_API_KEY", "")
    if not api_key:
        return {"results": [], "query": query, "error": "COINMARKETCAP_API_KEY not set"}

    # Normalize query for matching
    query_lower = query.lower().strip()

    # Try to match against known cryptos
    matched_symbol = None
    for key, symbol in _KNOWN_CRYPTOS.items():
        if query_lower == key or query_lower == symbol.lower():
            matched_symbol = symbol
            break

    headers = {
        "Accept": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }

    try:
        client = _get_cmc_client()
        if matched_symbol:
            # Fetch specific cryptocurrency
            params = {"symbol": matched_symbol}
            resp = client.get(_CMC_QUOTES_URL, params=params, headers=headers)
        else:
            # Fetch top cryptocurrencies by market cap
            params = {"limit": n, "convert": "USD"}
            resp = client.get(_CMC_LISTINGS_URL, params=params, headers=headers)

        resp.raise_for_status()
        data = resp.json()

        results: list[dict[str, Any]] = []

        if matched_symbol:
            # Process single crypto from quotes endpoint
            crypto_data = data.get("data", {}).get(matched_symbol, {})
            if crypto_data:
                quote = crypto_data.get("quote", {}).get("USD", {})
                results.append(
                    {
                        "symbol": crypto_data.get("symbol", matched_symbol),
                        "name": crypto_data.get("name", ""),
                        "price_usd": quote.get("price"),
                        "market_cap": quote.get("market_cap"),
                        "volume_24h": quote.get("volume_24h"),
                        "percent_change_24h": quote.get("percent_change_24h"),
                    }
                )
        else:
            # Process multiple cryptos from listings endpoint
            for crypto in data.get("data", []):
                quote = crypto.get("quote", {}).get("USD", {})
                results.append(
                    {
                        "symbol": crypto.get("symbol", ""),
                        "name": crypto.get("name", ""),
                        "price_usd": quote.get("price"),
                        "market_cap": quote.get("market_cap"),
                        "volume_24h": quote.get("volume_24h"),
                        "percent_change_24h": quote.get("percent_change_24h"),
                    }
                )

        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("cmc_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": "search failed"}

    except Exception as exc:
        # Don't log full exception to avoid leaking API keys (HIGH #4)
        logger.error("cmc_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
