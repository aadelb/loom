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


# ── Dynamic strategy count caching ──
_STRATEGY_COUNT: int | None = None

def _get_strategy_count() -> int:
    """Get cached strategy count from ALL_STRATEGIES registry.
    
    Strategies don't change at runtime, so we cache the count
    to avoid repeated imports and len() calls.
    
    Returns:
        Total count of registered reframing strategies
    """
    global _STRATEGY_COUNT
    if _STRATEGY_COUNT is None:
        try:
            from loom.tools.reframe_strategies import ALL_STRATEGIES
            _STRATEGY_COUNT = len(ALL_STRATEGIES)
        except (ImportError, Exception):
            _STRATEGY_COUNT = 0
    return _STRATEGY_COUNT


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




async def research_audit_query(
    tool_name: str = "",
    hours: int = 24,
    limit: int = 100,
) -> dict[str, Any]:
    """Query audit log entries by tool name and time range.

    Searches audit logs from the last N hours and returns matching entries.
    Entries include tool name, execution duration, status, and parameters (PII-scrubbed).

    Args:
        tool_name: Filter by tool name (empty = all tools)
        hours: Look back N hours (1-720, default 24)
        limit: Maximum entries to return (1-1000, default 100)

    Returns:
        Dict with keys:
        - entries: List of audit entries matching the query
        - count: Number of entries returned
        - total_count: Total matching entries in audit log
        - timestamp: Query timestamp (ISO UTC)
        - query_duration_ms: Query execution time
    """
    from loom.tools.audit_query import research_audit_query as _research_audit_query
    return await _research_audit_query(tool_name=tool_name, hours=hours, limit=limit)


async def research_audit_stats(
    hours: int = 24,
) -> dict[str, Any]:
    """Generate audit statistics for compliance reporting.

    Summarizes tool call metrics: success/failure counts, top tools, error types,
    duration statistics, and cost estimates.

    Args:
        hours: Look back N hours (1-720, default 24)

    Returns:
        Dict with keys:
        - total_calls: Total tool invocations
        - successful_calls: Calls with status == "success"
        - failed_calls: Calls with status == "error"
        - timeout_calls: Calls with status == "timeout"
        - other_error_calls: Other error statuses
        - top_tools: Dict of {tool_name: call_count}, top 10
        - top_errors: Dict of {error_type: count}, top 10
        - avg_duration_ms: Average execution duration
        - min_duration_ms: Minimum execution duration
        - max_duration_ms: Maximum execution duration
        - total_duration_ms: Sum of all durations
        - total_cost_credits: Estimated total credits used
        - timestamp: Stats timestamp (ISO UTC)
    """
    from loom.tools.audit_query import research_audit_stats as _research_audit_stats
    return await _research_audit_stats(hours=hours)
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
        "strategy_count": _get_strategy_count(),
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




async def research_cpu_pool_status() -> dict[str, Any]:
    """Get health and status of the CPU executor pool.

    Returns executor pool metrics including worker count, active tasks,
    and current status (idle, busy, saturated).

    Returns:
        Dict with:
        - pool_initialized: bool
        - max_workers: Configured number of workers
        - active_tasks: Currently executing tasks
        - pending_tasks: Tasks in queue
        - status: "idle", "healthy", "busy", or "saturated"
        - configuration: Environment variables used
    """
    try:
        from loom.cpu_executor import get_pool_status
        return await get_pool_status()
    except Exception as exc:
        log.error("cpu_pool_status failed: %s", exc)
        return {
            "status": "error",
            "error": str(exc)[:100],
        }


async def research_cpu_executor_shutdown() -> dict[str, Any]:
    """Gracefully shut down the CPU executor pool.

    Waits for all pending tasks to complete before shutting down
    worker processes. Should be called during server shutdown.

    Returns:
        Dict with shutdown result:
        - status: "success" or "error"
        - message: Human-readable status message
        - tasks_waited: Number of tasks that were waiting
    """
    try:
        from loom.cpu_executor import shutdown_executor
        return await shutdown_executor()
    except Exception as exc:
        log.error("cpu_executor_shutdown failed: %s", exc)
        return {
            "status": "error",
            "message": str(exc)[:100],
            "tasks_waited": 0,
        }



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
        research_audit_query, research_audit_stats,
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
