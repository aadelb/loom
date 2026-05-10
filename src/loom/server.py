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
from starlette.middleware.cors import CORSMiddleware

from starlette.websockets import WebSocket
from loom.websocket import get_ws_manager, WebSocketManager

from loom.config import load_config, research_config_get, research_config_set
from loom.feature_flags import research_feature_flags, get_feature_flags
from loom.orchestrator import research_orchestrate
from loom.audit import export_audit, log_invocation
from loom.backup_manager import (
    research_backup_create,
    research_backup_restore,
    research_backup_list,
    research_backup_cleanup,
)
from loom.alerting import handle_tool_error
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

from loom.batch_queue import (
    research_batch_submit,
    research_batch_status,
    research_batch_list,
    start_batch_queue_background,
    stop_batch_queue_background,
)

from loom.scheduler import (
    get_scheduler,
    register_default_tasks,
)

from loom.api_auth import ApiKeyAuthMiddleware
from loom.request_id_middleware import RequestIdMiddleware

from loom.tracing import install_tracing, new_request_id
from loom.versioning import (
    get_version_info,
    is_version_supported,
    DEFAULT_VERSION,
)
from loom.billing.meter import record_usage
from loom.billing.token_economy import get_tool_cost, check_balance, deduct_credits
from loom.analytics import ToolAnalytics, research_analytics_dashboard

log = logging.getLogger("loom.server")
from loom.registrations.tracking import record_optional_module_loaded, record_import_failure
from loom.secret_manager import get_secret_manager, research_secret_health
from loom.tools.quota_status import research_quota_status
from loom.tools.sla_status import research_sla_status
from loom.startup_validator import (
    validate_all_tools,
    validate_registrations,
    research_validate_startup,
)
from loom.tool_latency import get_latency_tracker
from loom.tools.latency_report import research_latency_report
from loom.tool_rate_limiter import check_tool_rate_limit, research_rate_limits
from loom.tools.scheduler_status import research_scheduler_status
from loom.sla_monitor import get_sla_monitor

# ── Extracted modules (wired in) ──
from loom.middleware import _wrap_tool, _fuzzy_correct_params, _normalize_result  # noqa: E402
from loom.shutdown import _shutdown, _handle_signal  # noqa: E402
from loom.routes import register_http_routes  # noqa: E402
from loom.tool_functions import (  # noqa: E402
    _get_strategy_count,
    _check_llm_provider_available,
    _check_search_provider_available,
    research_health_check,
    research_cpu_pool_status,
    research_cpu_executor_shutdown,
    research_coverage_run,
)

# ── Prometheus metrics (optional, graceful fallback if not installed) ──
try:
    from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest

    # Create a registry for Loom metrics
    _PROMETHEUS_REGISTRY = CollectorRegistry()

    # Define metrics
    _loom_tool_calls_total = Counter(
        "loom_tool_calls_total",
        "Total MCP tool calls",
        labelnames=["tool_name", "status"],
        registry=_PROMETHEUS_REGISTRY,
    )

    _loom_tool_duration_seconds = Histogram(
        "loom_tool_duration_seconds",
        "Tool execution duration in seconds",
        labelnames=["tool_name"],
        registry=_PROMETHEUS_REGISTRY,
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
    )

    _loom_tool_errors_total = Counter(
        "loom_tool_errors_total",
        "Total MCP tool errors by type",
        labelnames=["tool_name", "error_type"],
        registry=_PROMETHEUS_REGISTRY,
    )

    _prometheus_enabled = True

except ImportError:
    # Stub classes for when prometheus_client is not installed
    _prometheus_enabled = False
    _PROMETHEUS_REGISTRY = None

    class _StubCounter:
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            pass

    class _StubHistogram:
        def labels(self, **kwargs):
            return self
        def observe(self, value):
            pass

    _loom_tool_calls_total = _StubCounter()
    _loom_tool_duration_seconds = _StubHistogram()
    _loom_tool_errors_total = _StubCounter()


# PostgreSQL migration tools (optional, graceful fallback if asyncpg not installed)
_pg_tools: dict[str, Any] = {}
with suppress(ImportError):
    from loom.pg_store import research_pg_migrate, research_pg_status
    _pg_tools["pg_migrate"] = research_pg_migrate
    _pg_tools["pg_status"] = research_pg_status
    record_optional_module_loaded("pg_store")



# Dynamically import optional tool modules (LLM tools, etc.)
_optional_tools: dict[str, Any] = {}
with suppress(ImportError):
    from loom.tools import llm as llm_tools

    _optional_tools["llm"] = llm_tools
    record_optional_module_loaded("llm")

with suppress(ImportError):
    from loom.tools import enrich as enrich_tools

    _optional_tools["enrich"] = enrich_tools
    record_optional_module_loaded("enrich")

with suppress(ImportError):
    from loom.tools import experts as experts_tools

    _optional_tools["experts"] = experts_tools
    record_optional_module_loaded("experts")

with suppress(ImportError):
    from loom.tools import creative as creative_tools

    _optional_tools["creative"] = creative_tools
    record_optional_module_loaded("creative")

with suppress(ImportError):
    from loom.providers import youtube_transcripts as yt_tools

    _optional_tools["youtube"] = yt_tools
    record_optional_module_loaded("youtube")

with suppress(ImportError):
    from loom.tools import vastai as vastai_tools

    _optional_tools["vastai"] = vastai_tools
    record_optional_module_loaded("vastai")

with suppress(ImportError):
    from loom.tools import billing as billing_tools

    _optional_tools["billing"] = billing_tools
    record_optional_module_loaded("billing")

with suppress(ImportError):
    from loom.tools import email_report as email_tools

    _optional_tools["email"] = email_tools
    record_optional_module_loaded("email")

with suppress(ImportError):
    from loom.tools import joplin as joplin_tools

    _optional_tools["joplin"] = joplin_tools
    record_optional_module_loaded("joplin")

with suppress(ImportError):
    from loom.tools import tor as tor_tools

    _optional_tools["tor"] = tor_tools
    record_optional_module_loaded("tor")

with suppress(ImportError):
    from loom.tools import transcribe as transcribe_tools

    _optional_tools["transcribe"] = transcribe_tools
    record_optional_module_loaded("transcribe")

with suppress(ImportError):
    from loom.tools import document as document_tools

    _optional_tools["document"] = document_tools
    record_optional_module_loaded("document")


with suppress(ImportError):
    from loom.tools import metrics as metrics_tools

    _optional_tools["metrics"] = metrics_tools
    record_optional_module_loaded("metrics")

with suppress(ImportError):
    from loom.tools import slack as slack_tools

    _optional_tools["slack"] = slack_tools
    record_optional_module_loaded("slack")

with suppress(ImportError):
    from loom.tools import gcp as gcp_tools

    _optional_tools["gcp"] = gcp_tools
    record_optional_module_loaded("gcp")

with suppress(ImportError):
    from loom.tools import vercel as vercel_tools

    _optional_tools["vercel"] = vercel_tools
    record_optional_module_loaded("vercel")

# ── v3 modules: scorers, pipelines, orchestration, tracking ──
with suppress(ImportError):
    from loom.tools import attack_scorer as attack_scorer_tools
    _optional_tools["attack_scorer"] = attack_scorer_tools
    record_optional_module_loaded("attack_scorer")

with suppress(ImportError):
    from loom.tools import stealth_score as stealth_score_tools
    _optional_tools["stealth_score"] = stealth_score_tools
    record_optional_module_loaded("stealth_score")

with suppress(ImportError):
    from loom.tools import potency_meter as potency_meter_tools
    _optional_tools["potency_meter"] = potency_meter_tools
    record_optional_module_loaded("potency_meter")

with suppress(ImportError):
    from loom.tools import stealth_scorer as stealth_scorer_tools
    _optional_tools["stealth_scorer"] = stealth_scorer_tools
    record_optional_module_loaded("stealth_scorer")

with suppress(ImportError):
    from loom.tools import model_sentiment as model_sentiment_tools
    _optional_tools["model_sentiment"] = model_sentiment_tools
    record_optional_module_loaded("model_sentiment")

with suppress(ImportError):
    from loom.tools import toxicity_checker_tool as toxicity_tools
    _optional_tools["toxicity"] = toxicity_tools
    record_optional_module_loaded("toxicity")

with suppress(ImportError):
    from loom.tools import drift_monitor_tool as drift_tools
    _optional_tools["drift"] = drift_tools
    record_optional_module_loaded("drift")

with suppress(ImportError):
    from loom.tools import bpj as bpj_tools
    _optional_tools["bpj"] = bpj_tools
    record_optional_module_loaded("bpj")

with suppress(ImportError):
    from loom.tools import daisy_chain_tool as daisy_tools
    _optional_tools["daisy_chain"] = daisy_tools
    record_optional_module_loaded("daisy_chain")

with suppress(ImportError):
    from loom.tools import consistency_pressure as consistency_tools
    _optional_tools["consistency"] = consistency_tools
    record_optional_module_loaded("consistency")

with suppress(ImportError):
    from loom.tools import constraint_optimizer as constraint_tools
    _optional_tools["constraint"] = constraint_tools
    record_optional_module_loaded("constraint")

with suppress(ImportError):
    from loom.tools import jailbreak_evolution as jailbreak_evo_tools
    _optional_tools["jailbreak_evo"] = jailbreak_evo_tools
    record_optional_module_loaded("jailbreak_evo")

with suppress(ImportError):
    from loom.tools import semantic_cache_mgmt as sem_cache_tools
    _optional_tools["sem_cache"] = sem_cache_tools
    record_optional_module_loaded("sem_cache")

with suppress(ImportError):
    from loom.tools import param_sweep as param_sweep_tools
    _optional_tools["param_sweep"] = param_sweep_tools
    record_optional_module_loaded("param_sweep")

with suppress(ImportError):
    from loom.tools import strategy_oracle as strategy_oracle_tools
    _optional_tools["strategy_oracle"] = strategy_oracle_tools
    record_optional_module_loaded("strategy_oracle")

with suppress(ImportError):
    from loom.tools import stealth_detect as stealth_detect_tools
    _optional_tools["stealth_detect"] = stealth_detect_tools
    record_optional_module_loaded("stealth_detect")

with suppress(ImportError):
    from loom.tools import tool_recommender_tool as recommender_tools
    _optional_tools["recommender"] = recommender_tools
    record_optional_module_loaded("recommender")

with suppress(ImportError):
    from loom.tools import reframe_router as reframe_router_tools
    _optional_tools["reframe_router"] = reframe_router_tools
    record_optional_module_loaded("reframe_router")

with suppress(ImportError):
    from loom.tools import pipeline_enhancer as pipeline_enhancer_tools
    _optional_tools["pipeline_enhancer"] = pipeline_enhancer_tools
    record_optional_module_loaded("pipeline_enhancer")

with suppress(ImportError):
    from loom.tools import ytdlp_backend as ytdlp_tools
    _optional_tools["ytdlp"] = ytdlp_tools
    record_optional_module_loaded("ytdlp")

# ── v3 direct imports (functions in src/loom/*.py) ──
with suppress(ImportError):
    from loom.danger_prescore import research_danger_prescore
    _optional_tools["danger_prescore"] = research_danger_prescore
    record_optional_module_loaded("danger_prescore")

with suppress(ImportError):
    from loom.quality_scorer import research_quality_score
    _optional_tools["quality_scorer"] = research_quality_score
    record_optional_module_loaded("quality_scorer")

with suppress(ImportError):
    from loom.evidence_pipeline import research_evidence_pipeline
    _optional_tools["evidence_pipeline"] = research_evidence_pipeline
    record_optional_module_loaded("evidence_pipeline")

with suppress(ImportError):
    from loom.context_poisoning import research_context_poison
    _optional_tools["context_poison"] = research_context_poison
    record_optional_module_loaded("context_poison")

with suppress(ImportError):
    from loom.adversarial_debate import research_adversarial_debate
    _optional_tools["adversarial_debate"] = research_adversarial_debate
    record_optional_module_loaded("adversarial_debate")

with suppress(ImportError):
    from loom.model_evidence import research_model_evidence
    _optional_tools["model_evidence"] = research_model_evidence
    record_optional_module_loaded("model_evidence")

with suppress(ImportError):
    from loom.target_orchestrator import research_target_orchestrate
    _optional_tools["target_orchestrate"] = research_target_orchestrate
    record_optional_module_loaded("target_orchestrate")

with suppress(ImportError):
    from loom.reid_auto import ReidAutoReframe
    _optional_tools["reid_auto"] = ReidAutoReframe
    record_optional_module_loaded("reid_auto")

with suppress(ImportError):
    from loom.mcp_security import research_mcp_security_scan
    _optional_tools["mcp_security"] = research_mcp_security_scan
    record_optional_module_loaded("mcp_security")

with suppress(ImportError):
    from loom.cicd import research_cicd_run
    _optional_tools["cicd"] = research_cicd_run
    record_optional_module_loaded("cicd")

with suppress(ImportError):
    from loom.stealth_detector import research_stealth_detect as stealth_det_fn
    _optional_tools["stealth_detector"] = stealth_det_fn
    record_optional_module_loaded("stealth_detector")

with suppress(ImportError):
    from loom.doc_parser import research_ocr_advanced, research_pdf_advanced, research_document_analyze
    _optional_tools["doc_parser"] = {"ocr": research_ocr_advanced, "pdf": research_pdf_advanced, "analyze": research_document_analyze}
    record_optional_module_loaded("doc_parser")

with suppress(ImportError):
    from loom.tools import cipher_mirror as cipher_mirror_tools

    _optional_tools["cipher_mirror"] = cipher_mirror_tools
    record_optional_module_loaded("cipher_mirror")

with suppress(ImportError):
    from loom.tools import forum_cortex as forum_cortex_tools

    _optional_tools["forum_cortex"] = forum_cortex_tools
    record_optional_module_loaded("forum_cortex")

with suppress(ImportError):
    from loom.tools import onion_spectra as onion_spectra_tools

    _optional_tools["onion_spectra"] = onion_spectra_tools
    record_optional_module_loaded("onion_spectra")

with suppress(ImportError):
    from loom.tools import ghost_weave as ghost_weave_tools

    _optional_tools["ghost_weave"] = ghost_weave_tools
    record_optional_module_loaded("ghost_weave")

with suppress(ImportError):
    from loom.tools import dead_drop_scanner as dead_drop_scanner_tools

    _optional_tools["dead_drop_scanner"] = dead_drop_scanner_tools
    record_optional_module_loaded("dead_drop_scanner")

with suppress(ImportError):
    from loom.tools import persona_profile as persona_profile_tools

    _optional_tools["persona_profile"] = persona_profile_tools
    record_optional_module_loaded("persona_profile")

with suppress(ImportError):
    from loom.tools import radicalization_detect as radicalization_detect_tools

    _optional_tools["radicalization_detect"] = radicalization_detect_tools
    record_optional_module_loaded("radicalization_detect")
with suppress(ImportError):
    from loom.tools import sentiment_deep as sentiment_deep_tools

    _optional_tools["sentiment_deep"] = sentiment_deep_tools
    record_optional_module_loaded("sentiment_deep")

with suppress(ImportError):
    from loom.tools import network_persona as network_persona_tools

    _optional_tools["network_persona"] = network_persona_tools
    record_optional_module_loaded("network_persona")

with suppress(ImportError):
    from loom.tools import text_analyze as text_analyze_tools

    _optional_tools["text_analyze"] = text_analyze_tools
    record_optional_module_loaded("text_analyze")

with suppress(ImportError):
    from loom.tools import epistemic_score as epistemic_score_tools

    _optional_tools["epistemic_score"] = epistemic_score_tools
    record_optional_module_loaded("epistemic_score")

with suppress(ImportError):
    from loom.tools import screenshot as screenshot_tools

    _optional_tools["screenshot"] = screenshot_tools
    record_optional_module_loaded("screenshot")


with suppress(ImportError):
    from loom.tools import geoip_local as geoip_local_tools

    _optional_tools["geoip_local"] = geoip_local_tools
    record_optional_module_loaded("geoip_local")

with suppress(ImportError):
    from loom.tools import image_intel as image_intel_tools

    _optional_tools["image_intel"] = image_intel_tools
    record_optional_module_loaded("image_intel")

with suppress(ImportError):
    from loom.tools import ip_intel as ip_intel_tools

    _optional_tools["ip_intel"] = ip_intel_tools
    record_optional_module_loaded("ip_intel")

with suppress(ImportError):
    from loom.tools import cve_lookup as cve_lookup_tools

    _optional_tools["cve_lookup"] = cve_lookup_tools
    record_optional_module_loaded("cve_lookup")

with suppress(ImportError):
    from loom.tools import vuln_intel as vuln_intel_tools

    _optional_tools["vuln_intel"] = vuln_intel_tools
    record_optional_module_loaded("vuln_intel")

with suppress(ImportError):
    from loom.tools import urlhaus_lookup as urlhaus_lookup_tools

    _optional_tools["urlhaus_lookup"] = urlhaus_lookup_tools
    record_optional_module_loaded("urlhaus_lookup")

with suppress(ImportError):
    from loom.tools import job_research as job_research_tools

    _optional_tools["job_research"] = job_research_tools
    record_optional_module_loaded("job_research")


with suppress(ImportError):
    from loom.tools import career_intel as career_intel_tools

    _optional_tools["career_intel"] = career_intel_tools
    record_optional_module_loaded("career_intel")

with suppress(ImportError):
    from loom.tools import resume_intel as resume_intel_tools

    _optional_tools["resume_intel"] = resume_intel_tools
    record_optional_module_loaded("resume_intel")


with suppress(ImportError):
    from loom.tools import career_trajectory as career_trajectory_tools

    _optional_tools["career_trajectory"] = career_trajectory_tools
    record_optional_module_loaded("career_trajectory")

with suppress(ImportError):
    from loom.tools import consistency_pressure as consistency_pressure_tools

    _optional_tools["consistency_pressure"] = consistency_pressure_tools
    record_optional_module_loaded("consistency_pressure")

with suppress(ImportError):
    from loom.tools import constraint_optimizer as constraint_optimizer_tools

    _optional_tools["constraint_optimizer"] = constraint_optimizer_tools
    record_optional_module_loaded("constraint_optimizer")

with suppress(ImportError):
    from loom.tools import semantic_cache_mgmt as semantic_cache_mgmt_tools

    _optional_tools["semantic_cache_mgmt"] = semantic_cache_mgmt_tools
    record_optional_module_loaded("semantic_cache_mgmt")

with suppress(ImportError):
    from loom.tools import param_sweep as param_sweep_tools

    _optional_tools["param_sweep"] = param_sweep_tools
    record_optional_module_loaded("param_sweep")

with suppress(ImportError):
    from loom import nodriver_backend

    _optional_tools["nodriver"] = nodriver_backend
    record_optional_module_loaded("nodriver")

with suppress(ImportError):
    from loom.tools import ytdlp_backend as ytdlp_backend_tools

    _optional_tools["ytdlp_backend"] = ytdlp_backend_tools
    record_optional_module_loaded("ytdlp_backend")


with suppress(ImportError):
    from loom.tools import model_consensus as model_consensus_tools

    _optional_tools["model_consensus"] = model_consensus_tools
    record_optional_module_loaded("model_consensus")


with suppress(ImportError):
    from loom import doc_parser as doc_parser_tools

    _optional_tools["doc_parser"] = doc_parser_tools
    record_optional_module_loaded("doc_parser")

with suppress(ImportError):
    from loom.tools import mcp_auth as mcp_auth_tools

    _optional_tools["mcp_auth"] = mcp_auth_tools
    record_optional_module_loaded("mcp_auth")

with suppress(ImportError):
    from loom.tools import retry_stats as retry_stats_tools

    _optional_tools["retry_stats"] = retry_stats_tools
    record_optional_module_loaded("retry_stats")

_start_time = time.time()

# ── Startup validation results (populated in create_app) ──
_startup_validation_result: dict[str, Any] | None = None
_health_status: str = "initializing"  # initializing, healthy, degraded, unhealthy
_validation_error_count: int = 0

# ── Graceful Shutdown Handling ──
_shutting_down: bool = False
_shutdown_start_time: float | None = None
_shutdown_timeout_seconds: int = 30


def _set_shutting_down() -> None:
    """Mark server as shutting down."""
    global _shutting_down, _shutdown_start_time
    _shutting_down = True
    _shutdown_start_time = time.time()
    log.info("shutdown_flag_set timeout_seconds=%d", _shutdown_timeout_seconds)


def _is_shutting_down() -> bool:
    """Check if server is in shutdown state."""
    return _shutting_down


def _shutdown_grace_time_remaining() -> float:
    """Get remaining shutdown grace period in seconds."""
    if not _shutdown_start_time:
        return float(_shutdown_timeout_seconds)
    elapsed = time.time() - _shutdown_start_time
    remaining = max(0, _shutdown_timeout_seconds - elapsed)
    return remaining
def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools from modular registration system.

    Delegates to category-specific registration functions for maintainability.
    """
    from loom.registrations import register_all_tools

    # WebSocket endpoint defined in src/loom/websocket.py
    # Registration deferred to after app creation (FastMCP custom_route)
    try:
        ws_mgr = get_ws_manager()
        log.info("websocket_manager_initialized")
    except Exception:
        log.debug("websocket_manager_not_available")

    # Register all tools from 8 category modules
    register_all_tools(mcp, _wrap_tool)

    # Register optional tools (loaded with suppress(ImportError) at module level)
    for _mod_name, _mod in _optional_tools.items():
        for _attr in dir(_mod):
            if _attr.startswith("research_"):
                _func = getattr(_mod, _attr)
                if callable(_func):
                    try:
                        mcp.tool()(_wrap_tool(_func))
                    except Exception:
                        pass


    # Register PostgreSQL tools from _pg_tools (optional)
    for _tool_name, _tool_func in _pg_tools.items():
        try:
            mcp.tool()(_wrap_tool(_tool_func))
        except Exception:
            pass

    # Register core loom.* module tools (sessions, config, orchestrator, scoring, etc.)
    _core_funcs = [
        research_session_open, research_session_list, research_session_close,
        research_config_get, research_config_set, research_feature_flags,
        research_orchestrate, research_score_all, research_unified_score,
        research_benchmark_run, research_consensus_build, research_consensus_pressure,
        research_crescendo_loop, research_model_profile, research_reid_pipeline,
        research_pool_stats, research_pool_reset, export_audit,
        research_backup_create, research_backup_restore, research_backup_list, research_backup_cleanup,
        research_cpu_pool_status, research_cpu_executor_shutdown,
        research_analytics_dashboard, research_secret_health, research_quota_status, research_sla_status,
        research_rate_limits,
        research_validate_startup,
        research_latency_report,
        research_scheduler_status,
    ]
    for _func in _core_funcs:
        try:
            mcp.tool()(_wrap_tool(_func))
        except Exception:
            pass

    # Register crawlee/zendriver backends (in loom namespace)
    try:
        if crawlee_backend:
            for _attr in dir(crawlee_backend):
                if _attr.startswith("research_"):
                    mcp.tool()(_wrap_tool(getattr(crawlee_backend, _attr)))
    except Exception:
        pass
    try:
        if zendriver_backend:
            for _attr in dir(zendriver_backend):
                if _attr.startswith("research_"):
                    mcp.tool()(_wrap_tool(getattr(zendriver_backend, _attr)))
    except Exception:
        pass

    log.info("tool_registration_complete")

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
    # Load .env file for API keys
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        for env_path in [Path('/opt/research-toolbox/.env'), Path('.env'), Path(__file__).parent.parent.parent / '.env']:
            if env_path.exists():
                load_dotenv(env_path)
                break
    except ImportError:
        pass

    # Load runtime config
    config = load_config()

    # Set up logging with request_id support
    log_level = config.get("LOG_LEVEL", "INFO")
    log_format = os.environ.get("LOG_FORMAT", config.get("LOG_FORMAT", "text"))
    setup_logging(log_level=log_level, log_format=log_format)
    install_tracing()

    # Validate environment
    _validate_environment()

    # Run startup validation on tools
    global _startup_validation_result, _health_status, _validation_error_count
    try:
        _startup_validation_result = validate_all_tools()
        if _startup_validation_result["failed"] > 0:
            failure_rate = (_startup_validation_result["failed"] / max(1, _startup_validation_result["total"])) * 100
            _validation_error_count = _startup_validation_result["failed"]
            if failure_rate > 20:
                _health_status = "unhealthy"
                log.error(
                    "startup_validation_unhealthy failure_rate=%.2f%% tools_passed=%d tools_failed=%d",
                    failure_rate,
                    _startup_validation_result["passed"],
                    _startup_validation_result["failed"],
                )
            else:
                _health_status = "degraded"
                log.warning(
                    "startup_validation_degraded failure_rate=%.2f%% tools_passed=%d tools_failed=%d",
                    failure_rate,
                    _startup_validation_result["passed"],
                    _startup_validation_result["failed"],
                )
        else:
            _health_status = "healthy"
            log.info(
                "startup_validation_passed total=%d duration_ms=%.2f",
                _startup_validation_result["total"],
                _startup_validation_result["duration_ms"],
            )
    except Exception as e:
        log.error("startup_validation_error error=%s", str(e))
        _health_status = "unhealthy"
        _validation_error_count = 1


    # Initialize and validate API keys (SecretManager singleton)
    try:
        secret_mgr = get_secret_manager()
        validation_results = secret_mgr.validate_all_keys()
        health = secret_mgr.get_health()
        log.info(
            "secret_manager_initialized status=%s valid_keys=%d missing_keys=%d",
            health["overall_status"],
            health["valid_keys"],
            health["missing_keys"],
        )
        if health["stale_keys"]:
            log.warning(
                "stale_keys_detected providers=%s days_threshold=%d",
                health["stale_keys"],
                health["stale_threshold_days"],
            )
    except Exception as e:
        log.error("secret_manager_init_failed error=%s", str(e))

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

    # Register HTTP routes (health, metrics, docs, openapi)
    register_http_routes(mcp)

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
        "Loom MCP server initialized: name=%s host=%s port=%d prometheus_enabled=%s",
        "loom",
        host,
        port,
        _prometheus_enabled,
    )

    # Wire middleware (FastMCP may not expose .app — use try/except)
    try:
        app = mcp.streamable_http_app()
        app.add_middleware(RequestIdMiddleware)
        app.add_middleware(ApiKeyAuthMiddleware)
        if os.environ.get("LOOM_CORS_ENABLED", "true").lower() == "true":
            origins = os.environ.get("LOOM_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
            app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
        log.info("middleware_registered request_id=true auth=true cors=%s", os.environ.get("LOOM_CORS_ENABLED", "true"))
    except (AttributeError, TypeError) as e:
        log.warning("middleware_registration_skipped reason=%s (FastMCP version may not support .app)", str(e)[:100])
        log.info("cors_middleware_registered origins=%s", origins)
    else:
        log.info("cors_middleware_disabled")


    # Register and start background task scheduler
    try:
        register_default_tasks()
        scheduler = get_scheduler()
        asyncio.create_task(scheduler.start())
        log.info("background_task_scheduler_started")
    except Exception as exc:
        log.error("scheduler_startup_failed: %s", exc)

        # Start batch queue background processing
    try:
        start_batch_queue_background()
        log.info("batch_queue_background_started")
    except Exception as exc:
        log.error("batch_queue_startup_failed: %s", exc)

    return mcp



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
