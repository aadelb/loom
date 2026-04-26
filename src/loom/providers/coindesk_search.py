"""CoinDesk cryptocurrency news provider (REST API via httpx)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.coindesk_search")

_COINDESK_ARTICLES_URL = "https://api.coindesk.com/v1/news"
_COINDESK_BPI_URL = "https://api.coindesk.com/v1/bpi/currentprice.json"

# Module-level client for connection pooling
_coindesk_client: httpx.Client | None = None


def _get_coindesk_client() -> httpx.Client:
    """Get or create CoinDesk client with connection pooling."""
    global _coindesk_client
    if _coindesk_client is None:
        _coindesk_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
    return _coindesk_client


def search_coindesk_news(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search CoinDesk news articles or fetch Bitcoin price data.

    If query contains "bitcoin" or "price", fetches current BTC price via BPI endpoint.
    Otherwise, searches news articles.

    Args:
        query: search query
        n: max number of results
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list.
    """
    api_key = os.environ.get("COINDESK_API_KEY", "")

    query_lower = query.lower()
    is_price_query = "bitcoin" in query_lower or "price" in query_lower or "btc" in query_lower

    try:
        client = _get_coindesk_client()
        if is_price_query:
            # Fetch Bitcoin price via BPI endpoint (no API key needed)
            resp = client.get(_COINDESK_BPI_URL)
            resp.raise_for_status()
            data = resp.json()

            # Extract BPI data
            bpi_data = data.get("bpi", {}).get("USD", {})
            results = [
                {
                    "symbol": "BTC",
                    "price": bpi_data.get("rate_float"),
                    "rate_formatted": bpi_data.get("rate"),
                    "description": f"Bitcoin price as of {data.get('time', {}).get('updated', '')}",
                    "source": "CoinDesk BPI",
                }
            ]
            return {"results": results, "query": query}
        else:
            # Fetch news articles
            headers = {}
            if api_key:
                headers["X-API-Key"] = api_key

            params: dict[str, Any] = {"limit": n}
            resp = client.get(_COINDESK_ARTICLES_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            results = [
                {
                    "url": article.get("id", ""),
                    "title": article.get("title", ""),
                    "snippet": (article.get("description", "") or "")[:500],
                    "published_date": article.get("created_at"),
                    "source": "CoinDesk News",
                }
                for article in data.get("data", [])
            ]
            return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("coindesk_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": "search failed"}

    except Exception as exc:
        logger.error("coindesk_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
