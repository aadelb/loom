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
from mcp.server.auth.settings import AuthSettings

from loom.config import load_config, research_config_get, research_config_set
from loom.logging_config import setup_logging
from loom.rate_limiter import rate_limited
from loom.sessions import (
    cleanup_all_sessions,
    research_session_close,
    research_session_list,
    research_session_open,
)

# Import tool modules to register their functions
from loom.tools import (
    academic_integrity,
    ai_safety,
    ai_safety_extended,
    bias_lens,
    breach_check,
    cache_mgmt,
    cert_analyzer,
    change_monitor,
    company_intel,
    competitive_intel,
    crypto_trace,
    culture_dna,
    dark_forum,
    darkweb_early_warning,
    dead_content,
    deception_detect,
    deception_job_scanner,
    deep,
    domain_intel,
    fact_checker,
    fetch,
    github,
    identity_resolve,
    infra_correlator,
    invisible_web,
    job_signals,
    js_intel,
    knowledge_graph,
    leak_scan,
    markdown,
    metadata_forensics,
    multi_search,
    onion_discover,
    osint_extended,
    passive_recon,
    pdf_extract,
    psycholinguistic,
    realtime_monitor,
    report_generator,
    rss_monitor,
    salary_synthesizer,
    search,
    security_headers,
    signal_detection,
    social_graph,
    social_intel,
    spider,
    stealth,
    stego_detect,
    stylometry,
    supply_chain_intel,
    synth_echo,
    threat_profile,
    trend_predictor,
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
    from loom.tools import geoip_local as geoip_local_tools

    _optional_tools["geoip_local"] = geoip_local_tools

with suppress(ImportError):
    from loom.tools import image_intel as image_intel_tools

    _optional_tools["image_intel"] = image_intel_tools

with suppress(ImportError):
    from loom.tools import ip_intel as ip_intel_tools

    _optional_tools["ip_intel"] = ip_intel_tools

with suppress(ImportError):
    from loom.tools import cve_lookup as cve_lookup_tools

    _optional_tools["cve_lookup"] = cve_lookup_tools

with suppress(ImportError):
    from loom.tools import vuln_intel as vuln_intel_tools

    _optional_tools["vuln_intel"] = vuln_intel_tools

with suppress(ImportError):
    from loom.tools import urlhaus_lookup as urlhaus_lookup_tools

    _optional_tools["urlhaus_lookup"] = urlhaus_lookup_tools

with suppress(ImportError):
    from loom.tools import job_research as job_research_tools

    _optional_tools["job_research"] = job_research_tools


with suppress(ImportError):
    from loom.tools import career_intel as career_intel_tools

    _optional_tools["career_intel"] = career_intel_tools

with suppress(ImportError):
    from loom.tools import resume_intel as resume_intel_tools

    _optional_tools["resume_intel"] = resume_intel_tools


with suppress(ImportError):
    from loom.tools import career_trajectory as career_trajectory_tools

    _optional_tools["career_trajectory"] = career_trajectory_tools
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

    # Killer research tools (20 tools — Loom's unfair advantage)
    mcp.tool()(_wrap_tool(dead_content.research_dead_content, "fetch"))
    mcp.tool()(_wrap_tool(invisible_web.research_invisible_web, "fetch"))
    mcp.tool()(_wrap_tool(js_intel.research_js_intel, "fetch"))
    mcp.tool()(_wrap_tool(multi_search.research_multi_search, "search"))
    mcp.tool()(_wrap_tool(dark_forum.research_dark_forum, "search"))
    mcp.tool()(_wrap_tool(infra_correlator.research_infra_correlator, "fetch"))
    mcp.tool()(_wrap_tool(passive_recon.research_passive_recon, "fetch"))
    mcp.tool()(_wrap_tool(onion_discover.research_onion_discover, "fetch"))
    mcp.tool()(_wrap_tool(metadata_forensics.research_metadata_forensics, "fetch"))
    mcp.tool()(_wrap_tool(crypto_trace.research_crypto_trace, "fetch"))
    mcp.tool()(_wrap_tool(stego_detect.research_stego_detect))
    mcp.tool()(_wrap_tool(threat_profile.research_threat_profile, "fetch"))
    mcp.tool()(_wrap_tool(leak_scan.research_leak_scan, "fetch"))
    mcp.tool()(_wrap_tool(social_graph.research_social_graph, "fetch"))

    # Psychology & behavioral analysis tools
    mcp.tool()(_wrap_tool(stylometry.research_stylometry))  # CPU-only, no category
    mcp.tool()(_wrap_tool(deception_detect.research_deception_detect))  # CPU-only, no category

    # Company intelligence tools
    mcp.tool()(_wrap_tool(company_intel.research_company_diligence, "search"))
    mcp.tool()(_wrap_tool(company_intel.research_salary_intelligence, "search"))
    mcp.tool()(_wrap_tool(competitive_intel.research_competitive_intel, "search"))

    # Supply chain intelligence tools
    mcp.tool()(_wrap_tool(supply_chain_intel.research_supply_chain_risk, "fetch"))
    mcp.tool()(_wrap_tool(supply_chain_intel.research_patent_landscape, "search"))
    mcp.tool()(_wrap_tool(supply_chain_intel.research_dependency_audit, "fetch"))

    # Domain intelligence tools
    mcp.tool()(_wrap_tool(domain_intel.research_whois, "fetch"))
    mcp.tool()(_wrap_tool(domain_intel.research_dns_lookup, "fetch"))
    mcp.tool()(_wrap_tool(domain_intel.research_nmap_scan, "fetch"))

    # Identity resolution tool
    mcp.tool()(_wrap_tool(identity_resolve.research_identity_resolve, "fetch"))

    # Job market intelligence tools
    mcp.tool()(_wrap_tool(job_signals.research_funding_signal, "search"))
    mcp.tool()(_wrap_tool(job_signals.research_stealth_hire_scanner, "search"))
    mcp.tool()(_wrap_tool(job_signals.research_interviewer_profiler, "fetch"))

    # Security tools (cert analysis, headers, breach checking)
    mcp.tool()(_wrap_tool(cert_analyzer.research_cert_analyze, "fetch"))
    mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))

    # Signal detection tools
    mcp.tool()(_wrap_tool(signal_detection.research_ghost_protocol, "search"))
    mcp.tool()(_wrap_tool(signal_detection.research_temporal_anomaly, "fetch"))
    mcp.tool()(_wrap_tool(signal_detection.research_sec_tracker, "search"))
    mcp.tool()(_wrap_tool(breach_check.research_breach_check, "fetch"))
    mcp.tool()(_wrap_tool(breach_check.research_password_check))

    # AI Safety red-team tools (5 tools for EU AI Act Article 15 compliance testing)
    mcp.tool()(_wrap_tool(ai_safety.research_prompt_injection_test, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_model_fingerprint, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_bias_probe, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_safety_filter_map, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_compliance_check, "fetch"))

    # Extended AI Safety tools (2 tools for advanced compliance testing)
    mcp.tool()(_wrap_tool(ai_safety_extended.research_hallucination_benchmark, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety_extended.research_adversarial_robustness, "fetch"))

    # Extended OSINT tools (2 tools for social engineering assessment)
    mcp.tool()(_wrap_tool(osint_extended.research_social_engineering_score, "fetch"))
    mcp.tool()(_wrap_tool(osint_extended.research_behavioral_fingerprint, "fetch"))

    # PDF extraction tools
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))

    # Academic integrity tools
    mcp.tool()(_wrap_tool(academic_integrity.research_citation_analysis, "fetch"))
    mcp.tool()(_wrap_tool(academic_integrity.research_retraction_check, "fetch"))
    mcp.tool()(_wrap_tool(academic_integrity.research_predatory_journal_check, "fetch"))

    # Creative research tools (4 tools for advanced research scenarios)
    mcp.tool()(_wrap_tool(darkweb_early_warning.research_darkweb_early_warning, "search"))
    mcp.tool()(_wrap_tool(deception_job_scanner.research_deception_job_scan))
    mcp.tool()(_wrap_tool(bias_lens.research_bias_lens, "fetch"))
    mcp.tool()(_wrap_tool(salary_synthesizer.research_salary_synthesize, "search"))

    # Real-time monitoring tools
    mcp.tool()(_wrap_tool(realtime_monitor.research_realtime_monitor, "fetch"))

    # RSS feed tools
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_fetch, "fetch"))
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_search, "search"))

    # Social intelligence tools
    mcp.tool()(_wrap_tool(social_intel.research_social_search, "fetch"))
    mcp.tool()(_wrap_tool(social_intel.research_social_profile, "fetch"))

    # Trend prediction and report generation tools
    mcp.tool()(_wrap_tool(trend_predictor.research_trend_predict, "search"))
    mcp.tool()(_wrap_tool(report_generator.research_generate_report, "search"))

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

    # Job research tools (if available)
    if "job_research" in _optional_tools:
        job_research_mod = _optional_tools["job_research"]
        if hasattr(job_research_mod, "research_job_search"):
            mcp.tool()(_wrap_tool(job_research_mod.research_job_search, "search"))
        if hasattr(job_research_mod, "research_job_market"):
            mcp.tool()(_wrap_tool(job_research_mod.research_job_market, "search"))

    # Career intelligence tools (if available)
    if "career_intel" in _optional_tools:
        career_intel_mod = _optional_tools["career_intel"]
        if hasattr(career_intel_mod, "research_map_research_to_product"):
            mcp.tool()(_wrap_tool(career_intel_mod.research_map_research_to_product, "llm"))
        if hasattr(career_intel_mod, "research_translate_academic_skills"):
            mcp.tool()(_wrap_tool(career_intel_mod.research_translate_academic_skills, "llm"))

    # Career trajectory and market velocity tools (if available)
    if "career_trajectory" in _optional_tools:
        career_traj_mod = _optional_tools["career_trajectory"]
        if hasattr(career_traj_mod, "research_career_trajectory"):
            mcp.tool()(_wrap_tool(career_traj_mod.research_career_trajectory, "fetch"))
        if hasattr(career_traj_mod, "research_market_velocity"):
            mcp.tool()(_wrap_tool(career_traj_mod.research_market_velocity, "search"))


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

    # Vulnerability intelligence tools (if available)
    if "vuln_intel" in _optional_tools:
        vuln_intel_mod = _optional_tools["vuln_intel"]
        if hasattr(vuln_intel_mod, "research_vuln_intel"):
            mcp.tool()(_wrap_tool(vuln_intel_mod.research_vuln_intel, "search"))

    # URLhaus lookup tools (if available)
    if "urlhaus_lookup" in _optional_tools:
        urlhaus_lookup_mod = _optional_tools["urlhaus_lookup"]
        if hasattr(urlhaus_lookup_mod, "research_urlhaus_check"):
            mcp.tool()(_wrap_tool(urlhaus_lookup_mod.research_urlhaus_check, "fetch"))
        if hasattr(urlhaus_lookup_mod, "research_urlhaus_search"):
            mcp.tool()(_wrap_tool(urlhaus_lookup_mod.research_urlhaus_search, "search"))

    # GeoIP local lookup
    if "geoip_local" in _optional_tools:
        geoip_mod = _optional_tools["geoip_local"]
        if hasattr(geoip_mod, "research_geoip_local"):
            mcp.tool()(_wrap_tool(geoip_mod.research_geoip_local, "fetch"))

    # Image intelligence (EXIF + OCR)
    if "image_intel" in _optional_tools:
        image_mod = _optional_tools["image_intel"]
        if hasattr(image_mod, "research_exif_extract"):
            mcp.tool()(_wrap_tool(image_mod.research_exif_extract, "fetch"))
        if hasattr(image_mod, "research_ocr_extract"):
            mcp.tool()(_wrap_tool(image_mod.research_ocr_extract, "fetch"))

    # Resume and interview prep tools (if available)
    if "resume_intel" in _optional_tools:
        resume_intel_mod = _optional_tools["resume_intel"]
        if hasattr(resume_intel_mod, "research_optimize_resume"):
            mcp.tool()(_wrap_tool(resume_intel_mod.research_optimize_resume, "llm"))
        if hasattr(resume_intel_mod, "research_interview_prep"):
            mcp.tool()(_wrap_tool(resume_intel_mod.research_interview_prep, "llm"))


def _validate_environment() -> None:
    """Validate that required environment variables are configured.

    Checks for:
    1. At least one LLM provider key
    2. At least one search provider key (or ddgs which needs no key)
    3. Logs warnings for optional missing keys

    Does NOT crash — server still boots if validation fails.
    """
    llm_keys = [
        "GROQ_API_KEY",
        "NVIDIA_NIM_API_KEY",
        "DEEPSEEK_API_KEY",
        "GOOGLE_AI_KEY",
        "MOONSHOT_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]

    search_keys = [
        "EXA_API_KEY",
        "TAVILY_API_KEY",
        "FIRECRAWL_API_KEY",
        "BRAVE_API_KEY",
        "NEWS_API_KEY",
        "UMMRO_RAG_URL",
    ]

    optional_keys = [
        "GITHUB_TOKEN",
        "VASTAI_API_KEY",
        "STRIPE_LIVE_KEY",
        "SMTP_USER",
        "SMTP_APP_PASSWORD",
        "JOPLIN_TOKEN",
        "TOR_CONTROL_PASSWORD",
    ]

    # Check for at least one LLM provider
    llm_configured = any(os.environ.get(key) for key in llm_keys)
    if not llm_configured:
        log.warning(
            "no_llm_provider_configured. Set at least one of: %s",
            ", ".join(llm_keys),
        )

    # Check for at least one search provider (ddgs doesn't need a key)
    search_configured = any(os.environ.get(key) for key in search_keys)
    if not search_configured:
        log.warning(
            "no_search_provider_configured. Set at least one of: %s (or use ddgs)",
            ", ".join(search_keys),
        )

    # Log warnings for missing optional keys
    for key in optional_keys:
        if not os.environ.get(key):
            log.debug("optional_key_not_set key=%s", key)

def create_app() -> FastMCP:
    """Create and configure the FastMCP server instance.

    Loads runtime config, sets up logging, registers all 94 tools,
    and prepares the server to listen on LOOM_HOST:LOOM_PORT.

    Returns:
        Configured FastMCP instance ready to run
    """
    # Load runtime config
    config = load_config()

    # Set up logging with request_id support
    log_level = config.get("LOG_LEVEL", "INFO")
    log_format = os.environ.get("LOG_FORMAT", config.get("LOG_FORMAT", "text"))
    setup_logging(log_level=log_level, log_format=log_format)
    install_tracing()

    # Validate environment
    _validate_environment()

    # Create FastMCP instance
    host = os.environ.get("LOOM_HOST", "127.0.0.1")
    port = int(os.environ.get("LOOM_PORT", "8787"))

    # Set up authentication if LOOM_API_KEY is configured
    api_key = os.environ.get("LOOM_API_KEY", "")
    token_verifier = None
    auth = None
    if api_key:
        from loom.auth import ApiKeyVerifier
        token_verifier = ApiKeyVerifier()
        # AuthSettings requires issuer_url and resource_server_url for OAuth compliance
        # For simple bearer token verification, provide minimal URLs
        auth = AuthSettings(
            issuer_url="http://loom.local",
            resource_server_url="http://loom.local",
        )
        log.info("auth_enabled LOOM_API_KEY_LENGTH=%d", len(api_key))
    else:
        log.warning("auth_disabled no_LOOM_API_KEY_set")

    mcp = FastMCP(
        name="loom",
        host=host,
        port=port,
        auth=auth,
        token_verifier=token_verifier,
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
