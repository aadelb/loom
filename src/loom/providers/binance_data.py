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
        return _get_top_crypto(n)

    # Try to map query to a trading pair
    pair = _QUERY_TO_PAIR.get(query_lower)
    if not pair:
        # Attempt uppercase as-is (e.g., "BTCUSDT")
        if query_upper := query.upper():
            pair = query_upper if query_upper.endswith("USDT") else f"{query_upper}USDT"

    if pair:
        return _get_single_ticker(pair)

    return {
        "error": f"Unknown cryptocurrency: {query}",
        "results": [],
    }


def _get_single_ticker(pair: str) -> dict[str, Any]:
    """Fetch 24hr ticker for a single pair."""
    try:
        with httpx.Client(timeout=15.0) as client:
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

            logger.info(
                "binance_ticker symbol=%s price=%.2f volume=%.0f",
                pair,
                result["price"],
                result["volume_24h"],
            )

            return {"results": [result]}

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            logger.warning("binance_invalid_symbol symbol=%s", pair)
            return {"error": f"Invalid trading pair: {pair}", "results": []}
        logger.warning("binance_api_error status=%d", e.response.status_code)
        return {"error": f"API error: {e.response.status_code}", "results": []}
    except Exception as e:
        logger.warning("binance_fetch_failed pair=%s: %s", pair, e)
        return {"error": str(e), "results": []}


def _get_top_crypto(n: int = 10) -> dict[str, Any]:
    """Fetch all 24hr tickers and return top n by volume."""
    n = max(1, min(n, 100))

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{_BINANCE_API_BASE}/ticker/24hr",
            )
            resp.raise_for_status()
            tickers = resp.json()

            # Filter USDT pairs and sort by volume
            usdt_pairs = [
                {
                    "symbol": t.get("symbol", ""),
                    "price": float(t.get("lastPrice", 0)),
                    "volume_24h": float(t.get("volume", 0)),
                    "quote_asset_volume_24h": float(t.get("quoteAssetVolume", 0)),
                    "price_change_24h": float(t.get("priceChange", 0)),
                    "price_change_pct": round(float(t.get("priceChangePercent", 0)), 2),
                    "high_24h": float(t.get("highPrice", 0)),
                    "low_24h": float(t.get("lowPrice", 0)),
                }
                for t in tickers
                if t.get("symbol", "").endswith("USDT")
                and float(t.get("quoteAssetVolume", 0)) > 0
            ]

            # Sort by quote asset volume (USD volume) descending
            usdt_pairs.sort(
                key=lambda x: x.get("quote_asset_volume_24h", 0),
                reverse=True,
            )

            top_n = usdt_pairs[:n]

            logger.info("binance_top_crypto n=%d fetched=%d", n, len(top_n))

            return {
                "results": top_n,
                "total_pairs": len(usdt_pairs),
            }

    except Exception as e:
        logger.warning("binance_top_crypto_failed: %s", e)
        return {
            "error": str(e),
            "results": [],
        }
