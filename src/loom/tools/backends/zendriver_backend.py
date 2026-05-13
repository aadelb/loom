"""Zendriver async browser backend for Docker-friendly undetected web automation.

Provides three main tools:
1. research_zen_fetch — Single URL fetch with undetected browser
2. research_zen_batch — Concurrent batch fetching of multiple URLs
3. research_zen_interact — Interactive page operations (click, fill, scroll, wait)

Zendriver is a fork of nodriver that uses Chrome DevTools Protocol (CDP)
for undetectable automation in async-first applications.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    import zendriver as zd

    _HAS_ZENDRIVER = True
except ImportError:  # pragma: no cover — optional dependency
    _HAS_ZENDRIVER = False

from loom.validators import validate_url, EXTERNAL_TIMEOUT_SECS

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.zendriver_backend")

# Module-level browser instance and event loop management
_browser_instance: Any = None
_event_loop: asyncio.AbstractEventLoop | None = None


class ZenFetchResult(BaseModel):
    """Result from a zendriver fetch operation."""

    url: str
    html: str = ""
    text: str = ""
    status: int | None = None
    method: str = "GET"
    error: str | None = None
    elapsed_ms: int = 0
    title: str = ""

    model_config = ConfigDict(populate_by_name=True)


class ZenBatchResult(BaseModel):
    """Result from a zendriver batch fetch operation."""

    urls_requested: int = 0
    urls_succeeded: int = 0
    urls_failed: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)
    elapsed_ms: int = 0
    errors: list[str] = Field(default_factory=list)


class ZenInteractResult(BaseModel):
    """Result from a zendriver interaction operation."""

    url: str
    actions_performed: int = 0
    final_html: str = ""
    final_text: str = ""
    error: str | None = None
    elapsed_ms: int = 0


def _ensure_event_loop() -> asyncio.AbstractEventLoop:
    """Ensure an event loop exists and is running in the current thread."""
    global _event_loop
    try:
        loop = asyncio.get_running_loop()
        return loop
    except RuntimeError:
        # No running loop, try to get the current thread's event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _event_loop = loop
            return loop


async def _get_browser() -> Any:
    """Get or create the shared browser instance."""
    global _browser_instance
    if _browser_instance is None:
        try:
            _browser_instance = await zd.start(
                headless=True,
                # Docker-friendly options
                user_data_dir=None,  # Use default temp dir
            )
            logger.info("zendriver_browser_started")
        except Exception as e:
            logger.error("zendriver_start_failed error=%s", str(e))
            raise
    return _browser_instance


async def _cleanup_browser() -> None:
    """Close the shared browser instance."""
    global _browser_instance
    if _browser_instance is not None:
        try:
            await _browser_instance.stop()
            logger.info("zendriver_browser_stopped")
        except Exception as e:
            logger.warning("zendriver_browser_cleanup_error error=%s", str(e))
        finally:
            _browser_instance = None


async def _fetch_with_zendriver(
    url: str,
    timeout: int = 30,
    headless: bool = True,
) -> dict[str, Any]:
    """Fetch a single URL using zendriver (async).

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds (1-120)
        headless: Run in headless mode (Docker-friendly)

    Returns:
        Dictionary with url, html, text, status, method, error, elapsed_ms, title
    """
    if not _HAS_ZENDRIVER:
        raise ImportError("zendriver not installed. Install with: pip install zendriver")

    start_time = time.time()
    result: dict[str, Any] = {
        "url": url,
        "html": "",
        "text": "",
        "status": None,
        "method": "GET",
        "error": None,
    }

    try:
        browser = await _get_browser()
        page = await asyncio.wait_for(
            browser.get(url),
            timeout=timeout,
        )

        # Extract content with timeout
        content_task = asyncio.create_task(page.get_content())
        text_task = asyncio.create_task(page.get_all_text())

        try:
            html = await asyncio.wait_for(content_task, timeout=timeout)
            text = await asyncio.wait_for(text_task, timeout=timeout)
        except asyncio.TimeoutError:
            html = ""
            text = ""

        # Extract title if available
        title_task = asyncio.create_task(
            page.evaluate("document.title"),
        )
        try:
            title = await asyncio.wait_for(title_task, timeout=5)
            if not isinstance(title, str):
                title = ""
        except Exception:
            title = ""

        result["html"] = html
        result["text"] = text
        result["title"] = title
        result["status"] = 200  # CDP doesn't expose status, assume 200 if loaded
        result["error"] = None

    except asyncio.TimeoutError:
        result["error"] = f"timeout after {timeout} seconds"
    except Exception as e:
        result["error"] = str(e)
        logger.error("zendriver_fetch_error url=%s error=%s", url, str(e))

    result["elapsed_ms"] = int((time.time() - start_time) * 1000)
    return result

@handle_tool_errors("research_zen_fetch")

def research_zen_fetch(
    url: str,
    timeout: int = 30,
    headless: bool = True,
) -> dict[str, Any]:
    """Fetch a single URL using undetected async browser (zendriver).

    Args:
        url: URL to fetch (SSRF-validated)
        timeout: Request timeout in seconds (1-120, default 30)
        headless: Run browser in headless mode (default True, Docker-friendly)

    Returns:
        Dictionary: {url, html, text, status, method, error, elapsed_ms, title}
        - html: Full HTML content of the page
        - text: Extracted text content
        - status: HTTP status code (None if not available via CDP)
        - title: Page title from <title> tag
        - error: Error message if fetch failed

    Example:
        result = research_zen_fetch("https://example.com", timeout=30)
        print(result["text"])
    """
    if not _HAS_ZENDRIVER:
        raise ImportError("zendriver not installed. Install with: pip install zendriver")

    # Validate URL
    validated_url = validate_url(url)

    # Validate timeout
    if timeout < 1 or timeout > 120:
        raise ValueError("timeout must be 1-120 seconds")

    # Get or create event loop and run async fetch
    loop = _ensure_event_loop()
    try:
        result = loop.run_until_complete(
            _fetch_with_zendriver(validated_url, timeout, headless),
        )
        return ZenFetchResult(**result).model_dump()
    except Exception as e:
        logger.error("research_zen_fetch_failed url=%s error=%s", url, str(e))
        return ZenFetchResult(
            url=validated_url,
            error=str(e),
        ).model_dump()


async def _batch_fetch_concurrent(
    urls: list[str],
    max_concurrent: int = 5,
    timeout: int = 30,
) -> dict[str, Any]:
    """Fetch multiple URLs concurrently with semaphore (async).

    Args:
        urls: List of URLs to fetch
        max_concurrent: Max concurrent requests (1-50)
        timeout: Per-request timeout in seconds

    Returns:
        Dictionary with urls_requested, urls_succeeded, urls_failed, results, errors
    """
    start_time = time.time()
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []
    errors = []
    succeeded = 0
    failed = 0

    async def fetch_with_semaphore(url: str) -> None:
        nonlocal succeeded, failed
        async with semaphore:
            try:
                result = await _fetch_with_zendriver(url, timeout)
                if not result.get("error"):
                    succeeded += 1
                else:
                    failed += 1
                results.append(result)
            except Exception as e:
                failed += 1
                error_msg = f"{url}: {str(e)}"
                errors.append(error_msg)
                results.append({
                    "url": url,
                    "error": str(e),
                })

    # Create tasks for all URLs
    tasks = [fetch_with_semaphore(url) for url in urls]
    await asyncio.gather(*tasks, return_exceptions=False)

    return {
        "urls_requested": len(urls),
        "urls_succeeded": succeeded,
        "urls_failed": failed,
        "results": results,
        "errors": errors,
        "elapsed_ms": int((time.time() - start_time) * 1000),
    }

@handle_tool_errors("research_zen_batch")

def research_zen_batch(
    urls: list[str],
    max_concurrent: int = 5,
    timeout: int = 30,
) -> dict[str, Any]:
    """Batch fetch multiple URLs concurrently with undetected browser.

    Args:
        urls: List of URLs to fetch (2-100 items)
        max_concurrent: Max concurrent requests (1-50, default 5)
        timeout: Per-request timeout in seconds (1-120, default 30)

    Returns:
        Dictionary: {urls_requested, urls_succeeded, urls_failed, results, errors, elapsed_ms}
        - results: List of fetch results, each with {url, html, text, status, error, ...}
        - errors: List of error strings

    Example:
        result = research_zen_batch(["https://example.com", "https://test.com"])
        print(f"Fetched {result['urls_succeeded']}/{result['urls_requested']}")
    """
    if not _HAS_ZENDRIVER:
        raise ImportError("zendriver not installed. Install with: pip install zendriver")

    # Validate URLs list
    if not urls:
        raise ValueError("urls list cannot be empty")
    if len(urls) > 100:
        raise ValueError("urls list max 100 items")

    validated_urls = [validate_url(u) for u in urls]

    # Validate parameters
    if max_concurrent < 1 or max_concurrent > 50:
        raise ValueError("max_concurrent must be 1-50")
    if timeout < 1 or timeout > 120:
        raise ValueError("timeout must be 1-120 seconds")

    # Run batch fetch
    loop = _ensure_event_loop()
    try:
        result = loop.run_until_complete(
            _batch_fetch_concurrent(validated_urls, max_concurrent, timeout),
        )
        return ZenBatchResult(**result).model_dump()
    except Exception as e:
        logger.error("research_zen_batch_failed urls_count=%d error=%s", len(urls), str(e))
        return ZenBatchResult(
            urls_requested=len(urls),
            urls_failed=len(urls),
            errors=[str(e)],
        ).model_dump()


async def _interact_with_page(
    url: str,
    actions: list[dict[str, Any]],
    timeout: int = 30,
) -> dict[str, Any]:
    """Perform interactive operations on a page (async).

    Args:
        url: URL to navigate to
        actions: List of action dicts, each with:
            - type: "click", "fill", "scroll", "wait"
            - selector: CSS selector for the element (for click/fill)
            - value: Text to fill or wait_ms (for scroll, value is unused)
        timeout: Total operation timeout in seconds

    Returns:
        Dictionary with url, actions_performed, final_html, final_text, error, elapsed_ms
    """
    start_time = time.time()
    result: dict[str, Any] = {
        "url": url,
        "actions_performed": 0,
        "final_html": "",
        "final_text": "",
        "error": None,
    }

    if not actions:
        result["error"] = "actions list is empty"
        return result

    try:
        browser = await _get_browser()
        page = await asyncio.wait_for(
            browser.get(url),
            timeout=timeout,
        )

        actions_performed = 0
        for i, action in enumerate(actions):
            if i > 0:
                # Check if we've exceeded timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    result["error"] = f"timeout after {timeout}s, completed {i} of {len(actions)} actions"
                    break

            action_type = action.get("type", "").lower()
            selector = action.get("selector", "")
            value = action.get("value", "")

            try:
                if action_type == "click":
                    # Wait for element and click
                    elements = await asyncio.wait_for(
                        page.find(selector, best_match=True),
                        timeout=5,
                    )
                    if elements:
                        element = elements[0] if isinstance(elements, list) else elements
                        await element.click()
                        actions_performed += 1
                    else:
                        result["error"] = f"click: element not found for selector '{selector}'"
                        break

                elif action_type == "fill":
                    # Fill input field
                    elements = await asyncio.wait_for(
                        page.find(selector, best_match=True),
                        timeout=5,
                    )
                    if elements:
                        element = elements[0] if isinstance(elements, list) else elements
                        await element.clear()
                        await element.send_keys(value)
                        actions_performed += 1
                    else:
                        result["error"] = f"fill: element not found for selector '{selector}'"
                        break

                elif action_type == "scroll":
                    # Scroll by pixels (value is pixel count, or 0 for page down)
                    scroll_px = int(value) if value else 500
                    await page.scroll(0, scroll_px)
                    actions_performed += 1

                elif action_type == "wait":
                    # Wait for element to appear
                    try:
                        await asyncio.wait_for(
                            page.find(selector),
                            timeout=int(value) if value else 10,
                        )
                        actions_performed += 1
                    except asyncio.TimeoutError:
                        result["error"] = f"wait: timeout waiting for selector '{selector}'"
                        break

                else:
                    result["error"] = f"unknown action type: {action_type}"
                    break

                # Small delay between actions
                await asyncio.sleep(0.5)

            except Exception as e:
                result["error"] = f"{action_type} action failed: {str(e)}"
                break

        # Extract final content
        try:
            final_html = await asyncio.wait_for(
                page.get_content(),
                timeout=5,
            )
            final_text = await asyncio.wait_for(
                page.get_all_text(),
                timeout=5,
            )
            result["final_html"] = final_html
            result["final_text"] = final_text
        except Exception as e:
            logger.warning("failed_to_extract_final_content error=%s", str(e))

        result["actions_performed"] = actions_performed

    except asyncio.TimeoutError:
        result["error"] = f"timeout after {timeout} seconds"
    except Exception as e:
        result["error"] = str(e)
        logger.error("zendriver_interact_error url=%s error=%s", url, str(e))

    result["elapsed_ms"] = int((time.time() - start_time) * 1000)
    return result

@handle_tool_errors("research_zen_interact")

def research_zen_interact(
    url: str,
    actions: list[dict[str, str]],
    timeout: int = 30,
) -> dict[str, Any]:
    """Interact with a web page: click, fill, scroll, wait for elements.

    Args:
        url: URL to navigate to (SSRF-validated)
        actions: List of action dicts with:
            - type: "click" | "fill" | "scroll" | "wait"
            - selector: CSS selector for element (for click/fill/wait)
            - value: Text to fill, pixels to scroll, or wait timeout in seconds
        timeout: Total operation timeout (1-120 seconds, default 30)

    Returns:
        Dictionary: {url, actions_performed, final_html, final_text, error, elapsed_ms}
        - actions_performed: Number of actions completed before error/finish
        - final_html: Page HTML after all actions
        - final_text: Page text content after all actions

    Example:
        actions = [
            {"type": "click", "selector": "button.submit"},
            {"type": "fill", "selector": "input#email", "value": "test@example.com"},
            {"type": "wait", "selector": "div.result", "value": "10"},
        ]
        result = research_zen_interact("https://example.com", actions)
    """
    if not _HAS_ZENDRIVER:
        raise ImportError("zendriver not installed. Install with: pip install zendriver")

    # Validate URL
    validated_url = validate_url(url)

    # Validate timeout
    if timeout < 1 or timeout > 120:
        raise ValueError("timeout must be 1-120 seconds")

    # Validate actions type (reject string input to avoid masking errors)
    if isinstance(actions, str):
        raise ValueError("actions must be a list of dicts, not a string. Example: [{\"type\": \"click\", \"selector\": \"button\"}]")

    # Validate actions
    if not isinstance(actions, list):
        raise ValueError("actions must be a list")
    if not actions:
        raise ValueError("actions list cannot be empty")
    if len(actions) > 50:
        raise ValueError("actions list max 50 items")

    # Get or create event loop and run async interact
    loop = _ensure_event_loop()
    try:
        result = loop.run_until_complete(
            _interact_with_page(validated_url, actions, timeout),
        )
        return ZenInteractResult(**result).model_dump()
    except Exception as e:
        logger.error("research_zen_interact_failed url=%s error=%s", url, str(e))
        return ZenInteractResult(
            url=validated_url,
            error=str(e),
        ).model_dump()
