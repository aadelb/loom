"""Registration module for core tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.core")


def register_core_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 17 core tools including tool discovery."""
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
    try:
        from loom.tools.tool_discovery import research_discover
        mcp.tool()(wrap_tool(research_discover))
        record_success("core", "research_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_discovery: %s", e)
        record_failure("core", "tool_discovery", str(e))
    log.info("registered core tools count=17")

    # CloakBrowser stealth (Tier 3.5 — passes all bot detection)
    try:
        from loom.tools.cloak_backend import research_cloak_fetch, research_cloak_extract, research_cloak_session
        mcp.tool()(wrap_tool(research_cloak_fetch))
        mcp.tool()(wrap_tool(research_cloak_extract))
        mcp.tool()(wrap_tool(research_cloak_session))
    except (ImportError, AttributeError) as e:
        log.debug("skip cloak_backend: %s", e)

    # Webhook management tools
    try:
        from loom.tools.webhooks import (
            research_webhook_register,
            research_webhook_list,
            research_webhook_unregister,
            research_webhook_test,
        )
        mcp.tool()(wrap_tool(research_webhook_register))
        record_success("core", "research_webhook_register")
        mcp.tool()(wrap_tool(research_webhook_list))
        record_success("core", "research_webhook_list")
        mcp.tool()(wrap_tool(research_webhook_unregister))
        record_success("core", "research_webhook_unregister")
        mcp.tool()(wrap_tool(research_webhook_test))
        record_success("core", "research_webhook_test")
    except (ImportError, AttributeError) as e:
        log.debug("skip webhooks: %s", e)
        record_failure("core", "webhooks", str(e))

    # MCP authentication tools
    try:
        from loom.tools.mcp_auth import (
            research_auth_create_token,
            research_auth_validate,
            research_auth_revoke,
        )
        mcp.tool()(wrap_tool(research_auth_create_token))
        record_success("core", "research_auth_create_token")
        mcp.tool()(wrap_tool(research_auth_validate))
        record_success("core", "research_auth_validate")
        mcp.tool()(wrap_tool(research_auth_revoke))
        record_success("core", "research_auth_revoke")
    except (ImportError, AttributeError) as e:
        log.debug("skip mcp_auth: %s", e)
        record_failure("core", "mcp_auth", str(e))

    # CPU pool and circuit breaker status tools
    try:
        from loom.server import research_cpu_pool_status
        mcp.tool()(wrap_tool(research_cpu_pool_status))
        record_success("core", "research_cpu_pool_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip cpu_pool_status: %s", e)
        record_failure("core", "cpu_pool_status", str(e))

    try:
        from loom.tools.llm import research_circuit_status
        mcp.tool()(wrap_tool(research_circuit_status))
        record_success("core", "research_circuit_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip circuit_status: %s", e)
        record_failure("core", "circuit_status", str(e))

    # Analytics dashboard tool
    try:
        from loom.analytics import research_analytics_dashboard
        mcp.tool()(wrap_tool(research_analytics_dashboard))
        record_success("core", "research_analytics_dashboard")
    except (ImportError, AttributeError) as e:
        log.debug("skip analytics_dashboard: %s", e)
        record_failure("core", "analytics_dashboard", str(e))
