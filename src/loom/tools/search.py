"""research_search — Unified search across multiple providers (Exa, Tavily, Firecrawl, Brave)."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import TextContent

logger = logging.getLogger("loom.tools.search")


def research_search(
    query: str,
    provider: str | None = None,
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    language: str | None = None,
    provider_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search the web using the configured provider.

    Args:
        query: search query
        provider: exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia,
            hackernews, or reddit
        n: max number of results (1-50)
        include_domains: list of domains to include
        exclude_domains: list of domains to exclude
        start_date: ISO yyyy-mm-dd start date
        end_date: ISO yyyy-mm-dd end date
        language: language hint (ISO 639-1)
        provider_config: provider-specific kwargs

    Returns:
        Dict with keys: provider, query, results (list of dicts), error (if any)
    """
    from loom.config import get_config
    from loom.validators import filter_provider_config

    config = get_config()
    if provider is None:
        provider = config.get("DEFAULT_SEARCH_PROVIDER", "exa")
    provider_config = filter_provider_config(provider, provider_config)

    # Validate and normalize
    n = max(1, min(n, 50))
    if include_domains is not None:
        include_domains = [d.lower().strip() for d in include_domains]
    if exclude_domains is not None:
        exclude_domains = [d.lower().strip() for d in exclude_domains]

    logger.info(
        "search query=%s provider=%s n=%d",
        query[:50],
        provider,
        n,
    )

    try:
        if provider == "exa":
            from loom.providers.exa import search_exa

            result = search_exa(
                query=query,
                n=n,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_date=start_date,
                end_date=end_date,
                **provider_config,
            )
            result["provider"] = "exa"
            return result  # type: ignore[no-any-return]

        elif provider == "tavily":
            from loom.providers.tavily import search_tavily

            result = search_tavily(
                query=query,
                n=n,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_date=start_date,
                end_date=end_date,
                **provider_config,
            )
            result["provider"] = "tavily"
            return result  # type: ignore[no-any-return]

        elif provider == "firecrawl":
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl(
                query=query,
                n=n,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                **provider_config,
            )
            result["provider"] = "firecrawl"
            return result  # type: ignore[no-any-return]

        elif provider == "brave":
            from loom.providers.brave import search_brave

            result = search_brave(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "brave"
            return result  # type: ignore[no-any-return]

        elif provider == "ddgs":
            from loom.providers.ddgs import search_ddgs

            result = search_ddgs(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "ddgs"
            return result  # type: ignore[no-any-return]

        elif provider == "arxiv":
            from loom.providers.arxiv_search import search_arxiv

            result = search_arxiv(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "arxiv"
            return result  # type: ignore[no-any-return]

        elif provider == "wikipedia":
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "wikipedia"
            return result  # type: ignore[no-any-return]

        elif provider == "hackernews":
            from loom.providers.hn_reddit import search_hackernews

            result = search_hackernews(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "hackernews"
            return result  # type: ignore[no-any-return]

        elif provider == "reddit":
            from loom.providers.hn_reddit import search_reddit

            result = search_reddit(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "reddit"
            return result  # type: ignore[no-any-return]

        elif provider == "newsapi":
            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "newsapi"
            return result  # type: ignore[no-any-return]

        elif provider == "crypto":
            from loom.providers.coinmarketcap import search_crypto

            result = search_crypto(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "crypto"
            return result  # type: ignore[no-any-return]

        elif provider == "coindesk":
            from loom.providers.coindesk_search import search_coindesk_news

            result = search_coindesk_news(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "coindesk"
            return result  # type: ignore[no-any-return]

        elif provider == "binance":
            from loom.providers.binance_data import search_binance

            result = search_binance(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "binance"
            return result  # type: ignore[no-any-return]

        elif provider == "investing":
            from loom.providers.investing_data import search_investing

            result = search_investing(
                query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "investing"
            return result  # type: ignore[no-any-return]

        else:
            logger.error("unknown_search_provider provider=%s", provider)
            return {
                "provider": provider,
                "query": query,
                "results": [],
                "error": f"Unknown provider: {provider}",
            }

    except Exception as exc:
        logger.exception("search_failed provider=%s", provider)
        return {
            "provider": provider,
            "query": query,
            "results": [],
            "error": str(exc),
        }


def tool_search(
    query: str,
    provider: str = "exa",
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[TextContent]:
    """MCP wrapper for research_search."""
    result = research_search(
        query=query,
        provider=provider,
        n=n,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        start_date=start_date,
        end_date=end_date,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
