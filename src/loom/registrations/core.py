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
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.cache_mgmt import research_cache_stats, research_cache_clear
        mcp.tool()(wrap_tool(research_cache_stats))
        record_success("core", "research_cache_stats")
        mcp.tool()(wrap_tool(research_cache_clear))
        record_success("core", "research_cache_clear")
    except (ImportError, AttributeError) as e:
        log.debug("skip cache_mgmt: %s", e)
        record_failure("core", "cache_mgmt", str(e))
    try:
        from loom.tools.deep import research_deep
        mcp.tool()(wrap_tool(research_deep))
        record_success("core", "research_deep")
    except (ImportError, AttributeError) as e:
        log.debug("skip deep: %s", e)
        record_failure("core", "deep", str(e))
    try:
        from loom.tools.deep_url_analysis import research_deep_url_analysis
        mcp.tool()(wrap_tool(research_deep_url_analysis))
        record_success("core", "research_deep_url_analysis")
    except (ImportError, AttributeError) as e:
        log.debug("skip deep_url_analysis: %s", e)
        record_failure("core", "deep_url_analysis", str(e))
    try:
        from loom.tools.fetch import research_fetch
        mcp.tool()(wrap_tool(research_fetch))
        record_success("core", "research_fetch")
    except (ImportError, AttributeError) as e:
        log.debug("skip fetch: %s", e)
        record_failure("core", "fetch", str(e))
    try:
        from loom.tools.github import research_github, research_github_readme, research_github_releases
        mcp.tool()(wrap_tool(research_github))
        record_success("core", "research_github")
        mcp.tool()(wrap_tool(research_github_readme))
        record_success("core", "research_github_readme")
        mcp.tool()(wrap_tool(research_github_releases))
        record_success("core", "research_github_releases")
    except (ImportError, AttributeError) as e:
        log.debug("skip github: %s", e)
        record_failure("core", "github", str(e))
    try:
        from loom.tools.help_system import research_help, research_tools_list
        mcp.tool()(wrap_tool(research_help))
        record_success("core", "research_help")
        mcp.tool()(wrap_tool(research_tools_list))
        record_success("core", "research_tools_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip help_system: %s", e)
        record_failure("core", "help_system", str(e))
    try:
        from loom.tools.markdown import research_markdown
        mcp.tool()(wrap_tool(research_markdown))
        record_success("core", "research_markdown")
    except (ImportError, AttributeError) as e:
        log.debug("skip markdown: %s", e)
        record_failure("core", "markdown", str(e))
    try:
        from loom.tools.multi_search import research_multi_search
        mcp.tool()(wrap_tool(research_multi_search))
        record_success("core", "research_multi_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip multi_search: %s", e)
        record_failure("core", "multi_search", str(e))
    try:
        from loom.tools.search import research_search
        mcp.tool()(wrap_tool(research_search))
        record_success("core", "research_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip search: %s", e)
        record_failure("core", "search", str(e))
    try:
        from loom.tools.spider import research_spider
        mcp.tool()(wrap_tool(research_spider))
        record_success("core", "research_spider")
    except (ImportError, AttributeError) as e:
        log.debug("skip spider: %s", e)
        record_failure("core", "spider", str(e))
    try:
        from loom.tools.stealth import research_camoufox, research_botasaurus
        mcp.tool()(wrap_tool(research_camoufox))
        record_success("core", "research_camoufox")
        mcp.tool()(wrap_tool(research_botasaurus))
        record_success("core", "research_botasaurus")
    except (ImportError, AttributeError) as e:
        log.debug("skip stealth: %s", e)
        record_failure("core", "stealth", str(e))
    log.info("registered core tools count=16")
