"""FastMCP server entrypoint for Loom MCP service.

Exports the FastMCP instance with all 23 research tools registered
via dynamic tool discovery from the loom.tools namespace.
"""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from typing import Any

from mcp.server import FastMCP

from loom.config import load_config, research_config_get, research_config_set
from loom.sessions import research_session_close, research_session_list, research_session_open

# Import tool modules to register their functions
from loom.tools import cache_mgmt, deep, fetch, github, markdown, search, spider, stealth

log = logging.getLogger("loom.server")

# Dynamically import optional tool modules (LLM tools, etc.)
_optional_tools: dict[str, Any] = {}
with suppress(ImportError):
    from loom.tools import llm as llm_tools

    _optional_tools["llm"] = llm_tools

with suppress(ImportError):
    from loom.tools import enrich as enrich_tools

    _optional_tools["enrich"] = enrich_tools

with suppress(ImportError):
    from loom.tools import experts as experts_tools

    _optional_tools["experts"] = experts_tools

with suppress(ImportError):
    from loom.tools import creative as creative_tools

    _optional_tools["creative"] = creative_tools


def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from tool modules.

    Dynamically discovers and registers tool functions decorated with @mcp.tool()
    or explicitly defined in tool modules.

    Args:
        mcp: FastMCP instance to register tools with
    """
    # Core tools: fetch, spider, markdown, search, deep, github, stealth, cache
    mcp.tool()(fetch.research_fetch)
    mcp.tool()(spider.research_spider)
    mcp.tool()(markdown.research_markdown)
    mcp.tool()(search.research_search)
    mcp.tool()(deep.research_deep)
    mcp.tool()(github.research_github)
    mcp.tool()(stealth.research_camoufox)
    mcp.tool()(stealth.research_botasaurus)
    mcp.tool()(cache_mgmt.research_cache_stats)
    mcp.tool()(cache_mgmt.research_cache_clear)

    # Session tools
    mcp.tool()(research_session_open)
    mcp.tool()(research_session_list)
    mcp.tool()(research_session_close)

    # Config tools
    mcp.tool()(research_config_get)
    mcp.tool()(research_config_set)

    # GitHub enhanced tools
    mcp.tool()(github.research_github_readme)
    mcp.tool()(github.research_github_releases)

    # LLM tools (if available)
    if "llm" in _optional_tools:
        llm_mod = _optional_tools["llm"]
        if hasattr(llm_mod, "research_llm_summarize"):
            mcp.tool()(llm_mod.research_llm_summarize)
        if hasattr(llm_mod, "research_llm_extract"):
            mcp.tool()(llm_mod.research_llm_extract)
        if hasattr(llm_mod, "research_llm_classify"):
            mcp.tool()(llm_mod.research_llm_classify)
        if hasattr(llm_mod, "research_llm_translate"):
            mcp.tool()(llm_mod.research_llm_translate)
        if hasattr(llm_mod, "research_llm_query_expand"):
            mcp.tool()(llm_mod.research_llm_query_expand)
        if hasattr(llm_mod, "research_llm_answer"):
            mcp.tool()(llm_mod.research_llm_answer)
        if hasattr(llm_mod, "research_llm_embed"):
            mcp.tool()(llm_mod.research_llm_embed)
        if hasattr(llm_mod, "research_llm_chat"):
            mcp.tool()(llm_mod.research_llm_chat)

    # Enrichment tools (if available)
    if "enrich" in _optional_tools:
        enrich_mod = _optional_tools["enrich"]
        if hasattr(enrich_mod, "research_detect_language"):
            mcp.tool()(enrich_mod.research_detect_language)
        if hasattr(enrich_mod, "research_wayback"):
            mcp.tool()(enrich_mod.research_wayback)

    # Expert finder (if available)
    if "experts" in _optional_tools:
        experts_mod = _optional_tools["experts"]
        if hasattr(experts_mod, "research_find_experts"):
            mcp.tool()(experts_mod.research_find_experts)

    # Creative research tools (if available)
    if "creative" in _optional_tools:
        creative_mod = _optional_tools["creative"]
        _creative_tools = [
            "research_red_team",
            "research_multilingual",
            "research_consensus",
            "research_misinfo_check",
            "research_temporal_diff",
            "research_citation_graph",
            "research_ai_detect",
            "research_curriculum",
            "research_community_sentiment",
            "research_wiki_ghost",
        ]
        for tool_name in _creative_tools:
            if hasattr(creative_mod, tool_name):
                mcp.tool()(getattr(creative_mod, tool_name))


def create_app() -> FastMCP:
    """Create and configure the FastMCP server instance.

    Loads runtime config, sets up logging, registers all 23 tools,
    and prepares the server to listen on LOOM_HOST:LOOM_PORT.

    Returns:
        Configured FastMCP instance ready to run
    """
    # Load runtime config
    config = load_config()

    # Set up logging
    log_level = config.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create FastMCP instance
    host = os.environ.get("LOOM_HOST", "127.0.0.1")
    port = int(os.environ.get("LOOM_PORT", "8787"))

    mcp = FastMCP(
        name="loom",
        host=host,
        port=port,
    )

    # Register all tools
    _register_tools(mcp)

    log.info(
        "Loom MCP server initialized: name=%s host=%s port=%d",
        "loom",
        host,
        port,
    )

    return mcp


def main() -> None:
    """Console script entry point. Creates the app and runs the MCP server.

    Invoked by the 'loom-server' console script registered in pyproject.toml.
    """
    app = create_app()
    log.info("Starting Loom MCP server on streamable-http transport")
    app.run(transport="streamable-http")


if __name__ == "__main__":
    main()
