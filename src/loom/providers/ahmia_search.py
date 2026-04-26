"""Ahmia.fi search provider — Clearnet onion directory with safety filtering.

Ahmia is a free, clearnet-accessible search engine for .onion sites that actively
filters child abuse material and other illegal content. Useful for discovering
legitimate onion services without requiring Tor.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.ahmia_search")

_AHMIA_SEARCH_URL = "https://ahmia.fi/search/"

# Module-level client for connection pooling
_ahmia_client: httpx.Client | None = None


def _get_ahmia_client() -> httpx.Client:
    """Get or create Ahmia search client with connection pooling."""
    global _ahmia_client
    if _ahmia_client is None:
        _ahmia_client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
        )
    return _ahmia_client


def search_ahmia(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search .onion sites via Ahmia.fi.

    Ahmia is a free, clearnet-accessible search engine for discovering .onion sites.
    It actively filters child abuse material and other illegal content. No API key required.

    Args:
        query: search query (will search for .onion sites)
        n: max number of results (Ahmia returns roughly n results per page)
        **kwargs: ignored (accepted for interface compatibility)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
        Each result has: url, title, snippet.
    """
    params = {"q": query}

    try:
        client = _get_ahmia_client()
        resp = client.get(_AHMIA_SEARCH_URL, params=params)
        resp.raise_for_status()

        # Parse HTML response
        html_content = resp.text
        results = _parse_ahmia_results(html_content, n)

        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("ahmia_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        logger.error("ahmia_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}


def _parse_ahmia_results(html: str, n: int) -> list[dict[str, str]]:
    """Parse Ahmia search results from HTML.

    Ahmia uses a simple HTML structure with result divs. This parser attempts
    to extract .onion URLs, titles, and snippets using basic HTML patterns.

    Args:
        html: HTML response body from Ahmia
        n: max number of results to extract

    Returns:
        List of normalized result dicts with url, title, snippet.
    """
    results = []

    try:
        # Try using selectolax first if available (faster)
        try:
            from selectolax.parser import HTMLParser

            parser = HTMLParser(html)
            # Ahmia uses <h2> for titles and <p> for descriptions within result divs
            result_divs = parser.css("div.result")

            for div in result_divs[:n]:
                title_elem = div.css_first("h2")
                link_elem = div.css_first("a")
                desc_elem = div.css_first("p")

                if link_elem:
                    url = link_elem.attributes.get("href", "")
                    title = title_elem.text() if title_elem else ""
                    snippet = desc_elem.text() if desc_elem else ""

                    if url:
                        results.append(
                            {
                                "url": url,
                                "title": (title or "")[:200],
                                "snippet": (snippet or "")[:500],
                            }
                        )

        except ImportError:
            # Fallback: simple regex-based parsing if selectolax not available
            import re

            # Pattern to match result containers
            pattern = r'<h2>\s*<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>\s*</h2>.*?<p>([^<]+)</p>'
            matches = re.finditer(pattern, html, re.DOTALL | re.IGNORECASE)

            for match in matches:
                if len(results) >= n:
                    break
                url, title, snippet = match.groups()
                results.append(
                    {
                        "url": url.strip(),
                        "title": title.strip()[:200],
                        "snippet": snippet.strip()[:500],
                    }
                )

    except Exception as exc:
        logger.warning("ahmia_parse_error: %s", type(exc).__name__)
        # Return empty results on parse failure rather than partial/broken data

    return results
