"""research_spider — Parallelized bulk URL fetching with semaphore and per-fetch timeout."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, cast

from loom.params import SpiderParams
from loom.tools.fetch import research_fetch
from loom.validators import EXTERNAL_TIMEOUT_SECS, MAX_SPIDER_URLS, SPIDER_CONCURRENCY

log = logging.getLogger("loom.tools.spider")


async def research_spider(
    urls: list[str],
    mode: str = "stealthy",
    max_chars_each: int = 5000,
    concurrency: int = SPIDER_CONCURRENCY,
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

    Args:
        urls: list of URLs to fetch
        mode: 'http' | 'stealthy' | 'dynamic' (passed to each fetch)
        max_chars_each: max chars per response (hard cap 200k)
        concurrency: max concurrent fetches (1-20, default SPIDER_CONCURRENCY)
        fail_fast: stop on first error
        dedupe: drop duplicate URLs
        order: result ordering 'input' | 'domain' | 'size'
        solve_cloudflare: pass to each fetch
        headers: custom headers
        user_agent: override UA
        proxy: proxy URL
        cookies: cookies dict
        accept_language: header value
        timeout: per-fetch timeout override (capped)

    Returns:
        List of fetch result dicts (one per URL), with error fields for
        failures.
    """
    # Validate and normalize params
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

    # Cap URL count
    url_list = params.urls[: min(len(params.urls), MAX_SPIDER_URLS)]

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
    concurrency = max(1, min(params.concurrency, SPIDER_CONCURRENCY))
    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()

    async def _one(u: str) -> dict[str, Any]:
        """Fetch a single URL with timeout."""
        async with sem:
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: research_fetch(
                            u,
                            mode=params.mode,
                            max_chars=params.max_chars_each,
                            solve_cloudflare=params.solve_cloudflare,
                            headers=params.headers,
                            user_agent=params.user_agent,
                            proxy=params.proxy,
                            cookies=params.cookies,
                            accept_language=params.accept_language,
                            timeout=params.timeout,
                        ),
                    ),
                    timeout=EXTERNAL_TIMEOUT_SECS * 2,
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
