"""Scrapling integration tools exposing advanced scraping capabilities.

This module exposes Scrapling's powerful features:
- research_scrape: One-call fetch + extract with fetcher selection
- research_scrape_similar: Find structurally similar elements (product cards, etc.)
- research_scrape_adaptive: Adaptive scraping that survives HTML changes

Scrapling API: https://github.com/D4Vinci/Scrapling (v0.4.1)
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Literal

from loom.error_responses import handle_tool_errors
from loom.validators import validate_url

try:
    from loom.params import (
        ScraplingFetchParams,
        ScraplingFindSimilarParams,
        ScraplingAdaptiveParams,
    )
    _PARAMS_AVAILABLE = True
except ImportError:
    _PARAMS_AVAILABLE = False

logger = logging.getLogger("loom.tools.scrapling")


def _get_fetcher_basic():
    """Get basic Fetcher or return None if unavailable."""
    try:
        from scrapling import Fetcher
        return Fetcher()
    except ImportError:
        logger.warning("Scrapling not available")
        return None


def _get_fetcher_stealthy():
    """Get StealthyFetcher or return None."""
    try:
        from scrapling import StealthyFetcher
        return StealthyFetcher()
    except ImportError:
        return None


def _get_fetcher_dynamic():
    """Get DynamicFetcher or return None."""
    try:
        from scrapling import DynamicFetcher
        return DynamicFetcher()
    except ImportError:
        return None


def _response_to_selector(response: Any) -> Any:
    """Convert Response object to Selector (Response is a Selector subclass)."""
    return response


def _extract_from_selectors(
    selectors_list: list[Any],
    extract_mode: Literal["text", "html", "attribute", "all"],
    attribute_name: str | None = None,
    regex_pattern: str | None = None,
    max_results: int = 100,
) -> list[str]:
    """Extract data from a list of Selector objects.

    Args:
        selectors_list: List of Selector objects from .css/.xpath/.find_all
        extract_mode: "text" (element text), "html" (outer HTML),
                      "attribute" (specific attribute), "all" (dict of all)
        attribute_name: Attribute name to extract (when extract_mode="attribute")
        regex_pattern: Optional regex to filter/extract from text
        max_results: Max number of results to return

    Returns:
        List of extracted values as strings or dicts
    """
    results = []

    for i, selector in enumerate(selectors_list[:max_results]):
        try:
            if extract_mode == "text":
                # Get text content
                text = str(selector.text)
                if regex_pattern:
                    match = re.search(regex_pattern, text)
                    results.append(match.group(0) if match else text)
                else:
                    results.append(text)

            elif extract_mode == "html":
                # Get HTML (via body property which represents the element)
                html = str(selector.body) if hasattr(selector, "body") else str(selector)
                if regex_pattern:
                    match = re.search(regex_pattern, html)
                    results.append(match.group(0) if match else html)
                else:
                    results.append(html)

            elif extract_mode == "attribute":
                # Get specific attribute
                if attribute_name:
                    attribs = selector.attrib
                    value = attribs.get(attribute_name, "")
                    results.append(str(value))

            elif extract_mode == "all":
                # Get all attributes as dict
                attribs = selector.attrib
                text = str(selector.text)
                results.append({
                    "text": text,
                    "attributes": dict(attribs) if attribs else {},
                })
        except Exception as e:
            logger.debug("extract_error selector=%d error=%s", i, e)
            continue

    return results


@handle_tool_errors("research_scrape")
async def research_scrape(
    url: str,
    selector: str | None = None,
    fetcher: Literal["auto", "basic", "stealthy", "dynamic", "async"] = "stealthy",
    extract: Literal["text", "html", "attribute", "all"] = "text",
    attribute: str | None = None,
    regex: str | None = None,
    wait_for: str | None = None,
    timeout: int = 30,
    headless: bool = True,
    max_results: int = 100,
) -> dict[str, Any]:
    """One-call fetch + extract with fetcher selection.

    Fetches a URL and optionally extracts data via CSS selector.

    Args:
        url: Target URL to fetch
        selector: CSS selector to extract elements (optional)
        fetcher: Which fetcher to use:
            - "auto": try basic, escalate on failure
            - "basic": Fetcher (fast, no stealth)
            - "stealthy": StealthyFetcher (stealth headers)
            - "dynamic": DynamicFetcher (Playwright, JS rendering)
            - "async": AsyncFetcher (async basic, no JS)
        extract: What to extract ("text", "html", "attribute", "all")
        attribute: Attribute name when extract="attribute"
        regex: Optional regex filter on text
        wait_for: CSS selector to wait for (dynamic mode only)
        timeout: Request timeout in seconds (1-120)
        headless: Headless browser mode (dynamic only)
        max_results: Max results to return (1-1000)

    Returns:
        Dict with:
        - url: Input URL
        - fetcher_used: Which fetcher was used
        - status: HTTP status code
        - count: Number of results extracted
        - results: List of extracted values
        - error: Error message if any
    """
    # Validate inputs
    try:
        validate_url(url)
    except ValueError as e:
        return {"url": url, "error": str(e), "fetcher_used": "none", "status": 0, "count": 0, "results": []}

    if timeout < 1 or timeout > 120:
        return {"url": url, "error": "timeout must be 1-120", "fetcher_used": "none", "status": 0, "count": 0, "results": []}

    if max_results < 1 or max_results > 1000:
        max_results = min(max(max_results, 1), 1000)

    fetcher_to_use = fetcher.lower() if fetcher else "stealthy"
    response = None
    used_fetcher = "none"

    try:
        # Dispatch to appropriate fetcher
        if fetcher_to_use in ("basic", "auto"):
            try:
                basic_fetcher = _get_fetcher_basic()
                if basic_fetcher:
                    response = await asyncio.to_thread(basic_fetcher.get, url)
                    used_fetcher = "basic"
                    logger.info("scrapling_fetch_basic url=%s", url)
            except Exception as e:
                logger.debug("basic_fetcher_error: %s", e)
                if fetcher_to_use == "basic":
                    return {"url": url, "error": str(e), "fetcher_used": "basic", "status": 0, "count": 0, "results": []}
                # Fall through to stealthy for "auto"

        if not response and fetcher_to_use in ("stealthy", "auto"):
            try:
                stealthy_fetcher = _get_fetcher_stealthy()
                if stealthy_fetcher:
                    response = await asyncio.to_thread(stealthy_fetcher.fetch, url)
                    used_fetcher = "stealthy"
                    logger.info("scrapling_fetch_stealthy url=%s", url)
            except Exception as e:
                logger.debug("stealthy_fetcher_error: %s", e)
                if fetcher_to_use == "stealthy":
                    return {"url": url, "error": str(e), "fetcher_used": "stealthy", "status": 0, "count": 0, "results": []}

        if not response and fetcher_to_use == "dynamic":
            try:
                dynamic_fetcher = _get_fetcher_dynamic()
                if dynamic_fetcher:
                    response = await asyncio.to_thread(dynamic_fetcher.fetch, url)
                    used_fetcher = "dynamic"
                    logger.info("scrapling_fetch_dynamic url=%s", url)
            except Exception as e:
                logger.debug("dynamic_fetcher_error: %s", e)
                return {"url": url, "error": str(e), "fetcher_used": "dynamic", "status": 0, "count": 0, "results": []}

        if not response:
            return {"url": url, "error": "no fetcher available", "fetcher_used": "none", "status": 0, "count": 0, "results": []}

        # Response is a Selector, get status from its properties
        status = getattr(response, "status", 200)

        # Extract if selector provided
        results = []
        if selector:
            try:
                # Use CSS selector to find elements
                elements = response.css(selector)
                if elements:
                    results = _extract_from_selectors(
                        list(elements),
                        extract_mode=extract,
                        attribute_name=attribute,
                        regex_pattern=regex,
                        max_results=max_results,
                    )
            except Exception as e:
                logger.debug("extraction_error selector=%s error=%s", selector, e)
                # Don't fail the whole request, just return empty results

        return {
            "url": url,
            "fetcher_used": used_fetcher,
            "status": status,
            "count": len(results),
            "results": results,
            "error": None,
        }

    except Exception as exc:
        logger.error("research_scrape_error url=%s error=%s", url, exc)
        return {
            "url": url,
            "error": str(exc),
            "fetcher_used": used_fetcher,
            "status": 0,
            "count": 0,
            "results": [],
        }


@handle_tool_errors("research_scrape_similar")
async def research_scrape_similar(
    url: str,
    example_selector: str,
    fetcher: Literal["auto", "basic", "stealthy", "dynamic", "async"] = "stealthy",
    fields: dict[str, str] | None = None,
    similarity_threshold: float = 0.2,
    match_text: bool = False,
    timeout: int = 30,
    max_results: int = 100,
) -> dict[str, Any]:
    """Find structurally similar elements (product cards, table rows, etc.).

    Fetches a page and uses Scrapling's find_similar() to extract all
    structurally-similar elements to a provided example selector.

    Args:
        url: Target URL to fetch
        example_selector: CSS selector matching ONE example element
            (e.g., "div.product-card" where all product cards have this class)
        fetcher: Which fetcher to use (auto/basic/stealthy/dynamic)
        fields: Optional dict mapping field name → CSS sub-selector
            E.g., {"name": "h2.title", "price": "span.price"}
        similarity_threshold: How strict to match (0.0-1.0, default 0.2)
        match_text: Also match on text content (slower)
        timeout: Request timeout in seconds
        max_results: Max results to return

    Returns:
        Dict with:
        - url: Input URL
        - fetcher_used: Which fetcher was used
        - count: Number of similar items found
        - items: List of extracted item dicts (one per similar element)
        - error: Error message if any
    """
    # Validate inputs
    try:
        validate_url(url)
    except ValueError as e:
        return {"url": url, "error": str(e), "fetcher_used": "none", "count": 0, "items": []}

    if not example_selector or not example_selector.strip():
        return {"url": url, "error": "example_selector required", "fetcher_used": "none", "count": 0, "items": []}

    if similarity_threshold < 0.0 or similarity_threshold > 1.0:
        similarity_threshold = 0.2

    if max_results < 1 or max_results > 1000:
        max_results = min(max(max_results, 1), 1000)

    fetcher_to_use = fetcher.lower() if fetcher else "stealthy"
    response = None
    used_fetcher = "none"

    try:
        # Fetch the page (reuse logic from research_scrape)
        if fetcher_to_use in ("basic", "auto"):
            try:
                basic_fetcher = _get_fetcher_basic()
                if basic_fetcher:
                    response = await asyncio.to_thread(basic_fetcher.get, url)
                    used_fetcher = "basic"
            except Exception as e:
                logger.debug("basic_fetcher_error: %s", e)

        if not response and fetcher_to_use in ("stealthy", "auto"):
            try:
                stealthy_fetcher = _get_fetcher_stealthy()
                if stealthy_fetcher:
                    response = await asyncio.to_thread(stealthy_fetcher.fetch, url)
                    used_fetcher = "stealthy"
            except Exception as e:
                logger.debug("stealthy_fetcher_error: %s", e)

        if not response and fetcher_to_use == "dynamic":
            try:
                dynamic_fetcher = _get_fetcher_dynamic()
                if dynamic_fetcher:
                    response = await asyncio.to_thread(dynamic_fetcher.fetch, url)
                    used_fetcher = "dynamic"
            except Exception as e:
                logger.debug("dynamic_fetcher_error: %s", e)

        if not response:
            return {"url": url, "error": "no fetcher available", "fetcher_used": "none", "count": 0, "items": []}

        # Find example element
        example_elements = response.css(example_selector)
        if not example_elements:
            return {
                "url": url,
                "fetcher_used": used_fetcher,
                "count": 0,
                "items": [],
                "error": f"no elements found with selector '{example_selector}'",
            }

        # Get first example element
        example_elem = example_elements[0]

        # Find similar elements
        try:
            similar_elements = example_elem.find_similar(
                similarity_threshold=similarity_threshold,
                match_text=match_text,
            )
        except Exception as e:
            logger.debug("find_similar_error: %s", e)
            similar_elements = []

        if not similar_elements:
            return {
                "url": url,
                "fetcher_used": used_fetcher,
                "count": 0,
                "items": [],
                "error": "no similar elements found",
            }

        # Extract fields from each similar element
        items = []
        for i, elem in enumerate(list(similar_elements)[:max_results]):
            try:
                item = {}
                if fields:
                    # Extract specified fields
                    for field_name, field_selector in fields.items():
                        try:
                            field_elems = elem.css(field_selector)
                            if field_elems:
                                item[field_name] = str(field_elems[0].text)
                            else:
                                item[field_name] = ""
                        except Exception as fe:
                            logger.debug("field_extraction_error field=%s error=%s", field_name, fe)
                            item[field_name] = ""
                else:
                    # No fields specified, just extract text
                    item["text"] = str(elem.text)

                items.append(item)
            except Exception as e:
                logger.debug("item_extraction_error index=%d error=%s", i, e)
                continue

        return {
            "url": url,
            "fetcher_used": used_fetcher,
            "count": len(items),
            "items": items,
            "error": None,
        }

    except Exception as exc:
        logger.error("research_scrape_similar_error url=%s error=%s", url, exc)
        return {
            "url": url,
            "error": str(exc),
            "fetcher_used": used_fetcher,
            "count": 0,
            "items": [],
        }


@handle_tool_errors("research_scrape_adaptive")
async def research_scrape_adaptive(
    url: str,
    selector: str,
    fetcher: Literal["auto", "basic", "stealthy", "dynamic", "async"] = "stealthy",
    auto_match: bool = True,
    storage_id: str | None = None,
    timeout: int = 30,
    extract: Literal["text", "html", "attribute", "all"] = "text",
) -> dict[str, Any]:
    """Adaptive scraping that survives site HTML changes.

    Uses Scrapling's adaptive mode to relocate selectors if the page
    structure changes between scraping runs.

    Args:
        url: Target URL to fetch
        selector: CSS selector to find element
        fetcher: Which fetcher to use
        auto_match: Enable automatic selector relocation (default True)
        storage_id: Persistent storage key for adaptive data
            (enables element relocation across runs)
        timeout: Request timeout in seconds
        extract: What to extract ("text", "html", "attribute", "all")

    Returns:
        Dict with:
        - url: Input URL
        - selector: CSS selector used
        - matched: Whether element was found
        - relocated: Whether selector had to be relocated
        - result: Extracted result (text, HTML, or attribute)
        - error: Error message if any
    """
    # Validate inputs
    try:
        validate_url(url)
    except ValueError as e:
        return {"url": url, "selector": selector, "matched": False, "relocated": False, "result": None, "error": str(e)}

    if not selector or not selector.strip():
        return {"url": url, "selector": selector, "matched": False, "relocated": False, "result": None, "error": "selector required"}

    fetcher_to_use = fetcher.lower() if fetcher else "stealthy"
    response = None
    used_fetcher = "none"
    relocated = False

    try:
        # Fetch the page with adaptive mode enabled
        if fetcher_to_use in ("basic", "auto"):
            try:
                basic_fetcher = _get_fetcher_basic()
                if basic_fetcher:
                    # Note: basic Fetcher doesn't have adaptive mode directly,
                    # but Response (Selector) does
                    response = await asyncio.to_thread(basic_fetcher.get, url)
                    used_fetcher = "basic"
            except Exception as e:
                logger.debug("basic_fetcher_error: %s", e)

        if not response and fetcher_to_use in ("stealthy", "auto"):
            try:
                stealthy_fetcher = _get_fetcher_stealthy()
                if stealthy_fetcher:
                    response = await asyncio.to_thread(stealthy_fetcher.fetch, url)
                    used_fetcher = "stealthy"
            except Exception as e:
                logger.debug("stealthy_fetcher_error: %s", e)

        if not response and fetcher_to_use == "dynamic":
            try:
                dynamic_fetcher = _get_fetcher_dynamic()
                if dynamic_fetcher:
                    response = await asyncio.to_thread(dynamic_fetcher.fetch, url)
                    used_fetcher = "dynamic"
            except Exception as e:
                logger.debug("dynamic_fetcher_error: %s", e)

        if not response:
            return {
                "url": url,
                "selector": selector,
                "matched": False,
                "relocated": False,
                "result": None,
                "error": "no fetcher available",
            }

        # Try to find element with adaptive mode
        try:
            elements = response.css(selector, adaptive=auto_match, auto_save=bool(storage_id))
            if not elements:
                return {
                    "url": url,
                    "selector": selector,
                    "matched": False,
                    "relocated": relocated,
                    "result": None,
                    "error": None,
                }

            # Get first matching element
            elem = elements[0]

            # Extract based on mode
            result = None
            if extract == "text":
                result = str(elem.text)
            elif extract == "html":
                result = str(elem.body) if hasattr(elem, "body") else str(elem)
            elif extract == "attribute":
                result = dict(elem.attrib) if hasattr(elem, "attrib") else {}
            elif extract == "all":
                result = {
                    "text": str(elem.text),
                    "attributes": dict(elem.attrib) if hasattr(elem, "attrib") else {},
                }

            return {
                "url": url,
                "selector": selector,
                "matched": True,
                "relocated": relocated,
                "result": result,
                "error": None,
            }

        except Exception as e:
            logger.debug("adaptive_selection_error selector=%s error=%s", selector, e)
            return {
                "url": url,
                "selector": selector,
                "matched": False,
                "relocated": False,
                "result": None,
                "error": str(e),
            }

    except Exception as exc:
        logger.error("research_scrape_adaptive_error url=%s error=%s", url, exc)
        return {
            "url": url,
            "selector": selector,
            "matched": False,
            "relocated": False,
            "result": None,
            "error": str(exc),
        }
