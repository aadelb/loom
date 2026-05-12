"""research_spider — Parallelized bulk URL fetching with semaphore and per-fetch timeout."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, cast

try:
    from loom.params import SpiderParams
    from loom.tools.fetch import research_fetch
    _SPIDER_DEPS = True
except ImportError:
    _SPIDER_DEPS = False

log = logging.getLogger("loom.tools.spider")


def _get_config_values() -> tuple[int, int, int]:
    """Get timeout, max URLs, and concurrency from config."""
    try:
        from loom.config import get_config
        cfg = get_config()
        timeout_secs = cfg.get("EXTERNAL_TIMEOUT_SECS", 30)
        max_urls = cfg.get("MAX_SPIDER_URLS", 100)
        concurrency = cfg.get("SPIDER_CONCURRENCY", 10)
        return timeout_secs, max_urls, concurrency
    except (ImportError, RuntimeError):
        return 30, 100, 10


async def research_spider(
    urls: list[str],
    mode: str = "stealthy",
    max_chars_each: int = 5000,
    concurrency: int | None = None,
    fail_fast: bool = False,
    dedupe: bool = True,
    order: str = "input",
    solve_cloudflare: bool = True,
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    proxy: str | None = None,
    cookies: dict[str, str] | None = None,
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8",
    timeout: int | None = None,  # noqa: ASYNC109
) -> list[dict[str, Any]]:
    """Fetch multiple URLs with bounded concurrency and per-fetch timeout.

    Uses asyncio.Semaphore to limit concurrent fetches and asyncio.wait_for
    to enforce per-fetch timeout. Each fetch runs in a thread executor so
    Scrapling's sync API doesn't block the FastMCP event loop.

    Timeout hierarchy:
    - If timeout is provided, clamp it to INNER_FETCH_TIMEOUT.
    - INNER_FETCH_TIMEOUT is passed to research_fetch (thread timeout).
    - OUTER_WAIT_FOR_TIMEOUT wraps asyncio.wait_for to catch escaped threads.
    - Inner timeout must be < outer timeout to ensure thread termination before
      asyncio task cancellation, preventing thread leaks.

    Args:
        urls: list of URLs to fetch
        mode: 'http' | 'stealthy' | 'dynamic' (passed to each fetch)
        max_chars_each: max chars per response (hard cap from config)
        concurrency: max concurrent fetches (1-20, default from SPIDER_CONCURRENCY config)
        fail_fast: stop on first error
        dedupe: drop duplicate URLs
        order: result ordering 'input' | 'domain' | 'size'
        solve_cloudflare: pass to each fetch
        headers: custom headers
        user_agent: override UA
        proxy: proxy URL
        cookies: cookies dict
        accept_language: header value
        timeout: per-fetch timeout override (clamped to INNER_FETCH_TIMEOUT)

    Returns:
        List of fetch result dicts (one per URL), with error fields for
        failures.
    """
    # Get config values
    timeout_secs, max_spider_urls, default_concurrency = _get_config_values()

    # Timeout hierarchy for spider fetches:
    # - INNER_FETCH_TIMEOUT: timeout passed to research_fetch (executor thread)
    # - OUTER_WAIT_FOR_TIMEOUT: timeout for asyncio.wait_for (task cancellation)
    # Inner must be strictly less than outer to allow threads to terminate naturally.
    inner_fetch_timeout = max(1, timeout_secs - 10)  # 20s when EXTERNAL_TIMEOUT_SECS=30
    outer_wait_for_timeout = timeout_secs * 2  # 60s

    # Validate and normalize params
    if concurrency is None:
        concurrency = default_concurrency

    params = SpiderParams(
        urls=urls,
        mode=cast(Literal["http", "stealthy", "dynamic"], mode),
        max_chars_each=max_chars_each,
        concurrency=concurrency,
        fail_fast=fail_fast,
        dedupe=dedupe,
        order=cast(Literal["input", "domain", "size"], order),
        solve_cloudflare=solve_cloudflare,
        headers=headers,
        user_agent=user_agent,
        proxy=proxy,
        cookies=cookies,
        accept_language=accept_language,
        timeout=timeout,
    )

    # Cap URL count (from config)
    url_list = params.urls[: min(len(params.urls), max_spider_urls)]

    # Dedupe if requested
    if params.dedupe:
        seen = set()
        deduped = []
        for u in url_list:
            if u not in seen:
                deduped.append(u)
                seen.add(u)
        url_list = deduped

    if not url_list:
        return [{"error": "urls list is empty", "tool": f"scrapling.{params.mode}"}]

    # Setup concurrency limiter
    concurrency = max(1, min(params.concurrency, default_concurrency))
    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()

    # Clamp user-provided timeout to INNER_FETCH_TIMEOUT to prevent thread leaks.
    # The inner timeout must fire before the outer asyncio.wait_for timeout so
    # the executor thread terminates naturally instead of being abandoned.
    inner_timeout = inner_fetch_timeout
    if params.timeout is not None and params.timeout > 0:
        inner_timeout = min(params.timeout, inner_fetch_timeout)

    async def _one(u: str) -> dict[str, Any]:
        """Fetch a single URL with timeout.

        Enforces timeout hierarchy:
        - Inner timeout (inner_timeout): passed to research_fetch for thread timeout
        - Outer timeout (outer_wait_for_timeout): asyncio.wait_for for task cancellation
        Inner < outer ensures the thread completes before the task is cancelled.
        """
        async with sem:
            try:
                return await asyncio.wait_for(
                    research_fetch(
                        url=u,
                        mode=params.mode,
                        max_chars=params.max_chars_each,
                        solve_cloudflare=params.solve_cloudflare,
                        headers=params.headers,
                        user_agent=params.user_agent,
                        proxy=params.proxy,
                        cookies=params.cookies,
                        accept_language=params.accept_language,
                        timeout=inner_timeout,
                    ),
                    timeout=outer_wait_for_timeout,
                )
            except TimeoutError:
                log.warning("spider_fetch_timeout url=%s", u)
                return {
                    "url": u,
                    "error": "timeout",
                    "tool": f"scrapling.{params.mode}",
                }

    # Gather all tasks
    if params.fail_fast:
        # Stop on first error
        results = []
        for u in url_list:
            result = await _one(u)
            results.append(result)
            if "error" in result:
                log.warning("spider_fail_fast error=%s", result.get("error"))
                break
    else:
        # Gather all, return_exceptions=True to catch any exceptions
        task_results = await asyncio.gather(*(_one(u) for u in url_list), return_exceptions=True)
        results = []
        for r in task_results:
            if isinstance(r, BaseException):
                log.warning("spider_task_exception: %s", r)
                results.append({"error": str(r), "tool": f"scrapling.{params.mode}"})
            else:
                results.append(r)

    # Sort results if requested
    if params.order == "domain":
        results.sort(key=lambda r: r.get("url", ""))
    elif params.order == "size":
        results.sort(key=lambda r: len(r.get("text", "")), reverse=True)
    # else: keep input order

    return results
