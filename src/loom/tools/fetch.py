"""research_fetch — Unified URL fetcher with HTTP, stealth, and dynamic modes."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, Literal, cast

import httpx
from mcp.types import TextContent
from pydantic import BaseModel, ConfigDict, Field

try:
    from selectolax.parser import HTMLParser

    _HAS_SELECTOLAX = True
except ImportError:  # pragma: no cover — optional HTML parser
    HTMLParser = None
    _HAS_SELECTOLAX = False

from loom.cache import get_cache
from loom.params import FetchParams
from loom.validators import EXTERNAL_TIMEOUT_SECS, MAX_FETCH_CHARS, get_validated_dns

logger = logging.getLogger("loom.tools.fetch")

# Module-level connection pool for httpx (reused across calls).
_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    """Return a shared httpx client with connection pooling."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            timeout=EXTERNAL_TIMEOUT_SECS,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _http_client


class FetchResult(BaseModel):
    """Result from a fetch operation.

    The ``json_data`` field is serialized with the alias ``json`` so the
    output dict still has the historical ``json`` key, but the attribute
    name avoids shadowing ``BaseModel.json()`` in strict type checking.
    """

    url: str
    status_code: int | None = None
    content_type: str | None = None
    title: str | None = None
    text: str = ""
    html: str | None = None
    json_data: Any | None = Field(default=None, serialization_alias="json")
    screenshot: str | None = None
    error: str | None = None
    tool: str = "unknown"
    elapsed_ms: int = 0

    model_config = ConfigDict(populate_by_name=True)


def _to_scrapling_schema(result: dict[str, Any], max_chars: int) -> dict[str, Any]:
    """Transform httpx result to Scrapling-compatible schema.

    Adds: title, html_len, fetched_at
    Keeps: url, text, tool, status_code, error, elapsed_ms (all optional)
    """
    output: dict[str, Any] = {
        "url": result.get("url", ""),
        "tool": result.get("tool", "unknown"),
    }

    # Extract title from text or set empty
    output["title"] = result.get("title", "")

    # Ensure text is capped
    text = result.get("text", "")
    if text and len(text) > max_chars:
        text = text[:max_chars]
    output["text"] = text

    # html_len from html field if present
    html = result.get("html", "")
    output["html_len"] = len(html) if html else 0

    # Add fetched_at timestamp
    output["fetched_at"] = datetime.now(UTC).isoformat()

    # Optionally include legacy fields for backward compat
    if result.get("status_code"):
        output["status_code"] = result["status_code"]
    if result.get("error"):
        output["error"] = result["error"]
    if result.get("elapsed_ms"):
        output["elapsed_ms"] = result["elapsed_ms"]

    return output


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


def _make_cache_key(url: str, mode: str) -> str:
    """Create a cache key from url and mode."""
    combined = f"{url}|{mode}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


def _is_cloudflare_block(result: FetchResult) -> bool:
    """Detect Cloudflare challenge or block in a fetch result."""
    text = ((result.text or "") + (result.html or "")).lower()
    if result.status_code == 403 and ("ray id" in text or "cf-ray" in text or "cloudflare" in text):
        return True
    return result.status_code == 503 and "cloudflare" in text


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
    bypass_cache: bool = False,
    auto_escalate: bool | None = None,
) -> dict[str, Any]:
    """Fetch a URL with configurable strategy.

    Args:
        url: URL to fetch
        mode: 'http' | 'stealthy' | 'dynamic'
        max_chars: maximum characters to return (capped)
        solve_cloudflare: attempt Cloudflare bypass (stealthy/dynamic only)
        headers: custom HTTP headers
        user_agent: override User-Agent
        proxy: proxy URL (http:// or socks5://)
        cookies: dict of cookies
        accept_language: Accept-Language header
        wait_for: CSS selector to wait for (dynamic only)
        return_format: 'text' | 'html' | 'json' | 'screenshot'
        timeout: request timeout in seconds
        bypass_cache: skip cache read/write when True

    Returns:
        Dict with keys: url, title, text, html_len, fetched_at, tool, and optionally
        status_code, error, elapsed_ms for backward compatibility
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

    # Wire config defaults for auto_escalate
    if auto_escalate is None:
        from loom.config import get_config

        auto_escalate = get_config().get("FETCH_AUTO_ESCALATE", False)

    logger.info(
        "fetch_start url=%s mode=%s return=%s bypass_cache=%s auto_escalate=%s",
        url,
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

    # Auto-escalation: http -> stealthy -> dynamic on Cloudflare block
    if auto_escalate and params.mode == "http" and _is_cloudflare_block(result):
        logger.info("auto_escalate http->stealthy url=%s", url)
        result = _fetch_stealthy(params)
        if _is_cloudflare_block(result):
            logger.info("auto_escalate stealthy->dynamic url=%s", url)
            result = _fetch_dynamic(params)

    # Convert to dict and enrich with Scrapling-compatible fields
    # by_alias=True so the historical "json" dict key is preserved despite
    # the internal field being renamed to json_data for mypy --strict.
    output = result.model_dump(exclude_none=True, by_alias=True)
    output["elapsed_ms"] = int((time.time() - start) * 1000)

    # For mode='http', transform result to Scrapling-compatible schema
    if params.mode == "http" and not output.get("error"):
        output = _to_scrapling_schema(output, params.max_chars)

    # Cache all successful results (any mode)
    if not output.get("error") and not bypass_cache:
        get_cache().put(cache_key, output)

    return output


def _fetch_http(params: FetchParams) -> FetchResult:
    """Fetch using plain HTTP.

    Tries Scrapling first (if available), falls back to httpx.
    """
    try:
        from scrapling.fetchers import Fetcher

        return _fetch_http_scrapling(params, Fetcher)
    except ImportError:
        logger.debug("Scrapling not available, falling back to httpx")
        return _fetch_http_httpx(params)


def _fetch_http_scrapling(params: FetchParams, Fetcher: Any) -> FetchResult:
    """Fetch using Scrapling (if available)."""
    try:
        page = Fetcher.get(params.url)

        # Extract title
        title = page.css("title::text").get() or page.css("h1::text").get() or ""

        # Extract text
        text = page.get_all_text()
        if text and len(text) > params.max_chars:
            text = text[: params.max_chars]

        # Get HTML length
        len(page.html_content) if page.html_content else 0

        return FetchResult(
            url=params.url,
            text=text,
            html=page.html_content,
            tool="scrapling",
            # Include title for Scrapling compatibility (will be used in schema transform)
            title=title,
            status_code=200,
            content_type="text/html",
        )
    except Exception as e:
        logger.warning("scrapling_fetch_failed url=%s error=%s", params.url, e)
        return FetchResult(url=params.url, error=str(e), tool="scrapling")


def _fetch_http_httpx(params: FetchParams) -> FetchResult:
    """Fetch using httpx (fallback).

    Uses validated DNS resolution from get_validated_dns() to prevent
    TOCTOU DNS rebinding attacks between validation and request time.
    When validated IPs are available, constructs a URL with the IP address
    directly while preserving the original hostname in the Host header for
    virtual hosting / SNI.
    """
    # Build headers
    headers = params.headers or {}
    if params.user_agent:
        headers["User-Agent"] = params.user_agent
    if params.accept_language:
        headers["Accept-Language"] = params.accept_language

    # Build cookies
    cookies = params.cookies or {}

    proxy_client: httpx.Client | None = None
    try:
        if params.proxy:
            proxy_client = httpx.Client(
                timeout=params.timeout or EXTERNAL_TIMEOUT_SECS,
                follow_redirects=True,
                proxy=params.proxy,
            )
            client = proxy_client
        else:
            client = _get_http_client()

        # Attempt to use validated DNS resolution to prevent TOCTOU rebinding.
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(params.url)
        hostname = parsed.hostname
        port = parsed.port
        request_url = params.url

        if hostname:
            validated_ips = get_validated_dns(hostname)
            if validated_ips:
                # Reconstruct URL using the first validated IP as the netloc,
                # while preserving the original hostname in the Host header.
                # This forces the connection to use the validated IP while
                # still supporting virtual hosting and SNI.
                ip = validated_ips[0]
                # Preserve port if present
                netloc_with_ip = f"{ip}:{port}" if port else ip
                new_parsed = parsed._replace(netloc=netloc_with_ip)
                request_url = urlunparse(new_parsed)
                # Ensure Host header uses original hostname for virtual hosting
                headers["Host"] = hostname if not port else f"{hostname}:{port}"
                logger.debug(
                    "dns_rebinding_prevention original_url=%s request_url=%s "
                    "hostname=%s ip=%s",
                    params.url, request_url, hostname, ip
                )

        resp = client.get(
            request_url,
            headers=headers,
            cookies=cookies,
            timeout=params.timeout or EXTERNAL_TIMEOUT_SECS,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()

        if params.return_format == "json" or "application/json" in content_type:
            try:
                parsed_json = resp.json()
                return FetchResult(
                    url=params.url,
                    status_code=resp.status_code,
                    content_type=content_type,
                    json_data=parsed_json,
                    tool="httpx",
                )
            except ValueError:
                pass

        html = resp.text if params.return_format == "html" else None
        text = (
            resp.text
            if params.return_format == "text"
            else _extract_text(resp.text, params.max_chars)
        )

        return FetchResult(
            url=params.url,
            status_code=resp.status_code,
            content_type=content_type,
            text=text[: params.max_chars] if text else "",
            html=html[: params.max_chars] if html else None,
            tool="httpx",
        )

    except Exception as e:
        logger.warning("httpx_fetch_failed url=%s error=%s", params.url, e)
        return FetchResult(url=params.url, error=str(e), tool="httpx")
    finally:
        if proxy_client is not None:
            try:
                proxy_client.close()
            except Exception as e:
                logger.debug("proxy_client_close_error error=%s", e)


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
        with Camoufox() as _fox:
            # camoufox is untyped; narrow to Any once to avoid per-line ignores
            fox: Any = _fox
            fox.get(params.url)
            fox.wait_for_page_load()

            if params.wait_for:
                fox.wait_for(params.wait_for)

            html = fox.page_source
            text = fox.page_text

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
        from botasaurus.browser import browser
    except ImportError:
        return FetchResult(
            url=params.url,
            error="Botasaurus not installed: pip install botasaurus",
            tool="botasaurus",
        )

    # botasaurus' @browser decorator is untyped, so the resulting
    # ``scrape_page`` gets no annotation. Silence both ruff and mypy
    # with a narrow type-ignore block.
    @browser(  # type: ignore[untyped-decorator]
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
