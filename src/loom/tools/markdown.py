"""research_markdown — Crawl4AI async markdown extractor for LLM-ready content."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from loom.cache import CacheStore, _utc_now_iso
from loom.params import MarkdownParams
from loom.validators import EXTERNAL_TIMEOUT_SECS

log = logging.getLogger("loom.tools.markdown")

# Global cache instance
_cache: CacheStore | None = None


def _get_cache() -> CacheStore:
    """Get or initialize the global cache store."""
    global _cache
    if _cache is None:
        _cache = CacheStore()
    return _cache


async def research_markdown(
    url: str,
    bypass_cache: bool = False,
    css_selector: str | None = None,
    js_before_scrape: str | None = None,
    screenshot: bool = False,
    remove_selectors: list[str] | None = None,
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    proxy: str | None = None,
    cookies: dict[str, str] | None = None,
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8",
    timeout: int | None = None,  # noqa: ASYNC109
    extract_selector: str | None = None,
    wait_for: str | None = None,
) -> dict[str, Any]:
    """Extract clean LLM-ready markdown via Crawl4AI with optional CSS subtree
    and JS execution.

    Async-native to avoid asyncio.run() reentrancy inside FastMCP's event
    loop. URL is validated for SSRF safety before fetch.

    Args:
        url: target URL
        bypass_cache: force refetch
        css_selector: extract only this CSS subtree before markdown
        js_before_scrape: small JS to execute before scraping (max 2KB)
        screenshot: capture screenshot (writes to cache/screenshots/)
        remove_selectors: CSS selectors to remove before extraction
        headers: custom headers
        user_agent: override UA
        proxy: proxy URL
        cookies: cookies dict
        accept_language: header value
        timeout: per-call timeout override (capped)
        extract_selector: alias for css_selector
        wait_for: CSS selector to wait for before scraping

    Returns:
        Dict with: url, title, markdown, tool, fetched_at, and optionally
        error if fetch failed.
    """
    # Validate and normalize params
    params = MarkdownParams(
        url=url,
        bypass_cache=bypass_cache,
        css_selector=css_selector or extract_selector,
        js_before_scrape=js_before_scrape,
        screenshot=screenshot,
        remove_selectors=remove_selectors,
        headers=headers,
        user_agent=user_agent,
        proxy=proxy,
        cookies=cookies,
        accept_language=accept_language,
        timeout=timeout,
        extract_selector=extract_selector,
        wait_for=wait_for,
    )

    cache = _get_cache()
    cache_key = f"markdown::{params.url}"

    if not params.bypass_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            log.info("cache_hit url=%s", params.url)
            return cached

    log.info("markdown url=%s", params.url)

    # Import Crawl4AI lazily
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError as e:
        log.exception("crawl4ai import failed")
        return {
            "url": params.url,
            "error": f"crawl4ai not available: {e}",
            "tool": "crawl4ai",
        }

    try:
        # Prepare crawler kwargs
        crawler_kwargs: dict[str, Any] = {"verbose": False}
        if params.headers:
            crawler_kwargs["headers"] = params.headers
        if params.user_agent:
            crawler_kwargs["user_agent"] = params.user_agent
        if params.proxy:
            crawler_kwargs["proxy"] = params.proxy
        if params.cookies:
            crawler_kwargs["cookies"] = params.cookies

        # Run crawl with timeout
        async with AsyncWebCrawler(**crawler_kwargs) as crawler:
            run_kwargs: dict[str, Any] = {
                "url": params.url,
                "bypass_cache": params.bypass_cache,
            }

            if params.css_selector:
                run_kwargs["css_selector"] = params.css_selector
            if params.js_before_scrape:
                run_kwargs["js_code"] = params.js_before_scrape
            if params.screenshot:
                run_kwargs["screenshot"] = True
            if params.remove_selectors:
                run_kwargs["remove_overlay_elements"] = params.remove_selectors
            if params.wait_for:
                run_kwargs["wait_for"] = params.wait_for

            r = await asyncio.wait_for(
                crawler.arun(**run_kwargs),
                timeout=EXTERNAL_TIMEOUT_SECS * 2,
            )

            # Extract markdown and title
            md = ""
            try:
                md = (r.markdown or "")[:30000]
            except Exception:
                md = ""

            title = ""
            with contextlib.suppress(Exception):
                title = (r.metadata or {}).get("title", "")

            data = {
                "url": params.url,
                "title": title,
                "markdown": md,
                "tool": "crawl4ai",
                "fetched_at": _utc_now_iso(),
            }

    except TimeoutError:
        log.warning("markdown_timeout url=%s", params.url)
        return {"url": params.url, "error": "timeout", "tool": "crawl4ai"}
    except Exception as e:
        log.exception("markdown_failed url=%s", params.url)
        return {"url": params.url, "error": str(e), "tool": "crawl4ai"}

    # Cache result
    try:
        cache.put(cache_key, data)
    except Exception as e:
        log.warning("cache_put_failed key=%s: %s", cache_key, e)

    return data
