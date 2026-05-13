"""Standalone tool functions extracted from server.py.

These are MCP tool implementations that were defined in server.py but don't
depend on server internals. They're registered via _register_tools() and
also imported by health_deep.py, health_dashboard.py, registrations/core.py.
"""
from __future__ import annotations

import os
import time
import logging
from datetime import UTC, datetime
from typing import Any

from loom.server_state import get_start_time

log = logging.getLogger("loom.tool_functions")

# ── Dynamic strategy count caching ──
_STRATEGY_COUNT: int | None = None


def _get_strategy_count() -> int:
    """Get cached strategy count from ALL_STRATEGIES registry."""
    global _STRATEGY_COUNT
    if _STRATEGY_COUNT is None:
        try:
            from loom.tools.reframe_strategies import ALL_STRATEGIES
            _STRATEGY_COUNT = len(ALL_STRATEGIES)
        except (ImportError, Exception):
            _STRATEGY_COUNT = 0
    return _STRATEGY_COUNT


def _check_llm_provider_available(provider_name: str) -> bool:
    """Check if an LLM provider is configured (without making API calls)."""
    env_keys: dict[str, str] = {
        "groq": "GROQ_API_KEY",
        "nvidia_nim": "NVIDIA_NIM_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GOOGLE_AI_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "vllm": "VLLM_ENDPOINT",
    }
    key = env_keys.get(provider_name)
    if not key:
        return False
    return bool(os.environ.get(key, "").strip())


def _check_search_provider_available(provider_name: str) -> bool:
    """Check if a search provider is configured (without making API calls)."""
    always_available = {"ddgs", "arxiv", "wikipedia", "hackernews", "reddit"}
    if provider_name in always_available:
        return True

    env_keys: dict[str, str] = {
        "exa": "EXA_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "firecrawl": "FIRECRAWL_API_KEY",
        "brave": "BRAVE_API_KEY",
        "newsapi": "NEWS_API_KEY",
        "coindesk": "NEWS_API_KEY",
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
    return bool(os.environ.get(key, "").strip())


async def research_health_check() -> dict[str, Any]:
    """Return comprehensive server health status for monitoring."""
    from loom import __version__
    from loom.cache import get_cache
    from loom.sessions import _sessions

    uptime_seconds = int(time.time() - get_start_time())
    active_sessions = len(_sessions)

    llm_provider_names = [
        "groq", "nvidia_nim", "deepseek", "gemini",
        "moonshot", "openai", "anthropic", "vllm",
    ]
    llm_providers: dict[str, dict[str, Any]] = {}
    for name in llm_provider_names:
        llm_providers[name] = {"status": "up" if _check_llm_provider_available(name) else "down"}

    search_provider_names = [
        "exa", "tavily", "firecrawl", "brave", "ddgs",
        "arxiv", "wikipedia", "hackernews", "reddit",
        "newsapi", "coindesk", "coinmarketcap", "binance",
        "ahmia", "darksearch", "ummro_rag", "onionsearch",
        "torcrawl", "darkweb_cti", "robin_osint", "investing",
    ]
    search_providers: dict[str, dict[str, Any]] = {}
    for name in search_provider_names:
        search_providers[name] = {"status": "up" if _check_search_provider_available(name) else "down"}

    cache = get_cache()
    cache_stats = cache.stats()
    cache_size_mb = round(cache_stats.get("total_bytes", 0) / (1024 * 1024), 2)

    llm_up = sum(1 for p in llm_providers.values() if p["status"] == "up")
    search_up = sum(1 for p in search_providers.values() if p["status"] == "up")

    if llm_up == 0 or search_up == 0:
        overall_status = "unhealthy"
    elif llm_up < len(llm_provider_names) or search_up < len(search_provider_names):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "uptime_seconds": uptime_seconds,
        "tool_count": 885,
        "strategy_count": _get_strategy_count(),
        "llm_providers": llm_providers,
        "search_providers": search_providers,
        "cache": {
            "entries": cache_stats.get("file_count", 0),
            "size_mb": cache_size_mb,
            "hit_rate": 0.0,
        },
        "sessions": {"active": active_sessions, "max": 10},
        "version": __version__,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def research_cpu_pool_status() -> dict[str, Any]:
    """Get CPU executor pool status and statistics."""
    try:
        from loom.cpu_pool import get_pool_stats
        return get_pool_stats()
    except ImportError:
        return {"status": "unavailable", "reason": "cpu_pool module not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def research_cpu_executor_shutdown() -> dict[str, Any]:
    """Gracefully shut down the CPU executor pool."""
    try:
        from loom.cpu_pool import shutdown_pool
        result = await shutdown_pool()
        return {"status": "shutdown_complete", **result}
    except ImportError:
        return {"status": "unavailable", "reason": "cpu_pool module not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def research_coverage_run(
    tools_to_test: list[str] | None = None,
    timeout: float = 30.0,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Run comprehensive test coverage across all MCP tools."""
    from loom.test_runner import ToolCoverageRunner

    runner = ToolCoverageRunner(mcp_app=None, dry_run=dry_run)
    results = await runner.run_coverage(tools_to_test=tools_to_test, timeout=timeout)
    results["report_markdown"] = runner.generate_coverage_report(results)
    return results


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