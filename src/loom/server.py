"""FastMCP server entrypoint for Loom MCP service.

Exports the FastMCP instance with all research tools registered
via dynamic tool discovery from the loom.tools namespace.
"""

from __future__ import annotations

import asyncio
import functools
import difflib
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
from loom.orchestrator import research_orchestrate
from loom.audit import export_audit
from loom.logging_config import setup_logging
from loom.rate_limiter import rate_limited
from loom.sessions import (
    cleanup_all_sessions,
    research_session_close,
    research_session_list,
    research_session_open,
)
from loom.scoring import research_score_all
from loom.unified_scorer import research_unified_score

from loom.benchmarks import research_benchmark_run
from loom.consensus_builder import (
    research_consensus_build,
    research_consensus_pressure,
)
from loom.crescendo_loop import research_crescendo_loop
from loom.model_profiler import research_model_profile
from loom.reid_pipeline import research_reid_pipeline
from loom.full_spectrum import FullSpectrumPipeline
from loom import crawlee_backend
from loom import zendriver_backend
from loom.sqlite_pool import research_pool_stats, research_pool_reset


# Import tool modules to register their functions
from loom.tools import (
    api_version,
    academic_integrity,
    access_tools,
    adversarial_debate_tool,
    adversarial_craft,
    agent_benchmark,
    auto_experiment,
    auto_pipeline,
    auto_params,
    audit_log,
    ai_safety,
    ai_safety_extended,
    auto_docs,
    antiforensics,
    anomaly_detector,
    arxiv_pipeline,
    autonomous_agent,
    bias_lens,
    backoff_dlq,
    backup_system,
    benchmark_suite,
    breach_check,
    circuit_breaker,
    cache_mgmt,
    capability_matrix,
    changelog_gen,
    chain_composer,
    compliance_checker,
    config_reload,
    cert_analyzer,
    chronos,
    change_monitor,
    company_intel,
    competitive_intel,
    competitive_monitor,
    context_manager,
    coevolution,
    composition_optimizer,
    credential_vault,
    crypto_risk,
    crypto_trace,
    cost_estimator,
    cultural_attacks,
    culture_dna,
    cyberscraper,
    dark_forum,
    dark_recon,
    data_export,
    data_pipeline,
    dependency_graph,
    darkweb_early_warning,
    dead_content,
    deception_detect,
    deception_job_scanner,
    deployment,
    dist_tracing,
    deep,
    defender_mode,
    embedding_collision,
    env_inspector,
    enterprise_sso,
    error_wrapper,
    ensemble_attack,
    evidence_fusion,
    deep_research_agent,
    domain_intel,
    exploit_db,
    ethereum_tools,
    explainability,
    execution_planner,
    feature_flags,
    fact_checker,
    gamification,
    geodesic_forcing,
    fetch,
    fingerprint_evasion,
    full_pipeline,
    functor_map,
    gap_tools_academic,
    gap_tools_advanced,
    gap_tools_ai,
    gap_tools_infra,
    github,
    graph_analysis,
    graph_scraper,
    health_dashboard,
    help_system,
    hcs10_academic,
    hcs_escalation,
    hcs_report,
    hcs_rubric_tool,
    hcs_scorer,
    hitl_eval,
    holographic_payload,
    integration_runner,
    identity_resolve,
    infowar_tools,
    infra_analysis,
    infra_correlator,
    input_sanitizer,
    invisible_web,
    job_signals,
    key_rotation,
    js_intel,
    json_logger,
    knowledge_injector,
    knowledge_base,
    knowledge_graph,
    leak_scan,
    lifetime_oracle,
    live_registry,
    lightpanda_backend,
    markdown,
    metric_alerts,
    memory_mgmt,
    memetic_simulator,
    metadata_forensics,
    meta_learner,
    multilang_attack,
    model_fingerprinter,
    multi_search,
    nightcrawler,
    nl_executor,
    neo4j_backend,
    neuromorphic,
    network_map,
    notifications,
    observability,
    onion_discover,
    osint_extended,
    output_formatter,
    output_diff,
    p3_tools,
    parallel_executor,
    paradox_detector,
    polyglot_scraper,
    persistent_memory,
    plugin_loader,
    passive_recon,
    pdf_extract,
    projectdiscovery,
    provider_health,
    privacy_advanced,
    proactive_defense,
    prompt_analyzer,
    prompt_reframe,
    progress_tracker,
    predictive_ranker,
    psycholinguistic,
    rag_anything,
    request_queue,
    rate_limiter_tool,
    realtime_adapt,
    realtime_monitor,
    report_generator,
    result_aggregator,
    resilience_predictor,
    research_journal,
    research_scheduler,
    retry_middleware,
    response_synthesizer,
    response_cache,
    redteam_hub,
    resumption,
    rss_monitor,
    salary_synthesizer,
    scraper_engine_tools,
    search,
    semantic_index,
    security_headers,
    safety_predictor,
    safety_neurons,
    schema_migrate,
    sherlock_backend,
    silk_guardian,
    signal_detection,
    social_graph,
    social_intel,
    social_scraper,
    smart_router,
    spider,
    session_replay,
    startup_validator,
    strange_attractors,
    swarm_attack,
    superposition_prompt,
    stagehand_backend,
    stealth,
    stego_detect,
    stego_encoder,
    thinking_injection,
    strategy_ab_test,
    strategy_cache,
    strategy_feedback,
    strategy_evolution,
    stylometry,
    supply_chain,
    supply_chain_intel,
    task_resolver,
    synth_echo,
    telemetry,
    tenant_isolation,
    synthetic_data,
    threat_intel,
    threat_profile,
    traffic_capture,
    tool_catalog,
    tool_tags,
    tool_versioning,
    tool_recommender_v2,
    tool_profiler,
    trend_predictor,
    usage_analytics,
    unique_tools,
    webhook_system,
    white_rabbit,
    vision_agent,
    workflow_engine,
    workflow_templates,
    workflow_expander,
    xover_attack,
    universal_orchestrator,
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

# ── v3 modules: scorers, pipelines, orchestration, tracking ──
with suppress(ImportError):
    from loom.tools import attack_scorer as attack_scorer_tools
    _optional_tools["attack_scorer"] = attack_scorer_tools

with suppress(ImportError):
    from loom.tools import stealth_score as stealth_score_tools
    _optional_tools["stealth_score"] = stealth_score_tools

with suppress(ImportError):
    from loom.tools import potency_meter as potency_meter_tools
    _optional_tools["potency_meter"] = potency_meter_tools

with suppress(ImportError):
    from loom.tools import stealth_scorer as stealth_scorer_tools
    _optional_tools["stealth_scorer"] = stealth_scorer_tools

with suppress(ImportError):
    from loom.tools import model_sentiment as model_sentiment_tools
    _optional_tools["model_sentiment"] = model_sentiment_tools

with suppress(ImportError):
    from loom.tools import toxicity_checker_tool as toxicity_tools
    _optional_tools["toxicity"] = toxicity_tools

with suppress(ImportError):
    from loom.tools import drift_monitor_tool as drift_tools
    _optional_tools["drift"] = drift_tools

with suppress(ImportError):
    from loom.tools import bpj as bpj_tools
    _optional_tools["bpj"] = bpj_tools

with suppress(ImportError):
    from loom.tools import daisy_chain_tool as daisy_tools
    _optional_tools["daisy_chain"] = daisy_tools

with suppress(ImportError):
    from loom.tools import consistency_pressure as consistency_tools
    _optional_tools["consistency"] = consistency_tools

with suppress(ImportError):
    from loom.tools import constraint_optimizer as constraint_tools
    _optional_tools["constraint"] = constraint_tools

with suppress(ImportError):
    from loom.tools import jailbreak_evolution as jailbreak_evo_tools
    _optional_tools["jailbreak_evo"] = jailbreak_evo_tools

with suppress(ImportError):
    from loom.tools import semantic_cache_mgmt as sem_cache_tools
    _optional_tools["sem_cache"] = sem_cache_tools

with suppress(ImportError):
    from loom.tools import param_sweep as param_sweep_tools
    _optional_tools["param_sweep"] = param_sweep_tools

with suppress(ImportError):
    from loom.tools import strategy_oracle as strategy_oracle_tools
    _optional_tools["strategy_oracle"] = strategy_oracle_tools

with suppress(ImportError):
    from loom.tools import stealth_detect as stealth_detect_tools
    _optional_tools["stealth_detect"] = stealth_detect_tools

with suppress(ImportError):
    from loom.tools import tool_recommender_tool as recommender_tools
    _optional_tools["recommender"] = recommender_tools

with suppress(ImportError):
    from loom.tools import ytdlp_backend as ytdlp_tools
    _optional_tools["ytdlp"] = ytdlp_tools

# ── v3 direct imports (functions in src/loom/*.py) ──
with suppress(ImportError):
    from loom.danger_prescore import research_danger_prescore
    _optional_tools["danger_prescore"] = research_danger_prescore

with suppress(ImportError):
    from loom.quality_scorer import research_quality_score
    _optional_tools["quality_scorer"] = research_quality_score

with suppress(ImportError):
    from loom.evidence_pipeline import research_evidence_pipeline
    _optional_tools["evidence_pipeline"] = research_evidence_pipeline

with suppress(ImportError):
    from loom.context_poisoning import research_context_poison
    _optional_tools["context_poison"] = research_context_poison

with suppress(ImportError):
    from loom.adversarial_debate import research_adversarial_debate
    _optional_tools["adversarial_debate"] = research_adversarial_debate

with suppress(ImportError):
    from loom.model_evidence import research_model_evidence
    _optional_tools["model_evidence"] = research_model_evidence

with suppress(ImportError):
    from loom.target_orchestrator import research_target_orchestrate
    _optional_tools["target_orchestrate"] = research_target_orchestrate

with suppress(ImportError):
    from loom.reid_auto import ReidAutoReframe
    _optional_tools["reid_auto"] = ReidAutoReframe

with suppress(ImportError):
    from loom.mcp_security import research_mcp_security_scan
    _optional_tools["mcp_security"] = research_mcp_security_scan

with suppress(ImportError):
    from loom.cicd import research_cicd_run
    _optional_tools["cicd"] = research_cicd_run

with suppress(ImportError):
    from loom.stealth_detector import research_stealth_detect as stealth_det_fn
    _optional_tools["stealth_detector"] = stealth_det_fn

with suppress(ImportError):
    from loom.doc_parser import research_ocr_advanced, research_pdf_advanced, research_document_analyze
    _optional_tools["doc_parser"] = {"ocr": research_ocr_advanced, "pdf": research_pdf_advanced, "analyze": research_document_analyze}

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
    from loom.tools import epistemic_score as epistemic_score_tools

    _optional_tools["epistemic_score"] = epistemic_score_tools

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

with suppress(ImportError):
    from loom.tools import consistency_pressure as consistency_pressure_tools

    _optional_tools["consistency_pressure"] = consistency_pressure_tools

with suppress(ImportError):
    from loom.tools import constraint_optimizer as constraint_optimizer_tools

    _optional_tools["constraint_optimizer"] = constraint_optimizer_tools

with suppress(ImportError):
    from loom.tools import semantic_cache_mgmt as semantic_cache_mgmt_tools

    _optional_tools["semantic_cache_mgmt"] = semantic_cache_mgmt_tools

with suppress(ImportError):
    from loom.tools import param_sweep as param_sweep_tools

    _optional_tools["param_sweep"] = param_sweep_tools

with suppress(ImportError):
    from loom import nodriver_backend

    _optional_tools["nodriver"] = nodriver_backend

with suppress(ImportError):
    from loom.tools import ytdlp_backend as ytdlp_backend_tools

    _optional_tools["ytdlp_backend"] = ytdlp_backend_tools


with suppress(ImportError):
    from loom.tools import model_consensus as model_consensus_tools

    _optional_tools["model_consensus"] = model_consensus_tools


with suppress(ImportError):
    from loom import doc_parser as doc_parser_tools

    _optional_tools["doc_parser"] = doc_parser_tools

with suppress(ImportError):
    from loom.tools import mcp_auth as mcp_auth_tools

    _optional_tools["mcp_auth"] = mcp_auth_tools

_start_time = time.time()


async def research_audit_export(
    start_date: str | None = None,
    end_date: str | None = None,
    format: str = "json",
) -> dict[str, Any]:
    """Export audit logs for compliance reporting.

    Retrieves audit log entries within an optional date range.
    Supports two export formats: JSON array or CSV string with headers.
    Each entry includes verification status (_verified field).

    Args:
        start_date: Start date (YYYY-MM-DD) or None for earliest
        end_date: End date (YYYY-MM-DD) or None for latest
        format: Export format, "json" (default) or "csv"

    Returns:
        Dict with:
        - format: Export format used ("json" or "csv")
        - data: Exported data (array for JSON, string for CSV)
        - count: Number of entries exported
    """
    from pathlib import Path
    from loom.audit import DEFAULT_AUDIT_DIR
    
    return export_audit(
        start_date=start_date,
        end_date=end_date,
        format=format,
        audit_dir=DEFAULT_AUDIT_DIR,
    )


async def research_health_check() -> dict[str, Any]:
    """Return comprehensive server health status for monitoring.

    Performs lightweight checks on all 8 LLM providers and available search
    providers without making actual API calls. Returns cache stats, session
    count, uptime, version, and overall health status.

    Returns:
        Dict with:
        - status: "healthy", "degraded", or "unhealthy"
        - uptime_seconds: Server uptime in seconds
        - tool_count: Registered tools count
        - strategy_count: Total strategy implementations
        - llm_providers: Dict of LLM provider statuses
        - search_providers: Dict of search provider statuses
        - cache: Cache stats (entries, size_mb, hit_rate)
        - sessions: Active session count and max
        - version: Loom version string
        - timestamp: ISO 8601 timestamp
    """
    from loom import __version__
    from loom.cache import get_cache
    from loom.sessions import _sessions

    # 1. Collect uptime and sessions
    uptime_seconds = int(time.time() - _start_time)
    active_sessions = len(_sessions)

    # 2. Check LLM providers (8 total)
    llm_providers: dict[str, dict[str, Any]] = {}
    llm_provider_names = [
        "groq",
        "nvidia_nim",
        "deepseek",
        "gemini",
        "moonshot",
        "openai",
        "anthropic",
        "vllm",
    ]

    for provider_name in llm_provider_names:
        is_available = _check_llm_provider_available(provider_name)
        llm_providers[provider_name] = {
            "status": "up" if is_available else "down",
        }

    # 3. Check search providers (21 total)
    search_providers: dict[str, dict[str, Any]] = {}
    search_provider_names = [
        "exa",
        "tavily",
        "firecrawl",
        "brave",
        "ddgs",
        "arxiv",
        "wikipedia",
        "hackernews",
        "reddit",
        "newsapi",
        "coindesk",
        "coinmarketcap",
        "binance",
        "ahmia",
        "darksearch",
        "ummro_rag",
        "onionsearch",
        "torcrawl",
        "darkweb_cti",
        "robin_osint",
        "investing",
    ]

    for provider_name in search_provider_names:
        is_available = _check_search_provider_available(provider_name)
        search_providers[provider_name] = {
            "status": "up" if is_available else "down",
        }

    # 4. Get cache stats
    cache = get_cache()
    cache_stats = cache.stats()
    # Convert bytes to MB
    cache_size_mb = round(cache_stats.get("total_bytes", 0) / (1024 * 1024), 2)

    cache_info = {
        "entries": cache_stats.get("file_count", 0),
        "size_mb": cache_size_mb,
        "hit_rate": 0.0,  # Placeholder; not tracked in current implementation
    }

    # 5. Calculate overall health status
    llm_up = sum(1 for p in llm_providers.values() if p["status"] == "up")
    search_up = sum(1 for p in search_providers.values() if p["status"] == "up")

    # Healthy if: all 8 LLM providers available OR at least 1 LLM and 5+ search
    # Degraded if: some LLM or search providers down
    # Unhealthy if: no LLMs or no search providers
    if llm_up == 0 or search_up == 0:
        overall_status = "unhealthy"
    elif llm_up < len(llm_provider_names) or search_up < len(search_provider_names):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # 6. Session management limits (hardcoded for now; can be from config)
    max_sessions = 10

    return {
        "status": overall_status,
        "uptime_seconds": uptime_seconds,
        "tool_count": 346,
        "strategy_count": 957,
        "llm_providers": llm_providers,
        "search_providers": search_providers,
        "cache": cache_info,
        "sessions": {
            "active": active_sessions,
            "max": max_sessions,
        },
        "version": __version__,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _check_llm_provider_available(provider_name: str) -> bool:
    """Check if an LLM provider is configured (without making API calls).

    Args:
        provider_name: Name of the LLM provider

    Returns:
        True if provider has required API key configured
    """
    env_keys: dict[str, str] = {
        "groq": "GROQ_API_KEY",
        "nvidia_nim": "NVIDIA_NIM_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GOOGLE_AI_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "vllm": "VLLM_ENDPOINT",  # vLLM checks for endpoint, not a key
    }

    key = env_keys.get(provider_name)
    if not key:
        return False

    value = os.environ.get(key, "").strip()
    return bool(value)


def _check_search_provider_available(provider_name: str) -> bool:
    """Check if a search provider is configured (without making API calls).

    Args:
        provider_name: Name of the search provider

    Returns:
        True if provider has required API key configured (or is always available)
    """
    # Providers that don't require keys (always available)
    always_available = {"ddgs", "arxiv", "wikipedia", "hackernews", "reddit"}
    if provider_name in always_available:
        return True

    # Providers that require keys
    env_keys: dict[str, str] = {
        "exa": "EXA_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "firecrawl": "FIRECRAWL_API_KEY",
        "brave": "BRAVE_API_KEY",
        "newsapi": "NEWS_API_KEY",
        "coindesk": "NEWS_API_KEY",  # Shared with newsapi
        "coinmarketcap": "COINMARKETCAP_API_KEY",
        "binance": "BINANCE_API_KEY",
        "ahmia": "AHMIA_API_KEY",
        "darksearch": "DARKSEARCH_API_KEY",
        "ummro_rag": "UMMRO_RAG_URL",
        "onionsearch": "ONIONSEARCH_API_KEY",
        "torcrawl": "TORCRAWL_API_KEY",
        "darkweb_cti": "DARKWEB_CTI_API_KEY",
        "robin_osint": "ROBIN_OSINT_API_KEY",
        "investing": "INVESTING_API_KEY",
    }

    key = env_keys.get(provider_name)
    if not key:
        return False

    value = os.environ.get(key, "").strip()
    return bool(value)



# Global dashboard instance (singleton)
_dashboard_instance: Any = None


def _get_dashboard() -> Any:
    """Get or create the global dashboard instance."""
    global _dashboard_instance
    if _dashboard_instance is None:
        from loom.dashboard import AttackDashboard
        _dashboard_instance = AttackDashboard()
    return _dashboard_instance


async def research_dashboard(
    action: str,
    event_type: str | None = None,
    event_data: dict[str, Any] | None = None,
    since: int = 0,
) -> dict[str, Any]:
    """Real-time attack visualization dashboard.

    Provides live event streaming and summary statistics for attack visualization.
    Supports adding events, retrieving event logs, generating summaries, and
    generating a standalone HTML dashboard page.

    Args:
        action: One of "add_event", "get_events", "summary", or "html"
        event_type: Event type when action="add_event"
                   (strategy_applied, model_response, score_update, attack_success, attack_failure)
        event_data: Event data dictionary when action="add_event"
        since: Get events since index N (default: 0)

    Returns:
        Dictionary with action results:
        - add_event: {success: bool, index: int}
        - get_events: {events: list, count: int}
        - summary: {total_attacks, successes, failures, success_rate, top_strategies, ...}
        - html: {html: str, size_bytes: int, event_count: int}
    """
    from loom.params import DashboardParams

    # Validate input
    params = DashboardParams(
        action=action,
        event_type=event_type,
        event_data=event_data or {},
        since=since,
    )

    dashboard = _get_dashboard()

    if params.action == "add_event":
        if not params.event_type or not params.event_data:
            raise ValueError("add_event requires event_type and event_data")
        dashboard.add_event(params.event_type, params.event_data)
        return {
            "success": True,
            "index": len(dashboard.events) - 1,
        }

    elif params.action == "get_events":
        events = dashboard.get_events(params.since)
        return {
            "events": events,
            "count": len(events),
            "total_count": len(dashboard.events),
        }

    elif params.action == "summary":
        return dashboard.get_summary()

    elif params.action == "html":
        html = dashboard.generate_html()
        return {
            "html": html,
            "size_bytes": len(html.encode("utf-8")),
            "event_count": len(dashboard.events),
        }

    else:
        raise ValueError(f"Unknown action: {params.action}")

def _fuzzy_correct_params(func: Callable[..., Any], kwargs: dict) -> tuple[dict, dict]:
    """Auto-correct misspelled param names using fuzzy matching.
    
    Args:
        func: The function to extract parameter names from
        kwargs: The keyword arguments to correct
    
    Returns:
        Tuple of (corrected_kwargs, corrections_made)
        corrections_made is dict mapping wrong_param -> correct_param (or None if dropped)
    """
    import inspect
    
    # Get valid param names from function signature
    sig = inspect.signature(func)
    valid_params = set(sig.parameters.keys())
    
    corrected = {}
    corrections = {}
    
    for key, value in kwargs.items():
        if key in valid_params:
            corrected[key] = value
        else:
            # Fuzzy match against valid params
            matches = difflib.get_close_matches(key, valid_params, n=1, cutoff=0.5)
            if matches:
                corrected[matches[0]] = value
                corrections[key] = matches[0]
            else:
                # No close match — drop but report
                corrections[key] = None  # means "no match found, dropped"
    
    return corrected, corrections


def _wrap_tool(func: Callable[..., Any], category: str | None = None) -> Callable[..., Any]:
    """Wrap tool with tracing and optional rate limiting.

    Handles both sync and async tool functions correctly.
    """
    import inspect

    is_async = inspect.iscoroutinefunction(func)

    tool_timeout = 60  # seconds

    if is_async:
        if category:
            func = rate_limited(category)(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            new_request_id()
            # Auto-correct parameters
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            if corrections:
                log.debug(f"Parameter corrections for {func.__name__}: {corrections}")
            try:
                result = await asyncio.wait_for(func(*args, **corrected_kwargs), timeout=tool_timeout)
                # Add correction metadata if there were corrections
                if corrections and isinstance(result, dict):
                    result["_param_corrections"] = corrections
                return result
            except asyncio.TimeoutError:
                return {"error": f"Tool timed out after {tool_timeout}s", "tool": func.__name__}

        return async_wrapper
    else:
        if category:
            from loom.rate_limiter import sync_rate_limited
            func = sync_rate_limited(category)(func)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            new_request_id()
            # Auto-correct parameters
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            if corrections:
                log.debug(f"Parameter corrections for {func.__name__}: {corrections}")
            result = func(*args, **corrected_kwargs)
            # Add correction metadata if there were corrections
            if corrections and isinstance(result, dict):
                result["_param_corrections"] = corrections
            return result

        return sync_wrapper




async def research_full_spectrum(
    query: str,
    model_name: str = "unknown",
    target_hcs: float = 8.0,
    reframing_strategy: str = "auto_select",
    include_multi_strategy: bool = False,
    include_report: bool = True,
    include_recommendations: bool = True,
) -> dict:
    """Run full-spectrum red-team pipeline: analyze → reframe → query → score → report.

    Combines all scoring dimensions (danger, quality, attack effectiveness, stealth,
    executability, harm, toxicity) with reframing strategies.

    Args:
        query: Original (potentially harmful) query to analyze
        model_name: Target model identifier (e.g., gpt-4, claude-3-sonnet)
        target_hcs: Target HCS (helpfulness/compliance/specificity) score (0-10)
        reframing_strategy: Strategy to apply or "auto_select" for automatic
        include_multi_strategy: Run all strategies and compare
        include_report: Generate executive summary
        include_recommendations: Generate improvement recommendations

    Returns:
        Dict with status, analysis, prompts, response, scores, violations, report, recommendations
    """
    pipeline = FullSpectrumPipeline()

    # Real LLM model function using cascade
    try:
        from loom.tools.llm import _call_with_cascade

        async def cascade_model(prompt: str = "") -> str:
            try:
                response_obj = await _call_with_cascade(
                    [{"role": "user", "content": prompt}],
                    max_tokens=1500,
                )
                return response_obj.text
            except Exception as e:
                return f"Error calling LLM: {str(e)[:200]}"

        model_fn = cascade_model
    except ImportError:
        logger.error("research_full_spectrum: LLM cascade not available")
        return {
            "error": "LLM provider required but unavailable",
            "query": query,
            "model_name": model_name,
        }

    strategy = None if reframing_strategy == "auto_select" else reframing_strategy

    if include_multi_strategy:
        result = await pipeline.run_multi_strategy(
            query=query,
            model_fn=model_fn,
            model_name=model_name,
        )
    else:
        result = await pipeline.run(
            query=query,
            model_fn=model_fn,
            model_name=model_name,
            target_hcs=target_hcs,
            reframing_strategy=strategy,
        )

    return result



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
    mcp.tool()(_wrap_tool(swarm_attack.research_swarm_attack))
    mcp.tool()(_wrap_tool(markdown.research_markdown, "fetch"))
    mcp.tool()(_wrap_tool(search.research_search, "search"))
    # Smart Search Router tools (3 tools)
    mcp.tool()(_wrap_tool(smart_router.research_route_query))
    mcp.tool()(_wrap_tool(smart_router.research_route_batch))
    mcp.tool()(_wrap_tool(smart_router.research_router_rebuild))
    # Universal Smart Orchestrator meta-tool (1 tool)
    mcp.tool()(_wrap_tool(universal_orchestrator.research_orchestrate_smart))
    mcp.tool()(_wrap_tool(deep.research_deep, "deep"))
    mcp.tool()(_wrap_tool(deep_research_agent.research_hierarchical_research, "hierarchical_research"))
    mcp.tool()(_wrap_tool(github.research_github, "search"))
    mcp.tool()(_wrap_tool(stealth.research_camoufox, "fetch"))
    mcp.tool()(_wrap_tool(stealth.research_botasaurus, "fetch"))
    mcp.tool()(_wrap_tool(cyberscraper.research_smart_extract, "fetch"))
    mcp.tool()(_wrap_tool(cyberscraper.research_paginate_scrape, "fetch"))
    mcp.tool()(_wrap_tool(cyberscraper.research_stealth_browser, "fetch"))
    mcp.tool()(_wrap_tool(cache_mgmt.research_cache_stats))
    mcp.tool()(_wrap_tool(error_wrapper.research_error_stats))
    mcp.tool()(_wrap_tool(error_wrapper.research_error_clear))
    mcp.tool()(_wrap_tool(capability_matrix.research_capability_matrix))
    mcp.tool()(_wrap_tool(capability_matrix.research_find_tools_by_capability))
    mcp.tool()(_wrap_tool(cache_mgmt.research_cache_clear))
    mcp.tool()(_wrap_tool(response_cache.research_cache_store))
    mcp.tool()(_wrap_tool(response_cache.research_cache_lookup))
    mcp.tool(name="research_response_cache_stats")(_wrap_tool(response_cache.research_cache_stats))

    # Data Pipeline Builder tools (3 tools)
    mcp.tool()(_wrap_tool(data_pipeline.research_pipeline_create))
    mcp.tool()(_wrap_tool(data_pipeline.research_pipeline_validate))
    mcp.tool()(_wrap_tool(data_pipeline.research_pipeline_list))
    # Input sanitization and validation tools (2 tools)
    mcp.tool()(_wrap_tool(input_sanitizer.research_sanitize_input))
    mcp.tool()(_wrap_tool(input_sanitizer.research_validate_params))
    mcp.tool()(_wrap_tool(metric_alerts.research_alert_create))
    mcp.tool()(_wrap_tool(metric_alerts.research_alert_check))
    mcp.tool()(_wrap_tool(metric_alerts.research_alert_list))
    # Changelog generator tools (2 tools)
    mcp.tool()(_wrap_tool(changelog_gen.research_changelog_generate))
    mcp.tool()(_wrap_tool(changelog_gen.research_changelog_stats))
    # Plugin loader tools (3 tools)
    mcp.tool()(_wrap_tool(plugin_loader.research_plugin_load))
    mcp.tool()(_wrap_tool(plugin_loader.research_plugin_list))
    mcp.tool()(_wrap_tool(plugin_loader.research_plugin_unload))
    # Anomaly detection tools (2 tools)
    mcp.tool()(_wrap_tool(anomaly_detector.research_detect_anomalies))
    mcp.tool()(_wrap_tool(anomaly_detector.research_detect_text_anomalies))
    # Tool Chain Composer (3 tools)
    mcp.tool()(_wrap_tool(chain_composer.research_chain_define))
    mcp.tool()(_wrap_tool(chain_composer.research_chain_list))
    mcp.tool()(_wrap_tool(chain_composer.research_chain_describe))
    # Data export tools (3 tools)
    mcp.tool()(_wrap_tool(data_export.research_export_json))
    mcp.tool()(_wrap_tool(data_export.research_export_csv))
    mcp.tool()(_wrap_tool(data_export.research_export_list))
    # Rate limiter tools (3 tools)
    mcp.tool()(_wrap_tool(rate_limiter_tool.research_ratelimit_check))
    mcp.tool()(_wrap_tool(rate_limiter_tool.research_ratelimit_configure))
    mcp.tool()(_wrap_tool(rate_limiter_tool.research_ratelimit_status))
    # Circuit breaker tools (3 tools)
    mcp.tool()(_wrap_tool(circuit_breaker.research_breaker_status))
    mcp.tool()(_wrap_tool(circuit_breaker.research_breaker_trip))
    mcp.tool()(_wrap_tool(circuit_breaker.research_breaker_reset))
    # Feature flags tools (3 tools)
    mcp.tool()(_wrap_tool(feature_flags.research_flag_check))
    mcp.tool()(_wrap_tool(feature_flags.research_flag_toggle))
    mcp.tool()(_wrap_tool(feature_flags.research_flag_list))
    # Config hot-reload (3 tools)
    mcp.tool()(_wrap_tool(config_reload.research_config_watch))
    mcp.tool()(_wrap_tool(config_reload.research_config_check))
    mcp.tool()(_wrap_tool(config_reload.research_config_diff))
    # Tool Composition Optimizer (3 tools)
    mcp.tool()(_wrap_tool(composition_optimizer.research_optimize_workflow))
    mcp.tool()(_wrap_tool(composition_optimizer.research_parallel_plan))
    mcp.tool()(_wrap_tool(composition_optimizer.research_optimizer_rebuild))
    # Research context management (3 tools)
    mcp.tool()(_wrap_tool(context_manager.research_context_set))
    mcp.tool()(_wrap_tool(context_manager.research_context_get))
    mcp.tool()(_wrap_tool(context_manager.research_context_clear))
    # Provider health monitoring (3 tools)
    mcp.tool()(_wrap_tool(provider_health.research_provider_ping))
    mcp.tool()(_wrap_tool(provider_health.research_provider_history))
    mcp.tool()(_wrap_tool(provider_health.research_provider_recommend))
    mcp.tool()(_wrap_tool(health_dashboard.research_dashboard_html))
    # Backup system (3 tools)
    mcp.tool()(_wrap_tool(backup_system.research_backup_create))
    mcp.tool()(_wrap_tool(backup_system.research_backup_list))
    mcp.tool()(_wrap_tool(backup_system.research_backup_restore))
    # Performance benchmark tools (2 tools)
    mcp.tool()(_wrap_tool(benchmark_suite.research_benchmark_run))
    mcp.tool()(_wrap_tool(benchmark_suite.research_benchmark_compare))
    # Request queue system (3 tools)
    mcp.tool()(_wrap_tool(request_queue.research_queue_add))
    mcp.tool()(_wrap_tool(request_queue.research_queue_status))
    mcp.tool()(_wrap_tool(request_queue.research_queue_drain))
    # Memory management tools (3 tools)
    mcp.tool()(_wrap_tool(memory_mgmt.research_memory_status))
    mcp.tool()(_wrap_tool(memory_mgmt.research_memory_gc))
    mcp.tool()(_wrap_tool(memory_mgmt.research_memory_profile))

    # Tool performance profiler (2 tools)
    mcp.tool()(_wrap_tool(tool_profiler.research_profile_tool))
    mcp.tool()(_wrap_tool(tool_profiler.research_profile_hotspots))

    # Deployment automation tools (3 tools)
    mcp.tool()(_wrap_tool(deployment.research_deploy_status))
    mcp.tool()(_wrap_tool(deployment.research_deploy_history))
    mcp.tool()(_wrap_tool(deployment.research_deploy_record))
    # Audit logging tools (3 tools)
    mcp.tool()(_wrap_tool(audit_log.research_audit_record))
    mcp.tool()(_wrap_tool(audit_log.research_audit_query))
    mcp.tool()(_wrap_tool(audit_log.research_audit_export))
    # Environment inspector tools (2 tools)
    mcp.tool()(_wrap_tool(env_inspector.research_env_inspect))
    mcp.tool()(_wrap_tool(env_inspector.research_env_requirements))
    # Enterprise SSO integration tools (3 tools)
    mcp.tool()(_wrap_tool(enterprise_sso.research_sso_configure))
    mcp.tool()(_wrap_tool(enterprise_sso.research_sso_validate_token))
    mcp.tool()(_wrap_tool(enterprise_sso.research_sso_user_info))
    # Red Team Hub tools (3 tools)
    mcp.tool()(_wrap_tool(redteam_hub.research_hub_share))
    mcp.tool()(_wrap_tool(redteam_hub.research_hub_feed))
    mcp.tool()(_wrap_tool(redteam_hub.research_hub_vote))
    # Dead Letter Queue tools (3 tools)
    mcp.tool()(_wrap_tool(backoff_dlq.research_dlq_push))
    mcp.tool()(_wrap_tool(backoff_dlq.research_dlq_list))
    mcp.tool()(_wrap_tool(backoff_dlq.research_dlq_retry))
    mcp.tool()(_wrap_tool(telemetry.research_telemetry_record))
    mcp.tool()(_wrap_tool(telemetry.research_telemetry_stats))
    mcp.tool()(_wrap_tool(telemetry.research_telemetry_reset))
    mcp.tool()(_wrap_tool(startup_validator.research_validate_startup))
    mcp.tool()(_wrap_tool(startup_validator.research_health_deep))
    mcp.tool()(_wrap_tool(key_rotation.research_key_status))
    mcp.tool()(_wrap_tool(key_rotation.research_key_rotate))
    mcp.tool()(_wrap_tool(key_rotation.research_key_test))
    mcp.tool()(_wrap_tool(json_logger.research_log_query))
    mcp.tool()(_wrap_tool(json_logger.research_log_stats))
    mcp.tool()(_wrap_tool(resumption.research_checkpoint_save))
    mcp.tool()(_wrap_tool(resumption.research_checkpoint_resume))
    mcp.tool()(_wrap_tool(research_pool_stats))
    mcp.tool()(_wrap_tool(research_pool_reset))
    mcp.tool()(_wrap_tool(resumption.research_checkpoint_list))
    mcp.tool()(_wrap_tool(chronos.research_chronos_reverse))
    mcp.tool()(_wrap_tool(exploit_db.research_exploit_register))
    mcp.tool()(_wrap_tool(exploit_db.research_exploit_search))
    # Result aggregation tools (2 tools)
    mcp.tool()(_wrap_tool(result_aggregator.research_aggregate_results))
    mcp.tool()(_wrap_tool(result_aggregator.research_aggregate_texts))
    mcp.tool()(_wrap_tool(exploit_db.research_exploit_stats))
    mcp.tool()(_wrap_tool(output_formatter.research_format_report))
    mcp.tool()(_wrap_tool(output_formatter.research_extract_actionables))
    # Output diff tracking tools (2 tools)
    mcp.tool()(_wrap_tool(output_diff.research_diff_compare))
    mcp.tool()(_wrap_tool(output_diff.research_diff_track))
    mcp.tool()(_wrap_tool(strategy_feedback.research_strategy_log))
    mcp.tool()(_wrap_tool(strategy_feedback.research_strategy_recommend))
    mcp.tool()(_wrap_tool(strategy_feedback.research_strategy_stats))
    # Human-in-the-Loop evaluation tools (3 tools)
    mcp.tool()(_wrap_tool(hitl_eval.research_hitl_submit))
    mcp.tool()(_wrap_tool(hitl_eval.research_hitl_evaluate))
    mcp.tool()(_wrap_tool(hitl_eval.research_hitl_queue))
    # Holographic payload fragmentation (RAG robustness testing)
    mcp.tool()(_wrap_tool(holographic_payload.research_holographic_encode))
    mcp.tool()(_wrap_tool(strategy_cache.research_cached_strategy))
    mcp.tool()(_wrap_tool(strategy_evolution.research_evolve_strategies))
    mcp.tool()(_wrap_tool(strategy_ab_test.research_ab_test_design))
    mcp.tool()(_wrap_tool(strategy_ab_test.research_ab_test_analyze))
    mcp.tool()(_wrap_tool(coevolution.research_coevolve))
    mcp.tool()(_wrap_tool(meta_learner.research_meta_learn))
    mcp.tool()(_wrap_tool(predictive_ranker.research_predict_success))
    mcp.tool()(_wrap_tool(auto_experiment.research_run_experiment))
    mcp.tool()(_wrap_tool(auto_experiment.research_experiment_design))
    mcp.tool()(_wrap_tool(auto_pipeline.research_auto_pipeline))
    mcp.tool()(_wrap_tool(autonomous_agent.research_auto_redteam))
    mcp.tool()(_wrap_tool(autonomous_agent.research_schedule_redteam))
    mcp.tool()(_wrap_tool(workflow_engine.research_workflow_create))
    mcp.tool()(_wrap_tool(workflow_engine.research_workflow_run))
    mcp.tool()(_wrap_tool(workflow_engine.research_workflow_status))
    # Workflow Templates (2 tools)
    mcp.tool()(_wrap_tool(workflow_templates.research_workflow_list))
    mcp.tool()(_wrap_tool(workflow_templates.research_workflow_get))
    # Workflow Coverage Expander (2 tools)
    mcp.tool()(_wrap_tool(workflow_expander.research_workflow_generate))
    mcp.tool()(_wrap_tool(workflow_expander.research_workflow_coverage))
    
    # Gamification system — leaderboards, challenges, competitions (3 tools)
    mcp.tool()(_wrap_tool(gamification.research_leaderboard))
    mcp.tool()(_wrap_tool(gamification.research_challenge_create))
    mcp.tool()(_wrap_tool(gamification.research_challenge_list))

    # Prompt transformation distance measurement (1 tool)
    mcp.tool()(_wrap_tool(geodesic_forcing.research_geodesic_path))

    # Observability tools (3 tools)
    mcp.tool()(_wrap_tool(observability.research_trace_start))
    mcp.tool()(_wrap_tool(observability.research_trace_end))
    mcp.tool()(_wrap_tool(observability.research_traces_list))
    
    # Notification system tools (3 tools)
    mcp.tool()(_wrap_tool(notifications.research_notify_send))
    mcp.tool()(_wrap_tool(notifications.research_notify_history))
    mcp.tool()(_wrap_tool(notifications.research_notify_rules))
    mcp.tool()(_wrap_tool(rag_anything.research_rag_ingest))
    mcp.tool()(_wrap_tool(rag_anything.research_rag_query))
    mcp.tool()(_wrap_tool(rag_anything.research_rag_clear))

    # Unified scraper escalation engine (3 tools)
    mcp.tool()(_wrap_tool(scraper_engine_tools.research_engine_fetch, "fetch"))
    mcp.tool()(_wrap_tool(scraper_engine_tools.research_engine_extract, "fetch"))
    mcp.tool()(_wrap_tool(scraper_engine_tools.research_engine_batch, "fetch"))

    # Zendriver async browser backend (Docker-friendly)
    mcp.tool()(_wrap_tool(zendriver_backend.research_zen_fetch, "fetch"))
    mcp.tool()(_wrap_tool(zendriver_backend.research_zen_batch, "fetch"))
    mcp.tool()(_wrap_tool(zendriver_backend.research_zen_interact, "fetch"))

    # Stagehand vision-first browser automation (2 tools)
    with suppress(ImportError):
        mcp.tool()(_wrap_tool(stagehand_backend.research_stagehand_act, "fetch"))
        mcp.tool()(_wrap_tool(stagehand_backend.research_stagehand_extract, "fetch"))

    # Crawlee multi-backend scraping framework (3 tools)
    with suppress(ImportError):
        mcp.tool()(_wrap_tool(crawlee_backend.research_crawl, "fetch"))
        mcp.tool()(_wrap_tool(crawlee_backend.research_sitemap_crawl, "fetch"))
        mcp.tool()(_wrap_tool(crawlee_backend.research_structured_crawl, "fetch"))

    # Killer research tools (20 tools — Loom's unfair advantage)
    mcp.tool()(_wrap_tool(dead_content.research_dead_content, "fetch"))
    mcp.tool()(_wrap_tool(invisible_web.research_invisible_web, "fetch"))
    mcp.tool()(_wrap_tool(js_intel.research_js_intel, "fetch"))
    mcp.tool()(_wrap_tool(multi_search.research_multi_search, "search"))
    mcp.tool()(_wrap_tool(dark_forum.research_dark_forum, "search"))
    mcp.tool()(_wrap_tool(infra_correlator.research_infra_correlator, "fetch"))
    mcp.tool()(_wrap_tool(passive_recon.research_passive_recon, "fetch"))
    mcp.tool()(_wrap_tool(network_map.research_network_map))
    mcp.tool()(_wrap_tool(network_map.research_network_visualize))
    mcp.tool()(_wrap_tool(gap_tools_infra.research_cloud_enum, "fetch"))
    mcp.tool()(_wrap_tool(gap_tools_infra.research_github_secrets, "search"))
    mcp.tool()(_wrap_tool(gap_tools_infra.research_whois_correlator, "fetch"))
    mcp.tool()(_wrap_tool(gap_tools_infra.research_output_consistency, "fetch"))
    mcp.tool()(_wrap_tool(gap_tools_advanced.research_talent_migration, "fetch"))
    mcp.tool()(_wrap_tool(gap_tools_advanced.research_funding_pipeline, "search"))
    mcp.tool()(_wrap_tool(gap_tools_advanced.research_jailbreak_library))
    mcp.tool()(_wrap_tool(gap_tools_advanced.research_patent_embargo, "fetch"))
    # Academic research intelligence tools
    mcp.tool()(_wrap_tool(gap_tools_academic.research_ideological_drift))
    mcp.tool()(_wrap_tool(gap_tools_academic.research_author_clustering))
    mcp.tool()(_wrap_tool(gap_tools_academic.research_citation_cartography))

    # AI model intelligence tools
    mcp.tool()(_wrap_tool(gap_tools_ai.research_capability_mapper, "fetch"))
    mcp.tool()(_wrap_tool(gap_tools_ai.research_memorization_scanner, "fetch"))
    mcp.tool()(_wrap_tool(gap_tools_ai.research_training_contamination, "fetch"))
    mcp.tool()(_wrap_tool(infra_analysis.research_registry_graveyard, "fetch"))
    mcp.tool()(_wrap_tool(infra_analysis.research_subdomain_temporal, "fetch"))
    mcp.tool()(_wrap_tool(infra_analysis.research_commit_analyzer, "fetch"))
    mcp.tool()(_wrap_tool(onion_discover.research_onion_discover, "fetch"))
    mcp.tool()(_wrap_tool(metadata_forensics.research_metadata_forensics, "fetch"))
    mcp.tool()(_wrap_tool(antiforensics.research_usb_kill_monitor))
    mcp.tool()(_wrap_tool(antiforensics.research_artifact_cleanup))
    mcp.tool()(_wrap_tool(silk_guardian.research_silk_guardian_monitor))
    # Privacy advanced tools (7 tools: fingerprint audit, metadata strip, secure delete, MAC randomize, DNS leak check, Tor circuit, privacy score)
    mcp.tool()(_wrap_tool(privacy_advanced.research_browser_fingerprint_audit, "fetch"))
    mcp.tool()(_wrap_tool(privacy_advanced.research_metadata_strip, "fetch"))
    mcp.tool()(_wrap_tool(privacy_advanced.research_secure_delete))
    mcp.tool()(_wrap_tool(privacy_advanced.research_mac_randomize))
    mcp.tool()(_wrap_tool(privacy_advanced.research_dns_leak_check))
    mcp.tool()(_wrap_tool(privacy_advanced.research_tor_circuit_info))
    mcp.tool()(_wrap_tool(privacy_advanced.research_privacy_score, "fetch"))
    mcp.tool()(_wrap_tool(crypto_trace.research_crypto_trace, "fetch"))
    mcp.tool()(_wrap_tool(crypto_risk.research_crypto_risk_score))
    mcp.tool()(_wrap_tool(ethereum_tools.research_ethereum_tx_decode))
    mcp.tool()(_wrap_tool(ethereum_tools.research_defi_security_audit))
    mcp.tool()(_wrap_tool(stego_detect.research_stego_detect))
    mcp.tool()(_wrap_tool(stego_encoder.research_stego_encode))
    mcp.tool()(_wrap_tool(stego_encoder.research_stego_analyze))
    mcp.tool()(_wrap_tool(superposition_prompt.research_superposition_attack))
    mcp.tool()(_wrap_tool(strange_attractors.research_attractor_trap))
    mcp.tool()(_wrap_tool(threat_profile.research_threat_profile, "fetch"))
    mcp.tool()(_wrap_tool(traffic_capture.research_capture_har, "fetch"))
    mcp.tool()(_wrap_tool(traffic_capture.research_extract_cookies))
    # Threat intelligence tools (7 tools for dark market, ransomware, phishing, botnets, malware, domains, IOCs)
    mcp.tool()(_wrap_tool(threat_intel.research_dark_market_monitor))
    mcp.tool()(_wrap_tool(threat_intel.research_ransomware_tracker))
    mcp.tool()(_wrap_tool(threat_intel.research_phishing_mapper))
    mcp.tool()(_wrap_tool(threat_intel.research_botnet_tracker))
    mcp.tool()(_wrap_tool(threat_intel.research_malware_intel))
    mcp.tool()(_wrap_tool(threat_intel.research_domain_reputation))
    mcp.tool()(_wrap_tool(threat_intel.research_ioc_enrich))
    mcp.tool()(_wrap_tool(leak_scan.research_leak_scan, "fetch"))
    mcp.tool()(_wrap_tool(social_graph.research_social_graph, "fetch"))

    # Psychology & behavioral analysis tools
    mcp.tool()(_wrap_tool(stylometry.research_stylometry))  # CPU-only, no category
    mcp.tool()(_wrap_tool(deception_detect.research_deception_detect))  # CPU-only, no category

    # Company intelligence tools
    mcp.tool()(_wrap_tool(company_intel.research_company_diligence, "search"))
    mcp.tool()(_wrap_tool(company_intel.research_salary_intelligence, "search"))
    mcp.tool()(_wrap_tool(competitive_intel.research_competitive_intel, "search"))
    competitive_monitor,

    # Supply chain intelligence tools
    mcp.tool()(_wrap_tool(supply_chain_intel.research_supply_chain_risk, "fetch"))
    mcp.tool()(_wrap_tool(supply_chain_intel.research_patent_landscape, "search"))
    mcp.tool()(_wrap_tool(supply_chain_intel.research_dependency_audit, "fetch"))
    mcp.tool()(_wrap_tool(supply_chain.research_package_audit))
    mcp.tool()(_wrap_tool(supply_chain.research_model_integrity))

    # Domain intelligence tools
    mcp.tool()(_wrap_tool(domain_intel.research_whois, "fetch"))
    mcp.tool()(_wrap_tool(domain_intel.research_dns_lookup, "fetch"))
    mcp.tool()(_wrap_tool(domain_intel.research_nmap_scan, "fetch"))

    # Dark reconnaissance tools (TorBot and OWASP Amass integration)
    mcp.tool()(_wrap_tool(dark_recon.research_torbot, "fetch"))
    mcp.tool()(_wrap_tool(dark_recon.research_amass_enum, "fetch"))
    mcp.tool()(_wrap_tool(dark_recon.research_amass_intel, "fetch"))

    # Tool dependency graph analysis (2 tools)
    mcp.tool()(_wrap_tool(dependency_graph.research_tool_dependencies))
    mcp.tool()(_wrap_tool(dependency_graph.research_tool_impact))

    # Access and content authenticity tools (5 tools for legal monitoring, open access, and deepfake detection)
    mcp.tool()(_wrap_tool(access_tools.research_legal_takedown, "fetch"))
    mcp.tool()(_wrap_tool(access_tools.research_open_access))
    mcp.tool()(_wrap_tool(access_tools.research_content_authenticity, "fetch"))
    mcp.tool()(_wrap_tool(access_tools.research_credential_monitor, "fetch"))
    mcp.tool()(_wrap_tool(access_tools.research_deepfake_checker, "fetch"))
    # Identity resolution tool
    # Integration testing tools (2 tools for validating all 311 tool modules)
    mcp.tool()(_wrap_tool(integration_runner.research_integration_test))
    mcp.tool()(_wrap_tool(integration_runner.research_smoke_test))
    mcp.tool()(_wrap_tool(identity_resolve.research_identity_resolve, "fetch"))

    # Information warfare tools (5 tools for narrative tracking, bot detection, censorship)
    mcp.tool()(_wrap_tool(infowar_tools.research_narrative_tracker, "search"))
    mcp.tool()(_wrap_tool(infowar_tools.research_bot_detector, "search"))
    mcp.tool()(_wrap_tool(infowar_tools.research_censorship_detector, "fetch"))
    mcp.tool()(_wrap_tool(infowar_tools.research_deleted_social, "fetch"))
    mcp.tool()(_wrap_tool(infowar_tools.research_robots_archaeology, "fetch"))

    # Job market intelligence tools
    mcp.tool()(_wrap_tool(job_signals.research_funding_signal, "search"))
    mcp.tool()(_wrap_tool(job_signals.research_stealth_hire_scanner, "search"))
    mcp.tool()(_wrap_tool(job_signals.research_interviewer_profiler, "fetch"))

    # Security tools (cert analysis, headers, breach checking)
    mcp.tool()(_wrap_tool(cert_analyzer.research_cert_analyze, "fetch"))
    mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))

    # Sherlock username OSINT tools
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_lookup, "search"))
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_batch, "search"))

    # Signal detection tools
    mcp.tool()(_wrap_tool(signal_detection.research_ghost_protocol, "search"))
    mcp.tool()(_wrap_tool(signal_detection.research_temporal_anomaly, "fetch"))
    mcp.tool()(_wrap_tool(signal_detection.research_sec_tracker, "search"))
    mcp.tool()(_wrap_tool(breach_check.research_breach_check, "fetch"))
    mcp.tool()(_wrap_tool(breach_check.research_password_check))
    # Compliance Checker tools (2 tools for regulatory validation)
    mcp.tool()(_wrap_tool(compliance_checker.research_compliance_check))
    mcp.tool()(_wrap_tool(compliance_checker.research_pii_scan))

    # AI Safety red-team tools (5 tools for EU AI Act Article 15 compliance testing)
    mcp.tool()(_wrap_tool(ai_safety.research_prompt_injection_test, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_model_fingerprint, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_bias_probe, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety.research_safety_filter_map, "fetch"))
    mcp.tool(name="research_ai_compliance_check")(_wrap_tool(ai_safety.research_compliance_check, "fetch"))

    # Extended AI Safety tools (2 tools for advanced compliance testing)
    mcp.tool()(_wrap_tool(ai_safety_extended.research_hallucination_benchmark, "fetch"))
    mcp.tool()(_wrap_tool(ai_safety_extended.research_adversarial_robustness, "fetch"))

    # Model Safety Update Predictor (1 tool for defense evolution prediction)
    mcp.tool()(_wrap_tool(safety_predictor.research_predict_safety_update))
    
    # Safety Circuit Identification (2 tools for LLM safety analysis)
    mcp.tool()(_wrap_tool(safety_neurons.research_safety_circuit_map))
    mcp.tool()(_wrap_tool(safety_neurons.research_circuit_bypass_plan))

    # Logical Paradox Detector (2 tools for defensive EU AI Act compliance)
    mcp.tool()(_wrap_tool(paradox_detector.research_detect_paradox))
    mcp.tool()(_wrap_tool(paradox_detector.research_paradox_immunize))

    # Explainability Engine for jailbreak strategies (2 tools for root cause analysis)
    mcp.tool()(_wrap_tool(explainability.research_explain_bypass))
    mcp.tool()(_wrap_tool(explainability.research_vulnerability_map))


    # Thinking-phase injection tools for reasoning model exploitation (2 tools)
    mcp.tool()(_wrap_tool(thinking_injection.research_thinking_inject))
    mcp.tool()(_wrap_tool(thinking_injection.research_reasoning_exploit))
    # Defender Mode: Blue-team system prompt hardening (2 tools)
    mcp.tool()(_wrap_tool(defender_mode.research_defend_test))
    mcp.tool()(_wrap_tool(defender_mode.research_harden_prompt))
    # Proactive Adversarial Defense: Attack prediction and preemptive patching (2 tools)
    mcp.tool()(_wrap_tool(proactive_defense.research_predict_attacks))
    mcp.tool()(_wrap_tool(proactive_defense.research_preemptive_patch))
    # Embedding Collision Attack: RAG poisoning tools (2 tools)
    mcp.tool()(_wrap_tool(embedding_collision.research_embedding_collide))
    mcp.tool()(_wrap_tool(embedding_collision.research_rag_attack))
    mcp.tool()(_wrap_tool(adversarial_debate_tool.research_adversarial_debate, "llm"))
    # LLM behavioral fingerprinting tool (1 tool for personality vector analysis)
    # Ensemble Adversarial Training: Combine multiple strategies for robustness (2 tools)
    mcp.tool()(_wrap_tool(ensemble_attack.research_ensemble_attack))
    mcp.tool()(_wrap_tool(ensemble_attack.research_attack_portfolio))
    mcp.tool()(_wrap_tool(evidence_fusion.research_fuse_evidence))
    mcp.tool()(_wrap_tool(evidence_fusion.research_authority_stack))
    mcp.tool()(_wrap_tool(adversarial_craft.research_craft_adversarial))
    mcp.tool()(_wrap_tool(adversarial_craft.research_adversarial_batch))
    mcp.tool()(_wrap_tool(model_fingerprinter.research_fingerprint_behavior, "llm"))
    mcp.tool()(_wrap_tool(fingerprint_evasion.research_fingerprint_evasion_test))


    # Agent scenario benchmarking tool
    mcp.tool()(_wrap_tool(agent_benchmark.research_agent_benchmark))

    # Extended OSINT tools (2 tools for social engineering assessment)
    mcp.tool()(_wrap_tool(osint_extended.research_social_engineering_score, "fetch"))
    mcp.tool()(_wrap_tool(osint_extended.research_behavioral_fingerprint, "fetch"))

    # PDF extraction tools
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))

    # Advanced document parsing tools (OCR + PDF extraction with EasyOCR & PyMuPDF)
    with suppress(ImportError):
        mcp.tool()(_wrap_tool(doc_parser_tools.research_ocr_advanced, "fetch"))
        mcp.tool()(_wrap_tool(doc_parser_tools.research_pdf_advanced, "fetch"))
        mcp.tool()(_wrap_tool(doc_parser_tools.research_document_analyze, "fetch"))

    # Academic integrity tools
    mcp.tool()(_wrap_tool(academic_integrity.research_citation_analysis, "fetch"))
    mcp.tool()(_wrap_tool(academic_integrity.research_retraction_check, "fetch"))
    mcp.tool()(_wrap_tool(academic_integrity.research_predatory_journal_check, "fetch"))


    # arXiv research paper extraction pipeline
    mcp.tool()(_wrap_tool(arxiv_pipeline.research_arxiv_ingest, "search"))
    mcp.tool()(_wrap_tool(arxiv_pipeline.research_arxiv_extract_techniques, "search"))
    # HCS-10 academic research tools (8 tools for research integrity & anomaly detection)
    mcp.tool()(_wrap_tool(hcs10_academic.research_grant_forensics))
    mcp.tool()(_wrap_tool(hcs10_academic.research_monoculture_detect))
    mcp.tool()(_wrap_tool(hcs10_academic.research_review_cartel, "fetch"))
    mcp.tool()(_wrap_tool(hcs10_academic.research_data_fabrication))
    mcp.tool()(_wrap_tool(hcs10_academic.research_institutional_decay, "fetch"))
    mcp.tool()(_wrap_tool(hcs10_academic.research_shell_funding, "fetch"))
    mcp.tool()(_wrap_tool(hcs10_academic.research_conference_arbitrage, "fetch"))
    mcp.tool()(_wrap_tool(hcs10_academic.research_preprint_manipulation, "fetch"))

    # HCS (Helpfulness Compliance Score) scoring tool
    mcp.tool()(_wrap_tool(hcs_scorer.research_hcs_score, "analysis"))
    mcp.tool()(_wrap_tool(hcs_report.research_hcs_report, "analysis"))
    mcp.tool()(_wrap_tool(hcs_rubric_tool.research_hcs_rubric, "analysis"))
    mcp.tool()(_wrap_tool(hcs_escalation.research_hcs_escalate, "orchestration"))
    mcp.tool()(_wrap_tool(full_pipeline.research_full_pipeline, "orchestration"))

    # Creative research tools (4 tools for advanced research scenarios)
    mcp.tool()(_wrap_tool(darkweb_early_warning.research_darkweb_early_warning, "search"))
    mcp.tool()(_wrap_tool(deception_job_scanner.research_deception_job_scan))
    mcp.tool()(_wrap_tool(bias_lens.research_bias_lens, "fetch"))
    mcp.tool()(_wrap_tool(salary_synthesizer.research_salary_synthesize, "search"))

    # Real-time monitoring tools
    mcp.tool()(_wrap_tool(realtime_monitor.research_realtime_monitor, "fetch"))
    mcp.tool()(_wrap_tool(realtime_adapt.research_track_refusal))
    mcp.tool()(_wrap_tool(realtime_adapt.research_get_best_model))

    # NIGHTCRAWLER arXiv monitoring daemon
    mcp.tool()(_wrap_tool(nightcrawler.research_arxiv_scan, "search"))
    mcp.tool()(_wrap_tool(nightcrawler.research_nightcrawler_status))


    # Natural Language Tool Executor (1 tool)
    mcp.tool()(_wrap_tool(nl_executor.research_do))
    # RSS feed tools
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_fetch, "fetch"))
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_search, "search"))
    mcp.tool()(_wrap_tool(response_synthesizer.research_synthesize_report))

    # Social intelligence tools
    mcp.tool()(_wrap_tool(social_intel.research_social_search, "fetch"))
    mcp.tool()(_wrap_tool(social_intel.research_social_profile, "fetch"))

    # Social media and article extraction tools
    mcp.tool()(_wrap_tool(social_scraper.research_instagram, "fetch"))
    mcp.tool()(_wrap_tool(social_scraper.research_article_extract, "fetch"))
    mcp.tool()(_wrap_tool(social_scraper.research_article_batch, "fetch"))

    # Trend prediction and report generation tools
    mcp.tool()(_wrap_tool(trend_predictor.research_trend_predict, "search"))
    mcp.tool()(_wrap_tool(memetic_simulator.research_memetic_simulate))
    mcp.tool()(_wrap_tool(report_generator.research_generate_report, "search"))
    mcp.tool()(_wrap_tool(resilience_predictor.research_predict_resilience))
    mcp.tool()(_wrap_tool(lifetime_oracle.research_lifetime_predict))
    mcp.tool()(_wrap_tool(live_registry.research_registry_status))
    mcp.tool()(_wrap_tool(live_registry.research_registry_search))
    mcp.tool()(_wrap_tool(live_registry.research_registry_refresh))

    # Unique research tools (8 tools for propaganda, credibility, cascades, etc.)
    mcp.tool()(_wrap_tool(unique_tools.research_propaganda_detector))
    mcp.tool()(_wrap_tool(unique_tools.research_source_credibility, "fetch"))
    mcp.tool()(_wrap_tool(unique_tools.research_information_cascade, "search"))
    mcp.tool()(_wrap_tool(unique_tools.research_web_time_machine, "fetch"))
    mcp.tool()(_wrap_tool(unique_tools.research_influence_operation, "search"))
    mcp.tool()(_wrap_tool(unique_tools.research_dark_web_bridge, "search"))
    mcp.tool()(_wrap_tool(unique_tools.research_info_half_life, "fetch"))

    # Tool usage analytics (3 tools)
    mcp.tool()(_wrap_tool(usage_analytics.research_usage_record))
    mcp.tool()(_wrap_tool(usage_analytics.research_usage_report))
    mcp.tool()(_wrap_tool(usage_analytics.research_usage_trends))
    mcp.tool()(_wrap_tool(unique_tools.research_search_discrepancy, "search"))
    # Vision agent for screenshot and visual analysis
    mcp.tool()(_wrap_tool(vision_agent.research_vision_browse, "fetch"))
    mcp.tool()(_wrap_tool(vision_agent.research_vision_compare, "fetch"))
    # White Rabbit Path discovery tool
    mcp.tool()(_wrap_tool(white_rabbit.research_white_rabbit))

    # Webhook/Callback system for long-running tasks (3 tools)
    mcp.tool()(_wrap_tool(webhook_system.research_webhook_register))
    mcp.tool()(_wrap_tool(webhook_system.research_webhook_fire))
    mcp.tool()(_wrap_tool(webhook_system.research_webhook_list))

    # Cross-model transfer attack tools
    mcp.tool()(_wrap_tool(xover_attack.research_xover_transfer))
    mcp.tool()(_wrap_tool(xover_attack.research_xover_matrix))


    # Consensus and debate tools
    mcp.tool()(_wrap_tool(research_consensus_build))
    mcp.tool()(_wrap_tool(research_consensus_pressure))

    # Crescendo loop tool
    mcp.tool()(_wrap_tool(research_crescendo_loop))

    # Model profiling and benchmarking
    mcp.tool()(_wrap_tool(research_model_profile))
    mcp.tool()(_wrap_tool(research_benchmark_run))
    mcp.tool()(_wrap_tool(research_reid_pipeline))

    # Creative research tools (additional set)
    if "creative" in _optional_tools:
        creative_mod = _optional_tools["creative"]
        mcp.tool()(_wrap_tool(creative_mod.research_ai_detect))
        mcp.tool()(_wrap_tool(creative_mod.research_citation_graph))
        mcp.tool()(_wrap_tool(creative_mod.research_community_sentiment))
        mcp.tool()(_wrap_tool(creative_mod.research_curriculum))
        mcp.tool()(_wrap_tool(creative_mod.research_misinfo_check))
        mcp.tool()(_wrap_tool(creative_mod.research_multilingual))
        mcp.tool()(_wrap_tool(creative_mod.research_red_team))
        mcp.tool()(_wrap_tool(creative_mod.research_semantic_sitemap))
        mcp.tool()(_wrap_tool(creative_mod.research_temporal_diff))
        mcp.tool()(_wrap_tool(creative_mod.research_wiki_ghost))

    # Consistency pressure tools
    if "consistency_pressure" in _optional_tools:
        consistency_mod = _optional_tools["consistency_pressure"]
        mcp.tool()(_wrap_tool(consistency_mod.research_consistency_pressure))
        mcp.tool()(_wrap_tool(consistency_mod.research_consistency_pressure_history))
        mcp.tool()(_wrap_tool(consistency_mod.research_consistency_pressure_record))

    # Constraint optimizer tool
    if "constraint_optimizer" in _optional_tools:
        constraint_mod = _optional_tools["constraint_optimizer"]
        mcp.tool()(_wrap_tool(constraint_mod.research_constraint_optimize))

    # Parameter sweep tool
    if "param_sweep" in _optional_tools:
        param_mod = _optional_tools["param_sweep"]
        mcp.tool()(_wrap_tool(param_mod.research_parameter_sweep))

    # Semantic cache management tools
    if "semantic_cache_mgmt" in _optional_tools:
        cache_mod = _optional_tools["semantic_cache_mgmt"]
        mcp.tool()(_wrap_tool(cache_mod.research_semantic_cache_stats))
        mcp.tool()(_wrap_tool(cache_mod.research_semantic_cache_clear))

    # Semantic tool index (2 tools)
    mcp.tool()(_wrap_tool(semantic_index.research_semantic_search))
    mcp.tool()(_wrap_tool(semantic_index.research_semantic_rebuild))

    # Session tools
    mcp.tool()(_wrap_tool(research_session_open))
    mcp.tool()(_wrap_tool(research_session_list))
    mcp.tool()(_wrap_tool(research_session_close))
    mcp.tool()(_wrap_tool(session_replay.research_session_record))
    mcp.tool()(_wrap_tool(session_replay.research_session_replay))
    mcp.tool()(_wrap_tool(session_replay.research_session_list))

    # Task dependency resolver tools (2 tools)
    mcp.tool()(_wrap_tool(task_resolver.research_resolve_order))
    mcp.tool()(_wrap_tool(task_resolver.research_critical_path))

    # Tenant isolation tools (3 tools)
    mcp.tool()(_wrap_tool(tenant_isolation.research_tenant_create))
    mcp.tool()(_wrap_tool(tenant_isolation.research_tenant_list))
    mcp.tool()(_wrap_tool(tenant_isolation.research_tenant_usage))

    # MCP authentication tools
    if "mcp_auth" in _optional_tools:
        auth_mod = _optional_tools["mcp_auth"]
        mcp.tool()(_wrap_tool(auth_mod.research_auth_create_token))
        mcp.tool()(_wrap_tool(auth_mod.research_auth_validate))
        mcp.tool()(_wrap_tool(auth_mod.research_auth_revoke))

    # Config tools
    mcp.tool()(_wrap_tool(research_config_get))
    mcp.tool()(_wrap_tool(research_config_set))

    # Help system tools (2 tools)
    mcp.tool()(_wrap_tool(help_system.research_help))
    mcp.tool()(_wrap_tool(help_system.research_tools_list))

    # Auto-parameter generator tools (2 tools)
    mcp.tool()(_wrap_tool(auto_params.research_auto_params))
    mcp.tool()(_wrap_tool(auto_params.research_inspect_tool))

    # Audit export tool
    mcp.tool()(_wrap_tool(research_audit_export))

    # Pentest AI agents (32 specialized offensive security tools)
    try:
        from loom.tools.pentest import (
            research_pentest_agent,
            research_pentest_plan,
            research_pentest_recommend,
            research_pentest_docs,
            research_pentest_findings_db,
        )
        mcp.tool()(_wrap_tool(research_pentest_agent))
        mcp.tool()(_wrap_tool(research_pentest_plan))
        mcp.tool()(_wrap_tool(research_pentest_recommend))
        mcp.tool()(_wrap_tool(research_pentest_docs))
        mcp.tool()(_wrap_tool(research_pentest_findings_db))
        log.info("pentest_tools_registered count=5")
    except ImportError as exc:
        log.warning("pentest_tools_unavailable: %s", exc)

    # OSINT & Reconnaissance tools (maigret, theHarvester, spiderfoot, SingleFile)
    try:
        from loom.tools.maigret_backend import research_maigret
        mcp.tool()(_wrap_tool(research_maigret))
    except ImportError as exc:
        log.debug("maigret_unavailable: %s", exc)

    try:
        from loom.tools.harvester_backend import research_harvest
        mcp.tool()(_wrap_tool(research_harvest))
    except ImportError as exc:
        log.debug("harvester_unavailable: %s", exc)

    try:
        from loom.tools.spiderfoot_backend import research_spiderfoot_scan
        mcp.tool()(_wrap_tool(research_spiderfoot_scan))
    except ImportError as exc:
        log.debug("spiderfoot_unavailable: %s", exc)

    try:
        from loom.tools.singlefile_backend import research_archive_page
        mcp.tool()(_wrap_tool(research_archive_page))
    except ImportError as exc:
        log.debug("singlefile_unavailable: %s", exc)

    # Social & OSINT analysis tools
    try:
        from loom.tools.social_analyzer_backend import research_social_analyze
        mcp.tool()(_wrap_tool(research_social_analyze))
    except ImportError as exc:
        log.debug("social_analyzer_unavailable: %s", exc)

    # Malware & Threat Intelligence tools
    try:
        from loom.tools.yara_backend import research_yara_scan
        mcp.tool()(_wrap_tool(research_yara_scan))
    except ImportError as exc:
        log.debug("yara_unavailable: %s", exc)

    try:
        from loom.tools.misp_backend import research_misp_lookup
        mcp.tool()(_wrap_tool(research_misp_lookup))
    except ImportError as exc:
        log.debug("misp_unavailable: %s", exc)

    # Research agent tools (gpt-researcher, DocsGPT, deer-flow)
    try:
        from loom.tools.gpt_researcher_backend import research_gpt_researcher
        mcp.tool()(_wrap_tool(research_gpt_researcher))
    except ImportError as exc:
        log.debug("gpt_researcher_unavailable: %s", exc)

    try:
        from loom.tools.docsgpt_backend import research_docs_ai
        mcp.tool()(_wrap_tool(research_docs_ai))
    except ImportError as exc:
        log.debug("docsgpt_unavailable: %s", exc)

    try:
        from loom.tools.deerflow_backend import research_deer_flow
        mcp.tool()(_wrap_tool(research_deer_flow))
    except ImportError as exc:
        log.debug("deerflow_unavailable: %s", exc)

    log.info("integration_tools_registered count=10 (maigret,harvester,spiderfoot,singlefile,social_analyzer,yara,misp,gpt_researcher,docsgpt,deerflow)")

    # New integrations (web-check, Shodan, Photon, h8mail, Censys, unstructured, instructor)
    try:
        from loom.tools.webcheck_backend import research_web_check
        mcp.tool()(_wrap_tool(research_web_check))
    except ImportError as exc:
        log.debug("webcheck_unavailable: %s", exc)

    try:
        from loom.tools.shodan_backend import research_shodan_host, research_shodan_search
        mcp.tool()(_wrap_tool(research_shodan_host))
        mcp.tool()(_wrap_tool(research_shodan_search))
    except ImportError as exc:
        log.debug("shodan_unavailable: %s", exc)

    try:
        from loom.tools.photon_backend import research_photon_crawl
        mcp.tool()(_wrap_tool(research_photon_crawl))
    except ImportError as exc:
        log.debug("photon_unavailable: %s", exc)

    try:
        from loom.tools.h8mail_backend import research_email_breach
        mcp.tool()(_wrap_tool(research_email_breach))
    except ImportError as exc:
        log.debug("h8mail_unavailable: %s", exc)

    try:
        from loom.tools.censys_backend import research_censys_host, research_censys_search
        mcp.tool()(_wrap_tool(research_censys_host))
        mcp.tool()(_wrap_tool(research_censys_search))
    except ImportError as exc:
        log.debug("censys_unavailable: %s", exc)

    try:
        from loom.tools.unstructured_backend import research_document_extract
        mcp.tool()(_wrap_tool(research_document_extract))
    except ImportError as exc:
        log.debug("unstructured_unavailable: %s", exc)

    try:
        from loom.tools.instructor_backend import research_structured_extract
        mcp.tool()(_wrap_tool(research_structured_extract))
    except ImportError as exc:
        log.debug("instructor_unavailable: %s", exc)

    # Pydantic AI agent framework (type-safe structured outputs)
    try:
        from loom.tools.pydantic_ai_backend import (
            research_pydantic_agent,
            research_structured_llm,
        )
        mcp.tool()(_wrap_tool(research_pydantic_agent, "llm"))
        mcp.tool()(_wrap_tool(research_structured_llm, "llm"))
    except ImportError as exc:
        log.debug("pydantic_ai_unavailable: %s", exc)

    # Query builder (DSPy-powered intent extraction + query optimization)
    try:
        from loom.tools.query_builder import research_build_query
        mcp.tool()(_wrap_tool(research_build_query))
    except ImportError as exc:
        log.debug("query_builder_unavailable: %s", exc)

    # Threat intelligence (opencti, IntelOwl, deepdarkCTI)
    try:
        from loom.tools.opencti_backend import research_opencti_query
        mcp.tool()(_wrap_tool(research_opencti_query))
    except ImportError as exc:
        log.debug("opencti_unavailable: %s", exc)
    try:
        from loom.tools.intelowl_backend import research_intelowl_analyze
        mcp.tool()(_wrap_tool(research_intelowl_analyze))
    except ImportError as exc:
        log.debug("intelowl_unavailable: %s", exc)
    try:
        from loom.tools.deepdarkcti_backend import research_dark_cti
        mcp.tool()(_wrap_tool(research_dark_cti))
    except ImportError as exc:
        log.debug("deepdarkcti_unavailable: %s", exc)

    # Social media OSINT (Telegram, LinkedIn, Discord)
    try:
        from loom.tools.telegram_osint import research_telegram_intel
        mcp.tool()(_wrap_tool(research_telegram_intel))
    except ImportError as exc:
        log.debug("telegram_unavailable: %s", exc)
    try:
        from loom.tools.linkedin_osint import research_linkedin_intel
        mcp.tool()(_wrap_tool(research_linkedin_intel))
    except ImportError as exc:
        log.debug("linkedin_unavailable: %s", exc)
    try:
        from loom.tools.discord_osint import research_discord_intel
        mcp.tool()(_wrap_tool(research_discord_intel))
    except ImportError as exc:
        log.debug("discord_unavailable: %s", exc)

    # Reconnaissance (Recon-ng, massdns, EagleEye, robin, OnionScan, testssl, Masscan)
    try:
        from loom.tools.reconng_backend import research_reconng_scan
        mcp.tool()(_wrap_tool(research_reconng_scan))
    except ImportError as exc:
        log.debug("reconng_unavailable: %s", exc)
    try:
        from loom.tools.massdns_backend import research_massdns_resolve
        mcp.tool()(_wrap_tool(research_massdns_resolve))
    except ImportError as exc:
        log.debug("massdns_unavailable: %s", exc)
    try:
        from loom.tools.eagleeye_backend import research_reverse_image
        mcp.tool()(_wrap_tool(research_reverse_image))
    except ImportError as exc:
        log.debug("eagleeye_unavailable: %s", exc)
    try:
        from loom.tools.robin_backend import research_robin_scan
        mcp.tool()(_wrap_tool(research_robin_scan))
    except ImportError as exc:
        log.debug("robin_unavailable: %s", exc)
    try:
        from loom.tools.onionscan_backend import research_onionscan
        mcp.tool()(_wrap_tool(research_onionscan))
    except ImportError as exc:
        log.debug("onionscan_unavailable: %s", exc)
    try:
        from loom.tools.testssl_backend import research_testssl
        mcp.tool()(_wrap_tool(research_testssl))
    except ImportError as exc:
        log.debug("testssl_unavailable: %s", exc)
    try:
        from loom.tools.masscan_backend import research_masscan
        mcp.tool()(_wrap_tool(research_masscan))
    except ImportError as exc:
        log.debug("masscan_unavailable: %s", exc)

    # Data extraction (PaddleOCR, camelot, Scapy)
    try:
        from loom.tools.paddleocr_backend import research_paddle_ocr
        mcp.tool()(_wrap_tool(research_paddle_ocr))
    except ImportError as exc:
        log.debug("paddleocr_unavailable: %s", exc)
    try:
        from loom.tools.camelot_backend import research_table_extract
        mcp.tool()(_wrap_tool(research_table_extract))
    except ImportError as exc:
        log.debug("camelot_unavailable: %s", exc)
    try:
        from loom.tools.scapy_backend import research_packet_craft
        mcp.tool()(_wrap_tool(research_packet_craft))
    except ImportError as exc:
        log.debug("scapy_unavailable: %s", exc)

    # Privacy research (FingerprintJS, supercookie)
    try:
        from loom.tools.fingerprint_backend import research_browser_fingerprint
        mcp.tool()(_wrap_tool(research_browser_fingerprint))
    except ImportError as exc:
        log.debug("fingerprint_unavailable: %s", exc)
    try:
        from loom.tools.supercookie_backend import research_supercookie_check
        mcp.tool()(_wrap_tool(research_supercookie_check))
    except ImportError as exc:
        log.debug("supercookie_unavailable: %s", exc)
    try:
        from loom.tools.lightpanda_backend import research_lightpanda_fetch, research_lightpanda_batch
        mcp.tool()(_wrap_tool(research_lightpanda_fetch, "fetch"))
        mcp.tool()(_wrap_tool(research_lightpanda_batch, "fetch"))
    except ImportError as exc:
        log.debug("lightpanda_unavailable: %s", exc)

    try:
        from loom.tools.creepjs_backend import research_creepjs_audit
        mcp.tool()(_wrap_tool(research_creepjs_audit))
    except ImportError as exc:
        log.debug("creepjs_unavailable: %s", exc)

    try:
        from loom.tools.hipporag_backend import research_memory_store, research_memory_recall
        mcp.tool()(_wrap_tool(research_memory_store))
        mcp.tool()(_wrap_tool(research_memory_recall))
    except ImportError as exc:
        log.debug("hipporag_unavailable: %s", exc)


    log.info("new_integrations_registered count=9 (webcheck,shodan_host,shodan_search,photon,h8mail,censys_host,censys_search,unstructured,instructor)")
    log.info("additional_integrations_registered count=18 (query_builder,opencti,intelowl,deepdarkcti,telegram,linkedin,discord,reconng,massdns,eagleeye,robin,onionscan,testssl,masscan,paddleocr,camelot,scapy,fingerprint,supercookie)")

    # Arabic language support
    try:
        from loom.arabic import detect_arabic, route_by_language

        async def research_detect_arabic(text: str) -> dict:
            """Detect if text contains Arabic and suggest provider routing."""
            is_arabic = detect_arabic(text)
            from loom.config import CONFIG
            cascade = CONFIG.get("LLM_CASCADE_ORDER", [])
            routed = route_by_language(text, cascade)
            return {"is_arabic": is_arabic, "recommended_cascade": routed}

        mcp.tool()(_wrap_tool(research_detect_arabic))
    except ImportError:
        pass

    # Storage monitoring
    try:
        from loom.storage import get_storage_stats, check_storage_alerts

        async def research_storage_dashboard(base_dir: str = "") -> dict:
            """Get storage usage stats and alerts."""
            from pathlib import Path
            path = Path(base_dir) if base_dir else Path.home() / ".cache" / "loom"
            stats = get_storage_stats(path)
            alerts = check_storage_alerts(path)
            return {"stats": stats, "alerts": alerts}

        mcp.tool()(_wrap_tool(research_storage_dashboard))
    except ImportError:
        pass

    # Health check
    mcp.tool()(_wrap_tool(research_health_check))
    mcp.tool()(_wrap_tool(research_coverage_run))
    mcp.tool()(_wrap_tool(research_dashboard))

    # API versioning and metadata
    mcp.tool()(_wrap_tool(api_version.research_api_version))
    mcp.tool()(_wrap_tool(api_version.research_api_changelog))
    mcp.tool()(_wrap_tool(api_version.research_api_deprecations))

    # Orchestration engine
    mcp.tool()(_wrap_tool(research_orchestrate))

    # Parallel execution engine
    mcp.tool()(_wrap_tool(parallel_executor.research_parallel_execute))
    mcp.tool()(_wrap_tool(parallel_executor.research_parallel_plan_and_execute))

    # Red-team scoring framework
    mcp.tool()(_wrap_tool(research_score_all))
    mcp.tool()(_wrap_tool(research_full_spectrum))
    mcp.tool()(_wrap_tool(research_unified_score, "analysis"))

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
            mcp.tool(name="research_billing_report")(_wrap_tool(billing_mod.research_usage_report))
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

    # Epistemic confidence scoring tool
    if "epistemic_score" in _optional_tools:
        epistemic_mod = _optional_tools["epistemic_score"]
        if hasattr(epistemic_mod, "research_epistemic_score"):
            mcp.tool()(_wrap_tool(epistemic_mod.research_epistemic_score, "analysis"))

    # Screenshot tool (if playwright available)
    if "screenshot" in _optional_tools:
        screenshot_mod = _optional_tools["screenshot"]
        if hasattr(screenshot_mod, "research_screenshot"):
            mcp.tool()(_wrap_tool(screenshot_mod.research_screenshot, "fetch"))

    # yt-dlp backend tools (if yt-dlp available)
    if "ytdlp_backend" in _optional_tools:
        ytdlp_mod = _optional_tools["ytdlp_backend"]
        if hasattr(ytdlp_mod, "research_video_download"):
            mcp.tool()(_wrap_tool(ytdlp_mod.research_video_download, "fetch"))
        if hasattr(ytdlp_mod, "research_video_info"):
            mcp.tool()(_wrap_tool(ytdlp_mod.research_video_info, "fetch"))
        if hasattr(ytdlp_mod, "research_audio_extract"):
            mcp.tool()(_wrap_tool(ytdlp_mod.research_audio_extract, "fetch"))

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

    # Nodriver undetected browser backend (3 tools)
    if "nodriver" in _optional_tools:
        nodriver_mod = _optional_tools["nodriver"]
        if hasattr(nodriver_mod, "research_nodriver_fetch"):
            mcp.tool()(_wrap_tool(nodriver_mod.research_nodriver_fetch, "fetch"))
        if hasattr(nodriver_mod, "research_nodriver_extract"):
            mcp.tool()(_wrap_tool(nodriver_mod.research_nodriver_extract, "fetch"))
        if hasattr(nodriver_mod, "research_nodriver_session"):
            mcp.tool()(_wrap_tool(nodriver_mod.research_nodriver_session, "fetch"))

    # P3 research tools (4 tools for model comparison, data poisoning detection, Wiki event correlation, and FOIA tracking)
    mcp.tool()(_wrap_tool(p3_tools.research_model_comparator, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_data_poisoning, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_wiki_event_correlator, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_foia_tracker, "search"))

    # Previously missing registrations (found by Gemini audit)
    mcp.tool()(_wrap_tool(change_monitor.research_change_monitor, "fetch"))
    mcp.tool()(_wrap_tool(knowledge_injector.research_personalize_output))
    mcp.tool()(_wrap_tool(knowledge_injector.research_adapt_complexity))
    mcp.tool()(_wrap_tool(knowledge_graph.research_knowledge_graph, "search"))
    mcp.tool()(_wrap_tool(knowledge_base.research_kb_store))
    mcp.tool()(_wrap_tool(knowledge_base.research_kb_search))
    mcp.tool()(_wrap_tool(knowledge_base.research_kb_stats))
    mcp.tool()(_wrap_tool(graph_scraper.research_graph_scrape, "fetch"))
    mcp.tool()(_wrap_tool(graph_scraper.research_knowledge_extract, "search"))
    mcp.tool()(_wrap_tool(graph_scraper.research_multi_page_graph, "fetch"))
    mcp.tool()(_wrap_tool(graph_analysis.research_graph_analyze))
    mcp.tool()(_wrap_tool(graph_analysis.research_transaction_graph))

    mcp.tool()(_wrap_tool(neo4j_backend.research_graph_store))
    mcp.tool()(_wrap_tool(neo4j_backend.research_graph_query))
    mcp.tool()(_wrap_tool(neo4j_backend.research_graph_visualize))
    mcp.tool()(_wrap_tool(persistent_memory.research_remember))
    mcp.tool()(_wrap_tool(persistent_memory.research_recall))
    mcp.tool()(_wrap_tool(persistent_memory.research_memory_stats))
    mcp.tool()(_wrap_tool(fact_checker.research_fact_check, "search"))
    mcp.tool()(_wrap_tool(culture_dna.research_culture_dna, "search"))
    mcp.tool()(_wrap_tool(cultural_attacks.research_cultural_reframe))
    mcp.tool()(_wrap_tool(cultural_attacks.research_multilingual_attack))
    mcp.tool()(_wrap_tool(synthetic_data.research_generate_redteam_dataset))
    mcp.tool()(_wrap_tool(synthetic_data.research_augment_dataset))
    mcp.tool()(_wrap_tool(synth_echo.research_synth_echo, "fetch"))
    mcp.tool()(_wrap_tool(psycholinguistic.research_psycholinguistic))

    # Multi-language confusion attacks (3 tools)
    mcp.tool()(_wrap_tool(multilang_attack.research_code_switch_attack))
    mcp.tool()(_wrap_tool(multilang_attack.research_script_confusion))
    mcp.tool()(_wrap_tool(multilang_attack.research_token_split_attack))

    # Prompt danger pre-analysis
    mcp.tool()(_wrap_tool(prompt_analyzer.research_prompt_analyze))

    # Prompt reframing tools (auto-bypass LLM refusals for authorized research)
    mcp.tool()(_wrap_tool(prompt_reframe.research_prompt_reframe))
    mcp.tool()(_wrap_tool(prompt_reframe.research_auto_reframe, "llm"))
    mcp.tool()(_wrap_tool(prompt_reframe.research_refusal_detector))
    mcp.tool()(_wrap_tool(prompt_reframe.research_stack_reframe))
    mcp.tool()(_wrap_tool(prompt_reframe.research_crescendo_chain))
    mcp.tool()(_wrap_tool(prompt_reframe.research_model_vulnerability_profile))
    mcp.tool()(_wrap_tool(prompt_reframe.research_format_smuggle))
    mcp.tool()(_wrap_tool(prompt_reframe.research_fingerprint_model))
    mcp.tool()(_wrap_tool(prompt_reframe.research_adaptive_reframe))

    # Category theoretic functor mapping (exploit translation across domains)
    mcp.tool()(_wrap_tool(functor_map.research_functor_translate))

    # Multi-LLM query (ask all available providers simultaneously)
    from loom.tools import ask_all_models, multi_llm
    mcp.tool()(_wrap_tool(multi_llm.research_ask_all_llms, "llm"))
    mcp.tool()(_wrap_tool(ask_all_models.research_ask_all_models, "llm"))

    # ── v3 gap fix: register all previously unregistered modules ──

    if "attack_scorer" in _optional_tools:
        mod = _optional_tools["attack_scorer"]
        if hasattr(mod, "research_attack_score"):
            mcp.tool()(_wrap_tool(mod.research_attack_score))

    if "stealth_score" in _optional_tools:
        mod = _optional_tools["stealth_score"]
        if hasattr(mod, "research_stealth_score"):
            mcp.tool()(_wrap_tool(mod.research_stealth_score))

    if "potency_meter" in _optional_tools:
        mod = _optional_tools["potency_meter"]
        if hasattr(mod, "research_potency_score"):
            mcp.tool()(_wrap_tool(mod.research_potency_score))

    if "model_sentiment" in _optional_tools:
        mod = _optional_tools["model_sentiment"]
        if hasattr(mod, "research_model_sentiment"):
            mcp.tool()(_wrap_tool(mod.research_model_sentiment))

    if "toxicity" in _optional_tools:
        mod = _optional_tools["toxicity"]
        if hasattr(mod, "research_toxicity_check"):
            mcp.tool()(_wrap_tool(mod.research_toxicity_check))

    if "drift" in _optional_tools:
        mod = _optional_tools["drift"]
        if hasattr(mod, "research_drift_monitor"):
            mcp.tool()(_wrap_tool(mod.research_drift_monitor))
        if hasattr(mod, "research_drift_monitor_list"):
            mcp.tool()(_wrap_tool(mod.research_drift_monitor_list))

    if "bpj" in _optional_tools:
        mod = _optional_tools["bpj"]
        if hasattr(mod, "research_bpj_generate"):
            mcp.tool()(_wrap_tool(mod.research_bpj_generate))

    if "daisy_chain" in _optional_tools:
        mod = _optional_tools["daisy_chain"]
        if hasattr(mod, "research_daisy_chain"):
            mcp.tool()(_wrap_tool(mod.research_daisy_chain))

    # Jailbreak evolution detailed tools (stats already registered above via jailbreak_evolution key)
    if "jailbreak_evo" in _optional_tools:
        mod = _optional_tools["jailbreak_evo"]
        for fn_name in ["research_jailbreak_evolution_stats",
                        "research_jailbreak_evolution_record", "research_jailbreak_evolution_get",
                        "research_jailbreak_evolution_timeline", "research_jailbreak_evolution_patches",
                        "research_jailbreak_evolution_adapt"]:
            if hasattr(mod, fn_name):
                mcp.tool()(_wrap_tool(getattr(mod, fn_name)))

    if "strategy_oracle" in _optional_tools:
        mod = _optional_tools["strategy_oracle"]
        if hasattr(mod, "research_strategy_oracle"):
            mcp.tool()(_wrap_tool(mod.research_strategy_oracle))

    if "stealth_detect" in _optional_tools:
        mod = _optional_tools["stealth_detect"]
        if hasattr(mod, "research_stealth_detect"):
            mcp.tool()(_wrap_tool(mod.research_stealth_detect))

    if "recommender" in _optional_tools:
        mod = _optional_tools["recommender"]
        if hasattr(mod, "research_recommend_tools"):
            mcp.tool()(_wrap_tool(mod.research_recommend_tools))

    # Direct function registrations
    if "danger_prescore" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["danger_prescore"]))
    if "quality_scorer" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["quality_scorer"]))
    if "evidence_pipeline" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["evidence_pipeline"], "llm"))
    if "context_poison" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["context_poison"]))
    if "adversarial_debate" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["adversarial_debate"], "llm"))
    if "model_evidence" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["model_evidence"], "llm"))
    if "target_orchestrate" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["target_orchestrate"]))
    if "reid_auto" in _optional_tools:
        async def research_reid_auto(
            query: str,
            model_name: str = "auto",
            max_turns: int = 15,
            context: str = "EU AI Act Article 15 compliance testing",
            dry_run: bool = True,
        ) -> dict[str, Any]:
            """Execute automated Reid 9-step interrogation with adaptive reframing.

            Runs the full Reid interrogation sequence against the specified model
            using Loom's LLM cascade for model interaction.

            Args:
                query: The research query to investigate.
                model_name: Target model name or "auto" for cascade.
                max_turns: Maximum conversation turns (safety limit).
                context: Research context for theme development.
                dry_run: If True, simulate without calling real model.
            """
            ReidAutoReframe = _optional_tools["reid_auto"]
            reframer = ReidAutoReframe(verbose=False)

            if dry_run:
                async def mock_fn(prompt: str) -> str:
                    return f"[Simulated response from {model_name}]"
                model_fn = mock_fn
            else:
                from loom.tools.llm import _get_provider
                provider = await _get_provider(model_name if model_name != "auto" else None)
                async def llm_fn(prompt: str) -> str:
                    resp = await provider.chat([{"role": "user", "content": prompt}])
                    return resp.text if resp else ""
                model_fn = llm_fn

            result = await reframer.run(
                query=query,
                model_fn=model_fn,
                model_name=model_name,
                max_turns=max_turns,
                context=context,
            )
            return {
                "success": result.success,
                "steps_taken": [
                    {
                        "step_index": s.step_index,
                        "step_name": s.step_name,
                        "response_length": s.response_length,
                        "classification": s.classification.value,
                        "turn_number": s.turn_number,
                    }
                    for s in result.steps_taken
                ],
                "final_response": result.final_response,
                "hcs_score": result.hcs_score,
                "total_turns": result.total_turns,
                "step_at_compliance": result.step_at_compliance,
                "model_name": result.model_name,
                "query": result.query,
            }

        mcp.tool()(_wrap_tool(research_reid_auto, "llm"))
    if "mcp_security" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["mcp_security"]))
    if "cicd" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["cicd"]))
    if "stealth_detector" in _optional_tools:
        mcp.tool()(_wrap_tool(_optional_tools["stealth_detector"]))

    # Tool Catalog and Knowledge Graph (4 tools)
    mcp.tool()(_wrap_tool(tool_catalog.research_tool_catalog))
    mcp.tool()(_wrap_tool(tool_catalog.research_tool_graph))
    mcp.tool()(_wrap_tool(tool_catalog.research_tool_pipeline))
    # Tool Tags & Organization (3 tools)
    mcp.tool()(_wrap_tool(tool_tags.research_tag_tool))
    mcp.tool()(_wrap_tool(tool_tags.research_tag_search))
    mcp.tool()(_wrap_tool(tool_tags.research_tag_cloud))
    # Tool Versioning (3 tools)
    mcp.tool()(_wrap_tool(tool_versioning.research_tool_version))
    mcp.tool()(_wrap_tool(tool_versioning.research_version_diff))
    mcp.tool()(_wrap_tool(tool_versioning.research_version_snapshot))
    # Tool Recommender v2 (2 tools)
    mcp.tool()(_wrap_tool(tool_recommender_v2.research_recommend_next))
    mcp.tool()(_wrap_tool(tool_recommender_v2.research_suggest_workflow))
    mcp.tool()(_wrap_tool(tool_catalog.research_tool_standalone))

    # Doc parser (multiple functions)
    if "doc_parser" in _optional_tools:
        dp = _optional_tools["doc_parser"]
        if isinstance(dp, dict):
            for fn in dp.values():
                mcp.tool()(_wrap_tool(fn, "fetch"))
    # Multi-model consensus tool (LLM analysis)
    if "model_consensus" in _optional_tools:
        mod = _optional_tools["model_consensus"]
        if hasattr(mod, "research_multi_consensus"):
            mcp.tool()(_wrap_tool(mod.research_multi_consensus, "llm"))



    # Auto-documentation tools (2 tools)

    # Research Journal tools (3 tools)
    mcp.tool()(_wrap_tool(research_journal.research_journal_add))
    mcp.tool()(_wrap_tool(research_journal.research_journal_search))
    mcp.tool()(_wrap_tool(research_journal.research_journal_timeline))
    mcp.tool()(_wrap_tool(auto_docs.research_generate_docs))
    mcp.tool()(_wrap_tool(auto_docs.research_docs_coverage))
    # Tool Execution Planner (2 tools)
    mcp.tool()(_wrap_tool(execution_planner.research_plan_execution))
    mcp.tool()(_wrap_tool(execution_planner.research_plan_validate))

    # Schema migration tools (3 tools)
    mcp.tool()(_wrap_tool(schema_migrate.research_migrate_status))
    mcp.tool()(_wrap_tool(schema_migrate.research_migrate_run))
    mcp.tool()(_wrap_tool(schema_migrate.research_migrate_backup))

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
        log.critical("SECURITY WARNING: LOOM_API_KEY not set. Server accepts anonymous connections. Set LOOM_API_KEY for production.")

    mcp = FastMCP(
        stateless_http=True,
        name="loom",
        host=host,
        port=port,
        auth=auth,
        token_verifier=token_verifier,
    )

    # Register custom HTTP endpoints (health check, root)
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    @mcp.custom_route("/", methods=["GET"])
    async def root_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({
            "service": "loom",
            "version": "3.0.0",
            "description": "Loom MCP Research Server — 303 tools, 957 strategies",
            "mcp_endpoint": "/mcp",
            "health_endpoint": "/health",
            "status": "running",
        })

    @mcp.custom_route("/health", methods=["GET"])
    async def health_endpoint(request: Request) -> JSONResponse:
        uptime = int(time.time() - _start_time)
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 346
        return JSONResponse({
            "status": "healthy",
            "uptime_seconds": uptime,
            "tool_count": tool_count,
            "strategy_count": 957,
            "timestamp": datetime.now(UTC).isoformat(),
        })

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

async def research_coverage_run(
    tools_to_test: list[str] | None = None,
    timeout: float = 30.0,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Run comprehensive test coverage across all 227+ MCP tools.

    Executes each tool with minimal valid parameters and reports
    coverage statistics, success rates, and failures.

    Args:
        tools_to_test: Specific tools to test. If None, tests all.
        timeout: Timeout per tool in seconds (1-300)
        dry_run: If True, skip network-required tools

    Returns:
        Dict with coverage statistics, per-tool results, and markdown report.
        Keys:
        - total_tools: Total tools in coverage suite
        - tools_tested: Tools actually tested
        - tools_passed: Successful tools
        - tools_failed: Failed tools
        - tools_skipped: Skipped tools
        - coverage_pct: Coverage percentage
        - total_elapsed_ms: Total execution time
        - per_tool_results: List of per-tool result dicts
        - report_markdown: Formatted markdown report
    """
    from loom.test_runner import ToolCoverageRunner

    runner = ToolCoverageRunner(mcp_app=None, dry_run=dry_run)
    results = await runner.run_coverage(
        tools_to_test=tools_to_test,
        timeout=timeout,
    )
    
    # Add markdown report to results
    results["report_markdown"] = runner.generate_coverage_report(results)
    
    return results
