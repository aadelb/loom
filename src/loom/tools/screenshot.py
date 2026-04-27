"""research_screenshot — Capture webpage screenshots using Playwright.

Provides full-page, element-level, and viewport screenshots with
base64 encoding.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

try:
    from playwright.async_api import async_playwright

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.screenshot")

# Constraints
MAX_URL_LENGTH = 2048
SCREENSHOT_TIMEOUT_MS = 30000
DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_VIEWPORT_HEIGHT = 1080


async def research_screenshot(
    url: str,
    full_page: bool = False,
    selector: str | None = None,
) -> dict[str, Any]:
    """Take a screenshot of a webpage using Playwright.

    Args:
        url: webpage URL to screenshot
        full_page: if True, capture full scrollable page height
        selector: if provided, capture only this CSS selector element

    Returns:
        Dict with:
        - url: the input URL
        - screenshot_base64: base64-encoded PNG image
        - width: image width in pixels
        - height: image height in pixels
        - full_page: whether full-page capture was used
        - selector: the selector used (if any)
        - error: error message if any
    """
    # Validate Playwright availability
    if not _HAS_PLAYWRIGHT:
        error_msg = "Playwright not installed. Run: pip install playwright && playwright install chromium"
        logger.error("playwright_not_available")
        return {
            "url": url,
            "error": error_msg,
            "full_page": full_page,
            "selector": selector,
        }

    # Validate URL
    try:
        validated_url = validate_url(url)
    except ValueError as e:
        error_msg = f"invalid URL: {e!s}"
        logger.warning("screenshot_invalid_url error=%s", error_msg)
        return {
            "url": url,
            "error": error_msg,
            "full_page": full_page,
            "selector": selector,
        }

    # Additional URL length check
    if len(validated_url) > MAX_URL_LENGTH:
        error_msg = f"URL exceeds {MAX_URL_LENGTH} character limit"
        logger.warning("screenshot_url_too_long length=%d", len(validated_url))
        return {
            "url": validated_url,
            "error": error_msg,
            "full_page": full_page,
            "selector": selector,
        }

    # Validate selector if provided
    if selector is not None:
        if not isinstance(selector, str) or len(selector) == 0:
            error_msg = "selector must be a non-empty string"
            logger.warning("screenshot_invalid_selector")
            return {
                "url": validated_url,
                "error": error_msg,
                "full_page": full_page,
                "selector": selector,
            }

        if len(selector) > 256:
            error_msg = "selector exceeds 256 character limit"
            logger.warning("screenshot_selector_too_long")
            return {
                "url": validated_url,
                "error": error_msg,
                "full_page": full_page,
                "selector": selector,
            }

    browser = None
    try:
        # Launch Playwright browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # Create new page with default viewport
            page = await browser.new_page(
                viewport={"width": DEFAULT_VIEWPORT_WIDTH, "height": DEFAULT_VIEWPORT_HEIGHT}
            )

            try:
                # Navigate to URL
                await page.goto(validated_url, timeout=SCREENSHOT_TIMEOUT_MS, wait_until="networkidle")

                # Take screenshot
                if selector:
                    # Screenshot specific element
                    element = await page.query_selector(selector)
                    if not element:
                        error_msg = f"element not found: {selector}"
                        logger.warning("screenshot_selector_not_found selector=%s", selector)
                        await page.close()
                        return {
                            "url": validated_url,
                            "error": error_msg,
                            "full_page": full_page,
                            "selector": selector,
                        }

                    screenshot_bytes = await element.screenshot()
                    # Get element bounding box for dimensions
                    bbox = await element.bounding_box()
                    width = int(bbox["width"]) if bbox else DEFAULT_VIEWPORT_WIDTH
                    height = int(bbox["height"]) if bbox else DEFAULT_VIEWPORT_HEIGHT
                else:
                    # Screenshot full page or viewport
                    screenshot_bytes = await page.screenshot(full_page=full_page)

                    # Get viewport dimensions
                    if full_page:
                        # Get actual page dimensions
                        dimensions = await page.evaluate(
                            "() => ({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight})"
                        )
                        width = dimensions.get("width", DEFAULT_VIEWPORT_WIDTH)
                        height = dimensions.get("height", DEFAULT_VIEWPORT_HEIGHT)
                    else:
                        width = DEFAULT_VIEWPORT_WIDTH
                        height = DEFAULT_VIEWPORT_HEIGHT

                # Encode to base64
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                logger.info(
                    "screenshot_captured url=%s selector=%s full_page=%s dimensions=%dx%d",
                    validated_url[:50],
                    selector or "none",
                    full_page,
                    width,
                    height,
                )

                return {
                    "url": validated_url,
                    "screenshot_base64": screenshot_base64,
                    "width": width,
                    "height": height,
                    "full_page": full_page,
                    "selector": selector,
                }

            except Exception as page_error:
                error_msg = f"page operation failed: {page_error!s}"
                logger.error("screenshot_page_error: %s", page_error)
                return {
                    "url": validated_url,
                    "error": error_msg,
                    "full_page": full_page,
                    "selector": selector,
                }

            finally:
                await page.close()

    except TimeoutError:
        error_msg = f"screenshot timeout ({SCREENSHOT_TIMEOUT_MS}ms)"
        logger.warning("screenshot_timeout url=%s", validated_url[:50])
        return {
            "url": validated_url,
            "error": error_msg,
            "full_page": full_page,
            "selector": selector,
        }

    except Exception as e:
        error_msg = f"screenshot failed: {e!s}"
        logger.error("screenshot_error: %s", e)
        return {
            "url": validated_url,
            "error": error_msg,
            "full_page": full_page,
            "selector": selector,
        }

    finally:
        if browser:
            try:
                await browser.close()
            except Exception as close_error:
                logger.warning("screenshot_browser_close_error: %s", close_error)
