"""Registration module for core tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.core")


def register_core_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 16 core tools."""
    try:
        from loom.tools.cache_mgmt import research_cache_stats, research_cache_clear
        mcp.tool()(wrap_tool(research_cache_stats))
        mcp.tool()(wrap_tool(research_cache_clear))
    except (ImportError, AttributeError) as e:
        log.debug("skip cache_mgmt: %s", e)
    try:
        from loom.tools.deep import research_deep
        mcp.tool()(wrap_tool(research_deep))
    except (ImportError, AttributeError) as e:
        log.debug("skip deep: %s", e)
    try:
        from loom.tools.deep_url_analysis import research_deep_url_analysis
        mcp.tool()(wrap_tool(research_deep_url_analysis))
    except (ImportError, AttributeError) as e:
        log.debug("skip deep_url_analysis: %s", e)
    try:
        from loom.tools.fetch import research_fetch
        mcp.tool()(wrap_tool(research_fetch))
    except (ImportError, AttributeError) as e:
        log.debug("skip fetch: %s", e)
    try:
        from loom.tools.github import research_github, research_github_readme, research_github_releases
        mcp.tool()(wrap_tool(research_github))
        mcp.tool()(wrap_tool(research_github_readme))
        mcp.tool()(wrap_tool(research_github_releases))
    except (ImportError, AttributeError) as e:
        log.debug("skip github: %s", e)
    try:
        from loom.tools.help_system import research_help, research_tools_list
        mcp.tool()(wrap_tool(research_help))
        mcp.tool()(wrap_tool(research_tools_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip help_system: %s", e)
    try:
        from loom.tools.markdown import research_markdown
        mcp.tool()(wrap_tool(research_markdown))
    except (ImportError, AttributeError) as e:
        log.debug("skip markdown: %s", e)
    try:
        from loom.tools.multi_search import research_multi_search
        mcp.tool()(wrap_tool(research_multi_search))
    except (ImportError, AttributeError) as e:
        log.debug("skip multi_search: %s", e)
    try:
        from loom.tools.search import research_search
        mcp.tool()(wrap_tool(research_search))
    except (ImportError, AttributeError) as e:
        log.debug("skip search: %s", e)
    try:
        from loom.tools.spider import research_spider
        mcp.tool()(wrap_tool(research_spider))
    except (ImportError, AttributeError) as e:
        log.debug("skip spider: %s", e)
    try:
        from loom.tools.stealth import research_camoufox, research_botasaurus
        mcp.tool()(wrap_tool(research_camoufox))
        mcp.tool()(wrap_tool(research_botasaurus))
    except (ImportError, AttributeError) as e:
        log.debug("skip stealth: %s", e)
    log.info("registered core tools count=16")
