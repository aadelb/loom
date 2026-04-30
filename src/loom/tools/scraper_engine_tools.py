"""MCP tool wrappers for ScraperEngine escalation system.

Registers three tools:
- research_engine_fetch: Single URL fetch with escalation
- research_engine_extract: Fetch + LLM extraction
- research_engine_batch: Batch fetch multiple URLs
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from loom.params import (
    ScraperEngineFetchParams,
    ScraperEngineExtractParams,
    ScraperEngineBatchParams,
)
from loom.scraper_engine import ScraperEngine

logger = logging.getLogger("loom.tools.scraper_engine_tools")

# Singleton engine instance
_engine: ScraperEngine | None = None


def _get_engine() -> ScraperEngine:
    """Get or create singleton ScraperEngine instance."""
    global _engine
    if _engine is None:
        _engine = ScraperEngine(cache_enabled=True, max_retries=3)
    return _engine


async def research_engine_fetch(params: ScraperEngineFetchParams) -> dict[str, Any]:
    """Fetch URL with automatic backend escalation.

    Chains through HTTP → Scrapling → Crawl4AI → Patchright → nodriver →
    zendriver → Camoufox → Botasaurus with automatic escalation on failure.

    Args:
        params: ScraperEngineFetchParams with url, mode, max_escalation, etc.

    Returns:
        Dict with:
        - success: bool
        - content: str
        - backend_used: str (e.g., "httpx", "crawl4ai", "camoufox")
        - escalation_level: int (0-7)
        - escalation_history: list of backends tried
        - url: str
        - error: str or None
        - elapsed_ms: int
    """
    engine = _get_engine()

    logger.info("engine_fetch_start url=%s mode=%s max_escalation=%s", params.url, params.mode, params.max_escalation)

    result = await engine.fetch(
        url=params.url,
        mode=params.mode,
        max_escalation=params.max_escalation,
        extract_title=params.extract_title,
        force_backend=params.force_backend,
    )

    logger.info(
        "engine_fetch_complete url=%s success=%s backend=%s level=%s elapsed=%s",
        params.url,
        result.success,
        result.backend_used,
        result.escalation_level,
        result.elapsed_ms,
    )

    return {
        "url": result.url,
        "success": result.success,
        "content": result.content if result.success else None,
        "content_preview": result.content[:500] if result.content else None,
        "backend_used": result.backend_used,
        "escalation_level": result.escalation_level,
        "escalation_history": result.escalation_history,
        "content_type": result.content_type,
        "status_code": result.status_code,
        "title": result.title,
        "elapsed_ms": result.elapsed_ms,
        "error": result.error,
    }


async def research_engine_extract(params: ScraperEngineExtractParams) -> dict[str, Any]:
    """Fetch + LLM-powered structured data extraction.

    First fetches the URL with automatic escalation, then uses LLM to extract
    structured data based on the provided query.

    Args:
        params: ScraperEngineExtractParams with url, query, model, mode

    Returns:
        Dict with:
        - success: bool
        - url: str
        - backend_used: str
        - escalation_level: int
        - extracted: dict (if successful)
        - error: str (if failed)
        - fetch_elapsed_ms: int
    """
    engine = _get_engine()

    logger.info("engine_extract_start url=%s query=%s model=%s", params.url, params.query[:50], params.model)

    result = await engine.smart_extract(
        url=params.url,
        query=params.query,
        model=params.model,
        mode=params.mode,
    )

    logger.info("engine_extract_complete url=%s success=%s", params.url, result.get("success"))

    return result


async def research_engine_batch(params: ScraperEngineBatchParams) -> dict[str, Any]:
    """Batch fetch multiple URLs with per-URL escalation.

    Fetches a list of URLs concurrently with configurable concurrency limit.
    Each URL is escalated independently if needed.

    Args:
        params: ScraperEngineBatchParams with urls, mode, max_concurrent, fail_fast

    Returns:
        Dict with:
        - success: bool (True if all succeeded)
        - results: list of fetch results
        - stats: dict with succeeded/failed/total counts and timing
    """
    engine = _get_engine()

    logger.info(
        "engine_batch_start urls_count=%d mode=%s max_concurrent=%d fail_fast=%s",
        len(params.urls),
        params.mode,
        params.max_concurrent,
        params.fail_fast,
    )

    result = await engine.batch_fetch(
        urls=params.urls,
        mode=params.mode,
        max_concurrent=params.max_concurrent,
        fail_fast=params.fail_fast,
    )

    logger.info(
        "engine_batch_complete urls_count=%d success=%s succeeded=%d failed=%d",
        len(params.urls),
        result["success"],
        result["stats"].get("succeeded", 0),
        result["stats"].get("failed", 0),
    )

    return result
