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
from loom.tools import (
    cache_mgmt,
    deception_detect,
    deep,
    domain_intel,
    fetch,
    github,
    markdown,
    pdf_extract,
    rss_monitor,
    search,
    social_intel,
    spider,
    stealth,
    stylometry,
)
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


with suppress(ImportError):
    from loom.tools import metrics as metrics_tools

    _optional_tools["metrics"] = metrics_tools

with suppress(ImportError):
    from loom.tools import slack as slack_tools

    _optional_tools["slack"] = slack_tools

with suppress(ImportError):
    from loom.tools import gcp as gcp_tools

    _optional_tools["gcp"] = gcp_tools

with suppress(ImportError):
    from loom.tools import vercel as vercel_tools

    _optional_tools["vercel"] = vercel_tools

with suppress(ImportError):
    from loom.tools import cipher_mirror as cipher_mirror_tools

    _optional_tools["cipher_mirror"] = cipher_mirror_tools

with suppress(ImportError):
    from loom.tools import forum_cortex as forum_cortex_tools

    _optional_tools["forum_cortex"] = forum_cortex_tools

with suppress(ImportError):
    from loom.tools import onion_spectra as onion_spectra_tools

    _optional_tools["onion_spectra"] = onion_spectra_tools

with suppress(ImportError):
    from loom.tools import ghost_weave as ghost_weave_tools

    _optional_tools["ghost_weave"] = ghost_weave_tools

with suppress(ImportError):
    from loom.tools import dead_drop_scanner as dead_drop_scanner_tools

    _optional_tools["dead_drop_scanner"] = dead_drop_scanner_tools

with suppress(ImportError):
    from loom.tools import persona_profile as persona_profile_tools

    _optional_tools["persona_profile"] = persona_profile_tools

with suppress(ImportError):
    from loom.tools import radicalization_detect as radicalization_detect_tools

    _optional_tools["radicalization_detect"] = radicalization_detect_tools
with suppress(ImportError):
    from loom.tools import sentiment_deep as sentiment_deep_tools

    _optional_tools["sentiment_deep"] = sentiment_deep_tools

with suppress(ImportError):
    from loom.tools import network_persona as network_persona_tools

    _optional_tools["network_persona"] = network_persona_tools

with suppress(ImportError):
    from loom.tools import text_analyze as text_analyze_tools

    _optional_tools["text_analyze"] = text_analyze_tools

with suppress(ImportError):
    from loom.tools import screenshot as screenshot_tools

    _optional_tools["screenshot"] = screenshot_tools

with suppress(ImportError):
    from loom.tools import cert_analyzer as cert_analyzer_tools

    _optional_tools["cert_analyzer"] = cert_analyzer_tools

with suppress(ImportError):
    from loom.tools import security_headers as security_headers_tools

    _optional_tools["security_headers"] = security_headers_tools

with suppress(ImportError):
    from loom.tools import breach_check as breach_check_tools

    _optional_tools["breach_check"] = breach_check_tools

with suppress(ImportError):
    from loom.tools import ip_intel as ip_intel_tools

    _optional_tools["ip_intel"] = ip_intel_tools

with suppress(ImportError):
    from loom.tools import cve_lookup as cve_lookup_tools

    _optional_tools["cve_lookup"] = cve_lookup_tools

with suppress(ImportError):
    from loom.tools import urlhaus_lookup as urlhaus_lookup_tools

    _optional_tools["urlhaus_lookup"] = urlhaus_lookup_tools




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
        if category:
            from loom.rate_limiter import sync_rate_limited
            func = sync_rate_limited(category)(func)

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

    # Psychology & behavioral analysis tools
    mcp.tool()(_wrap_tool(stylometry.research_stylometry))
    mcp.tool()(_wrap_tool(deception_detect.research_deception_detect))

    # Domain intelligence tools
    mcp.tool()(_wrap_tool(domain_intel.research_whois, "fetch"))
    mcp.tool()(_wrap_tool(domain_intel.research_dns_lookup, "fetch"))
    mcp.tool()(_wrap_tool(domain_intel.research_nmap_scan, "fetch"))

    # PDF extraction tools
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))

    # RSS feed tools
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_fetch, "fetch"))
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_search, "search"))

    # Social intelligence tools
    mcp.tool()(_wrap_tool(social_intel.research_social_search))
    mcp.tool()(_wrap_tool(social_intel.research_social_profile, "fetch"))

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

    # Metrics collection tool (if available)
    if "metrics" in _optional_tools:
        metrics_mod = _optional_tools["metrics"]
        if hasattr(metrics_mod, "research_metrics"):
            mcp.tool()(_wrap_tool(metrics_mod.research_metrics))

    # Slack notification tool (if available)
    if "slack" in _optional_tools:
        slack_mod = _optional_tools["slack"]
        if hasattr(slack_mod, "research_slack_notify"):
            mcp.tool()(_wrap_tool(slack_mod.research_slack_notify))

    # Google Cloud tools (if available)
    if "gcp" in _optional_tools:
        gcp_mod = _optional_tools["gcp"]
        if hasattr(gcp_mod, "research_image_analyze"):
            mcp.tool()(_wrap_tool(gcp_mod.research_image_analyze))
        if hasattr(gcp_mod, "research_text_to_speech"):
            mcp.tool()(_wrap_tool(gcp_mod.research_text_to_speech))
        if hasattr(gcp_mod, "research_tts_voices"):
            mcp.tool()(_wrap_tool(gcp_mod.research_tts_voices))

    # Vercel deployment tool (if available)
    if "vercel" in _optional_tools:
        vercel_mod = _optional_tools["vercel"]
        if hasattr(vercel_mod, "research_vercel_status"):
            mcp.tool()(_wrap_tool(vercel_mod.research_vercel_status))

    # Darkweb tools (if available)
    if "cipher_mirror" in _optional_tools:
        cipher_mirror_mod = _optional_tools["cipher_mirror"]
        if hasattr(cipher_mirror_mod, "research_cipher_mirror"):
            mcp.tool()(_wrap_tool(cipher_mirror_mod.research_cipher_mirror, "fetch"))

    if "forum_cortex" in _optional_tools:
        forum_cortex_mod = _optional_tools["forum_cortex"]
        if hasattr(forum_cortex_mod, "research_forum_cortex"):
            mcp.tool()(_wrap_tool(forum_cortex_mod.research_forum_cortex, "fetch"))

    if "onion_spectra" in _optional_tools:
        onion_spectra_mod = _optional_tools["onion_spectra"]
        if hasattr(onion_spectra_mod, "research_onion_spectra"):
            mcp.tool()(_wrap_tool(onion_spectra_mod.research_onion_spectra, "fetch"))

    if "ghost_weave" in _optional_tools:
        ghost_weave_mod = _optional_tools["ghost_weave"]
        if hasattr(ghost_weave_mod, "research_ghost_weave"):
            mcp.tool()(_wrap_tool(ghost_weave_mod.research_ghost_weave, "fetch"))

    if "dead_drop_scanner" in _optional_tools:
        dead_drop_scanner_mod = _optional_tools["dead_drop_scanner"]
        if hasattr(dead_drop_scanner_mod, "research_dead_drop_scanner"):
            mcp.tool()(_wrap_tool(dead_drop_scanner_mod.research_dead_drop_scanner, "fetch"))

    if "persona_profile" in _optional_tools:
        persona_profile_mod = _optional_tools["persona_profile"]
        if hasattr(persona_profile_mod, "research_persona_profile"):
            mcp.tool()(_wrap_tool(persona_profile_mod.research_persona_profile, "llm"))

    if "radicalization_detect" in _optional_tools:
        radicalization_detect_mod = _optional_tools["radicalization_detect"]
        if hasattr(radicalization_detect_mod, "research_radicalization_detect"):
            mcp.tool()(_wrap_tool(radicalization_detect_mod.research_radicalization_detect, "llm"))


    if "sentiment_deep" in _optional_tools:
        sentiment_deep_mod = _optional_tools["sentiment_deep"]
        if hasattr(sentiment_deep_mod, "research_sentiment_deep"):
            mcp.tool()(_wrap_tool(sentiment_deep_mod.research_sentiment_deep, "analysis"))

    if "network_persona" in _optional_tools:
        network_persona_mod = _optional_tools["network_persona"]
        if hasattr(network_persona_mod, "research_network_persona"):
            mcp.tool()(_wrap_tool(network_persona_mod.research_network_persona, "analysis"))



    # Text analysis tool (if nltk available)
    if "text_analyze" in _optional_tools:
        text_analyze_mod = _optional_tools["text_analyze"]
        if hasattr(text_analyze_mod, "research_text_analyze"):
            mcp.tool()(_wrap_tool(text_analyze_mod.research_text_analyze, "analysis"))

    # Screenshot tool (if playwright available)
    if "screenshot" in _optional_tools:
        screenshot_mod = _optional_tools["screenshot"]
        if hasattr(screenshot_mod, "research_screenshot"):
            mcp.tool()(_wrap_tool(screenshot_mod.research_screenshot, "fetch"))

    # SSL/TLS certificate analyzer
    if "cert_analyzer" in _optional_tools:
        cert_mod = _optional_tools["cert_analyzer"]
        if hasattr(cert_mod, "research_cert_analyze"):
            mcp.tool()(_wrap_tool(cert_mod.research_cert_analyze, "fetch"))

    # HTTP security headers checker
    if "security_headers" in _optional_tools:
        sec_headers_mod = _optional_tools["security_headers"]
        if hasattr(sec_headers_mod, "research_security_headers"):
            mcp.tool()(_wrap_tool(sec_headers_mod.research_security_headers, "fetch"))

    # Breach/password check tools
    if "breach_check" in _optional_tools:
        breach_mod = _optional_tools["breach_check"]
        if hasattr(breach_mod, "research_breach_check"):
            mcp.tool()(_wrap_tool(breach_mod.research_breach_check, "fetch"))
        if hasattr(breach_mod, "research_password_check"):
            mcp.tool()(_wrap_tool(breach_mod.research_password_check))

    # IP intelligence tools (if available)
    if "ip_intel" in _optional_tools:
        ip_intel_mod = _optional_tools["ip_intel"]
        if hasattr(ip_intel_mod, "research_ip_reputation"):
            mcp.tool()(_wrap_tool(ip_intel_mod.research_ip_reputation, "fetch"))
        if hasattr(ip_intel_mod, "research_ip_geolocation"):
            mcp.tool()(_wrap_tool(ip_intel_mod.research_ip_geolocation, "fetch"))

    # CVE lookup tools (if available)
    if "cve_lookup" in _optional_tools:
        cve_lookup_mod = _optional_tools["cve_lookup"]
        if hasattr(cve_lookup_mod, "research_cve_lookup"):
            mcp.tool()(_wrap_tool(cve_lookup_mod.research_cve_lookup, "search"))
        if hasattr(cve_lookup_mod, "research_cve_detail"):
            mcp.tool()(_wrap_tool(cve_lookup_mod.research_cve_detail, "fetch"))

    # URLhaus lookup tools (if available)
    if "urlhaus_lookup" in _optional_tools:
        urlhaus_lookup_mod = _optional_tools["urlhaus_lookup"]
        if hasattr(urlhaus_lookup_mod, "research_urlhaus_check"):
            mcp.tool()(_wrap_tool(urlhaus_lookup_mod.research_urlhaus_check, "fetch"))
        if hasattr(urlhaus_lookup_mod, "research_urlhaus_search"):
            mcp.tool()(_wrap_tool(urlhaus_lookup_mod.research_urlhaus_search, "search"))

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
