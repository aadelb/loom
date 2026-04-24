"""Wikipedia search provider (free, no API key, via MediaWiki REST API)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.wikipedia_search")


def search_wikipedia(
    query: str,
    n: int = 5,
    language: str = "en",
    **kwargs: Any,
) -> dict[str, Any]:
    """Search Wikipedia for articles (free, no API key).

    Uses the MediaWiki opensearch API for discovery, then fetches
    summaries via the REST API.

    Args:
        query: search query
        n: max number of results (capped at 10)
        language: Wikipedia language code (default "en")
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    n = min(n, 10)
    base = f"https://{language}.wikipedia.org"

    try:
        with httpx.Client(
            timeout=15.0,
            headers={"User-Agent": "Loom/0.1 (research MCP server)"},
        ) as client:
            search_resp = client.get(
                f"{base}/w/api.php",
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": n,
                    "format": "json",
                },
            )
            search_resp.raise_for_status()
            data = search_resp.json()

            titles: list[str] = data[1] if len(data) > 1 else []
            urls: list[str] = data[3] if len(data) > 3 else []

            results: list[dict[str, Any]] = []
            for title, url in zip(titles, urls, strict=False):
                summary_resp = client.get(
                    f"{base}/api/rest_v1/page/summary/{title}",
                )
                if summary_resp.status_code == 200:
                    sdata = summary_resp.json()
                    results.append(
                        {
                            "url": url,
                            "title": sdata.get("title", title),
                            "snippet": (sdata.get("extract", "") or "")[:500],
                            "thumbnail": sdata.get("thumbnail", {}).get("source"),
                            "description": sdata.get("description"),
                        }
                    )
                else:
                    results.append(
                        {
                            "url": url,
                            "title": title,
                            "snippet": "",
                        }
                    )

        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("wikipedia_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        logger.exception("wikipedia_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "error": str(exc)}
