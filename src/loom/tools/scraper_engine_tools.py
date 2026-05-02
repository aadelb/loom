"""MCP tool wrappers for ScraperEngine escalation system.

Registers three tools:
- research_engine_fetch: Single URL fetch with escalation
- research_engine_extract: Fetch + selector/LLM extraction
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
from loom.tools.fetch import research_fetch

logger = logging.getLogger("loom.tools.scraper_engine_tools")


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
    logger.info("engine_fetch_start url=%s mode=%s max_escalation=%s", params.url, params.mode, params.max_escalation)

    # Delegate to research_fetch which handles the actual escalation
    result = await research_fetch(
        url=params.url,
        stealthy=params.mode == "stealthy",
        dynamic=params.mode == "dynamic",
    )

    logger.info(
        "engine_fetch_complete url=%s success=%s elapsed=%s",
        params.url,
        result.get("success"),
        result.get("elapsed_ms", 0),
    )

    # Map fetch result to engine format
    return {
        "url": result.get("url", params.url),
        "success": result.get("success", False),
        "content": result.get("content") if result.get("success") else None,
        "content_preview": result.get("content", "")[:500] if result.get("content") else None,
        "backend_used": result.get("backend_used", "unknown"),
        "escalation_level": result.get("escalation_level", 0),
        "escalation_history": result.get("escalation_history", []),
        "content_type": result.get("content_type", "text/html"),
        "status_code": result.get("status_code", 0),
        "title": result.get("title", ""),
        "elapsed_ms": result.get("elapsed_ms", 0),
        "error": result.get("error"),
    }


async def research_engine_extract(params: ScraperEngineExtractParams) -> dict[str, Any]:
    """Fetch + selector/LLM-powered structured data extraction.

    First fetches the URL with automatic escalation, then extracts data using
    either CSS selectors, XPath, or LLM-based extraction based on provided rules.

    Args:
        params: ScraperEngineExtractParams with url, query, selectors, model, mode

    Returns:
        Dict with:
        - success: bool
        - url: str
        - backend_used: str
        - escalation_level: int
        - extracted: dict (if successful)
        - error: str (if failed)
        - fetch_elapsed_ms: int
        - extraction_method: str ("css_selector" | "xpath" | "llm")
    """
    logger.info(
        "engine_extract_start url=%s query=%s css=%s xpath=%s model=%s",
        params.url,
        params.query[:50] if params.query else None,
        "yes" if params.css_selector else "no",
        "yes" if params.xpath_selector else "no",
        params.model,
    )

    # First fetch the content
    fetch_result = await research_fetch(
        url=params.url,
        stealthy=params.mode == "stealth",
        dynamic=params.mode == "max",
    )

    if not fetch_result.get("success"):
        logger.warning("engine_extract_fetch_failed url=%s", params.url)
        return {
            "success": False,
            "url": params.url,
            "backend_used": fetch_result.get("backend_used", "unknown"),
            "escalation_level": fetch_result.get("escalation_level", 0),
            "error": f"Failed to fetch: {fetch_result.get('error', 'unknown error')}",
            "fetch_elapsed_ms": fetch_result.get("elapsed_ms", 0),
        }

    content = fetch_result.get("content", "")

    # Try CSS selector extraction first if provided
    if params.css_selector:
        try:
            from parsel import Selector

            selector = Selector(text=content)
            elements = selector.css(params.css_selector).getall()
            if elements:
                logger.info("engine_extract_css_success url=%s count=%d", params.url, len(elements))
                return {
                    "success": True,
                    "url": params.url,
                    "backend_used": fetch_result.get("backend_used", "unknown"),
                    "escalation_level": fetch_result.get("escalation_level", 0),
                    "extracted": {
                        "query": params.query,
                        "selector": params.css_selector,
                        "raw_data": elements,
                        "extracted_count": len(elements),
                        "extraction_method": "css_selector",
                    },
                    "fetch_elapsed_ms": fetch_result.get("elapsed_ms", 0),
                    "extraction_method": "css_selector",
                }
            else:
                logger.warning("engine_extract_css_no_matches url=%s selector=%s", params.url, params.css_selector)
        except Exception as e:
            logger.warning("engine_extract_css_failed url=%s: %s", params.url, e)

    # Try XPath extraction if provided
    if params.xpath_selector:
        try:
            from lxml import etree

            try:
                parser = etree.HTMLParser()
                tree = etree.fromstring(content.encode(), parser)
            except Exception:
                tree = etree.fromstring(content.encode())

            elements = tree.xpath(params.xpath_selector)
            if elements:
                extracted_values = []
                for elem in elements:
                    if hasattr(elem, "text_content"):
                        extracted_values.append(elem.text_content())
                    else:
                        extracted_values.append(str(elem))

                logger.info("engine_extract_xpath_success url=%s count=%d", params.url, len(extracted_values))
                return {
                    "success": True,
                    "url": params.url,
                    "backend_used": fetch_result.get("backend_used", "unknown"),
                    "escalation_level": fetch_result.get("escalation_level", 0),
                    "extracted": {
                        "query": params.query,
                        "selector": params.xpath_selector,
                        "raw_data": extracted_values,
                        "extracted_count": len(extracted_values),
                        "extraction_method": "xpath",
                    },
                    "fetch_elapsed_ms": fetch_result.get("elapsed_ms", 0),
                    "extraction_method": "xpath",
                }
            else:
                logger.warning("engine_extract_xpath_no_matches url=%s xpath=%s", params.url, params.xpath_selector)
        except Exception as e:
            logger.warning("engine_extract_xpath_failed url=%s: %s", params.url, e)

    # Fallback to LLM extraction if selectors not provided or failed
    try:
        from loom.tools.llm import _call_with_cascade

        extraction_prompt = f"Extract the following from this HTML content: {params.query}\n\nContent:\n{content[:5000]}"
        extracted_text = await _call_with_cascade(extraction_prompt, max_tokens=1000)

        logger.info("engine_extract_llm_complete url=%s success=true", params.url)

        return {
            "success": True,
            "url": params.url,
            "backend_used": fetch_result.get("backend_used", "unknown"),
            "escalation_level": fetch_result.get("escalation_level", 0),
            "extracted": {
                "query": params.query,
                "result": extracted_text,
                "model_used": params.model,
                "extraction_method": "llm",
            },
            "fetch_elapsed_ms": fetch_result.get("elapsed_ms", 0),
            "extraction_method": "llm",
        }
    except Exception as e:
        logger.error("engine_extract_llm_failed: %s", e)
        return {
            "success": False,
            "url": params.url,
            "backend_used": fetch_result.get("backend_used", "unknown"),
            "escalation_level": fetch_result.get("escalation_level", 0),
            "error": f"All extraction methods failed: {str(e)[:100]}",
            "fetch_elapsed_ms": fetch_result.get("elapsed_ms", 0),
        }


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
    logger.info(
        "engine_batch_start urls_count=%d mode=%s max_concurrent=%d fail_fast=%s",
        len(params.urls),
        params.mode,
        params.max_concurrent,
        params.fail_fast,
    )

    # Fetch URLs with concurrency limit
    results = []
    succeeded = 0
    failed = 0
    total_elapsed_ms = 0

    # Use asyncio semaphore for concurrency control
    semaphore = asyncio.Semaphore(params.max_concurrent)

    async def fetch_one(url: str) -> dict[str, Any]:
        async with semaphore:
            try:
                result = await research_fetch(
                    url=url,
                    stealthy=params.mode == "stealthy",
                    dynamic=params.mode == "dynamic",
                )
                return result
            except Exception as e:
                logger.debug("batch_fetch_failed url=%s: %s", url, e)
                return {
                    "url": url,
                    "success": False,
                    "error": str(e)[:100],
                }

    # Fetch all URLs
    tasks = [fetch_one(url) for url in params.urls]
    batch_results = await asyncio.gather(*tasks, return_exceptions=False)

    for result in batch_results:
        if result.get("success"):
            succeeded += 1
        else:
            failed += 1
        total_elapsed_ms += result.get("elapsed_ms", 0)
        results.append(result)

        if params.fail_fast and failed > 0:
            break

    logger.info(
        "engine_batch_complete urls_count=%d success=%s succeeded=%d failed=%d",
        len(params.urls),
        succeeded == len(params.urls),
        succeeded,
        failed,
    )

    return {
        "success": failed == 0,
        "results": results,
        "stats": {
            "total": len(params.urls),
            "succeeded": succeeded,
            "failed": failed,
            "total_elapsed_ms": total_elapsed_ms,
        },
    }
