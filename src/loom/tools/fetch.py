"""research_fetch — Unified URL fetcher with HTTP, stealth, and dynamic modes."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal, cast

import httpx
from mcp.types import TextContent
from pydantic import BaseModel

try:
    from selectolax.parser import HTMLParser  # type: ignore[import-not-found]

    _HAS_SELECTOLAX = True
except ImportError:  # pragma: no cover — optional HTML parser
    HTMLParser = None  # type: ignore[assignment,misc]
    _HAS_SELECTOLAX = False

from loom.params import FetchParams
from loom.validators import EXTERNAL_TIMEOUT_SECS, MAX_FETCH_CHARS

logger = logging.getLogger("loom.tools.fetch")


class FetchResult(BaseModel):
    """Result from a fetch operation."""

    url: str
    status_code: int | None = None
    content_type: str | None = None
    text: str = ""
    html: str | None = None
    json: Any | None = None
    screenshot: str | None = None
    error: str | None = None
    tool: str = "unknown"
    elapsed_ms: int = 0


def _extract_text(html: str, max_chars: int) -> str:
    """Extract readable text from HTML.

    Uses selectolax when available; falls back to a crude tag-strip when the
    optional dependency is missing.
    """
    try:
        if _HAS_SELECTOLAX:
            parser = HTMLParser(html)
            if parser.body is None:
                return ""

            for tag in parser.css("script, style"):
                tag.decompose()

            text = parser.body.text(separator="\n", strip=True)
        else:
            import re as _re

            text = _re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=_re.DOTALL | _re.I)
            text = _re.sub(r"<[^>]+>", " ", text)

        text = " ".join(text.split())
        if len(text) > max_chars:
            text = text[:max_chars] + "…"
        return text
    except Exception as e:
        logger.warning("text_extraction_failed error=%s", e)
        return ""


def research_fetch(
    url: str,
    mode: str = "stealthy",
    max_chars: int = MAX_FETCH_CHARS,
    solve_cloudflare: bool = True,
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    proxy: str | None = None,
    cookies: dict[str, str] | None = None,
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8",
    wait_for: str | None = None,
    return_format: str = "text",
    timeout: int | None = None,
) -> dict[str, Any]:
    """Fetch a URL with configurable strategy.

    Args:
        url: URL to fetch
        mode: 'http' | 'stealthy' | 'dynamic'
        max_chars: maximum characters to return (capped)
        solve_cloudflare: attempt Cloudflare bypass (stealthy/dynamic only)
        headers: custom HTTP headers
        user_agent: override User‑Agent
        proxy: proxy URL (http:// or socks5://)
        cookies: dict of cookies
        accept_language: Accept‑Language header
        wait_for: CSS selector to wait for (dynamic only)
        return_format: 'text' | 'html' | 'json' | 'screenshot'
        timeout: request timeout in seconds

    Returns:
        Dict with keys: url, status_code, text, html, json, error, tool, elapsed_ms
    """
    # Validate and normalize
    params = FetchParams(
        url=url,
        mode=cast(Literal["http", "stealthy", "dynamic"], mode),
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

    logger.info(
        "fetch_start url=%s mode=%s return=%s",
        url,
        params.mode,
        params.return_format,
    )

    start = time.time()

    # Route to appropriate fetcher
    if params.mode == "http":
        result = _fetch_http(params)
    elif params.mode == "stealthy":
        result = _fetch_stealthy(params)
    elif params.mode == "dynamic":
        result = _fetch_dynamic(params)
    else:
        result = FetchResult(
            url=url,
            error=f"Unknown mode: {mode}",
            tool="unknown",
            elapsed_ms=int((time.time() - start) * 1000),
        )

    # Convert to dict
    output = result.model_dump(exclude_none=True)
    output["elapsed_ms"] = int((time.time() - start) * 1000)
    return output


def _fetch_http(params: FetchParams) -> FetchResult:
    """Fetch using plain HTTP (httpx)."""
    # Build headers
    headers = params.headers or {}
    if params.user_agent:
        headers["User-Agent"] = params.user_agent
    if params.accept_language:
        headers["Accept-Language"] = params.accept_language

    # Build cookies
    cookies = params.cookies or {}

    # Configure client
    client_kwargs: dict[str, Any] = {
        "timeout": params.timeout or EXTERNAL_TIMEOUT_SECS,
        "follow_redirects": True,
    }
    if params.proxy:
        client_kwargs["proxy"] = params.proxy

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(
                params.url,
                headers=headers,
                cookies=cookies,
            )
            resp.raise_for_status()

            # Determine content type
            content_type = resp.headers.get("content-type", "").lower()

            # Extract based on format
            if params.return_format == "json" or "application/json" in content_type:
                try:
                    json_data = resp.json()
                    return FetchResult(
                        url=params.url,
                        status_code=resp.status_code,
                        content_type=content_type,
                        json=json_data,
                        tool="httpx",
                    )
                except ValueError:
                    # Fall back to text
                    pass

            # HTML/text handling
            html = resp.text if params.return_format == "html" else None
            text = resp.text if params.return_format == "text" else _extract_text(resp.text, params.max_chars)

            return FetchResult(
                url=params.url,
                status_code=resp.status_code,
                content_type=content_type,
                text=text[: params.max_chars] if text else "",
                html=html[: params.max_chars] if html else None,
                tool="httpx",
            )

    except Exception as e:
        logger.warning("http_fetch_failed url=%s error=%s", params.url, e)
        return FetchResult(url=params.url, error=str(e), tool="httpx")


def _fetch_stealthy(params: FetchParams) -> FetchResult:
    """Fetch using stealth browser (Camoufox)."""
    try:
        from camoufox import Camoufox
    except ImportError:
        return FetchResult(
            url=params.url,
            error="Camoufox not installed: pip install camoufox",
            tool="camoufox",
        )

    try:
        with Camoufox() as fox:
            # Navigate
            fox.get(params.url)

            # Wait for page load
            fox.wait_for_page_load()

            # Optional: wait for selector
            if params.wait_for:
                fox.wait_for(params.wait_for)

            # Extract
            title = fox.title
            html = fox.page_source
            text = fox.page_text

            # Optional screenshot
            screenshot_b64 = None
            if params.return_format == "screenshot":
                screenshot_b64 = fox.screenshot_as_base64

            # Trim text
            if text and len(text) > params.max_chars:
                text = text[: params.max_chars] + "…"

            return FetchResult(
                url=params.url,
                text=text,
                html=html,
                screenshot=screenshot_b64,
                tool="camoufox",
            )
    except Exception as e:
        logger.warning("stealthy_fetch_failed url=%s error=%s", params.url, e)
        return FetchResult(url=params.url, error=str(e), tool="camoufox")


def _fetch_dynamic(params: FetchParams) -> FetchResult:
    """Fetch using dynamic browser (Botasaurus)."""
    try:
        from botasaurus.browser import browser  # type: ignore[import-not-found]
    except ImportError:
        return FetchResult(
            url=params.url,
            error="Botasaurus not installed: pip install botasaurus",
            tool="botasaurus",
        )

    @browser(
        headless=True,
        block_images=True,
        proxy=params.proxy,
        user_agent=params.user_agent,
    )
    def scrape_page(driver: Any, data: dict[str, Any]) -> dict[str, Any]:
        """Botasaurus scraping function."""
        url = data["url"]
        driver.get(url)

        # Wait for page load
        driver.wait_for_page_load()

        # Optional: wait for selector
        if data.get("wait_for"):
            driver.wait_for(data["wait_for"])

        # Extract
        title = driver.title
        html = driver.page_source
        text = driver.text

        # Optional screenshot
        screenshot_b64 = None
        if data.get("return_format") == "screenshot":
            screenshot_b64 = driver.get_screenshot_as_base64()

        return {
            "title": title,
            "html": html,
            "text": text,
            "screenshot": screenshot_b64,
        }

    try:
        result = scrape_page(
            {
                "url": params.url,
                "wait_for": params.wait_for,
                "return_format": params.return_format,
            }
        )

        # Trim text
        text = result.get("text", "")
        if text and len(text) > params.max_chars:
            text = text[: params.max_chars] + "…"

        return FetchResult(
            url=params.url,
            text=text,
            html=result.get("html"),
            screenshot=result.get("screenshot"),
            tool="botasaurus",
        )
    except Exception as e:
        logger.warning("dynamic_fetch_failed url=%s error=%s", params.url, e)
        return FetchResult(url=params.url, error=str(e), tool="botasaurus")


def tool_fetch(
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
    result = research_fetch(
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
