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
