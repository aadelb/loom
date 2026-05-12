"""research_fetch — Unified fetching with protocol-aware escalation.

Routes HTTP requests through three modes:
- http: Standard HTTP requests (via requests library)
- stealthy: Stealthy HTTP with custom headers, User-Agent rotation, and IP rotation via proxies (via Scrapling)
- dynamic: Headless browser automation (via Playwright or Camoufox)

Auto-escalates: http -> stealthy -> dynamic on Cloudflare block (if solve_cloudflare or auto_escalate).

Supports caching via content-hash (SHA-256), with daily cache dirs.
All mode functions are sync and CPU-bound; the async wrapper just calls them and returns results.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict
from typing import Any, Literal, cast
from loom.error_responses import handle_tool_errors

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]
from pydantic import BaseModel, Field

from loom.cache import get_cache
from loom.params import FetchParams
from loom.validators import validate_url, MAX_FETCH_CHARS

logger = logging.getLogger("loom.tools.fetch")


class FetchResult(BaseModel):
    """Result from a fetch operation."""

    url: str
    title: str = ""
    text: str = ""
    html: str = ""
    html_len: int = 0
    screenshot: str | None = None
    fetched_at: str = ""
    tool: str = "unknown"
    backend: str = "unknown"
    error: str | None = None
    cache_hit: bool = False
    elapsed_ms: int = 0


def _make_cache_key(url: str, mode: str) -> str:
    """Generate cache key from URL + mode."""
    key_str = f"{url}|{mode}"
    return hashlib.sha256(key_str.encode()).hexdigest()


def _fetch_http(params: FetchParams) -> FetchResult:
    """Fetch via standard HTTP."""
    try:
        import requests

        response = requests.get(
            params.url,
            headers=params.headers,
            timeout=params.timeout or 30,
            proxies={"http": params.proxy, "https": params.proxy} if params.proxy else None,
        )
        response.raise_for_status()
        return FetchResult(
            url=params.url,
            text=response.text[: params.max_chars],
            html=response.text[: params.max_chars],
            html_len=len(response.text),
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            tool="http",
        )
    except Exception as e:
        logger.error("http_fetch_error url=%s error=%s", params.url, str(e))
        return FetchResult(url=params.url, error=str(e), tool="http")


def _fetch_stealthy(params: FetchParams) -> FetchResult:
    """Fetch via stealthy mode (Scrapling Fetcher with stealth headers)."""
    try:
        from scrapling import Fetcher

        fetcher = Fetcher()
        response = fetcher.get(
            params.url,
            stealthy_headers=True,
            timeout=params.timeout or 30,
        )
        body = getattr(response, "body", b"") or b""
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
        return FetchResult(
            url=params.url,
            text=text[: params.max_chars],
            html=text[: params.max_chars],
            html_len=len(text),
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            tool="stealthy",
            backend="scrapling",
        )
    except Exception as e:
        logger.error("stealthy_fetch_error url=%s error=%s", params.url, str(e))
        return FetchResult(url=params.url, error=str(e), tool="stealthy")


def _fetch_dynamic(params: FetchParams) -> FetchResult:
    """Fetch via dynamic mode (browser automation)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(params.url, wait_until="networkidle", timeout=params.timeout * 1000 or 30000)
            if params.wait_for:
                page.wait_for_selector(params.wait_for)
            content = page.content()
            screenshot_b64 = page.screenshot(full_page=True, type="png") if params.return_format == "screenshot" else None
            browser.close()
            return FetchResult(
                url=params.url,
                text=content[: params.max_chars],
                html=content[: params.max_chars],
                html_len=len(content),
                screenshot=screenshot_b64,
                fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                tool="dynamic",
                backend="playwright",
            )
    except Exception as e:
        logger.error("dynamic_fetch_error url=%s error=%s", params.url, str(e))
        return FetchResult(url=params.url, error=str(e), tool="dynamic")


def _is_cloudflare_block(result: FetchResult) -> bool:
    """Detect if result is Cloudflare block."""
    return (
        "cloudflare" in result.text.lower()
        or "403" in result.text
        or "challenge" in result.text.lower()
    )


@handle_tool_errors("research_fetch")
async def research_fetch(
    url: str,
    mode: str = "stealthy",
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    proxy: str | None = None,
    cookies: dict[str, str] | None = None,
    accept_language: str = "en-US,en;q=0.9",
    wait_for: str | None = None,
    return_format: str = "text",
    timeout: int | None = None,
    backend: str | None = None,
    solve_cloudflare: bool = True,
    auto_escalate: bool | None = None,
    bypass_cache: bool = False,
    max_chars: int = MAX_FETCH_CHARS,
) -> dict[str, Any]:
    """Unified fetch with protocol-aware escalation.

    Args:
        url: URL to fetch
        mode: Fetch mode ('http', 'stealthy', 'dynamic') - default 'stealthy'
        headers: Custom headers dict
        user_agent: Custom User-Agent
        proxy: Proxy URL (http://ip:port or socks5://ip:port)
        cookies: Cookie dict
        accept_language: Accept-Language header
        wait_for: CSS selector to wait for (dynamic mode only)
        return_format: Output format ('text', 'html', 'json', 'screenshot')
        timeout: Timeout in seconds (default 30)
        backend: Preferred backend (ignored in favor of mode; for compatibility)
        solve_cloudflare: Auto-escalate on Cloudflare (default True)
        auto_escalate: Override config for auto-escalation (default None = use config)
        bypass_cache: Skip cache check (default False)
        max_chars: Max characters to return (default 1000000)

    Returns:
        Dict with url, text, html, title, fetched_at, tool, backend, error (if any)
    """
    # Validate URL
    try:
        validate_url(url)
    except ValueError as e:
        logger.warning("invalid_url url=%s error=%s", url, str(e))
        return {
            "url": url,
            "error": str(e),
            "tool": "unknown",
        }

    # Normalize mode
    mode_to_use = mode.lower() if mode else "stealthy"
    if mode_to_use not in ("http", "stealthy", "dynamic"):
        logger.warning("invalid_mode mode=%s, defaulting to stealthy", mode_to_use)
        mode_to_use = "stealthy"

    # Build headers
    headers = headers or {}
    if user_agent:
        headers["User-Agent"] = user_agent
    if accept_language:
        headers["Accept-Language"] = accept_language

    # Build params
    params = FetchParams(
        url=url,
        mode=cast(Literal["http", "stealthy", "dynamic"], mode_to_use),
        max_chars=min(max_chars, MAX_FETCH_CHARS),
        solve_cloudflare=solve_cloudflare,
        headers=headers,
        user_agent=user_agent,
        proxy=proxy,
        cookies=cookies,
        accept_language=accept_language,
        wait_for=wait_for,
        return_format=cast(Literal["text", "html", "json", "screenshot"], return_format),
        timeout=timeout,
    )

    # Wire config defaults for auto_escalate
    if auto_escalate is None:
        from loom.config import get_config

        auto_escalate = get_config().get("FETCH_AUTO_ESCALATE", False)

    logger.info(
        "fetch_start url=%s backend=%s mode=%s return=%s bypass_cache=%s auto_escalate=%s",
        url,
        backend,
        params.mode,
        params.return_format,
        bypass_cache,
        auto_escalate,
    )

    start = time.time()

    # Check cache for all modes
    cache_key = _make_cache_key(url, params.mode)
    cached = None
    if not bypass_cache:
        cached = get_cache().get(cache_key)
        if cached:
            logger.info("cache_hit url=%s mode=%s", url, params.mode)
            cached["elapsed_ms"] = int((time.time() - start) * 1000)
            return cached

    # Route to appropriate fetcher (sync helpers run in thread pool)
    if params.mode == "http":
        result = await asyncio.to_thread(_fetch_http, params)
    elif params.mode == "stealthy":
        result = await asyncio.to_thread(_fetch_stealthy, params)
    elif params.mode == "dynamic":
        result = await asyncio.to_thread(_fetch_dynamic, params)
    else:
        result = FetchResult(
            url=url,
            error=f"Unknown mode: {mode}",
            tool="unknown",
            elapsed_ms=int((time.time() - start) * 1000),
        )

    # Auto-escalation: http -> stealthy -> dynamic on Cloudflare block
    if auto_escalate and params.mode == "http" and _is_cloudflare_block(result):
        logger.info("auto_escalate http -> stealthy url=%s", url)
        params.mode = "stealthy"
        result = await asyncio.to_thread(_fetch_stealthy, params)

        if _is_cloudflare_block(result):
            logger.info("auto_escalate stealthy -> dynamic url=%s", url)
            params.mode = "dynamic"
            result = await asyncio.to_thread(_fetch_dynamic, params)

    # Cache successful result
    if not result.error:
        get_cache().put(cache_key, result.model_dump(exclude_none=True))

    # Convert to dict
    output = result.model_dump(exclude_none=True)
    output["elapsed_ms"] = int((time.time() - start) * 1000)
    return output


async def tool_fetch(
    url: str,
    mode: str = "stealthy",
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    proxy: str | None = None,
    cookies: dict[str, str] | None = None,
    accept_language: str = "en-US,en;q=0.9",
    wait_for: str | None = None,
    return_format: str = "text",
    timeout: int | None = None,
) -> list[TextContent]:
    """MCP wrapper for research_fetch."""
    result = await research_fetch(
        url=url,
        mode=mode,
        headers=headers,
        user_agent=user_agent,
        proxy=proxy,
        cookies=cookies,
        accept_language=accept_language,
        wait_for=wait_for,
        return_format=return_format,
        timeout=timeout,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
