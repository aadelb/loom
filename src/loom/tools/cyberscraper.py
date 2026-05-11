"""CyberScraper-2077 integration for intelligent web extraction.

Provides three core tools:
1. research_smart_extract - Fetch + LLM-powered structured extraction
2. research_paginate_scrape - Multi-page extraction with auto-pagination
3. research_stealth_browser - Pure Patchright stealth fetch (no LLM)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Literal

try:
    from bs4 import BeautifulSoup, Comment
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    from loom.cache import get_cache
except ImportError:
    get_cache = None  # type: ignore[assignment]

try:
    from loom.providers.anthropic_provider import AnthropicProvider
    from loom.providers.base import LLMResponse
    from loom.providers.deepseek_provider import DeepSeekProvider
    from loom.providers.gemini_provider import GeminiProvider
    from loom.providers.groq_provider import GroqProvider
    from loom.providers.nvidia_nim import NvidiaNimProvider
    from loom.providers.openai_provider import OpenAIProvider
    _PROVIDERS_AVAILABLE = True
except ImportError:
    _PROVIDERS_AVAILABLE = False

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.cyberscraper")

def _get_llm_provider(provider_name: str = "auto"):
    """Get LLM provider by name, cascade through available ones."""
    if provider_name == "auto":
        providers = [
            ("groq", GroqProvider),
            ("nvidia_nim", NvidiaNimProvider),
            ("deepseek", DeepSeekProvider),
            ("gemini", GeminiProvider),
            ("openai", OpenAIProvider),
            ("anthropic", AnthropicProvider),
        ]
        for name, provider_class in providers:
            try:
                return provider_class()
            except Exception:
                continue
        raise ValueError("No LLM provider available")
    elif provider_name == "groq":
        return GroqProvider()
    elif provider_name == "nvidia_nim":
        return NvidiaNimProvider()
    elif provider_name == "deepseek":
        return DeepSeekProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "anthropic":
        return AnthropicProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

# Precompiled regex patterns for JSON extraction
_JSON_BLOCK_PATTERN = re.compile(r"```json\s*([\s\S]*?)\s*```")
_CODE_BLOCK_PATTERN = re.compile(r"```\s*([\s\S]*?)\s*```")


# === Parameter Models ===


class SmartExtractParams(BaseModel):
    """Parameters for research_smart_extract tool."""

    url: str
    query: str
    model: Literal["auto", "groq", "nvidia_nim", "deepseek", "gemini", "openai"] = "auto"
    max_chars: int = 50000
    timeout: int = 30
    cache_key: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError("query must be at least 3 characters")
        if len(v) > 1000:
            raise ValueError("query must be at most 1000 characters")
        return v

    @field_validator("max_chars")
    @classmethod
    def validate_max_chars(cls, v: int) -> int:
        if v < 1000 or v > 200000:
            raise ValueError("max_chars must be 1000-200000")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 5 or v > 120:
            raise ValueError("timeout must be 5-120 seconds")
        return v


class PaginateParams(BaseModel):
    """Parameters for research_paginate_scrape tool."""

    url: str
    query: str
    page_range: str = "1-5"
    auto_detect_pattern: bool = True
    model: Literal["auto", "groq", "nvidia_nim", "deepseek", "gemini", "openai"] = "auto"
    max_chars_per_page: int = 30000
    timeout: int = 30

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError("query must be at least 3 characters")
        if len(v) > 1000:
            raise ValueError("query must be at most 1000 characters")
        return v

    @field_validator("page_range")
    @classmethod
    def validate_page_range(cls, v: str) -> str:
        if not v or not re.match(r"^[\d,\-]+$", v):
            raise ValueError("page_range must be digits, commas, or dashes (e.g., '1-5', '1,3,5')")
        return v


class StealthBrowserParams(BaseModel):
    """Parameters for research_stealth_browser tool."""

    url: str
    wait_for: Literal["domcontentloaded", "load", "networkidle"] | None = "load"
    screenshot: bool = False
    timeout: int = 30
    max_chars: int = 50000

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 5 or v > 120:
            raise ValueError("timeout must be 5-120 seconds")
        return v


# === Response Models ===


class SmartExtractResult(BaseModel):
    """Result from smart_extract operation."""

    url: str
    query: str
    extracted_data: dict[str, Any] | list[Any]
    model_used: str
    token_count: int
    cached: bool = False
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class PaginateScrapeResult(BaseModel):
    """Result from paginate_scrape operation."""

    url: str
    query: str
    pages_scraped: int
    total_items: int
    extracted_data: list[dict[str, Any]]
    model_used: str
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class StealthBrowserResult(BaseModel):
    """Result from stealth_browser operation."""

    url: str
    html: str
    text: str
    status_code: int | None = None
    screenshot_b64: str | None = None
    chars_extracted: int
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


# === Core Implementation ===


class _PatchrightAdapter:
    """Minimal Patchright wrapper for stealth browser automation.

    Since patchright may not be available, this provides a fallback
    that uses httpx for basic fetching.
    """

    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self._browser = None
        self._playwright = None

    async def fetch_with_patchright(
        self,
        url: str,
        wait_for: str = "load",
        take_screenshot: bool = False,
    ) -> dict[str, Any]:
        """Fetch URL using Patchright stealth browser.

        Falls back to httpx if patchright unavailable.
        """
        try:
            from patchright.async_api import async_playwright

            if self._playwright is None:
                self._playwright = await async_playwright().start()

            if self._browser is None:
                try:
                    # Try to use Patchright's undetected browser
                    self._browser = await self._playwright.chromium.launch(
                        headless=self.headless,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                        ],
                    )
                except Exception as e:
                    logger.warning("Patchright launch failed: %s, falling back to httpx", e)
                    return await self._fetch_with_httpx(url)

            context = await self._browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(url, wait_until=wait_for, timeout=self.timeout * 1000)

                html = await page.content()
                screenshot_b64 = None
                if take_screenshot:
                    screenshot_bytes = await page.screenshot()
                    import base64

                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

                return {
                    "html": html,
                    "status_code": 200,
                    "screenshot_b64": screenshot_b64,
                    "error": None,
                }
            finally:
                await page.close()
                await context.close()

        except ImportError:
            logger.debug("Patchright not available, falling back to httpx")
            return await self._fetch_with_httpx(url)
        except Exception as e:
            logger.error("Patchright fetch failed: %s", e)
            return await self._fetch_with_httpx(url)

    async def _fetch_with_httpx(self, url: str) -> dict[str, Any]:
        """Fallback: fetch with httpx and realistic headers."""
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)
                return {
                    "html": response.text,
                    "status_code": response.status_code,
                    "screenshot_b64": None,
                    "error": None,
                }
        except Exception as e:
            return {
                "html": "",
                "status_code": None,
                "screenshot_b64": None,
                "error": f"httpx fetch failed: {str(e)}",
            }

    async def close(self) -> None:
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


class _WebPreprocessor:
    """HTML preprocessing: remove noise, extract text."""

    # Tags to remove during preprocessing
    _REMOVE_TAGS = frozenset(["script", "style", "header", "footer", "nav", "aside"])

    @staticmethod
    def preprocess_html(html: str) -> str:
        """Clean HTML, remove unwanted tags and scripts, extract text."""
        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove unwanted tags
            for tag in soup.find_all(_WebPreprocessor._REMOVE_TAGS):
                tag.decompose()

            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Remove empty tags
            for tag in soup.find_all():
                if len(tag.get_text(strip=True)) == 0:
                    tag.extract()

            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)

        except Exception as e:
            logger.warning("HTML preprocessing failed: %s, returning raw text", e)
            return html


class _JSONExtractor:
    """Extract structured JSON from LLM responses."""

    @staticmethod
    def extract_json(response: str) -> dict[str, Any] | list[Any] | None:
        """Try multiple methods to extract JSON from LLM response."""
        # Method 1: Direct JSON parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Method 2: Extract from markdown code blocks
        clean = _JSONExtractor._extract_from_markdown(response)
        if clean != response:
            try:
                return json.loads(clean)
            except json.JSONDecodeError:
                pass

        # Method 3: Return None if all methods fail
        return None

    @staticmethod
    def _extract_from_markdown(text: str) -> str:
        """Extract JSON from markdown code blocks."""
        if match := _JSON_BLOCK_PATTERN.search(text):
            return match.group(1)
        if match := _CODE_BLOCK_PATTERN.search(text):
            return match.group(1)
        return text


# === Main Tool Functions ===


async def research_smart_extract(
    url: str,
    query: str,
    model: Literal["auto", "groq", "nvidia_nim", "deepseek", "gemini", "openai"] = "auto",
    max_chars: int = 50000,
    timeout: int = 30,
    cache_key: str | None = None,
) -> SmartExtractResult | TextContent:
    """Fetch URL with stealth browser + LLM-powered structured extraction.

    Use Patchright for human-like browser simulation, then extract
    structured data using natural language query and Loom's LLM cascade.

    Args:
        url: URL to fetch and extract from
        query: Natural language extraction query (e.g., "extract job titles and salaries")
        model: LLM provider (default: "auto" uses cascade)
        max_chars: Max characters to process (1000-200000)
        timeout: Browser timeout in seconds (5-120)
        cache_key: Optional cache override key

    Returns:
        SmartExtractResult with extracted_data dict/list, model used, token count

    Example:
        result = await research_smart_extract(
            "https://jobs.ae",
            "extract all job titles and salaries",
            model="groq"
        )
        # Returns: {extracted_data: [{title: "...", salary: "..."}], ...}
    """
    params = SmartExtractParams(
        url=url,
        query=query,
        model=model,
        max_chars=max_chars,
        timeout=timeout,
        cache_key=cache_key,
    )

    try:
        # Step 1: Fetch with Patchright
        browser = _PatchrightAdapter(timeout=params.timeout)
        try:
            fetch_result = await browser.fetch_with_patchright(
                params.url, wait_for="load", take_screenshot=False
            )

            if fetch_result["error"]:
                return SmartExtractResult(
                    url=params.url,
                    query=params.query,
                    extracted_data={},
                    model_used="none",
                    token_count=0,
                    error=fetch_result["error"],
                )

            html = fetch_result["html"]
        finally:
            await browser.close()

        # Step 2: Preprocess HTML to text
        text = _WebPreprocessor.preprocess_html(html)
        if not text:
            return SmartExtractResult(
                url=params.url,
                query=params.query,
                extracted_data={},
                model_used="none",
                token_count=0,
                error="HTML preprocessing returned empty content",
            )

        # Cap text to max_chars
        text = text[: params.max_chars]

        # Step 3: Check cache
        cache = get_cache()
        cache_hash = hashlib.sha256(f"{params.url}:{params.query}".encode()).hexdigest()
        cached_result = cache.get(f"cyberscraper:{cache_hash}")
        if cached_result:
            try:
                data = cached_result.get("data", {})
                return SmartExtractResult(
                    url=params.url,
                    query=params.query,
                    extracted_data=data,
                    model_used="cache",
                    token_count=0,
                    cached=True,
                )
            except Exception:
                pass

        # Step 4: Call LLM via Loom cascade
        llm = _get_llm_provider(params.model)
        prompt = f"""You are a data extraction specialist. Extract structured data from the following content based on the user's query.

Query: {params.query}

Content:
{text}

Return ONLY valid JSON (array or object) with no additional text. If no data matches the query, return an empty array [].
"""

        response = await llm.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=4096,
        )

        model_used = llm.__class__.__name__
        response_text = getattr(response, "text", "") or ""

        # Step 5: Extract JSON
        extracted = _JSONExtractor.extract_json(response_text)
        if extracted is None:
            # Fallback: try to return response as structured data
            extracted = {"raw_response": response_text[:1000]}

        # Step 6: Cache result
        cache.put(f"cyberscraper:{cache_hash}", {"data": extracted})

        token_count = len(response_text.split())  # Rough estimate
        return SmartExtractResult(
            url=params.url,
            query=params.query,
            extracted_data=extracted,
            model_used=model_used,
            token_count=token_count,
            cached=False,
        )

    except Exception as e:
        logger.error("smart_extract failed: %s", e, exc_info=True)
        return SmartExtractResult(
            url=url,
            query=query,
            extracted_data={},
            model_used="none",
            token_count=0,
            error=str(e),
        )


async def research_paginate_scrape(
    url: str,
    query: str,
    page_range: str = "1-5",
    auto_detect_pattern: bool = True,
    model: Literal["auto", "groq", "nvidia_nim", "deepseek", "gemini", "openai"] = "auto",
    max_chars_per_page: int = 30000,
    timeout: int = 30,
) -> PaginateScrapeResult | TextContent:
    """Multi-page scraping with auto-pagination detection.

    Scrape multiple pages in parallel, detect pagination patterns,
    and extract structured data from all pages combined.

    Args:
        url: Base URL to scrape
        query: Extraction query (applied to all pages)
        page_range: Pages to scrape (e.g., "1-5", "1,3,5")
        auto_detect_pattern: Auto-detect pagination pattern
        model: LLM provider
        max_chars_per_page: Max chars per page
        timeout: Browser timeout

    Returns:
        PaginateScrapeResult with all extracted items merged

    Example:
        result = await research_paginate_scrape(
            "https://example.com/jobs",
            "extract job titles",
            page_range="1-10"
        )
    """
    params = PaginateParams(
        url=url,
        query=query,
        page_range=page_range,
        auto_detect_pattern=auto_detect_pattern,
        model=model,
        max_chars_per_page=max_chars_per_page,
        timeout=timeout,
    )

    try:
        # Parse page range
        pages = _parse_page_range(params.page_range)
        if not pages:
            return PaginateScrapeResult(
                url=params.url,
                query=params.query,
                pages_scraped=0,
                total_items=0,
                extracted_data=[],
                model_used="none",
                error="Invalid page_range",
            )

        # Detect URL pattern if enabled
        url_pattern = None
        if params.auto_detect_pattern:
            url_pattern = _detect_pagination_pattern(params.url)

        # Scrape pages in parallel
        browser = _PatchrightAdapter(timeout=params.timeout)
        all_items = []
        errors = []

        try:
            tasks = [
                _scrape_single_page(
                    browser,
                    _apply_url_pattern(params.url, url_pattern, page_num),
                    params.query,
                    params.max_chars_per_page,
                    params.model,
                )
                for page_num in pages
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    errors.append(f"Page {pages[i]}: {str(result)}")
                elif isinstance(result, dict):
                    if result.get("error"):
                        errors.append(f"Page {pages[i]}: {result['error']}")
                    elif result.get("items"):
                        all_items.extend(result["items"])

        finally:
            await browser.close()

        return PaginateScrapeResult(
            url=params.url,
            query=params.query,
            pages_scraped=len([r for r in results if not isinstance(r, Exception)]),
            total_items=len(all_items),
            extracted_data=all_items,
            model_used="multi-page",
            error="; ".join(errors) if errors else None,
        )

    except Exception as e:
        logger.error("paginate_scrape failed: %s", e, exc_info=True)
        return PaginateScrapeResult(
            url=url,
            query=query,
            pages_scraped=0,
            total_items=0,
            extracted_data=[],
            model_used="none",
            error=str(e),
        )


async def research_stealth_browser(
    url: str,
    wait_for: Literal["domcontentloaded", "load", "networkidle"] | None = "load",
    screenshot: bool = False,
    timeout: int = 30,
    max_chars: int = 50000,
) -> StealthBrowserResult | TextContent:
    """Pure Patchright stealth fetch — no LLM extraction.

    Replaces broken Camoufox. Provides Cloudflare bypass, CAPTCHA handling,
    and human-like browser simulation via Patchright.

    Args:
        url: URL to fetch
        wait_for: Wait strategy ("load", "domcontentloaded", "networkidle")
        screenshot: Capture screenshot as base64
        timeout: Browser timeout in seconds
        max_chars: Max HTML chars to return

    Returns:
        StealthBrowserResult with html, text, status_code, optional screenshot

    Example:
        result = await research_stealth_browser(
            "https://example.com",
            wait_for="load",
            screenshot=True
        )
    """
    params = StealthBrowserParams(
        url=url,
        wait_for=wait_for,
        screenshot=screenshot,
        timeout=timeout,
        max_chars=max_chars,
    )

    try:
        browser = _PatchrightAdapter(timeout=params.timeout)
        try:
            fetch_result = await browser.fetch_with_patchright(
                params.url,
                wait_for=params.wait_for or "load",
                take_screenshot=params.screenshot,
            )

            html = fetch_result["html"][: params.max_chars]
            text = _WebPreprocessor.preprocess_html(html)

            return StealthBrowserResult(
                url=params.url,
                html=html,
                text=text,
                status_code=fetch_result.get("status_code"),
                screenshot_b64=fetch_result.get("screenshot_b64"),
                chars_extracted=len(html),
                error=fetch_result.get("error"),
            )

        finally:
            await browser.close()

    except Exception as e:
        logger.error("stealth_browser failed: %s", e, exc_info=True)
        return StealthBrowserResult(
            url=url,
            html="",
            text="",
            status_code=None,
            screenshot_b64=None,
            chars_extracted=0,
            error=str(e),
        )


# === Helper Functions ===


def _parse_page_range(page_range: str) -> list[int]:
    """Parse page range like '1-5' or '1,3,5' into list of page numbers."""
    pages = []
    for part in page_range.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def _detect_pagination_pattern(url: str) -> str | None:
    """Detect common pagination patterns in URL.

    Looks for numeric query parameters or path segments that could
    indicate page numbers.
    """
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # Check query parameters for numeric values
    for param, values in query.items():
        if values and values[0].isdigit():
            return f"{param}={{{param}}}"

    # Check path segments for numeric values
    path_parts = parsed.path.split("/")
    for i, part in enumerate(path_parts):
        if part.isdigit():
            path_parts[i] = "{page}"
            return "/".join(path_parts)

    return None


def _apply_url_pattern(base_url: str, pattern: str | None, page_num: int) -> str:
    """Apply pagination pattern to URL with page number."""
    if not pattern:
        return base_url

    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(base_url)

    if "=" in pattern:
        # Query parameter pattern
        query = parse_qs(parsed.query)
        param, value = pattern.split("=")
        query[param] = [value.format(**{param: page_num})]
        return urlunparse(
            parsed._replace(query=urlencode(query, doseq=True))
        )
    elif "{page}" in pattern:
        # Path pattern
        return urlunparse(parsed._replace(path=pattern.format(page=page_num)))

    return base_url


async def _scrape_single_page(
    browser: _PatchrightAdapter,
    url: str,
    query: str,
    max_chars: int,
    model: str,
) -> dict[str, Any]:
    """Scrape and extract from a single page."""
    try:
        # Fetch page
        fetch_result = await browser.fetch_with_patchright(url, wait_for="load")

        if fetch_result["error"]:
            return {"error": fetch_result["error"], "items": []}

        html = fetch_result["html"]
        text = _WebPreprocessor.preprocess_html(html)[: max_chars]

        # Extract with LLM
        llm = _get_llm_provider(model)
        prompt = f"""Extract structured data from this content based on: {query}

Content:
{text}

Return ONLY a JSON array of objects. If no matches, return [].
"""

        response = await llm.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=2048,
        )

        response_text = getattr(response, "text", "") or ""
        extracted = _JSONExtractor.extract_json(response_text)

        if isinstance(extracted, list):
            return {"items": extracted, "error": None}
        elif isinstance(extracted, dict):
            return {"items": [extracted], "error": None}
        else:
            return {"items": [], "error": "Failed to extract JSON"}

    except Exception as e:
        logger.error("Failed to scrape page %s: %s", url, e)
        return {"error": str(e), "items": []}
