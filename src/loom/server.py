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

from loom.config import load_config, research_config_get, research_config_set
from loom.orchestrator import research_orchestrate
from loom.audit import export_audit, log_invocation
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
from loom.startup_validator import (
    validate_all_tools,
    validate_registrations,
    research_validate_startup,
)
from loom.tool_latency import get_latency_tracker
from loom.tool_rate_limiter import check_tool_rate_limit, research_rate_limits

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
    """Wrap tool with tracing, rate limiting, metrics, and optional billing.

    Handles both sync and async tool functions correctly.
    Instruments tools with Prometheus metrics (call count, duration, errors).
    """
    import inspect

    is_async = inspect.iscoroutinefunction(func)

    tool_timeout = 60  # seconds
    billing_enabled = os.getenv("LOOM_BILLING_ENABLED", "").lower() == "true"
    token_economy_enabled = os.getenv("LOOM_TOKEN_ECONOMY", "").lower() == "true"
    tool_name = func.__name__

    if is_async:
        if category:
            func = rate_limited(category)(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = new_request_id()
            start_time = time.time()
            # Auto-correct parameters
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            if corrections:
                log.debug(f"Parameter corrections for {tool_name}: {corrections}")

            # Tool-specific rate limiting (per-tool granular limits)
            user_id_for_rate = os.getenv("LOOM_USER_ID", "default")
            rate_limit_error = await check_tool_rate_limit(tool_name, user_id_for_rate)
            if rate_limit_error:
                log.warning("tool_rate_limit_exceeded", tool=tool_name, user_id=user_id_for_rate)
                _loom_tool_calls_total.labels(tool_name=tool_name, status="rate_limited").inc()
                return rate_limit_error

            # ── Graceful Shutdown Check ──
            if _is_shutting_down():
                grace_remaining = _shutdown_grace_time_remaining()
                log.warning("tool_call_during_shutdown tool=%s grace_remaining_seconds=%.1f", tool_name, grace_remaining)
                _loom_tool_calls_total.labels(tool_name=tool_name, status="shutdown").inc()
                return {
                    "error": "server_shutting_down",
                    "message": "Server is shutting down. No new tool calls accepted.",
                    "retry_after_seconds": int(grace_remaining) + 1,
                    "graceful_shutdown": True,
                }


            # Token Economy: check credits before execution (if enabled)
            user_id = os.getenv("LOOM_USER_ID", "anonymous")
            current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
            token_economy_result = {}
            
            if token_economy_enabled:
                balance_check = check_balance(user_id, current_balance, tool_name)
                
                if not balance_check["sufficient"]:
                    log.warning(
                        "insufficient_credits",
                        user_id=user_id,
                        tool_name=tool_name,
                        required=balance_check["required"],
                        balance=balance_check["balance"],
                        shortfall=balance_check["shortfall"],
                    )
                    return {
                        "error": "insufficient_credits",
                        "message": f"Tool '{tool_name}' requires {balance_check['required']} credits, but you have {balance_check['balance']}. Need {balance_check['shortfall']} more credits.",
                        "tool": tool_name,
                        "required_credits": balance_check["required"],
                        "available_credits": balance_check["balance"],
                        "shortfall": balance_check["shortfall"],
                    }
                
                token_economy_result = {
                    "cost": balance_check["required"],
                    "balance_before": current_balance,
                }
            
            # Billing: check credits before execution (if enabled)
            customer_id = os.getenv("LOOM_CUSTOMER_ID", "default")
            if billing_enabled:
                # Credit check would go here; for now we just record
                log.debug(f"Billing enabled for tool {tool_name}, customer {customer_id}")

            try:
                result = await asyncio.wait_for(func(*args, **corrected_kwargs), timeout=tool_timeout)
                # Add correction metadata if there were corrections
                if corrections and isinstance(result, dict):
                    result["_param_corrections"] = corrections

                # Token Economy: deduct credits after successful execution
                if token_economy_enabled:
                    cost = get_tool_cost(tool_name)
                    new_balance = max(0, current_balance - cost)
                    token_economy_result["balance_after"] = new_balance
                    
                    log.info(
                        "token_economy_deduction",
                        user_id=user_id,
                        tool_name=tool_name,
                        cost=cost,
                        balance_before=current_balance,
                        balance_after=new_balance,
                    )
                    
                    if isinstance(result, dict):
                        result["_token_economy"] = token_economy_result

                # Prometheus: record success
                _loom_tool_calls_total.labels(tool_name=tool_name, status="success").inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record per-tool latency
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                    # Add p95 to response if duration slow (>1000ms)
                    if duration_ms > 1000 and isinstance(result, dict):
                        stats = latency_tracker.get_percentiles(tool_name)
                        result['_latency_p95_ms'] = stats['p95']
                except Exception as e:
                    log.debug(f'Latency tracking error: {e}')

                # Billing: record usage after successful execution
                if billing_enabled:
                    duration_ms = duration * 1000
                    # Estimate credits: 1 credit per second of execution
                    credits_used = max(1, int(duration_ms / 1000))
                    try:
                        record_usage(customer_id, tool_name, credits_used, duration_ms)
                        log.debug(f"Billed {credits_used} credits to {customer_id} for {tool_name}")
                    except Exception as e:
                        log.error(f"Billing error for {tool_name}: {e}", exc_info=False)

                
                # Analytics: record tool call
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, True, user_id)
                except Exception as e:
                    log.debug(f"Analytics recording error: {e}")

                # Audit: Log tool call success
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    result_size = len(str(result)) if result else 0
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"success: {result_size} bytes",
                        duration_ms=int(duration_ms),
                        status="success"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at success: {audit_e}")

                return result
            except asyncio.TimeoutError:
                # Prometheus: record timeout error
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type="timeout").inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
                
                # Analytics: record tool call error
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, False, user_id)
                except Exception as e:
                    log.debug(f"Analytics recording error: {e}")

                # Audit: Log tool call timeout
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary="timeout_error",
                        duration_ms=int(duration * 1000),
                        status="timeout"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at timeout: {audit_e}")

                return {"error": f"Tool timed out after {tool_timeout}s", "tool": tool_name}
            except Exception as e:
                # Prometheus: record error
                error_type = type(e).__name__
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
                # Audit: Log tool call error
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"error: {error_type}",
                        duration_ms=int(duration * 1000),
                        status="error"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at error: {audit_e}")

                raise

        return async_wrapper
    else:
        if category:
            from loom.rate_limiter import sync_rate_limited
            func = sync_rate_limited(category)(func)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = new_request_id()
            start_time = time.time()
            # Auto-correct parameters
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            if corrections:
                log.debug(f"Parameter corrections for {tool_name}: {corrections}")

            # ── Graceful Shutdown Check ──
            if _is_shutting_down():
                grace_remaining = _shutdown_grace_time_remaining()
                log.warning("tool_call_during_shutdown sync tool=%s grace_remaining_seconds=%.1f", tool_name, grace_remaining)
                _loom_tool_calls_total.labels(tool_name=tool_name, status="shutdown").inc()
                return {
                    "error": "server_shutting_down",
                    "message": "Server is shutting down. No new tool calls accepted.",
                    "retry_after_seconds": int(grace_remaining) + 1,
                    "graceful_shutdown": True,
                }


            # Token Economy: check credits before execution (if enabled)
            user_id = os.getenv("LOOM_USER_ID", "anonymous")
            current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
            token_economy_result = {}
            
            if token_economy_enabled:
                balance_check = check_balance(user_id, current_balance, tool_name)
                
                if not balance_check["sufficient"]:
                    log.warning(
                        "insufficient_credits",
                        user_id=user_id,
                        tool_name=tool_name,
                        required=balance_check["required"],
                        balance=balance_check["balance"],
                        shortfall=balance_check["shortfall"],
                    )
                    return {
                        "error": "insufficient_credits",
                        "message": f"Tool '{tool_name}' requires {balance_check['required']} credits, but you have {balance_check['balance']}. Need {balance_check['shortfall']} more credits.",
                        "tool": tool_name,
                        "required_credits": balance_check["required"],
                        "available_credits": balance_check["balance"],
                        "shortfall": balance_check["shortfall"],
                    }
                
                token_economy_result = {
                    "cost": balance_check["required"],
                    "balance_before": current_balance,
                }
            
            # Token Economy: check credits before execution (if enabled)
            user_id = os.getenv("LOOM_USER_ID", "anonymous")
            current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
            token_economy_result = {}
            
            if token_economy_enabled:
                balance_check = check_balance(user_id, current_balance, tool_name)
                
                if not balance_check["sufficient"]:
                    log.warning(
                        "insufficient_credits",
                        user_id=user_id,
                        tool_name=tool_name,
                        required=balance_check["required"],
                        balance=balance_check["balance"],
                        shortfall=balance_check["shortfall"],
                    )
                    return {
                        "error": "insufficient_credits",
                        "message": f"Tool '{tool_name}' requires {balance_check['required']} credits, but you have {balance_check['balance']}. Need {balance_check['shortfall']} more credits.",
                        "tool": tool_name,
                        "required_credits": balance_check["required"],
                        "available_credits": balance_check["balance"],
                        "shortfall": balance_check["shortfall"],
                    }
                
                token_economy_result = {
                    "cost": balance_check["required"],
                    "balance_before": current_balance,
                }
            
            # Billing: check credits before execution (if enabled)
            customer_id = os.getenv("LOOM_CUSTOMER_ID", "default")
            if billing_enabled:
                # Credit check would go here; for now we just record
                log.debug(f"Billing enabled for tool {tool_name}, customer {customer_id}")

            try:
                result = func(*args, **corrected_kwargs)
                # Add correction metadata if there were corrections
                if corrections and isinstance(result, dict):
                    result["_param_corrections"] = corrections

                # Token Economy: deduct credits after successful execution
                if token_economy_enabled:
                    cost = get_tool_cost(tool_name)
                    new_balance = max(0, current_balance - cost)
                    token_economy_result["balance_after"] = new_balance
                    
                    log.info(
                        "token_economy_deduction",
                        user_id=user_id,
                        tool_name=tool_name,
                        cost=cost,
                        balance_before=current_balance,
                        balance_after=new_balance,
                    )
                    
                    if isinstance(result, dict):
                        result["_token_economy"] = token_economy_result

                # Prometheus: record success
                _loom_tool_calls_total.labels(tool_name=tool_name, status="success").inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record per-tool latency (sync wrapper)
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                    # Add p95 to response if duration slow (>1000ms)
                    if duration_ms > 1000 and isinstance(result, dict):
                        stats = latency_tracker.get_percentiles(tool_name)
                        result['_latency_p95_ms'] = stats['p95']
                except Exception as e:
                    log.debug(f'Latency tracking error: {e}')

                # Billing: record usage after successful execution
                if billing_enabled:
                    duration_ms = duration * 1000
                    # Estimate credits: 1 credit per second of execution
                    credits_used = max(1, int(duration_ms / 1000))
                    try:
                        record_usage(customer_id, tool_name, credits_used, duration_ms)
                        log.debug(f"Billed {credits_used} credits to {customer_id} for {tool_name}")
                    except Exception as e:
                        log.error(f"Billing error for {tool_name}: {e}", exc_info=False)

                # Audit: Log tool call success (sync wrapper)
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    result_size = len(str(result)) if result else 0
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"success: {result_size} bytes",
                        duration_ms=int(duration_ms),
                        status="success"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at success (sync): {audit_e}")

                return result
            except Exception as e:
                # Prometheus: record error
                error_type = type(e).__name__
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
                # Audit: Log tool call error (sync wrapper)
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"error: {error_type}",
                        duration_ms=int(duration * 1000),
                        status="error"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at error (sync): {audit_e}")

                raise

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
        research_config_get, research_config_set,
        research_orchestrate, research_score_all, research_unified_score,
        research_benchmark_run, research_consensus_build, research_consensus_pressure,
        research_crescendo_loop, research_model_profile, research_reid_pipeline,
        research_pool_stats, research_pool_reset, export_audit,
        research_audit_query, research_audit_stats,
        research_cpu_pool_status, research_cpu_executor_shutdown,
        research_analytics_dashboard, research_secret_health, research_quota_status,
        research_rate_limits,
        research_validate_startup,
        research_latency_report,
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

    # Register custom HTTP endpoints (health check, root)
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response

    @mcp.custom_route("/", methods=["GET"])
    async def root_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({
            "service": "loom",
            "version": "3.0.0",
            "description": "Loom MCP Research Server — 303 tools, 957 strategies",
            "mcp_endpoint": "/mcp",
            "health_endpoint": "/health",
            "health_endpoint_v1": "/v1/health",
            "metrics_endpoint": "/metrics" if _prometheus_enabled else None,
            "metrics_endpoint_v1": "/v1/metrics" if _prometheus_enabled else None,
            "versions_endpoint": "/versions",
            "api_versions": ["v1"],
            "status": "running",
            "deprecation": "Unversioned endpoints (/, /health, /metrics) are deprecated. Use /v1/ prefixed versions instead.",
        })

    @mcp.custom_route("/health", methods=["GET"])
    async def health_endpoint(request: Request) -> JSONResponse:
        from loom.registrations import get_registration_stats
        
        uptime = int(time.time() - _start_time)
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 346
        
        # Get registration statistics
        reg_stats = get_registration_stats()
        
        # Try to get memory usage
        memory_mb = None
        try:
            import psutil
            memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
        except (ImportError, Exception):
            pass
        
        health_response = {
            "status": "healthy",
            "startup_validation_status": _health_status,
            "startup_validation_result": _startup_validation_result,
            "uptime_seconds": uptime,
            "tool_count": tool_count,
            "strategy_count": 957,
            "registration_stats": reg_stats.get("registration_stats", {}),
            "optional_modules_loaded": reg_stats.get("optional_modules_loaded", 0),
            "import_failures": reg_stats.get("import_failures", []),
            "total_tools_loaded": reg_stats.get("total_loaded", 0),
            "total_tools_failed": reg_stats.get("total_failed", 0),
            "validation_errors_found": _validation_error_count,
            "prometheus_enabled": _prometheus_enabled,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        if memory_mb is not None:
            health_response["memory_mb"] = memory_mb
        return JSONResponse(health_response)

    # Register Prometheus metrics endpoint if available
    if _prometheus_enabled:
        @mcp.custom_route("/metrics", methods=["GET"])
        async def metrics_endpoint(request: Request) -> Response:
            """Prometheus metrics endpoint (OpenMetrics format)."""
            metrics_output = generate_latest(_PROMETHEUS_REGISTRY)
            return Response(
                content=metrics_output,
                media_type="text/plain; charset=utf-8; version=0.0.4",
            )
        log.info("prometheus_metrics_endpoint_registered")

    # API versioning endpoints
    @mcp.custom_route("/versions", methods=["GET"])
    async def versions_endpoint(request: Request) -> JSONResponse:
        """Get available API versions and their status."""
        return JSONResponse(get_version_info())

    # Versioned routes: /v1/ prefix routes
    @mcp.custom_route("/v1/", methods=["GET"])
    async def v1_root_endpoint(request: Request) -> JSONResponse:
        """API v1 root endpoint with version info."""
        return JSONResponse({
            "api_version": "v1",
            "service": "loom",
            "version": "3.0.0",
            "description": "Loom MCP Research Server — 303 tools, 957 strategies",
            "endpoints": {
                "health": "/v1/health",
                "metrics": "/v1/metrics" if _prometheus_enabled else None,
            },
            "status": "running",
        })

    @mcp.custom_route("/v1/health", methods=["GET"])
    async def v1_health_endpoint(request: Request) -> JSONResponse:
        """Health check endpoint for API v1 (with version header)."""
        from loom.registrations import get_registration_stats, get_registration_errors
        
        uptime = int(time.time() - _start_time)
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 346
        
        # Get registration statistics
        reg_stats = get_registration_stats()
        reg_errors = get_registration_errors()
        
        # Determine overall health status based on registration failure rate
        reg_health = reg_stats.get("health_status", "healthy")
        overall_status = "degraded" if reg_health == "degraded" else "healthy"
        
        # Try to get memory usage
        memory_mb = None
        try:
            import psutil
            memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
        except (ImportError, Exception):
            pass
        
        health_response = {
            "api_version": "v1",
            "status": overall_status,
            "registration_health": reg_health,
            "startup_validation_status": _health_status,
            "startup_validation_result": _startup_validation_result,
            "uptime_seconds": uptime,
            "tool_count": tool_count,
            "strategy_count": 957,
            "registration_stats": reg_stats.get("registration_stats", {}),
            "optional_modules_loaded": reg_stats.get("optional_modules_loaded", 0),
            "import_failures": reg_stats.get("import_failures", []),
            "total_tools_loaded": reg_stats.get("total_loaded", 0),
            "total_tools_failed": reg_stats.get("total_failed", 0),
            "failure_rate_percent": reg_stats.get("failure_rate_percent", 0.0),
            "registration_errors": reg_errors,
            "validation_errors_found": _validation_error_count,
            "prometheus_enabled": _prometheus_enabled,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        if memory_mb is not None:
            health_response["memory_mb"] = memory_mb
        return JSONResponse(health_response)

    @mcp.custom_route("/v1/health/deep", methods=["GET"])
    async def v1_health_deep_endpoint(request: Request) -> JSONResponse:
        """Deep diagnostics health check endpoint for API v1.

        Performs comprehensive subsystem checks:
        - Database connectivity (Redis, PostgreSQL)
        - LLM provider API validation
        - Search provider API validation
        - Disk space and cache health
        - Memory and CPU metrics
        - Tool registry verification
        - Import diagnostics
        - Rate limiter state
        - Circuit breaker status
        """
        try:
            from loom.tools.health_deep import research_health_deep

            result = await research_health_deep()
            return JSONResponse(result)
        except Exception as e:
            log.error("health_deep_check_failed error=%s", str(e))
            return JSONResponse(
                {
                    "status": "unhealthy",
                    "error": "Deep health check failed",
                    "details": str(e),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                status_code=500,
            )

    @mcp.custom_route("/health/deep", methods=["GET"])
    async def health_deep_endpoint(request: Request) -> JSONResponse:
        """Deep diagnostics health check endpoint (unversioned, deprecated).

        Performs comprehensive subsystem checks. Prefer /v1/health/deep.
        """
        try:
            from loom.tools.health_deep import research_health_deep

            result = await research_health_deep()
            return JSONResponse(result)
        except Exception as e:
            log.error("health_deep_check_failed error=%s", str(e))
            return JSONResponse(
                {
                    "status": "unhealthy",
                    "error": "Deep health check failed",
                    "details": str(e),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                status_code=500,
            )


    # Register Prometheus metrics endpoint for v1 if available
    if _prometheus_enabled:
        @mcp.custom_route("/v1/metrics", methods=["GET"])
        async def v1_metrics_endpoint(request: Request) -> Response:
            """Prometheus metrics endpoint for API v1 (with version header)."""
            metrics_output = generate_latest(_PROMETHEUS_REGISTRY)
            return Response(
                content=metrics_output,
                media_type="text/plain; charset=utf-8; version=0.0.4",
            )
        log.info("prometheus_metrics_v1_endpoint_registered")


    # Register OpenAPI schema endpoint
    @mcp.custom_route("/openapi.json", methods=["GET"])
    async def openapi_endpoint(request: Request) -> JSONResponse:
        """Serve OpenAPI 3.1 specification for all registered tools."""
        from loom.openapi_gen import get_openapi_spec

        try:
            spec = get_openapi_spec(mcp, bypass_cache=False)
            return JSONResponse(spec)
        except Exception as e:
            log.error("openapi_spec_generation_failed error=%s", e)
            return JSONResponse(
                {"error": "Failed to generate OpenAPI spec", "details": str(e)},
                status_code=500,
            )

    # Register Swagger UI endpoint
    @mcp.custom_route("/docs", methods=["GET"])
    async def swagger_ui_endpoint(request: Request) -> Response:
        """Serve interactive Swagger UI for API documentation."""
        html = """
<!DOCTYPE html>
<html>
  <head>
    <title>Loom API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
    <style>
      html {
        box-sizing: border-box;
        overflow: -moz-scrollbars-vertical;
        overflow-y: scroll;
      }
      *, *:before, *:after {
        box-sizing: inherit;
      }
      body {
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <script>
      window.onload = function() {
        const ui = SwaggerUIBundle({
          url: "/openapi.json",
          dom_id: '#swagger-ui',
          presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIBundle.SwaggerUIStandalonePreset
          ],
          layout: "BaseLayout",
          requestInterceptor: (request) => {
            // Add Bearer token if present in localStorage
            const token = localStorage.getItem('api_token');
            if (token) {
              request.headers['Authorization'] = `Bearer ${token}`;
            }
            return request;
          }
        })
        window.ui = ui
      }
    </script>
  </body>
</html>
        """
        return Response(content=html, media_type="text/html")

    # Register ReDoc endpoint (alternative documentation)
    @mcp.custom_route("/redoc", methods=["GET"])
    async def redoc_endpoint(request: Request) -> Response:
        """Serve ReDoc alternative API documentation."""
        html = """
<!DOCTYPE html>
<html>
  <head>
    <title>Loom API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
      body {
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <redoc spec-url="/openapi.json"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
  </body>
</html>
        """
        return Response(content=html, media_type="text/html")

    log.info("openapi_endpoints_registered paths=/openapi.json,/docs,/redoc")

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

    # Wire API key authentication middleware (optional, opt-in via LOOM_AUTH_REQUIRED)
    # Wire request ID / correlation ID middleware (must come first in the stack)
    mcp.app.add_middleware(RequestIdMiddleware)
    log.info("request_id_middleware_registered")

    mcp.app.add_middleware(ApiKeyAuthMiddleware)
    log.info("api_auth_middleware_registered auth_required=%s",
             os.environ.get("LOOM_AUTH_REQUIRED", "false").lower() == "true")

    # Wire CORS middleware (configurable via LOOM_CORS_ENABLED and LOOM_CORS_ORIGINS)
    if os.environ.get("LOOM_CORS_ENABLED", "true").lower() == "true":
        origins = os.environ.get("LOOM_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        mcp.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        log.info("cors_middleware_registered origins=%s", origins)
    else:
        log.info("cors_middleware_disabled")


    # Start batch queue background processing
    try:
        start_batch_queue_background()
        log.info("batch_queue_background_started")
    except Exception as exc:
        log.error("batch_queue_startup_failed: %s", exc)

    return mcp


async def _shutdown() -> None:
    """Graceful shutdown: close all browser sessions, HTTP clients, and providers.
    
    Cleanup sequence:
    1. Mark server as shutting down (reject new requests)
    2. Wait up to 30s for in-flight requests to complete
    3. Flush DLQ (deadletter queue) if exists
    4. Save strategy adapter state
    5. Close database/Redis connections
    6. Close HTTP client pool
    7. Close LLM provider clients
    8. Stop batch queue background processing
    """
    _set_shutting_down()
    
    # Wait briefly for in-flight requests
    try:
        await asyncio.sleep(0.5)
        log.info("shutdown_grace_period_active max_wait_seconds=5")
    except Exception:
        pass
    
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

    # Flush DLQ (deadletter queue) if it exists
    try:
        from loom.batch_queue import get_dlq
        dlq = get_dlq()
        if dlq and hasattr(dlq, 'flush'):
            flushed = await dlq.flush()
            log.info("shutdown_dlq_flushed count=%d", len(flushed) if isinstance(flushed, list) else 0)
    except (ImportError, AttributeError):
        pass
    except Exception as exc:
        log.warning("shutdown_dlq_flush_failed: %s", exc)
    
    # Save strategy adapter state if it exists
    try:
        from loom.reid_auto import ReidAutoReframe
        adapter = ReidAutoReframe._instance if hasattr(ReidAutoReframe, '_instance') else None
        if adapter and hasattr(adapter, 'save_state'):
            await adapter.save_state()
            log.info("shutdown_strategy_state_saved")
    except (ImportError, AttributeError):
        pass
    except Exception as exc:
        log.warning("shutdown_strategy_state_save_failed: %s", exc)

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

    # Stop batch queue background processing
    try:
        stop_batch_queue_background()
        log.info("batch_queue_background_stopped")
    except Exception as exc:
        log.error("batch_queue_shutdown_failed: %s", exc)

    log.info("shutdown_complete")


_background_tasks: set[asyncio.Task[None]] = set()


def _handle_signal(sig: int, _frame: Any) -> None:
    """Signal handler that runs graceful shutdown in a new event loop."""
    _set_shutting_down()
    log.info("signal_handler_invoked signal=%s", signal.Signals(sig).name)
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
