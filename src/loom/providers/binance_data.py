"""Binance cryptocurrency market data provider (public API, no auth required).

Tools:
- search_binance: Search for crypto market data by trading pair
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.binance_data")

_BINANCE_API_BASE = "https://api.binance.com/api/v3"

# Module-level client for connection pooling
_binance_client: httpx.Client | None = None

# Common crypto queries to trading pair mappings
_QUERY_TO_PAIR = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "bnb": "BNBUSDT",
    "solana": "SOLUSDT",
    "cardano": "ADAUSDT",
    "xrp": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
    "polkadot": "DOTUSDT",
    "uniswap": "UNIUSDT",
    "litecoin": "LTCUSDT",
    "bitcoin cash": "BCHUSDT",
    "chainlink": "LINKUSDT",
    "polygon": "MATICUSDT",
    "avalanche": "AVAXUSDT",
    "cosmos": "ATOMUSDT",
    "monero": "XMRUSDT",
    "zcash": "ZECUSDT",
    "ethereum classic": "ETCUSDT",
}


def _get_binance_client() -> httpx.Client:
    """Get or create Binance client with connection pooling."""
    global _binance_client
    if _binance_client is None:
        _binance_client = httpx.Client(
            timeout=15.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
    return _binance_client


def search_binance(
    query: str,
    n: int = 10,
) -> dict[str, Any]:
    """Search for crypto market data on Binance.

    Supports two modes:
    1. Query for specific crypto (e.g., "bitcoin") → returns 24hr ticker
    2. Query "top crypto" or "top cryptocurrencies" → returns top n by volume

    Args:
        query: crypto name or "top crypto" / "top cryptocurrencies"
        n: max number of results (for top crypto search)

    Returns:
        Dict with 'results' list (each with symbol, price, volume_24h,
        price_change_pct, or_error' key if request fails.
    """
    query_lower = query.lower().strip()

    # Handle "top crypto" queries
    if "top" in query_lower and ("crypto" in query_lower or "cryptocurrencies" in query_lower):
        return _get_top_crypto(n, query)

    # Try to map query to a trading pair
    pair = _QUERY_TO_PAIR.get(query_lower)
    if not pair:
        # Attempt uppercase as-is (e.g., "BTCUSDT")
        if query_upper := query.upper():
            pair = query_upper if query_upper.endswith("USDT") else f"{query_upper}USDT"

    if pair:
        return _get_single_ticker(pair, query)

    return {
        "error": "search failed",
        "query": query,
        "results": [],
    }


def _get_single_ticker(pair: str, query: str) -> dict[str, Any]:
    """Fetch 24hr ticker for a single pair."""
    try:
        client = _get_binance_client()
        resp = client.get(
            f"{_BINANCE_API_BASE}/ticker/24hr",
            params={"symbol": pair},
        )
        resp.raise_for_status()
        data = resp.json()

        price_change_pct = round(float(data.get("priceChangePercent", 0)), 2)

        result = {
            "symbol": data.get("symbol", pair),
            "price": float(data.get("lastPrice", 0)),
            "volume_24h": float(data.get("volume", 0)),
            "quote_asset_volume_24h": float(data.get("quoteAssetVolume", 0)),
            "price_change_24h": float(data.get("priceChange", 0)),
            "price_change_pct": price_change_pct,
            "high_24h": float(data.get("highPrice", 0)),
            "low_24h": float(data.get("lowPrice", 0)),
        }
        return {"results": [result], "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("binance_ticker_http_error pair=%s status=%d", pair, code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        logger.error("binance_ticker_failed pair=%s: %s", pair, type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}


def _get_top_crypto(limit: int, query: str) -> dict[str, Any]:
    """Fetch top cryptocurrencies by 24hr quote asset volume."""
    limit = min(max(limit, 1), 50)

    try:
        client = _get_binance_client()
        resp = client.get(
            f"{_BINANCE_API_BASE}/ticker/24hr",
            params={"limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for ticker in data:
            price_change_pct = round(float(ticker.get("priceChangePercent", 0)), 2)
            results.append(
                {
                    "symbol": ticker.get("symbol", ""),
                    "price": float(ticker.get("lastPrice", 0)),
                    "volume_24h": float(ticker.get("volume", 0)),
                    "quote_asset_volume_24h": float(ticker.get("quoteAssetVolume", 0)),
                    "price_change_24h": float(ticker.get("priceChange", 0)),
                    "price_change_pct": price_change_pct,
                    "high_24h": float(ticker.get("highPrice", 0)),
                    "low_24h": float(ticker.get("lowPrice", 0)),
                }
            )

        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("binance_top_http_error status=%d", code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        logger.error("binance_top_failed: %s", type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
