"""CoinDesk cryptocurrency news provider (REST API via httpx)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.coindesk_search")

_COINDESK_ARTICLES_URL = "https://api.coindesk.com/v1/news"
_COINDESK_BPI_URL = "https://api.coindesk.com/v1/bpi/currentprice.json"


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
        with httpx.Client(timeout=30.0) as client:
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
                # Search news articles (requires API key)
                if not api_key:
                    return {"results": [], "query": query, "error": "COINDESK_API_KEY not set"}

                headers = {
                    "Accept": "application/json",
                    "X-Coindesk-API-Key": api_key,
                }

                params: dict[str, Any] = {
                    "limit": min(n, 50),  # CoinDesk limit
                }

                resp = client.get(_COINDESK_ARTICLES_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                # Parse news articles
                articles = data.get("articles", [])
                results = [
                    {
                        "url": article.get("link", ""),
                        "title": article.get("headline", ""),
                        "snippet": (article.get("brief", "") or "")[:500],
                        "published_date": article.get("published_at"),
                        "author": article.get("author"),
                    }
                    for article in articles
                ]

                return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("coindesk_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        # Don't log full exception to avoid leaking API keys (HIGH #4)
        logger.error("coindesk_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
