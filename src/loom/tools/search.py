"""research_search — Unified search across multiple providers (Exa, Tavily, Firecrawl, Brave)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.types import TextContent

from loom.retry import with_retry
from loom.tools.source_reputation import filter_by_reputation

logger = logging.getLogger("loom.tools.search")

# Free search providers (no API key required or unlimited free tier)
_FREE_PROVIDERS = frozenset({
    "ddgs",           # DuckDuckGo (free)
    "wikipedia",      # Wikipedia (free)
    "arxiv",          # arXiv academic search (free)
    "hackernews",     # HackerNews via Algolia (free)
    "reddit",         # Reddit JSON API (free)
    "ahmia",          # Ahmia Tor search (free)
    "darksearch",     # DarkSearch darkweb (free)
})


def _apply_reputation_filter(result: dict[str, Any]) -> dict[str, Any]:
    """Apply reputation filtering to search results."""
    if "results" in result and isinstance(result["results"], list):
        result["results"] = filter_by_reputation(result["results"])
    return result


@with_retry(max_attempts=3, backoff_base=1.0)
async def research_search(
    query: str,
    provider: str | None = None,
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    language: str | None = None,
    provider_config: dict[str, Any] | None = None,
    free_only: bool = False,
) -> dict[str, Any]:
    """Search the web using the configured provider.

    Args:
        query: search query
        provider: exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia,
            hackernews, reddit, ummro, onionsearch, torcrawl, darkweb_cti, robin_osint
        n: max number of results (1-50)
        include_domains: list of domains to include
        exclude_domains: list of domains to exclude
        start_date: ISO yyyy-mm-dd start date
        end_date: ISO yyyy-mm-dd end date
        language: language hint (ISO 639-1)
        provider_config: provider-specific kwargs
        free_only: if True, only use free providers (DDG, Wikipedia, ArXiv, HN, Reddit, etc.)

    Returns:
        Dict with keys: provider, query, results (list of dicts), error (if any),
        cost_estimate_usd, free_tier (bool)
    """
    from loom.config import get_config
    from loom.validators import filter_provider_config

    config = get_config()
    if provider is None:
        provider = config.get("DEFAULT_SEARCH_PROVIDER", "exa")

    # If free_only is True, validate that provider is in free list
    if free_only and provider not in _FREE_PROVIDERS:
        logger.warning("free_only=True but provider=%s is not free; switching to ddgs", provider)
        provider = "ddgs"

    provider_config = filter_provider_config(provider, provider_config)

    # Validate and normalize
    n = max(1, min(n, 50))
    if include_domains is not None:
        include_domains = [d.lower().strip() for d in include_domains]
    if exclude_domains is not None:
        exclude_domains = [d.lower().strip() for d in exclude_domains]

    is_free = provider in _FREE_PROVIDERS

    logger.info(
        "search query=%s provider=%s n=%d free_only=%s",
        query[:50],
        provider,
        n,
        free_only,
    )

    try:
        if provider == "exa":
            from loom.providers.exa import search_exa

            result = await asyncio.to_thread(
                search_exa, query=query,
                n=n,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_date=start_date,
                end_date=end_date,
                **provider_config,
            )
            result["provider"] = "exa"
            result["cost_estimate_usd"] = 0.05  # Estimated per-call cost
            result["free_tier"] = False
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "tavily":
            from loom.providers.tavily import search_tavily

            result = await asyncio.to_thread(
                search_tavily, query=query,
                n=n,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_date=start_date,
                end_date=end_date,
                **provider_config,
            )
            result["provider"] = "tavily"
            result["cost_estimate_usd"] = 0.03  # Estimated per-call cost
            result["free_tier"] = False
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "firecrawl":
            from loom.providers.firecrawl import search_firecrawl

            result = await asyncio.to_thread(
                search_firecrawl, query=query,
                n=n,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                **provider_config,
            )
            result["provider"] = "firecrawl"
            result["cost_estimate_usd"] = 0.02  # Estimated per-call cost
            result["free_tier"] = False
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "brave":
            from loom.providers.brave import search_brave

            result = await asyncio.to_thread(
                search_brave, query=query, n=n, **provider_config
            )
            result["provider"] = "brave"
            result["cost_estimate_usd"] = 0.01  # Brave free tier is cheap
            result["free_tier"] = False
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "ddgs":
            from loom.providers.ddgs import search_ddgs

            result = await asyncio.to_thread(
                search_ddgs, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "ddgs"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "arxiv":
            from loom.providers.arxiv_search import search_arxiv

            result = await asyncio.to_thread(
                search_arxiv, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "arxiv"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "wikipedia":
            from loom.providers.wikipedia_search import search_wikipedia

            result = await asyncio.to_thread(
                search_wikipedia, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "wikipedia"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "hackernews":
            from loom.providers.hn_reddit import search_hackernews

            result = await asyncio.to_thread(
                search_hackernews, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "hackernews"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "reddit":
            from loom.providers.hn_reddit import search_reddit

            result = await asyncio.to_thread(
                search_reddit, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "reddit"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "newsapi":
            from loom.providers.newsapi_search import search_newsapi

            result = await asyncio.to_thread(
                search_newsapi, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "newsapi"
            result["cost_estimate_usd"] = 0.0  # NewsAPI has free tier
            result["free_tier"] = False
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "crypto":
            from loom.providers.coinmarketcap import search_crypto

            result = await asyncio.to_thread(
                search_crypto, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "crypto"
            result["cost_estimate_usd"] = 0.0  # CoinMarketCap free data
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "coindesk":
            from loom.providers.coindesk_search import search_coindesk_news

            result = await asyncio.to_thread(
                search_coindesk_news, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "coindesk"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "binance":
            from loom.providers.binance_data import search_binance

            result = await asyncio.to_thread(
                search_binance, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "binance"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "investing":
            from loom.providers.investing_data import search_investing

            result = await asyncio.to_thread(
                search_investing, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "investing"
            result["cost_estimate_usd"] = 0.01
            result["free_tier"] = False
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "ahmia":
            from loom.providers.ahmia_search import search_ahmia

            result = await asyncio.to_thread(
                search_ahmia, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "ahmia"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "darksearch":
            from loom.providers.darksearch_search import search_darksearch

            result = await asyncio.to_thread(
                search_darksearch, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "darksearch"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "ummro":
            from loom.providers.ummro_rag import search_ummro_rag

            result = await asyncio.to_thread(
                search_ummro_rag, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "ummro"
            result["cost_estimate_usd"] = 0.0
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "onionsearch":
            from loom.providers.onionsearch import search_onionsearch

            result = await asyncio.to_thread(
                search_onionsearch, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "onionsearch"
            result["cost_estimate_usd"] = 0.0  # Free
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "torcrawl":
            from loom.providers.torcrawl import crawl_onion

            result = await asyncio.to_thread(
                crawl_onion,
                url=query,
                **provider_config,
            )
            result["provider"] = "torcrawl"
            result["cost_estimate_usd"] = 0.0
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "darkweb_cti":
            from loom.providers.darkweb_cti import search_darkweb_cti

            result = await asyncio.to_thread(
                search_darkweb_cti, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "darkweb_cti"
            result["cost_estimate_usd"] = 0.0
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        elif provider == "robin_osint":
            from loom.providers.robin_osint import search_robin_osint

            result = await asyncio.to_thread(
                search_robin_osint, query=query,
                n=n,
                **provider_config,
            )
            result["provider"] = "robin_osint"
            result["cost_estimate_usd"] = 0.0
            result["free_tier"] = True
            return _apply_reputation_filter(result)  # type: ignore[no-any-return]

        else:
            logger.error("unknown_search_provider provider=%s", provider)
            return {
                "provider": provider,
                "query": query,
                "results": [],
                "error": f"Unknown provider: {provider}",
                "cost_estimate_usd": 0.0,
                "free_tier": False,
            }

    except Exception as exc:
        logger.exception("search_failed provider=%s", provider)
        return {
            "provider": provider,
            "query": query,
            "results": [],
            "error": str(exc),
            "cost_estimate_usd": 0.0,
            "free_tier": is_free,
        }


async def tool_search(
    query: str,
    provider: str = "exa",
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[TextContent]:
    """MCP wrapper for research_search."""
    result = await research_search(
        query=query,
        provider=provider,
        n=n,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        start_date=start_date,
        end_date=end_date,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
