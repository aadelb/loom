"""Unified scraper escalation engine with automatic backend chaining.

Provides a ScraperEngine class that chains available scraping backends
with automatic escalation on failure. Supports HTTP, Scrapling, Crawl4AI,
Patchright, nodriver, zendriver, Camoufox, and Botasaurus.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any, Literal, cast
from urllib.parse import urlparse

from loom.cache import get_cache
from loom.config import get_config
from loom.validators import validate_url

logger = logging.getLogger("loom.scraper_engine")


class EscalationLevel(IntEnum):
    """Escalation levels ordered by stealth/complexity."""

    HTTPX = 0
    SCRAPLING = 1
    CRAWL4AI = 2
    PATCHRIGHT = 3
    NODRIVER = 4
    ZENDRIVER = 5
    CAMOUFOX = 6
    BOTASAURUS = 7


# Reverse mapping for convenience
LEVEL_TO_BACKEND = {
    EscalationLevel.HTTPX: "httpx",
    EscalationLevel.SCRAPLING: "scrapling",
    EscalationLevel.CRAWL4AI: "crawl4ai",
    EscalationLevel.PATCHRIGHT: "patchright",
    EscalationLevel.NODRIVER: "nodriver",
    EscalationLevel.ZENDRIVER: "zendriver",
    EscalationLevel.CAMOUFOX: "camoufox",
    EscalationLevel.BOTASAURUS: "botasaurus",
}

BACKEND_TO_LEVEL = {v: k for k, v in LEVEL_TO_BACKEND.items()}


@dataclass
class FetchSuccess:
    """Successful fetch result."""

    url: str
    content: str
    content_type: str | None = None
    status_code: int | None = None
    backend_used: str = ""
    escalation_level: int = 0
    elapsed_ms: int = 0
    title: str | None = None
    html: str | None = None


@dataclass
class FetchFailure:
    """Failed fetch with escalation history."""

    url: str
    error: str
    backend_attempted: str = ""
    escalation_level: int = 0
    elapsed_ms: int = 0
    cloudflare_detected: bool = False
    timeout: bool = False
    network_error: bool = False


@dataclass
class EscalationResult:
    """Result from an escalation attempt."""

    success: bool
    content: str | None = None
    backend: str = ""
    level: int = 0
    error: str | None = None
    cloudflare_detected: bool = False
    elapsed_ms: int = 0


@dataclass
class ScraperEngineResult:
    """Complete result from ScraperEngine.fetch()."""

    url: str
    success: bool
    content: str = ""
    backend_used: str = ""
    escalation_level: int = 0
    escalation_history: list[str] = field(default_factory=list)
    content_type: str | None = None
    status_code: int | None = None
    title: str | None = None
    html: str | None = None
    elapsed_ms: int = 0
    error: str | None = None


class BackendAvailability:
    """Tracks which backends are available at runtime."""

    _instance: BackendAvailability | None = None
    _cache: dict[str, bool] = {}

    def __new__(cls) -> BackendAvailability:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def check(cls, backend: str) -> bool:
        """Check if a backend is available (cached after first check)."""
        if backend not in cls._cache:
            cls._cache[backend] = cls._check_import(backend)
        return cls._cache[backend]

    @staticmethod
    def _check_import(backend: str) -> bool:
        """Try to import the backend and return availability."""
        try:
            if backend == "httpx":
                import httpx  # noqa: F401
            elif backend == "scrapling":
                from scrapling.fetchers import Fetcher  # noqa: F401
            elif backend == "crawl4ai":
                from crawl4ai import AsyncWebCrawler  # noqa: F401
            elif backend == "patchright":
                import patchright  # noqa: F401
            elif backend == "nodriver":
                import nodriver  # noqa: F401
            elif backend == "zendriver":
                import zendriver  # noqa: F401
            elif backend == "camoufox":
                from camoufox import sync_playwright  # noqa: F401
            elif backend == "botasaurus":
                from botasaurus.browser import Browser  # noqa: F401
            else:
                # Unknown backend
                return False
            return True
        except ImportError:
            return False

    @classmethod
    def reset_cache(cls) -> None:
        """Reset availability cache (useful for testing)."""
        cls._cache.clear()


class DomainEscalationHistory:
    """Tracks escalation levels per domain for caching."""

    _instance: DomainEscalationHistory | None = None
    _history: dict[str, int] = {}

    def __new__(cls) -> DomainEscalationHistory:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_min_level(cls, domain: str) -> int:
        """Get minimum escalation level to try for domain (based on history)."""
        return cls._history.get(domain, 0)

    @classmethod
    def record_success(cls, domain: str, level: int) -> None:
        """Record successful escalation level for domain."""
        current = cls._history.get(domain, 999)
        # Only update if we found a lower level
        if level < current:
            cls._history[domain] = level
            logger.info("domain_escalation_recorded domain=%s level=%s", domain, level)

    @classmethod
    def reset(cls) -> None:
        """Reset history (useful for testing)."""
        cls._history.clear()


class ScraperEngine:
    """Unified scraping engine with automatic escalation across backends."""

    def __init__(
        self,
        cache_enabled: bool = True,
        max_retries: int = 3,
        timeout_secs: int | None = None,
    ) -> None:
        """Initialize ScraperEngine.

        Args:
            cache_enabled: Whether to use content-hash cache
            max_retries: Max escalation retries per URL
            timeout_secs: HTTP timeout in seconds (uses config default if None)
        """
        self.cache_enabled = cache_enabled
        self.max_retries = max_retries
        self.timeout_secs = timeout_secs or get_config().get("EXTERNAL_TIMEOUT_SECS", 30)
        self.cache = get_cache() if cache_enabled else None
        self.availability = BackendAvailability()
        self.domain_history = DomainEscalationHistory()

    async def fetch(
        self,
        url: str,
        mode: Literal["auto", "stealth", "max", "fast"] | str = "auto",
        max_escalation: int | None = None,
        extract_title: bool = False,
        force_backend: str | None = None,
    ) -> ScraperEngineResult:
        """Fetch URL with automatic escalation.

        Args:
            url: URL to fetch
            mode: "auto" (level 0), "stealth" (level 3), "max" (level 5),
                  "fast" (no escalation), or specific backend name
            max_escalation: Max escalation level (default: 7)
            extract_title: Extract title from content
            force_backend: Force a specific backend (skip escalation)

        Returns:
            ScraperEngineResult with content, backend used, escalation history
        """
        # Validate URL
        validate_url(url)

        # Determine starting level
        if max_escalation is None:
            max_escalation = 7
        start_level = self._get_start_level(mode, force_backend)

        domain = urlparse(url).netloc
        domain_min_level = self.domain_history.get_min_level(domain)
        start_level = max(start_level, domain_min_level)

        # Check cache before escalation
        if self.cache_enabled:
            cached = await self._check_cache(url)
            if cached:
                logger.info("cache_hit url=%s", url)
                return ScraperEngineResult(
                    url=url,
                    success=True,
                    content=cached.get("content", ""),
                    backend_used="cache",
                    escalation_level=-1,
                    escalation_history=["cache"],
                    content_type=cached.get("content_type"),
                    status_code=cached.get("status_code"),
                    elapsed_ms=0,
                )

        # Escalate through backends
        result = await self._escalate(url, start_level, max_escalation)

        if result.success:
            # Record success in domain history
            self.domain_history.record_success(domain, result.level)

            # Cache the result
            if self.cache_enabled:
                await self._cache_result(url, result)

            return ScraperEngineResult(
                url=url,
                success=True,
                content=result.content or "",
                backend_used=result.backend,
                escalation_level=result.level,
                escalation_history=[LEVEL_TO_BACKEND.get(i, str(i)) for i in range(result.level + 1)],
                elapsed_ms=result.elapsed_ms,
            )

        # All escalations failed
        return ScraperEngineResult(
            url=url,
            success=False,
            backend_used=result.backend,
            escalation_level=result.level,
            escalation_history=[LEVEL_TO_BACKEND.get(i, str(i)) for i in range(max_escalation + 1)],
            error=result.error,
            elapsed_ms=result.elapsed_ms,
        )

    async def smart_extract(
        self,
        url: str,
        query: str,
        model: Literal["auto", "groq", "openai", "gemini"] = "auto",
        mode: Literal["auto", "stealth", "max", "fast"] = "auto",
    ) -> dict[str, Any]:
        """Fetch + LLM-powered structured data extraction.

        Args:
            url: URL to fetch
            query: What to extract
            model: LLM model to use
            mode: Fetch mode for escalation

        Returns:
            Dict with extracted data and metadata
        """
        # Fetch content with escalation
        fetch_result = await self.fetch(url, mode=mode)

        if not fetch_result.success:
            return {
                "success": False,
                "error": fetch_result.error or "Failed to fetch URL",
                "url": url,
            }

        # Use simple text extraction since structured extraction requires schema
        # For now, return the content with a basic summary
        try:
            # Try to extract a summary using LLM tools if available
            from loom.tools.llm.llm import research_llm_summarize

            summary = await research_llm_summarize(
                text=fetch_result.content[:5000],
                max_length=500,
                model=model,
            )

            return {
                "success": True,
                "url": url,
                "backend_used": fetch_result.backend_used,
                "escalation_level": fetch_result.escalation_level,
                "query": query,
                "summary": summary,
                "content_preview": fetch_result.content[:1000],
                "fetch_elapsed_ms": fetch_result.elapsed_ms,
            }
        except (ImportError, Exception) as e:
            # Fallback: return content matching the query
            logger.debug("llm_extraction_fallback error=%s", str(e))
            return {
                "success": True,
                "url": url,
                "backend_used": fetch_result.backend_used,
                "escalation_level": fetch_result.escalation_level,
                "query": query,
                "content_preview": fetch_result.content[:2000],
                "fetch_elapsed_ms": fetch_result.elapsed_ms,
            }

    async def batch_fetch(
        self,
        urls: list[str],
        mode: Literal["auto", "stealth", "max", "fast"] = "auto",
        max_concurrent: int = 10,
        fail_fast: bool = False,
    ) -> dict[str, Any]:
        """Batch fetch multiple URLs with per-URL escalation.

        Args:
            urls: List of URLs to fetch
            mode: Fetch mode for escalation
            max_concurrent: Max concurrent fetches
            fail_fast: Stop on first failure

        Returns:
            Dict with results and summary stats
        """
        if not urls:
            return {"success": True, "results": [], "stats": {}}

        # Validate all URLs
        validated_urls = []
        for url in urls:
            try:
                validate_url(url)
                validated_urls.append(url)
            except Exception as e:
                logger.warning("invalid_url url=%s error=%s", url, str(e))

        # Fetch with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [self._fetch_with_semaphore(url, mode, semaphore) for url in validated_urls]

        results = []
        failed = 0
        succeeded = 0
        total_elapsed = 0

        try:
            for result in await asyncio.gather(*tasks, return_exceptions=False):
                results.append(result)
                if result["success"]:
                    succeeded += 1
                else:
                    failed += 1
                    if fail_fast:
                        break
                total_elapsed += result.get("elapsed_ms", 0)
        except Exception as e:
            logger.error("batch_fetch error=%s", str(e))
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "stats": {"succeeded": succeeded, "failed": failed, "total": len(validated_urls)},
            }

        return {
            "success": failed == 0,
            "results": results,
            "stats": {
                "succeeded": succeeded,
                "failed": failed,
                "total": len(validated_urls),
                "total_elapsed_ms": total_elapsed,
                "avg_elapsed_ms": total_elapsed // max(succeeded, 1),
            },
        }

    async def _fetch_with_semaphore(
        self,
        url: str,
        mode: str,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        """Fetch URL with semaphore for concurrency control."""
        async with semaphore:
            result = await self.fetch(url, mode=mode)
            return {
                "url": url,
                "success": result.success,
                "content_preview": result.content[:200] if result.content else "",
                "backend_used": result.backend_used,
                "escalation_level": result.escalation_level,
                "error": result.error,
                "elapsed_ms": result.elapsed_ms,
            }

    async def _escalate(
        self,
        url: str,
        start_level: int,
        max_level: int,
    ) -> EscalationResult:
        """Try escalation chain from start_level to max_level."""
        start_time = time.time()

        for level in range(start_level, max_level + 1):
            backend = LEVEL_TO_BACKEND.get(level, str(level))

            # Check if backend is available
            if not self.availability.check(backend):
                logger.debug("backend_unavailable backend=%s level=%s", backend, level)
                continue

            logger.info("escalation_attempt url=%s backend=%s level=%s", url, backend, level)

            try:
                result = await self._try_backend(url, backend, level)

                if result.success:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return EscalationResult(
                        success=True,
                        content=result.content,
                        backend=backend,
                        level=level,
                        elapsed_ms=elapsed_ms,
                    )

                # Check if we hit Cloudflare (escalate harder)
                if result.cloudflare_detected:
                    logger.info("cloudflare_detected url=%s level=%s, continuing escalation", url, level)
                    continue

            except Exception as e:
                logger.warning("escalation_error url=%s backend=%s error=%s", url, backend, str(e))
                continue

        # All escalations failed
        elapsed_ms = int((time.time() - start_time) * 1000)
        return EscalationResult(
            success=False,
            backend=LEVEL_TO_BACKEND.get(max_level, str(max_level)),
            level=max_level,
            error="All escalation backends exhausted",
            elapsed_ms=elapsed_ms,
        )

    async def _try_backend(self, url: str, backend: str, level: int) -> EscalationResult:
        """Try a single backend."""
        start_time = time.time()

        try:
            if backend == "httpx":
                content = await self._fetch_httpx(url)
            elif backend == "scrapling":
                content = await self._fetch_scrapling(url)
            elif backend == "crawl4ai":
                content = await self._fetch_crawl4ai(url)
            elif backend == "patchright":
                content = await self._fetch_patchright(url)
            elif backend == "nodriver":
                content = await self._fetch_nodriver(url)
            elif backend == "zendriver":
                content = await self._fetch_zendriver(url)
            elif backend == "camoufox":
                content = await self._fetch_camoufox(url)
            elif backend == "botasaurus":
                content = await self._fetch_botasaurus(url)
            else:
                return EscalationResult(
                    success=False,
                    backend=backend,
                    level=level,
                    error=f"Unknown backend: {backend}",
                )

            if not content:
                return EscalationResult(
                    success=False,
                    backend=backend,
                    level=level,
                    error="Empty content",
                )

            elapsed_ms = int((time.time() - start_time) * 1000)
            return EscalationResult(
                success=True,
                content=content,
                backend=backend,
                level=level,
                elapsed_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            cloudflare_detected = "403" in str(e) or "cloudflare" in str(e).lower()
            return EscalationResult(
                success=False,
                backend=backend,
                level=level,
                error=str(e),
                cloudflare_detected=cloudflare_detected,
                elapsed_ms=elapsed_ms,
            )

    async def _fetch_httpx(self, url: str) -> str:
        """Fetch using httpx (simple HTTP)."""
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout_secs) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.text

    async def _fetch_scrapling(self, url: str) -> str:
        """Fetch using Scrapling with stealth headers."""
        try:
            from scrapling.fetchers import Fetcher

            fetcher = Fetcher(timeout=self.timeout_secs)
            page = await fetcher.fetch(url, use_stealth_headers=True)
            return page.get_all_text() or ""
        except ImportError:
            raise RuntimeError("Scrapling not installed")

    async def _fetch_crawl4ai(self, url: str) -> str:
        """Fetch using Crawl4AI for markdown extraction."""
        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url, timeout=self.timeout_secs)
                return result.markdown or result.html or ""
        except ImportError:
            raise RuntimeError("Crawl4AI not installed")

    async def _fetch_patchright(self, url: str) -> str:
        """Fetch using Patchright (undetected Playwright fork)."""
        try:
            import patchright
            from patchright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=self.timeout_secs * 1000)
                content = await page.content()
                await browser.close()
                return content
        except ImportError:
            raise RuntimeError("Patchright not installed")

    async def _fetch_nodriver(self, url: str) -> str:
        """Fetch using nodriver (undetected Chrome)."""
        try:
            import nodriver

            browser = await nodriver.start()
            tab = await browser.get_tab()
            await tab.goto(url)
            content = await tab.get_content()
            await browser.stop()
            return content
        except ImportError:
            raise RuntimeError("nodriver not installed")

    async def _fetch_zendriver(self, url: str) -> str:
        """Fetch using zendriver (Docker-optimized undetected Chrome)."""
        try:
            import zendriver

            driver = await zendriver.start()
            await driver.get(url)
            content = await driver.get_page_source()
            await driver.quit()
            return content
        except ImportError:
            raise RuntimeError("zendriver not installed")

    async def _fetch_camoufox(self, url: str) -> str:
        """Fetch using Camoufox (Firefox stealth)."""
        try:
            from camoufox import sync_playwright

            with sync_playwright() as p:
                browser = p.firefox.launch()
                page = browser.new_page()
                page.goto(url, timeout=self.timeout_secs * 1000)
                content = page.content()
                browser.close()
                return content
        except ImportError:
            raise RuntimeError("Camoufox not installed")

    async def _fetch_botasaurus(self, url: str) -> str:
        """Fetch using Botasaurus (last resort with detection evasion)."""
        try:
            from botasaurus.browser import Browser

            driver = Browser()
            driver.get(url)
            content = driver.page_source
            driver.close()
            return content
        except ImportError:
            raise RuntimeError("Botasaurus not installed")

    def _get_start_level(self, mode: str, force_backend: str | None) -> int:
        """Determine starting escalation level from mode or force_backend."""
        if force_backend:
            return BACKEND_TO_LEVEL.get(force_backend, 0)

        if mode == "fast":
            return 0
        elif mode == "stealth":
            return 3
        elif mode == "max":
            return 5
        else:  # "auto"
            return 0

    async def _check_cache(self, url: str) -> dict[str, Any] | None:
        """Check if URL is in cache."""
        if not self.cache:
            return None

        cache_key = f"scraper_engine::{url}"
        try:
            return self.cache.get(cache_key)
        except Exception as e:
            logger.warning("cache_get_error error=%s", str(e))
            return None

    async def _cache_result(self, url: str, result: EscalationResult) -> None:
        """Cache successful fetch result."""
        if not self.cache:
            return

        cache_key = f"scraper_engine::{url}"
        try:
            self.cache.put(
                cache_key,
                {
                    "url": url,
                    "content": result.content,
                    "backend": result.backend,
                    "level": result.level,
                    "cached_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as e:
            logger.warning("cache_put_error error=%s", str(e))
