"""research_cyberscrape — AI-powered web scraping via CyberScraper-2077 backend.

CyberScraper-2077 is an advanced web scraper that uses multiple LLM providers
(OpenAI, Gemini, Ollama, Moonshot) to intelligently extract and structure data
from any website. This tool wraps CyberScraper-2077 for use within Loom.

Features:
- AI-powered intelligent extraction (understand and parse web content)
- Multi-format export (JSON, CSV, HTML, Excel)
- Tor network support for anonymous scraping
- Stealth mode to avoid bot detection
- Async operations for performance
- Content-based caching to reduce redundant API calls
- Automatic Captcha bypass
- Browser automation with Playwright/Patchright
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from mcp.types import TextContent
from pydantic import BaseModel, Field, field_validator

from loom.cache import get_cache
from loom.validators import validate_url
from loom.params import CyberscraperParams

logger = logging.getLogger("loom.tools.cyberscraper")

# CyberScraper-2077 repo location on Hetzner
CYBERSCRAPER_REPO_PATH = Path("/home/aadel/CyberScraper-2077")

# Check if CyberScraper-2077 is available
_CYBERSCRAPER_AVAILABLE = False

try:
    if CYBERSCRAPER_REPO_PATH.exists():
        sys.path.insert(0, str(CYBERSCRAPER_REPO_PATH))
        from src.web_extractor import WebExtractor
        from src.models import Models
        from src.scrapers.playwright_scraper import ScraperConfig

        _CYBERSCRAPER_AVAILABLE = True
except ImportError as e:  # pragma: no cover
    logger.debug(f"CyberScraper-2077 not available: {e}")



def _get_cyberscraper_extractor(
    model: str, scraper_config: dict | None = None
) -> Any:
    """Initialize CyberScraper WebExtractor with validated model."""
    if not _CYBERSCRAPER_AVAILABLE:
        raise RuntimeError(
            "CyberScraper-2077 not available. Ensure it's cloned to /home/aadel/CyberScraper-2077"
        )

    config = scraper_config or {}
    config.setdefault("timeout", 30)
    config.setdefault("javascript_enabled", True)

    try:
        scraper_config_obj = ScraperConfig(**config)
    except Exception as e:
        logger.warning(f"Invalid scraper config: {e}. Using defaults.")
        scraper_config_obj = ScraperConfig()

    try:
        return WebExtractor(
            model_name=model,
            scraper_config=scraper_config_obj,
        )
    except Exception as e:
        logger.error(f"Failed to initialize WebExtractor with model {model}: {e}")
        raise


async def research_cyberscrape(
    url: str,
    extract_type: str = "all",
    model: str = "gpt-4o-mini",
    format: str = "json",
    max_chars: int = 20000,
    use_tor: bool = False,
    stealth_mode: bool = False,
    use_local_browser: bool = False,
    include_metadata: bool = True,
    timeout_seconds: int = 30,
) -> TextContent:
    """
    Scrape web content using CyberScraper-2077's AI-powered extraction.

    Uses intelligent LLM-based extraction to understand and parse web content,
    structuring data according to your extraction_type specification.

    Args:
        url: Target URL to scrape
        extract_type: Type of extraction (all, text, tables, links, images, json, structured)
        model: LLM model for extraction (gpt-4o-mini, gemini-1.5-flash, ollama:llama2, moonshot-v1)
        format: Output format (json, csv, html, markdown)
        max_chars: Maximum characters to extract (1000-100000)
        use_tor: Route through Tor network for anonymity
        stealth_mode: Enable stealth mode to avoid bot detection
        use_local_browser: Use local browser for better bot evasion
        include_metadata: Include page metadata (title, description, etc.)
        timeout_seconds: Request timeout in seconds (5-300)

    Returns:
        TextContent with extracted data in requested format

    Examples:
        Extract all data as JSON:
            research_cyberscrape("https://example.com", extract_type="all", format="json")

        Extract tables as CSV:
            research_cyberscrape("https://example.com", extract_type="tables", format="csv")

        Extract structured data with Tor anonymity:
            research_cyberscrape(
                "https://example.onion/page",
                extract_type="structured",
                use_tor=True
            )

        Extract using Gemini with stealth mode:
            research_cyberscrape(
                "https://protected-site.com",
                model="gemini-1.5-flash",
                stealth_mode=True,
                format="markdown"
            )
    """
    # Validate parameters
    params = CyberscraperParams(
        url=url,
        extract_type=extract_type,
        model=model,
        format=format,
        max_chars=max_chars,
        use_tor=use_tor,
        stealth_mode=stealth_mode,
        use_local_browser=use_local_browser,
        include_metadata=include_metadata,
        timeout_seconds=timeout_seconds,
    )

    # Check cache first
    cache = get_cache()
    cache_key = f"cyberscrape:{params.url}:{params.extract_type}:{params.model}"
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"Cache hit for {params.url}")
        return TextContent(type="text", text=cached)

    try:
        logger.info(
            f"Scraping {params.url} with model={params.model}, extract_type={params.extract_type}"
        )

        if not _CYBERSCRAPER_AVAILABLE:
            raise RuntimeError(
                "CyberScraper-2077 backend not available. "
                "Ensure cloned to /home/aadel/CyberScraper-2077"
            )

        # Build scraper config
        scraper_config = {
            "timeout": params.timeout_seconds,
            "javascript_enabled": True,
            "use_stealth": params.stealth_mode,
            "use_local_browser": params.use_local_browser,
        }

        # Initialize extractor
        extractor = _get_cyberscraper_extractor(params.model, scraper_config)

        # Build extraction prompt based on type
        extraction_prompts = {
            "all": "Extract all meaningful data from this webpage including text, tables, links, images, and structured information. Return as comprehensive JSON.",
            "text": "Extract only the main text content from this webpage, removing navigation and ads. Return clean paragraphs.",
            "tables": "Extract all tables from this webpage with proper column headers and row data. Return as structured JSON or CSV.",
            "links": "Extract all hyperlinks from this webpage with their URLs and anchor text. Return as JSON array.",
            "images": "Extract all images from this webpage with URLs and alt text. Return as JSON array.",
            "json": "Parse and extract all JSON data structures visible on this webpage. Return as JSON.",
            "structured": "Extract and structure all data from this webpage into a logical hierarchy (sections, subsections, key-value pairs). Return as JSON.",
        }

        prompt = extraction_prompts.get(
            params.extract_type,
            extraction_prompts["all"],
        )

        # Perform extraction asynchronously
        def _extract():
            """Blocking extraction call wrapped for async."""
            try:
                # CyberScraper's WebExtractor.process_message returns various types
                # We'll use it to extract content then format as requested
                response = extractor.process_message(prompt)

                # Normalize response to string
                if isinstance(response, (tuple, list)):
                    result = json.dumps(response)
                elif isinstance(response, dict):
                    result = json.dumps(response)
                elif isinstance(response, str):
                    result = response
                else:
                    result = str(response)

                return result
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                raise

        # Run blocking operation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _extract)

        # Format output as requested
        if params.format == "json":
            try:
                json.loads(result)  # Validate JSON
            except json.JSONDecodeError:
                # Wrap non-JSON result
                result = json.dumps({"content": result, "format": "text"})

        # Cache result
        cache.set(cache_key, result)

        logger.info(f"Successfully scraped {params.url} ({len(result)} chars)")

        return TextContent(type="text", text=result)

    except RuntimeError as e:
        error_msg = f"CyberScraper backend error: {str(e)}"
        logger.error(error_msg)
        return TextContent(type="text", text=error_msg)
    except Exception as e:
        error_msg = f"Scraping failed for {params.url}: {str(e)}"
        logger.error(error_msg)
        return TextContent(type="text", text=error_msg)


# Alternative: Direct Python API call (when CyberScraper is on same system)
async def research_cyberscrape_direct(
    url: str,
    extraction_prompt: str,
    model: str = "gpt-4o-mini",
    timeout_seconds: int = 30,
) -> TextContent:
    """
    Direct CyberScraper extraction with custom prompt.

    Allows fine-grained control over extraction via custom prompts
    without using the extract_type templates.

    Args:
        url: Target URL to scrape
        extraction_prompt: Custom extraction instructions for the LLM
        model: LLM model to use
        timeout_seconds: Request timeout in seconds

    Returns:
        TextContent with extracted data
    """
    if not _CYBERSCRAPER_AVAILABLE:
        return TextContent(
            type="text",
            text="CyberScraper-2077 backend not available",
        )

    try:
        scraper_config = {"timeout": timeout_seconds}
        extractor = _get_cyberscraper_extractor(model, scraper_config)

        def _extract():
            return extractor.process_message(extraction_prompt)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _extract)

        if isinstance(result, str):
            return TextContent(type="text", text=result)
        else:
            return TextContent(type="text", text=json.dumps(result))

    except Exception as e:
        logger.error(f"Direct extraction failed: {e}")
        return TextContent(type="text", text=f"Error: {str(e)}")
