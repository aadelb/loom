"""FastMCP server entrypoint for Loom MCP service.

Exports the FastMCP instance with all research tools registered
via dynamic tool discovery from the loom.tools namespace.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import signal
import time
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from mcp.server import FastMCP

from loom.config import load_config, research_config_get, research_config_set
from loom.rate_limiter import rate_limited
from loom.sessions import (
    cleanup_all_sessions,
    research_session_close,
    research_session_list,
    research_session_open,
)

# Import tool modules to register their functions
from loom.tools import cache_mgmt, deep, fetch, github, markdown, search, spider, stealth
from loom.tracing import install_tracing, new_request_id

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

with suppress(ImportError):
    from loom.providers import youtube_transcripts as yt_tools

    _optional_tools["youtube"] = yt_tools

with suppress(ImportError):
    from loom.tools import vastai as vastai_tools

    _optional_tools["vastai"] = vastai_tools

with suppress(ImportError):
    from loom.tools import billing as billing_tools

    _optional_tools["billing"] = billing_tools

with suppress(ImportError):
    from loom.tools import email_report as email_tools

    _optional_tools["email"] = email_tools

with suppress(ImportError):
    from loom.tools import joplin as joplin_tools

    _optional_tools["joplin"] = joplin_tools

with suppress(ImportError):
    from loom.tools import tor as tor_tools

    _optional_tools["tor"] = tor_tools

with suppress(ImportError):
    from loom.tools import transcribe as transcribe_tools

    _optional_tools["transcribe"] = transcribe_tools

with suppress(ImportError):
    from loom.tools import document as document_tools

    _optional_tools["document"] = document_tools


_start_time = time.time()


async def research_health_check() -> dict[str, Any]:
    """Return server health status for monitoring."""
    from loom.sessions import _sessions

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": int(time.time() - _start_time),
        "active_sessions": len(_sessions),
    }


def _wrap_tool(func: Callable[..., Any], category: str | None = None) -> Callable[..., Any]:
    """Wrap tool with tracing and optional rate limiting.

    Handles both sync and async tool functions correctly.
    """
    import inspect

    is_async = inspect.iscoroutinefunction(func)

    if is_async:
        if category:
            func = rate_limited(category)(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            new_request_id()
            return await func(*args, **kwargs)

        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            new_request_id()
            return func(*args, **kwargs)

        return sync_wrapper


def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from tool modules.

    Dynamically discovers and registers tool functions decorated with @mcp.tool()
    or explicitly defined in tool modules.

    Args:
        mcp: FastMCP instance to register tools with
    """
    # Core tools: fetch, spider, markdown, search, deep, github, stealth, cache
    mcp.tool()(_wrap_tool(fetch.research_fetch, "fetch"))
    mcp.tool()(_wrap_tool(spider.research_spider, "fetch"))
    mcp.tool()(_wrap_tool(markdown.research_markdown, "fetch"))
    mcp.tool()(_wrap_tool(search.research_search, "search"))
    mcp.tool()(_wrap_tool(deep.research_deep, "deep"))
    mcp.tool()(_wrap_tool(github.research_github, "search"))
    mcp.tool()(_wrap_tool(stealth.research_camoufox, "fetch"))
    mcp.tool()(_wrap_tool(stealth.research_botasaurus, "fetch"))
    mcp.tool()(_wrap_tool(cache_mgmt.research_cache_stats))
    mcp.tool()(_wrap_tool(cache_mgmt.research_cache_clear))

    # Session tools
    mcp.tool()(_wrap_tool(research_session_open))
    mcp.tool()(_wrap_tool(research_session_list))
    mcp.tool()(_wrap_tool(research_session_close))

    # Config tools
    mcp.tool()(_wrap_tool(research_config_get))
    mcp.tool()(_wrap_tool(research_config_set))

    # Health check
    mcp.tool()(_wrap_tool(research_health_check))

    # GitHub enhanced tools
    mcp.tool()(_wrap_tool(github.research_github_readme, "fetch"))
    mcp.tool()(_wrap_tool(github.research_github_releases, "fetch"))

    # Exa find_similar (if exa provider exists)
    try:
        from loom.providers.exa import find_similar_exa

        mcp.tool()(_wrap_tool(find_similar_exa, "search"))
    except ImportError:
        pass

    # LLM tools (if available)
    if "llm" in _optional_tools:
        llm_mod = _optional_tools["llm"]
        if hasattr(llm_mod, "research_llm_summarize"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_summarize, "llm"))
        if hasattr(llm_mod, "research_llm_extract"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_extract, "llm"))
        if hasattr(llm_mod, "research_llm_classify"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_classify, "llm"))
        if hasattr(llm_mod, "research_llm_translate"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_translate, "llm"))
        if hasattr(llm_mod, "research_llm_query_expand"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_query_expand, "llm"))
        if hasattr(llm_mod, "research_llm_answer"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_answer, "llm"))
        if hasattr(llm_mod, "research_llm_embed"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_embed, "llm"))
        if hasattr(llm_mod, "research_llm_chat"):
            mcp.tool()(_wrap_tool(llm_mod.research_llm_chat, "llm"))

    # Enrichment tools (if available)
    if "enrich" in _optional_tools:
        enrich_mod = _optional_tools["enrich"]
        if hasattr(enrich_mod, "research_detect_language"):
            mcp.tool()(_wrap_tool(enrich_mod.research_detect_language))
        if hasattr(enrich_mod, "research_wayback"):
            mcp.tool()(_wrap_tool(enrich_mod.research_wayback, "fetch"))

    # Expert finder (if available)
    if "experts" in _optional_tools:
        experts_mod = _optional_tools["experts"]
        if hasattr(experts_mod, "research_find_experts"):
            mcp.tool()(_wrap_tool(experts_mod.research_find_experts, "llm"))

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
            "research_semantic_sitemap",
        ]
        for tool_name in _creative_tools:
            if hasattr(creative_mod, tool_name):
                mcp.tool()(_wrap_tool(getattr(creative_mod, tool_name), "llm"))

    # YouTube transcript tool (if yt-dlp available)
    if "youtube" in _optional_tools:
        yt_mod = _optional_tools["youtube"]
        if hasattr(yt_mod, "fetch_youtube_transcript"):
            mcp.tool()(_wrap_tool(yt_mod.fetch_youtube_transcript, "fetch"))

    # Vast.ai GPU tools (if available)
    if "vastai" in _optional_tools:
        vastai_mod = _optional_tools["vastai"]
        if hasattr(vastai_mod, "research_vastai_search"):
            mcp.tool()(_wrap_tool(vastai_mod.research_vastai_search))
        if hasattr(vastai_mod, "research_vastai_status"):
            mcp.tool()(_wrap_tool(vastai_mod.research_vastai_status))

    # Billing/usage tools (if available)
    if "billing" in _optional_tools:
        billing_mod = _optional_tools["billing"]
        if hasattr(billing_mod, "research_usage_report"):
            mcp.tool()(_wrap_tool(billing_mod.research_usage_report))
        if hasattr(billing_mod, "research_stripe_balance"):
            mcp.tool()(_wrap_tool(billing_mod.research_stripe_balance))

    # Email report tool (if available)
    if "email" in _optional_tools:
        email_mod = _optional_tools["email"]
        if hasattr(email_mod, "research_email_report"):
            mcp.tool()(_wrap_tool(email_mod.research_email_report))

    # Joplin note tools (if available)
    if "joplin" in _optional_tools:
        joplin_mod = _optional_tools["joplin"]
        if hasattr(joplin_mod, "research_save_note"):
            mcp.tool()(_wrap_tool(joplin_mod.research_save_note))
        if hasattr(joplin_mod, "research_list_notebooks"):
            mcp.tool()(_wrap_tool(joplin_mod.research_list_notebooks))

    # Tor management tools (if available)
    if "tor" in _optional_tools:
        tor_mod = _optional_tools["tor"]
        if hasattr(tor_mod, "research_tor_status"):
            mcp.tool()(_wrap_tool(tor_mod.research_tor_status))
        if hasattr(tor_mod, "research_tor_new_identity"):
            mcp.tool()(_wrap_tool(tor_mod.research_tor_new_identity))

    # Transcription tool (if whisper available)
    if "transcribe" in _optional_tools:
        transcribe_mod = _optional_tools["transcribe"]
        if hasattr(transcribe_mod, "research_transcribe"):
            mcp.tool()(_wrap_tool(transcribe_mod.research_transcribe, "fetch"))

    # Document conversion tool (if pandoc available)
    if "document" in _optional_tools:
        document_mod = _optional_tools["document"]
        if hasattr(document_mod, "research_convert_document"):
            mcp.tool()(_wrap_tool(document_mod.research_convert_document, "fetch"))


def create_app() -> FastMCP:
    """Create and configure the FastMCP server instance.

    Loads runtime config, sets up logging, registers all 23 tools,
    and prepares the server to listen on LOOM_HOST:LOOM_PORT.

    Returns:
        Configured FastMCP instance ready to run
    """
    # Load runtime config
    config = load_config()

    # Set up logging with request_id support
    log_level = config.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s",
    )
    install_tracing()

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

    # Startup cache cleanup: Remove cache entries older than TTL (Issue #188)
    try:
        from loom.cache import get_cache

        cache = get_cache()
        config_ttl = config.get("CACHE_TTL_DAYS", 30)
        removed = cache.clear_older_than(days=config_ttl)
        if removed:
            log.info("startup_cache_cleanup removed=%d files", removed)
    except Exception as exc:
        log.warning("startup_cache_cleanup_failed: %s", exc)

    log.info(
        "Loom MCP server initialized: name=%s host=%s port=%d",
        "loom",
        host,
        port,
    )

    return mcp


async def _shutdown() -> None:
    """Graceful shutdown: close all browser sessions, HTTP clients, and providers."""
    log.info("shutdown_signal_received")
    try:
        result = await cleanup_all_sessions()
        log.info(
            "shutdown_sessions_closed=%d errors=%d",
            len(result.get("closed", [])),
            len(result.get("errors", [])),
        )
    except Exception as exc:
        log.error("shutdown_sessions_error: %s", exc)

    # Close httpx connection pool
    try:
        from loom.tools.fetch import _http_client

        if _http_client is not None:
            _http_client.close()
            log.info("shutdown_http_client_closed")
    except Exception as exc:
        log.error("shutdown_http_client_error: %s", exc)

    # Close LLM provider clients
    try:
        if "llm" in _optional_tools:
            from loom.tools.llm import close_all_providers

            await close_all_providers()
            log.info("shutdown_providers_closed")
    except Exception as exc:
        log.error("shutdown_providers_error: %s", exc)

    log.info("shutdown_complete")


_background_tasks: set[asyncio.Task[None]] = set()


def _handle_signal(sig: int, _frame: Any) -> None:
    """Signal handler that runs the async shutdown in a new event loop."""
    log.info("received_signal=%s", signal.Signals(sig).name)
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_shutdown())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        asyncio.run(_shutdown())


def main() -> None:
    """Console script entry point. Creates the app and runs the MCP server.

    Invoked by the 'loom-server' console script registered in pyproject.toml.
    """
    app = create_app()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log.info("Starting Loom MCP server on streamable-http transport")
    app.run(transport="streamable-http")


if __name__ == "__main__":
    main()
