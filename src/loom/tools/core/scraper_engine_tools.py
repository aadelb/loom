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

from loom.error_responses import handle_tool_errors
from loom.validators import validate_url, UrlSafetyError

try:
	from loom.params import (
		ScraperEngineFetchParams,
		ScraperEngineExtractParams,
		ScraperEngineBatchParams,
	)
	from loom.tools.core.fetch import research_fetch
	_SCRAPER_DEPS = True
except ImportError:
	_SCRAPER_DEPS = False

logger = logging.getLogger("loom.tools.scraper_engine_tools")


def _map_engine_mode_to_fetch_mode(engine_mode: str) -> str:
	"""Map ScraperEngine modes to research_fetch modes.

	ScraperEngine modes: ["auto", "stealth", "max", "fast"]
	research_fetch modes: ["http", "stealthy", "dynamic"]

	Mapping:
	- "fast" -> "http" (fastest, least stealthy)
	- "auto" -> "stealthy" (balanced)
	- "stealth" -> "stealthy" (stealthy)
	- "max" -> "dynamic" (most thorough with browser)
	"""
	mode_map = {
		"fast": "http",
		"auto": "stealthy",
		"stealth": "stealthy",
		"max": "dynamic",
	}
	return mode_map.get(engine_mode, "stealthy")


@handle_tool_errors("research_engine_fetch")
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
	try:
		# Extract URL from params (handle both Pydantic objects and dicts)
		url = params.url if hasattr(params, "url") else params.get("url", str(params))
		engine_mode = params.mode if hasattr(params, "mode") else params.get("mode", "auto")
		max_escalation = (
			params.max_escalation
			if hasattr(params, "max_escalation")
			else params.get("max_escalation", 7)
		)

		validate_url(url)

		# Map engine mode to fetch mode
		fetch_mode = _map_engine_mode_to_fetch_mode(engine_mode)

		logger.info(
			"engine_fetch_start url=%s engine_mode=%s fetch_mode=%s max_escalation=%s",
			url,
			engine_mode,
			fetch_mode,
			max_escalation,
		)

		# Delegate to research_fetch which handles the actual escalation
		result = await research_fetch(
			url=url,
			mode=fetch_mode,
		)

		logger.info(
			"engine_fetch_complete url=%s success=%s elapsed=%s",
			url,
			result.get("success"),
			result.get("elapsed_ms", 0),
		)

		# Map fetch result to engine format
		return {
			"success": result.get("success", False),
			"url": url,
			"content": result.get("content", ""),
			"backend_used": result.get("backend_used", "unknown"),
			"escalation_level": result.get("escalation_level", 0),
			"escalation_history": result.get("escalation_history", []),
			"error": result.get("error"),
			"elapsed_ms": result.get("elapsed_ms", 0),
		}
	except Exception as exc:
		logger.error("engine_fetch_error: %s", exc)
		return {"error": str(exc), "tool": "research_engine_fetch"}


@handle_tool_errors("research_engine_extract")
async def research_engine_extract(params: ScraperEngineExtractParams) -> dict[str, Any]:
	"""Fetch + selector/LLM-powered structured data extraction.

	Chains through HTTP → Scrapling → Crawl4AI → Patchright → nodriver →
	zendriver → Camoufox → Botasaurus with automatic escalation on failure.
	Then uses CSS selectors or LLM to extract structured data.

	Args:
		params: ScraperEngineExtractParams with url, selector/llm_extract, mode, etc.

	Returns:
		Dict with:
		- success: bool
		- url: str
		- extracted_data: dict or list
		- extraction_method: str ("css_selector", "llm", or "both")
		- backend_used: str
		- error: str or None
	"""
	try:
		# Extract parameters
		url = params.url if hasattr(params, "url") else params.get("url", str(params))
		selector = (
			params.selector if hasattr(params, "selector") else params.get("selector", "")
		)
		llm_extract = (
			params.llm_extract
			if hasattr(params, "llm_extract")
			else params.get("llm_extract", False)
		)
		mode = params.mode if hasattr(params, "mode") else params.get("mode", "auto")

		validate_url(url)

		logger.info(
			"engine_extract_start url=%s selector=%s llm_extract=%s",
			url,
			selector[:50] if selector else "none",
			llm_extract,
		)

		# Fetch content first
		fetch_mode = _map_engine_mode_to_fetch_mode(mode)
		fetch_result = await research_fetch(url=url, mode=fetch_mode)

		if not fetch_result.get("success"):
			return {
				"success": False,
				"url": url,
				"extracted_data": None,
				"extraction_method": "none",
				"backend_used": fetch_result.get("backend_used", "unknown"),
				"error": fetch_result.get("error", "fetch failed"),
			}

		content = fetch_result.get("content", "")

		# Extract using CSS selector if provided
		extracted_data: dict[str, Any] | list[Any] | None = None
		extraction_method = "none"

		if selector and content:
			try:
				from lxml import html

				doc = html.fromstring(content)
				elements = doc.cssselect(selector)

				if elements:
					extraction_method = "css_selector"
					extracted_data = [
						{
							"text": elem.text_content()[:500],
							"html": html.tostring(elem, encoding="unicode")[:500],
						}
						for elem in elements[:20]
					]
			except Exception as e:
				logger.warning("css_extraction_failed: %s", e)

		# Extract using LLM if requested and content available
		if llm_extract and content:
			try:
				from loom.tools.llm.llm import research_llm_extract

				extract_result = await research_llm_extract(
					text=content[:5000],
					extraction_schema="key-value pairs",
				)

				if extract_result.get("success"):
					llm_data = extract_result.get("extracted_data", {})
					if extracted_data:
						extraction_method = "both"
						if isinstance(extracted_data, list):
							extracted_data.append({"llm_extracted": llm_data})
					else:
						extraction_method = "llm"
						extracted_data = {"llm_extracted": llm_data}
			except Exception as e:
				logger.warning("llm_extraction_failed: %s", e)

		return {
			"success": bool(extracted_data),
			"url": url,
			"extracted_data": extracted_data,
			"extraction_method": extraction_method,
			"backend_used": fetch_result.get("backend_used", "unknown"),
			"error": None if extracted_data else "no data extracted",
		}
	except Exception as exc:
		logger.error("engine_extract_error: %s", exc)
		return {"error": str(exc), "tool": "research_engine_extract"}


@handle_tool_errors("research_engine_batch")
async def research_engine_batch(params: ScraperEngineBatchParams) -> dict[str, Any]:
	"""Batch fetch multiple URLs with escalation and concurrent limiting.

	Fetches multiple URLs in parallel (respecting concurrency limit) with
	automatic escalation chain for each URL.

	Args:
		params: ScraperEngineBatchParams with urls, mode, max_concurrent, etc.

	Returns:
		Dict with:
		- success: bool (all URLs succeeded)
		- total_urls: int
		- successful: int
		- failed: int
		- results: list of fetch results for each URL
		- error: str or None
	"""
	try:
		# Extract parameters
		urls = params.urls if hasattr(params, "urls") else params.get("urls", [])
		mode = params.mode if hasattr(params, "mode") else params.get("mode", "auto")
		max_concurrent = (
			params.max_concurrent
			if hasattr(params, "max_concurrent")
			else params.get("max_concurrent", 5)
		)

		if not urls:
			return {
				"success": False,
				"total_urls": 0,
				"successful": 0,
				"failed": 0,
				"results": [],
				"error": "no URLs provided",
			}

		# Validate all URLs
		for url in urls:
			validate_url(url)

		logger.info(
			"engine_batch_start total_urls=%d max_concurrent=%s",
			len(urls),
			max_concurrent,
		)

		fetch_mode = _map_engine_mode_to_fetch_mode(mode)

		# Fetch URLs with concurrency limit
		async def _fetch_with_limit(semaphore: asyncio.Semaphore, url: str) -> dict[str, Any]:
			async with semaphore:
				result = await research_fetch(url=url, mode=fetch_mode)
				return {"url": url, **result}

		semaphore = asyncio.Semaphore(max_concurrent)
		tasks = [_fetch_with_limit(semaphore, url) for url in urls]
		results = await asyncio.gather(*tasks, return_exceptions=True)
		# Filter out exceptions from results
		results = [r for r in results if not isinstance(r, Exception)]

		successful = sum(1 for r in results if r.get("success"))
		failed = len(results) - successful

		logger.info(
			"engine_batch_complete total=%d successful=%d failed=%d",
			len(results),
			successful,
			failed,
		)

		return {
			"success": failed == 0,
			"total_urls": len(results),
			"successful": successful,
			"failed": failed,
			"results": results,
			"error": None if failed == 0 else f"{failed} URLs failed",
		}
	except Exception as exc:
		logger.error("engine_batch_error: %s", exc)
		return {"error": str(exc), "tool": "research_engine_batch"}
