"""Core research tools — fetch, spider, search, markdown, deep, etc.

These are the essential foundation tools for research, scraping, and data retrieval.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.core")


def register_core_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 20 core research tools.

    These are the fundamental tools for research, caching, sessions, and help.
    """
    from loom.tools import (
        fetch,
        spider,
        markdown,
        search,
        deep,
        github,
        cache_mgmt,
        stealth,
        help_system,
        health_dashboard,
        startup_validator,
        cyberscraper,
    )

    # Core fetching and search
    mcp.tool()(wrap_tool(fetch.research_fetch, "fetch"))
    mcp.tool()(wrap_tool(spider.research_spider, "fetch"))
    mcp.tool()(wrap_tool(markdown.research_markdown, "fetch"))
    mcp.tool()(wrap_tool(search.research_search, "search"))
    mcp.tool()(wrap_tool(deep.research_deep, "deep"))
    mcp.tool()(wrap_tool(github.research_github, "search"))
    mcp.tool()(wrap_tool(stealth.research_camoufox, "fetch"))
    mcp.tool()(wrap_tool(stealth.research_botasaurus, "fetch"))
    mcp.tool()(wrap_tool(cyberscraper.research_smart_extract, "fetch"))
    mcp.tool()(wrap_tool(cyberscraper.research_paginate_scrape, "fetch"))
    mcp.tool()(wrap_tool(cyberscraper.research_stealth_browser, "fetch"))

    # Cache management
    mcp.tool()(wrap_tool(cache_mgmt.research_cache_stats))
    mcp.tool()(wrap_tool(cache_mgmt.research_cache_clear))

    # Help and status
    mcp.tool()(wrap_tool(help_system.research_help))
    mcp.tool()(wrap_tool(health_dashboard.research_dashboard_html))
    mcp.tool()(wrap_tool(startup_validator.research_validate_startup))

    log.info("registered core tools count=20")
