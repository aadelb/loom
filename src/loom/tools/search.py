"""research_search — Unified search across multiple providers (Exa, Tavily, Firecrawl, Brave)."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import TextContent

logger = logging.getLogger("loom.tools.search")


def research_search(
    query: str,
    provider: str = "exa",
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
        provider: 'exa' | 'tavily' | 'firecrawl' | 'brave'
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
    # Import here to avoid circular imports
    from loom.config import get_config

    get_config()
    provider_config = provider_config or {}

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
