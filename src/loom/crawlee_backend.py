"""Crawlee Python multi-backend scraping framework integration.

Provides three research tools:
1. research_crawl — Website crawling with optional link following
2. research_sitemap_crawl — Crawl via sitemap.xml for comprehensive coverage
3. research_structured_crawl — Crawl + extract structured data matching a schema

Uses Crawlee's PlaywrightCrawler (JavaScript-enabled) or BeautifulSoupCrawler
(HTTP-only, faster) depending on content requirements.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from loom.validators import validate_url

logger = logging.getLogger("loom.crawlee_backend")

# Optional Crawlee dependency
try:
    from crawlee import BeautifulSoupCrawler, PlaywrightCrawler
    from crawlee.crawlers import BeautifulSoupCrawlingContext, PlaywrightCrawlingContext

    _HAS_CRAWLEE = True
except ImportError:
    _HAS_CRAWLEE = False


class CrawlResult(BaseModel):
    """Single page crawl result."""

    url: str
    title: str | None = None
    text_snippet: str = ""
    html_len: int = 0
    links_found: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class CrawlResponse(BaseModel):
    """Response from research_crawl."""

    start_url: str
    pages_crawled: int
    links_found: int
    content: list[CrawlResult]
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class SitemapCrawlResponse(BaseModel):
    """Response from research_sitemap_crawl."""

    url: str
    sitemap_urls: list[str]
    pages_crawled: int
    content: list[CrawlResult]
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class StructuredCrawlResponse(BaseModel):
    """Response from research_structured_crawl."""

    url: str
    pages_crawled: int
    extracted_data: list[dict[str, Any]]
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


async def research_crawl(
    url: str,
    max_pages: int = 10,
    pattern: str | None = None,
    extract_links: bool = True,
    use_js: bool = False,
) -> CrawlResponse:
    """Crawl a website starting from URL, following links matching pattern.

    Uses BeautifulSoupCrawler by default (fast, HTTP-only). Set use_js=True
    to use PlaywrightCrawler for JavaScript-heavy sites (slower).

    Args:
        url: Starting URL to crawl
        max_pages: Maximum pages to crawl (1-100)
        pattern: Optional regex pattern to filter links (e.g., r"/blog/.*")
        extract_links: Whether to extract and follow links (enqueue_links)
        use_js: Use Playwright (JS-enabled) instead of BeautifulSoup (HTTP-only)

    Returns:
        CrawlResponse with pages_crawled, links_found, and content list
    """
    if not _HAS_CRAWLEE:
        return CrawlResponse(
            start_url=url,
            pages_crawled=0,
            links_found=0,
            content=[],
            error="Crawlee not installed. Install with: pip install crawlee[all]",
        )

    # Validate URL
    try:
        url = validate_url(url)
    except ValueError as e:
        return CrawlResponse(
            start_url=url,
            pages_crawled=0,
            links_found=0,
            content=[],
            error=f"Invalid URL: {e}",
        )

    # Bound max_pages
    max_pages = max(1, min(max_pages, 100))

    content: list[CrawlResult] = []
    pages_crawled = 0
    total_links = 0

    try:
        if use_js:
            crawler = PlaywrightCrawler(max_requests_per_crawl=max_pages)

            @crawler.router.default_handler
            async def handler_js(context: PlaywrightCrawlingContext) -> None:
                nonlocal pages_crawled, total_links

                try:
                    title = await context.page.title()
                    text = await context.page.evaluate(
                        """() => {
                        return document.body.innerText;
                    }"""
                    )
                    html = await context.page.content()

                    # Extract links if enabled
                    links = []
                    if extract_links:
                        links = await context.page.evaluate(
                            """() => {
                            return Array.from(document.querySelectorAll('a'))
                                .map(a => a.href)
                                .filter(href => href.startsWith('http'));
                        }"""
                        )

                        # Filter by pattern if provided
                        if pattern:
                            try:
                                links = [l for l in links if re.search(pattern, l)]
                            except re.error:
                                pass  # Ignore regex errors

                        total_links += len(links)

                    # Extract text snippet (first 500 chars)
                    text_snippet = (text or "")[:500]

                    result = CrawlResult(
                        url=context.request.url,
                        title=title,
                        text_snippet=text_snippet,
                        html_len=len(html or ""),
                        links_found=links,
                    )
                    content.append(result)
                    pages_crawled += 1

                    # Enqueue filtered links
                    if extract_links and links:
                        for link in links[:5]:  # Limit to 5 links per page to avoid explosion
                            await context.send_request(link)

                except Exception as e:
                    logger.error(f"Error processing {context.request.url}: {e}")

            await crawler.run([url])

        else:
            crawler = BeautifulSoupCrawler(max_requests_per_crawl=max_pages)

            @crawler.router.default_handler
            async def handler_bs(context: BeautifulSoupCrawlingContext) -> None:
                nonlocal pages_crawled, total_links

                try:
                    title = context.soup.title.string if context.soup.title else None
                    text = context.soup.get_text(separator=" ", strip=True)

                    # Extract links
                    links = []
                    if extract_links:
                        links = [
                            a.get("href")
                            for a in context.soup.find_all("a", href=True)
                            if a.get("href", "").startswith(("http://", "https://"))
                        ]

                        # Filter by pattern if provided
                        if pattern:
                            try:
                                links = [l for l in links if re.search(pattern, l)]
                            except re.error:
                                pass  # Ignore regex errors

                        total_links += len(links)

                    # Extract text snippet (first 500 chars)
                    text_snippet = text[:500]

                    result = CrawlResult(
                        url=context.request.url,
                        title=title,
                        text_snippet=text_snippet,
                        html_len=len(context.soup.prettify() or ""),
                        links_found=links,
                    )
                    content.append(result)
                    pages_crawled += 1

                    # Enqueue filtered links
                    if extract_links and links:
                        for link in links[:5]:  # Limit to 5 links per page
                            await context.enqueue_links(urls=[link])

                except Exception as e:
                    logger.error(f"Error processing {context.request.url}: {e}")

            await crawler.run([url])

        return CrawlResponse(
            start_url=url,
            pages_crawled=pages_crawled,
            links_found=total_links,
            content=content,
        )

    except Exception as e:
        logger.error(f"Crawl error for {url}: {e}")
        return CrawlResponse(
            start_url=url,
            pages_crawled=pages_crawled,
            links_found=total_links,
            content=content,
            error=str(e),
        )


async def research_sitemap_crawl(
    url: str,
    max_pages: int = 50,
    use_js: bool = False,
) -> SitemapCrawlResponse:
    """Crawl website via sitemap.xml for comprehensive site coverage.

    Attempts to fetch and parse sitemap.xml at the root, then crawls
    all URLs found in the sitemap (up to max_pages).

    Args:
        url: Starting URL (domain only, e.g., https://example.com)
        max_pages: Maximum pages to crawl from sitemap (1-500)
        use_js: Use Playwright (JS-enabled) instead of BeautifulSoup

    Returns:
        SitemapCrawlResponse with sitemap URLs and crawled content
    """
    if not _HAS_CRAWLEE:
        return SitemapCrawlResponse(
            url=url,
            sitemap_urls=[],
            pages_crawled=0,
            content=[],
            error="Crawlee not installed. Install with: pip install crawlee[all]",
        )

    # Validate URL
    try:
        url = validate_url(url)
    except ValueError as e:
        return SitemapCrawlResponse(
            url=url,
            sitemap_urls=[],
            pages_crawled=0,
            content=[],
            error=f"Invalid URL: {e}",
        )

    # Bound max_pages
    max_pages = max(1, min(max_pages, 500))

    # Extract domain from URL
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    sitemap_url = f"{domain}/sitemap.xml"

    sitemap_urls: list[str] = []
    content: list[CrawlResult] = []
    pages_crawled = 0

    try:
        # Try to fetch sitemap.xml
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(sitemap_url)
                if resp.status_code == 200:
                    # Simple XML parsing for sitemap URLs
                    import re as regex_module

                    urls = regex_module.findall(r"<loc>(https?://[^<]+)</loc>", resp.text)
                    sitemap_urls = urls[:max_pages]  # Limit to max_pages
            except Exception as e:
                logger.warning(f"Could not fetch sitemap.xml: {e}")

        # If no sitemap found, use the provided URL as fallback
        if not sitemap_urls:
            sitemap_urls = [url]

        # Crawl all sitemap URLs
        if use_js:
            crawler = PlaywrightCrawler(max_requests_per_crawl=len(sitemap_urls))

            @crawler.router.default_handler
            async def handler_js_sitemap(context: PlaywrightCrawlingContext) -> None:
                nonlocal pages_crawled

                try:
                    title = await context.page.title()
                    text = await context.page.evaluate(
                        """() => {
                        return document.body.innerText;
                    }"""
                    )
                    html = await context.page.content()

                    text_snippet = (text or "")[:500]

                    result = CrawlResult(
                        url=context.request.url,
                        title=title,
                        text_snippet=text_snippet,
                        html_len=len(html or ""),
                    )
                    content.append(result)
                    pages_crawled += 1

                except Exception as e:
                    logger.error(f"Error processing {context.request.url}: {e}")

            await crawler.run(sitemap_urls)

        else:
            crawler = BeautifulSoupCrawler(max_requests_per_crawl=len(sitemap_urls))

            @crawler.router.default_handler
            async def handler_bs_sitemap(context: BeautifulSoupCrawlingContext) -> None:
                nonlocal pages_crawled

                try:
                    title = context.soup.title.string if context.soup.title else None
                    text = context.soup.get_text(separator=" ", strip=True)
                    text_snippet = text[:500]

                    result = CrawlResult(
                        url=context.request.url,
                        title=title,
                        text_snippet=text_snippet,
                        html_len=len(context.soup.prettify() or ""),
                    )
                    content.append(result)
                    pages_crawled += 1

                except Exception as e:
                    logger.error(f"Error processing {context.request.url}: {e}")

            await crawler.run(sitemap_urls)

        return SitemapCrawlResponse(
            url=url,
            sitemap_urls=sitemap_urls,
            pages_crawled=pages_crawled,
            content=content,
        )

    except Exception as e:
        logger.error(f"Sitemap crawl error for {url}: {e}")
        return SitemapCrawlResponse(
            url=url,
            sitemap_urls=sitemap_urls,
            pages_crawled=pages_crawled,
            content=content,
            error=str(e),
        )


async def research_structured_crawl(
    url: str,
    schema_map: dict[str, str],
    max_pages: int = 5,
    use_js: bool = False,
) -> StructuredCrawlResponse:
    """Crawl + extract structured data matching a CSS selector schema.

    Uses CSS selectors to extract data from each page. Schema is a dict
    mapping field names to CSS selectors.

    Example schema:
        {
            "title": "h1",
            "price": ".price",
            "description": ".desc",
        }

    Args:
        url: Starting URL to crawl
        schema_map: Dict mapping field names to CSS selectors
        max_pages: Maximum pages to crawl (1-50)
        use_js: Use Playwright (JS-enabled) instead of BeautifulSoup

    Returns:
        StructuredCrawlResponse with extracted_data list of dicts
    """
    if not _HAS_CRAWLEE:
        return StructuredCrawlResponse(
            url=url,
            pages_crawled=0,
            extracted_data=[],
            error="Crawlee not installed. Install with: pip install crawlee[all]",
        )

    # Validate URL
    try:
        url = validate_url(url)
    except ValueError as e:
        return StructuredCrawlResponse(
            url=url,
            pages_crawled=0,
            extracted_data=[],
            error=f"Invalid URL: {e}",
        )

    # Validate schema
    if not isinstance(schema_map, dict) or not schema_map:
        return StructuredCrawlResponse(
            url=url,
            pages_crawled=0,
            extracted_data=[],
            error="schema_map must be a non-empty dict mapping field names to CSS selectors",
        )

    # Bound max_pages
    max_pages = max(1, min(max_pages, 50))

    extracted_data: list[dict[str, Any]] = []
    pages_crawled = 0

    try:
        if use_js:
            crawler = PlaywrightCrawler(max_requests_per_crawl=max_pages)

            @crawler.router.default_handler
            async def handler_js_structured(context: PlaywrightCrawlingContext) -> None:
                nonlocal pages_crawled

                try:
                    # Extract data using schema
                    data = {}
                    for field_name, selector in schema_map.items():
                        try:
                            # Use Playwright's page.locator for CSS selectors
                            elements = await context.page.query_selector_all(selector)
                            if elements:
                                # Get text from first matching element
                                text = await elements[0].text_content()
                                data[field_name] = text.strip() if text else ""
                            else:
                                data[field_name] = None
                        except Exception as e:
                            logger.debug(f"Error extracting {field_name}: {e}")
                            data[field_name] = None

                    # Only add if at least one field was extracted
                    if any(v is not None for v in data.values()):
                        data["_url"] = context.request.url
                        extracted_data.append(data)

                    pages_crawled += 1

                except Exception as e:
                    logger.error(f"Error processing {context.request.url}: {e}")

            await crawler.run([url])

        else:
            crawler = BeautifulSoupCrawler(max_requests_per_crawl=max_pages)

            @crawler.router.default_handler
            async def handler_bs_structured(context: BeautifulSoupCrawlingContext) -> None:
                nonlocal pages_crawled

                try:
                    # Extract data using BeautifulSoup CSS selectors
                    data = {}
                    for field_name, selector in schema_map.items():
                        try:
                            element = context.soup.select_one(selector)
                            if element:
                                data[field_name] = element.get_text(strip=True)
                            else:
                                data[field_name] = None
                        except Exception as e:
                            logger.debug(f"Error extracting {field_name}: {e}")
                            data[field_name] = None

                    # Only add if at least one field was extracted
                    if any(v is not None for v in data.values()):
                        data["_url"] = context.request.url
                        extracted_data.append(data)

                    pages_crawled += 1

                except Exception as e:
                    logger.error(f"Error processing {context.request.url}: {e}")

            await crawler.run([url])

        return StructuredCrawlResponse(
            url=url,
            pages_crawled=pages_crawled,
            extracted_data=extracted_data,
        )

    except Exception as e:
        logger.error(f"Structured crawl error for {url}: {e}")
        return StructuredCrawlResponse(
            url=url,
            pages_crawled=pages_crawled,
            extracted_data=extracted_data,
            error=str(e),
        )
