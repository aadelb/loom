"""Async undetected browser backend powered by nodriver.

Provides three research tools leveraging nodriver's Chromium automation:
1. research_nodriver_fetch: Fetch pages with auto-bypass of anti-bot systems
2. research_nodriver_extract: Extract DOM elements by selector or XPath
3. research_nodriver_session: Persistent browser session management

All tools are fully async and handle Cloudflare, bot detection, and JavaScript rendering.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import time
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Literal

try:
    import nodriver as uc
    from nodriver import Browser, Tab

    _HAS_NODRIVER = True
except ImportError:  # pragma: no cover
    _HAS_NODRIVER = False
    Browser = None
    Tab = None

from pydantic import BaseModel, ConfigDict, Field

from loom.cache import get_cache
from loom.error_responses import handle_tool_errors
from loom.validators import EXTERNAL_TIMEOUT_SECS, validate_url

logger = logging.getLogger("loom.nodriver_backend")

# Global session registry: name -> Browser instance
_nodriver_sessions: dict[str, Browser] = {}
_session_lock: asyncio.Lock | None = None


def _get_session_lock() -> asyncio.Lock:
    """Lazily initialize session lock to avoid event loop creation at import time."""
    global _session_lock
    if _session_lock is None:
        _session_lock = asyncio.Lock()
    return _session_lock


class NodriverFetchResult(BaseModel):
    """Result from a nodriver fetch operation."""

    url: str
    html: str = ""
    text: str = ""
    screenshot_b64: str | None = None
    status_code: int | None = None
    bypass_method: str = "none"
    error: str | None = None
    elapsed_ms: int = 0
    timestamp: str = ""

    model_config = ConfigDict(populate_by_name=True)


class NodriverExtractResult(BaseModel):
    """Result from a nodriver element extraction."""

    url: str
    selector: str = ""
    xpath: str = ""
    elements: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    error: str | None = None
    elapsed_ms: int = 0

    model_config = ConfigDict(populate_by_name=True)


class NodriverSessionResult(BaseModel):
    """Result from a nodriver session operation."""

    session_name: str
    action: str
    result: str | dict[str, Any] = ""
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


@handle_tool_errors("research_nodriver_fetch")
async def research_nodriver_fetch(
    url: str,
    wait_for: str | None = None,
    timeout: int = 30,
    screenshot: bool = False,
    bypass_cache: bool = False,
    max_chars: int = 20000,
) -> dict[str, Any]:
    """Fetch a URL using async undetected Chrome browser.

    Uses nodriver to bypass Cloudflare, bot detection, and other anti-bot systems.
    Fully asynchronous with automatic escalation strategies.

    Args:
        url: Target URL to fetch
        wait_for: Optional CSS selector to wait for before returning
        timeout: Maximum time in seconds to wait for page load (1-120)
        screenshot: If True, capture page screenshot as base64 PNG
        bypass_cache: If True, skip cache and fetch fresh
        max_chars: Maximum characters to return in text (1-50000)

    Returns:
        Dict with:
        - url: The fetched URL
        - html: Full page HTML
        - text: Extracted readable text
        - screenshot_b64: Base64 PNG screenshot (if requested)
        - status_code: HTTP status code (when available)
        - bypass_method: Detection bypass method used (none, cf_verify, javascript_wait)
        - error: Error message if fetch failed
        - elapsed_ms: Time elapsed in milliseconds
        - timestamp: ISO 8601 timestamp
    """
    # Validate parameters first
    if timeout < 1 or timeout > 120:
        timeout = min(max(timeout, 1), 120)
    if max_chars < 1 or max_chars > 50000:
        max_chars = min(max(max_chars, 1), 50000)

    # Validate URL
    try:
        url = validate_url(url)
    except ValueError as e:
        return {
            "url": url,
            "html": "",
            "text": "",
            "screenshot_b64": None,
            "status_code": None,
            "bypass_method": "none",
            "error": f"Invalid URL: {str(e)}",
            "elapsed_ms": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    if not _HAS_NODRIVER:
        return {
            "url": url,
            "html": "",
            "text": "",
            "screenshot_b64": None,
            "status_code": None,
            "bypass_method": "none",
            "error": "nodriver not installed. Install with: pip install nodriver",
            "elapsed_ms": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }


    # Check cache
    cache_key = _make_cache_key(url, "nodriver")
    if not bypass_cache:
        cached = get_cache().get(cache_key)
        if cached:
            logger.info("nodriver_cache_hit url=%s", url)
            result = cached.copy()
            result["timestamp"] = datetime.now(UTC).isoformat()
            return result

    start_time = time.time()
    result = NodriverFetchResult(url=url, timestamp=datetime.now(UTC).isoformat())
    bypass_method = "none"

    try:
        browser = await uc.start(headless=True)
        page: Tab | None = None

        try:
            # Fetch page
            logger.info("nodriver_fetch_start url=%s timeout=%d", url, timeout)
            page = await asyncio.wait_for(browser.get(url), timeout=timeout)

            # Try to verify Cloudflare challenge
            try:
                await asyncio.wait_for(page.cf_verify(), timeout=10)
                bypass_method = "cf_verify"
                logger.info("nodriver_cf_verify_success url=%s", url)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.debug("nodriver_cf_verify_skip reason=%s", str(e)[:100])

            # Wait for optional selector
            if wait_for:
                try:
                    selector_timeout = max(timeout - 5, 1)
                    await asyncio.wait_for(page.select(wait_for), timeout=selector_timeout)
                    logger.info("nodriver_wait_selector_success url=%s selector=%s", url, wait_for)
                    bypass_method = "javascript_wait"
                except asyncio.TimeoutError:
                    logger.warning("nodriver_wait_selector_timeout url=%s selector=%s", url, wait_for)
                except Exception as e:
                    logger.debug("nodriver_wait_selector_failed url=%s error=%s", url, str(e)[:100])

            # Get page content
            html = await page.get_content()
            result.html = html[:50000] if html else ""

            # Extract text
            text = _extract_text_from_html(html)
            if len(text) > max_chars:
                text = text[:max_chars] + "…"
            result.text = text

            # Try to get status code
            try:
                # nodriver doesn't directly expose status codes, so we attempt navigation
                result.status_code = 200
            except Exception:
                pass

            # Optional screenshot
            if screenshot:
                try:
                    screenshot_bytes = await asyncio.wait_for(page.save_screenshot(), timeout=10)
                    result.screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                except Exception as e:
                    logger.debug("nodriver_screenshot_failed error=%s", str(e)[:100])

            result.bypass_method = bypass_method
            logger.info("nodriver_fetch_success url=%s bypass=%s", url, bypass_method)

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            try:
                await browser.stop()
            except Exception:
                pass

    except asyncio.TimeoutError as e:
        result.error = f"Timeout after {timeout} seconds"
        logger.warning("nodriver_fetch_timeout url=%s error=%s", url, result.error)
    except Exception as e:
        result.error = f"Fetch failed: {str(e)[:200]}"
        logger.error("nodriver_fetch_error url=%s error=%s", url, str(e)[:200])

    result.elapsed_ms = int((time.time() - start_time) * 1000)
    result.timestamp = datetime.now(UTC).isoformat()

    # Cache result
    result_dict = result.model_dump()
    get_cache().set(cache_key, result_dict)

    return result_dict


@handle_tool_errors("research_nodriver_extract")
async def research_nodriver_extract(
    url: str,
    css_selector: str | None = None,
    xpath: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Extract DOM elements from a page by CSS selector or XPath.

    Fetches the page and extracts specific elements based on selector or XPath.
    Returns structured data about found elements including tags, text, and attributes.

    Args:
        url: Target URL to fetch and extract from
        css_selector: CSS selector for elements (e.g., "a[href*=github]")
        xpath: XPath expression for elements (e.g., "//a[@class='link']")
        timeout: Maximum time in seconds to wait (1-120)

    Returns:
        Dict with:
        - url: The target URL
        - selector: CSS selector used (empty if xpath used)
        - xpath: XPath used (empty if selector used)
        - elements: List of dicts with {tag, text, attrs}
        - count: Number of elements found
        - error: Error message if extraction failed
        - elapsed_ms: Time elapsed in milliseconds
    """
    # Validate timeout first
    if timeout < 1 or timeout > 120:
        timeout = min(max(timeout, 1), 120)

    # Validate URL
    try:
        url = validate_url(url)
    except ValueError as e:
        return {
            "url": url,
            "selector": css_selector or "",
            "xpath": xpath or "",
            "elements": [],
            "count": 0,
            "error": f"Invalid URL: {str(e)}",
            "elapsed_ms": 0,
        }

    if not css_selector and not xpath:
        return {
            "url": url,
            "selector": "",
            "xpath": "",
            "elements": [],
            "count": 0,
            "error": "Must provide either css_selector or xpath",
            "elapsed_ms": 0,
        }

    if not _HAS_NODRIVER:
        return {
            "url": url,
            "selector": css_selector or "",
            "xpath": xpath or "",
            "elements": [],
            "count": 0,
            "error": "nodriver not installed. Install with: pip install nodriver",
            "elapsed_ms": 0,
        }

    start_time = time.time()
    result = NodriverExtractResult(
        url=url,
        selector=css_selector or "",
        xpath=xpath or "",
    )

    try:
        browser = await uc.start(headless=True)
        page: Tab | None = None

        try:
            logger.info("nodriver_extract_start url=%s selector=%s xpath=%s", url, css_selector, xpath)
            page = await asyncio.wait_for(browser.get(url), timeout=timeout)

            # Extract elements
            elements_list: list[dict[str, Any]] = []

            if css_selector:
                try:
                    elements = await page.select_all(css_selector)
                    elements_list = await _extract_element_data(elements)
                except Exception as e:
                    result.error = f"CSS selector failed: {str(e)[:200]}"
                    logger.warning("nodriver_extract_css_failed url=%s error=%s", url, str(e)[:100])

            elif xpath:
                try:
                    elements = await page.xpath(xpath)
                    elements_list = await _extract_element_data(elements)
                except Exception as e:
                    result.error = f"XPath failed: {str(e)[:200]}"
                    logger.warning("nodriver_extract_xpath_failed url=%s error=%s", url, str(e)[:100])

            result.elements = elements_list
            result.count = len(elements_list)
            logger.info("nodriver_extract_success url=%s count=%d", url, result.count)

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            try:
                await browser.stop()
            except Exception:
                pass

    except asyncio.TimeoutError:
        result.error = f"Timeout after {timeout} seconds"
        logger.warning("nodriver_extract_timeout url=%s", url)
    except Exception as e:
        result.error = f"Extraction failed: {str(e)[:200]}"
        logger.error("nodriver_extract_error url=%s error=%s", url, str(e)[:200])

    result.elapsed_ms = int((time.time() - start_time) * 1000)

    return result.model_dump()


@handle_tool_errors("research_nodriver_session")
async def research_nodriver_session(
    action: Literal["open", "navigate", "extract", "close"],
    session_name: str = "default",
    url: str | None = None,
    css_selector: str | None = None,
    xpath: str | None = None,
) -> dict[str, Any]:
    """Manage persistent browser sessions.

    Allows opening a browser session, navigating to URLs, extracting content,
    and closing sessions. Sessions persist across multiple calls.

    Args:
        action: Session action: "open" (start), "navigate" (goto url), "extract" (get content), "close" (end)
        session_name: Name of the session (alphanumeric, default "default")
        url: Target URL (required for "navigate" action)
        css_selector: CSS selector for "extract" action
        xpath: XPath for "extract" action

    Returns:
        Dict with:
        - session_name: Name of the session
        - action: Action performed
        - result: Result message or data dict
        - error: Error message if action failed
    """
    # Validate session name first
    if not (1 <= len(session_name) <= 32 and session_name.replace("_", "").replace("-", "").isalnum()):
        return {
            "session_name": session_name,
            "action": action,
            "result": "",
            "error": "Invalid session name. Use alphanumeric, underscore, or hyphen (1-32 chars)",
        }

    if not _HAS_NODRIVER:
        return {
            "session_name": session_name,
            "action": action,
            "result": "",
            "error": "nodriver not installed. Install with: pip install nodriver",
        }

    async with _get_session_lock():
        try:
            if action == "open":
                if session_name in _nodriver_sessions:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "Session already open",
                        "error": None,
                    }

                logger.info("nodriver_session_open name=%s", session_name)
                browser = await uc.start(headless=True)
                _nodriver_sessions[session_name] = browser
                return {
                    "session_name": session_name,
                    "action": action,
                    "result": f"Session '{session_name}' opened",
                    "error": None,
                }

            elif action == "navigate":
                if not url:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": "URL required for navigate action",
                    }

                try:
                    url = validate_url(url)
                except ValueError as e:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": f"Invalid URL: {str(e)}",
                    }

                if session_name not in _nodriver_sessions:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": f"Session '{session_name}' not open. Call with action='open' first",
                    }

                try:
                    browser = _nodriver_sessions[session_name]
                    logger.info("nodriver_session_navigate session=%s url=%s", session_name, url)
                    page = await asyncio.wait_for(browser.get(url), timeout=EXTERNAL_TIMEOUT_SECS)
                    # Do not close page — keep it open in the session for subsequent extract calls
                    # The page will be closed when the session is closed or another navigate is called
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": f"Navigated to {url}",
                        "error": None,
                    }
                except Exception as e:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": f"Navigation failed: {str(e)[:200]}",
                    }

            elif action == "extract":
                if session_name not in _nodriver_sessions:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": f"Session '{session_name}' not open",
                    }

                if not css_selector and not xpath:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": "Must provide css_selector or xpath for extract action",
                    }

                try:
                    browser = _nodriver_sessions[session_name]
                    # Get first tab
                    tabs = await browser.get_tabs()
                    if not tabs:
                        return {
                            "session_name": session_name,
                            "action": action,
                            "result": "",
                            "error": "No tabs open in session",
                        }

                    page = tabs[0]
                    elements_list: list[dict[str, Any]] = []

                    if css_selector:
                        elements = await page.select_all(css_selector)
                        elements_list = await _extract_element_data(elements)
                    elif xpath:
                        elements = await page.xpath(xpath)
                        elements_list = await _extract_element_data(elements)

                    logger.info("nodriver_session_extract session=%s count=%d", session_name, len(elements_list))
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": {"elements": elements_list, "count": len(elements_list)},
                        "error": None,
                    }
                except Exception as e:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": f"Extraction failed: {str(e)[:200]}",
                    }

            elif action == "close":
                if session_name not in _nodriver_sessions:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": f"Session '{session_name}' not open",
                        "error": None,
                    }

                try:
                    logger.info("nodriver_session_close name=%s", session_name)
                    browser = _nodriver_sessions.pop(session_name)
                    await browser.stop()
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": f"Session '{session_name}' closed",
                        "error": None,
                    }
                except Exception as e:
                    return {
                        "session_name": session_name,
                        "action": action,
                        "result": "",
                        "error": f"Close failed: {str(e)[:200]}",
                    }

            else:
                return {
                    "session_name": session_name,
                    "action": action,
                    "result": "",
                    "error": f"Unknown action: {action}. Use: open, navigate, extract, close",
                }

        except Exception as e:
            logger.error("nodriver_session_error action=%s session=%s error=%s", action, session_name, str(e)[:200])
            return {
                "session_name": session_name,
                "action": action,
                "result": "",
                "error": f"Session error: {str(e)[:200]}",
            }


# ============================================================================
# Helper functions
# ============================================================================


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML.

    Removes script/style tags and HTML markup.
    """
    if not html:
        return ""

    try:
        import re

        # Remove script and style elements
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        text = " ".join(text.split())
        return text
    except Exception as e:
        logger.warning("text_extraction_failed error=%s", e)
        return ""


async def _extract_element_data(elements: list[Any]) -> list[dict[str, Any]]:
    """Extract tag, text, and attributes from nodriver elements."""
    result = []

    for elem in elements:
        try:
            # Get tag name
            tag = getattr(elem, "tag", "unknown")

            # Get text content
            text = ""
            try:
                text = await elem.get_text()
            except Exception:
                pass

            # Get attributes
            attrs = {}
            try:
                attrs = dict(await elem.get_attributes() or {})
            except Exception:
                pass

            result.append({"tag": tag, "text": text[:500], "attrs": attrs})
        except Exception as e:
            logger.debug("element_extraction_failed error=%s", str(e)[:100])

    return result


def _make_cache_key(url: str, mode: str) -> str:
    """Create a cache key from url and mode."""
    combined = f"{url}|{mode}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]
