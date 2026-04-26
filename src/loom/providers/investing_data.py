"""Financial market data research via Yahoo Finance API.

Provides stock quotes, forex rates, and commodity prices without authentication.

Provider:
- search_investing: Query stocks, forex, commodities via Yahoo Finance public API
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.investing_data")

# Yahoo Finance API endpoint (public, no auth required)
YAHOO_FINANCE_API = "https://query1.finance.yahoo.com/v8/finance/chart"

# Symbol mapping: common query terms to Yahoo Finance symbols
_SYMBOL_MAP: dict[str, str] = {
    # Stocks (US)
    "apple": "AAPL",
    "apple stock": "AAPL",
    "msft": "MSFT",
    "microsoft": "MSFT",
    "microsoft stock": "MSFT",
    "google": "GOOGL",
    "google stock": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "amazon stock": "AMZN",
    "tesla": "TSLA",
    "tesla stock": "TSLA",
    "meta": "META",
    "meta stock": "META",
    "nvidia": "NVDA",
    "nvidia stock": "NVDA",
    "amd": "AMD",
    "amd stock": "AMD",
    "intel": "INTC",
    "intel stock": "INTC",
    # Commodities
    "gold": "GC=F",
    "gold price": "GC=F",
    "silver": "SI=F",
    "silver price": "SI=F",
    "crude oil": "CL=F",
    "oil price": "CL=F",
    "natural gas": "NG=F",
    "copper": "HG=F",
    # Forex
    "eurusd": "EURUSD=X",
    "eur/usd": "EURUSD=X",
    "gbpusd": "GBPUSD=X",
    "gbp/usd": "GBPUSD=X",
    "usdjpy": "USDJPY=X",
    "usd/jpy": "USDJPY=X",
    "audusd": "AUDUSD=X",
    "aud/usd": "AUDUSD=X",
    # Indices
    "sp500": "^GSPC",
    "s&p 500": "^GSPC",
    "dow jones": "^DJI",
    "nasdaq": "^IXIC",
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
}

# Request timeout
REQUEST_TIMEOUT = 15.0


# Module-level client for connection pooling
_investing_client: httpx.Client | None = None


def _get_investing_client() -> httpx.Client:
    """Get or create investing client with connection pooling."""
    global _investing_client
    if _investing_client is None:
        _investing_client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
    return _investing_client
# Response constraints
MAX_RESULTS = 20


def _normalize_query(query: str) -> str:
    """Normalize query to lowercase and remove extra whitespace."""
    return query.lower().strip()


def _query_to_symbol(query: str) -> str | None:
    """Map query to Yahoo Finance symbol using predefined map and pattern matching.

    Args:
        query: search query (e.g., "Apple stock", "EUR/USD", "BTC price")

    Returns:
        Yahoo Finance symbol (e.g., "AAPL", "EURUSD=X") or None if not found
    """
    normalized = _normalize_query(query)

    # Direct map lookup
    if normalized in _SYMBOL_MAP:
        return _SYMBOL_MAP[normalized]

    # Try partial matches (e.g., "apple" in "apple stock")
    for key, symbol in _SYMBOL_MAP.items():
        if key in normalized:
            return symbol

    # Try to extract uppercase ticker (e.g., "AAPL", "TSLA")
    match = re.search(r"\b([A-Z]{1,5})\b", query.upper())
    if match:
        return match.group(1)

    # Try to extract forex pair (e.g., "EUR/USD" -> "EURUSD=X")
    forex_match = re.search(r"([A-Z]{3})[/\s-]?([A-Z]{3})", query.upper())
    if forex_match:
        pair = forex_match.group(1) + forex_match.group(2)
        # Check if it's a known forex pair
        if any(sym.startswith(pair) and sym.endswith("=X") for sym in _SYMBOL_MAP.values()):
            return f"{pair}=X"

    return None


def search_investing(
    query: str,
    n: int = 10,
) -> dict[str, Any]:
    """Search for stock/forex/commodity quotes via Yahoo Finance public API.

    Uses the public Yahoo Finance chart API (no authentication required).
    Fetches 5-day daily data for the queried symbol.

    Args:
        query: search query (e.g., "Apple stock", "EUR/USD", "BTC price")
        n: max results to return (capped at 20)

    Returns:
        Dict with ``results`` list (each with symbol, price, change, volume, name)
        and ``query_original``, or ``error`` on failure.
    """
    n = min(n, MAX_RESULTS)

    # Convert query to symbol
    symbol = _query_to_symbol(query)

    if not symbol:
        logger.debug("investing_symbol_not_found query=%s", query)
        return {
            "query": query,
            "error": "search failed",
            "results": [],
        }

    # Fetch data from Yahoo Finance
    try:
        client = _get_investing_client()
        response = client.get(
                YAHOO_FINANCE_API,
                params={
                    "symbols": symbol,
                    "interval": "1d",
                    "range": "5d",
                },
        )
        response.raise_for_status()

        data = response.json()
        chart_data = data.get("chart", {})
        error_data = chart_data.get("error")

        # Check for API errors
        if error_data:
                error_msg = error_data.get("description", "Unknown error")
                logger.warning("investing_api_error symbol=%s error=%s", symbol, error_msg)
                return {
                    "query": query,
                    "error": "search failed",
                    "results": [],
                }

        results_data = chart_data.get("result", [])

        if not results_data:
                return {
                    "query": query,
                    "error": "No data returned from Yahoo Finance",
                    "results": [],
                }

        # Extract quote data
        quote = results_data[0].get("meta", {})
        timestamps = results_data[0].get("timestamp", [])
        closes = results_data[0].get("indicators", {}).get("quote", [{}])[0].get(
                "close", []
        )
        volumes = results_data[0].get("indicators", {}).get("quote", [{}])[0].get(
                "volume", []
        )

        # Get latest price (last non-null close)
        current_price = None
        for close in reversed(closes):
                if close is not None:
                    current_price = close
                    break

        if current_price is None:
                return {
                    "query": query,
                    "error": "No price data available",
                    "results": [],
                }

        # Get previous close if available
        prev_close = quote.get("previousClose", current_price)
        change = current_price - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close and prev_close != 0 else 0

        # Get latest volume
        volume = None
        for vol in reversed(volumes):
                if vol is not None:
                    volume = vol
                    break

        # Build result
        result = {
                "symbol": symbol,
                "name": quote.get("shortName", quote.get("longName", symbol)),
                "price": round(current_price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "currency": quote.get("currency", "USD"),
                "volume": volume if volume is not None else 0,
                "market_cap": quote.get("marketCap"),
                "timezone": quote.get("exchangeTimezoneName"),
        }

        logger.info(
                "investing_quote_retrieved symbol=%s price=%s change_pct=%s",
                symbol,
                current_price,
                change_pct,
        )

        return {
                "query": query,
                "symbol": symbol,
                "results": [result],
                "updated": timestamps[-1] if timestamps else None,
        }

    except httpx.HTTPStatusError as exc:
        logger.warning("investing_http_error symbol=%s status=%d", symbol, exc.response.status_code)
        return {
        "query": query,
        "error": "search failed",
        "results": [],
        }

    except httpx.ConnectError:
        logger.warning("investing_connect_failed")
        return {
        "query": query,
        "error": "Could not connect to Yahoo Finance API",
        "results": [],
        }

    except httpx.TimeoutException:
        logger.warning("investing_timeout symbol=%s", symbol)
        return {
        "query": query,
        "error": "search failed",
        "results": [],
        }

    except Exception as exc:
        logger.error("investing_unexpected_error symbol=%s: %s", symbol, exc)
        return {
        "query": query,
        "error": "search failed",
        "results": [],
        }
