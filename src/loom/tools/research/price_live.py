"""Live Price Intelligence — real-time price discovery using multiple strategies.

Goes beyond basic HTTP scraping by using:
1. Crawl4AI for JavaScript-rendered price pages
2. Scrapling for anti-bot evasion on protected e-commerce sites
3. Google Shopping API integration via search
4. Price history estimation from multiple fetches
5. Multi-site aggregation with normalization

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.price_live")

_CURRENCY_MAP = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR",
    "د.إ": "AED", "AED": "AED", "SAR": "SAR", "EGP": "EGP",
    "KWD": "KWD", "BHD": "BHD", "QAR": "QAR",
}


async def _fetch_with_crawl4ai(url: str) -> str:
    """Fetch page with Crawl4AI (handles JavaScript rendering)."""
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return result.markdown if result else ""
    except Exception as e:
        logger.debug("crawl4ai_failed url=%s: %s", url[:50], str(e)[:80])
        return ""


async def _fetch_with_scrapling(url: str) -> str:
    """Fetch with Scrapling (stealthy, anti-bot)."""
    try:
        from scrapling import Fetcher
        fetcher = Fetcher(auto_match=True)
        response = fetcher.get(url)
        return response.text if response else ""
    except Exception as e:
        logger.debug("scrapling_failed url=%s: %s", url[:50], str(e)[:80])
        return ""


async def _search_product_prices(query: str, max_results: int = 5) -> list[dict]:
    """Search for product prices using DuckDuckGo (free, no API key needed)."""
    results = []
    try:
        from ddgs import DDGS
        search_results = DDGS().text(f"{query} price buy", max_results=max_results)
        for item in search_results:
            url = item.get("href", "")
            title = item.get("title", "")
            snippet = item.get("body", "")
            prices = _extract_prices_from_text(snippet)
            if prices or "price" in snippet.lower():
                results.append({
                    "url": url,
                    "title": title,
                    "snippet_prices": prices,
                    "source": "duckduckgo",
                })
    except ImportError:
        import requests
        try:
            r = requests.post(
                "http://localhost:8788/api/v1/tools/research_search",
                json={"query": f"{query} price buy shop", "n": max_results},
                timeout=30,
            )
            data = r.json()
            for item in data.get("results", []):
                url = item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("snippet", item.get("text", ""))
                prices = _extract_prices_from_text(snippet)
                if prices or "price" in snippet.lower():
                    results.append({
                        "url": url, "title": title,
                        "snippet_prices": prices, "source": "loom_search",
                    })
        except Exception:
            pass
    except Exception as e:
        logger.debug("search_prices_failed: %s", str(e)[:80])
    return results


def _extract_prices_from_text(text: str) -> list[dict]:
    """Extract prices from text using regex."""
    prices = []
    patterns = [
        r'[\$€£₹]\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*(?:USD|EUR|GBP|AED|SAR|EGP|KWD)',
        r'(?:price|cost)[:\s]*([\d,]+\.?\d*)',
        r'(?:د\.إ|ر\.س)\s*([\d,]+\.?\d*)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m.replace(",", ""))
                if 0.01 <= val <= 10_000_000:
                    prices.append({"price": val, "raw": m})
            except ValueError:
                pass
    return prices[:10]


@handle_tool_errors("research_price_live")
async def research_price_live(
    product: str,
    region: str = "ae",
    max_sources: int = 5,
    use_js_rendering: bool = True,
) -> dict[str, Any]:
    """Find real-time product prices from multiple live sources.

    Multi-strategy approach:
    1. Search for product + price across web
    2. Fetch top results with anti-bot scraping (Scrapling)
    3. For JS-heavy sites, use Crawl4AI with browser rendering
    4. Extract and normalize prices across all sources
    5. Return price range, cheapest source, and all findings

    Args:
        product: Product name/description to find prices for.
        region: Region code for localized results (ae, us, uk, sa).
        max_sources: Maximum sources to check (default 5).
        use_js_rendering: Use Crawl4AI for JS pages (default True).

    Returns:
        Dict with product, prices from each source, price range,
        cheapest source, average price, and all raw findings.
    """
    start = time.time()

    region_domains = {
        "ae": "amazon.ae noon.com dubizzle.com",
        "us": "amazon.com walmart.com bestbuy.com",
        "uk": "amazon.co.uk argos.co.uk",
        "sa": "amazon.sa noon.com jarir.com",
        "eg": "amazon.eg jumia.com.eg",
    }
    region_suffix = region_domains.get(region, "")
    search_query = f"{product} price {region_suffix}".strip()

    search_results = await _search_product_prices(search_query, max_sources)

    all_prices: list[dict] = []
    source_details: list[dict] = []

    for item in search_results[:max_sources]:
        url = item.get("url", "")
        if not url:
            continue

        page_content = ""
        fetch_method = "search_snippet"

        # Strategy 1: Extract from search snippet (instant)
        if item.get("snippet_prices"):
            for p in item["snippet_prices"]:
                all_prices.append({
                    "price": p["price"],
                    "source": url,
                    "title": item.get("title", ""),
                    "method": "search_snippet",
                })

        # Strategy 2: Crawl4AI — JS rendering for dynamic prices
        if use_js_rendering and not page_content:
            page_content = await _fetch_with_crawl4ai(url)
            if page_content:
                fetch_method = "crawl4ai"

        # Strategy 3: Scrapling — stealth anti-bot fetching
        if not page_content:
            page_content = await asyncio.to_thread(_fetch_scrapling_sync, url)
            if page_content:
                fetch_method = "scrapling"

        # Strategy 4: undetected-chromedriver — bypass advanced anti-bot
        if not page_content:
            page_content = await asyncio.to_thread(_fetch_undetected_chrome, url)
            if page_content:
                fetch_method = "undetected_chrome"

        # Strategy 5: extruct — extract Schema.org structured data
        if page_content:
            try:
                import extruct
                structured = extruct.extract(page_content[:50000], syntaxes=["json-ld", "microdata"])
                for item_ld in structured.get("json-ld", []):
                    if isinstance(item_ld, dict):
                        offers = item_ld.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        if isinstance(offers, dict) and offers.get("price"):
                            all_prices.append({
                                "price": float(offers["price"]),
                                "source": url,
                                "title": item_ld.get("name", item.get("title", "")),
                                "method": "extruct_jsonld",
                                "currency": offers.get("priceCurrency", ""),
                            })
            except Exception:
                pass

        # Strategy 6: price-parser — parse all price strings in page
        if page_content:
            try:
                from price_parser import Price
                import re as _re
                price_candidates = _re.findall(
                    r'[\$€£¥₹][\s]?[\d,]+\.?\d*|[\d,]+\.?\d*\s*(?:AED|USD|EUR|GBP|SAR|EGP)',
                    page_content[:5000]
                )
                for candidate in price_candidates[:5]:
                    parsed = Price.fromstring(candidate)
                    if parsed.amount and 0.01 <= float(parsed.amount) <= 10_000_000:
                        all_prices.append({
                            "price": float(parsed.amount),
                            "source": url,
                            "title": item.get("title", ""),
                            "method": "price_parser",
                            "currency": parsed.currency or "",
                        })
            except Exception:
                pass

        # Strategy 7: regex fallback
        if page_content and not any(p.get("source") == url and p.get("method") != "search_snippet" for p in all_prices):
            extracted = _extract_prices_from_text(page_content[:5000])
            for p in extracted[:3]:
                all_prices.append({
                    "price": p["price"],
                    "source": url,
                    "title": item.get("title", ""),
                    "method": f"regex_via_{fetch_method}",
                })

        # Strategy 8: AutoScraper — ML-based extraction (learns from samples)
        if not any(p.get("source") == url for p in all_prices):
            auto_prices = await asyncio.to_thread(_autoscrape_prices, url)
            for p in auto_prices[:2]:
                all_prices.append({
                    "price": p["price"],
                    "source": url,
                    "title": item.get("title", ""),
                    "method": "autoscraper",
                })

        source_details.append({
            "url": url,
            "title": item.get("title", ""),
            "prices_found": len([p for p in all_prices if p.get("source") == url]),
            "fetch_method": fetch_method,
        })

    unique_prices = []
    seen = set()
    for p in all_prices:
        key = f"{p['price']:.2f}"
        if key not in seen:
            seen.add(key)
            unique_prices.append(p)

    price_values = [p["price"] for p in unique_prices]

    cheapest = min(unique_prices, key=lambda x: x["price"]) if unique_prices else None

    return {
        "product": product,
        "region": region,
        "sources_checked": len(source_details),
        "prices_found": len(unique_prices),
        "price_range": {
            "min": min(price_values) if price_values else None,
            "max": max(price_values) if price_values else None,
            "avg": round(sum(price_values) / len(price_values), 2) if price_values else None,
        },
        "cheapest_source": cheapest,
        "all_prices": unique_prices[:15],
        "sources": source_details,
        "duration_ms": round((time.time() - start) * 1000),
        "methods_used": list(set(p.get("method", "") for p in all_prices)),
    }


def _fetch_scrapling_sync(url: str) -> str:
    """Sync wrapper for Scrapling fetch (v0.4+ API)."""
    try:
        from scrapling import Fetcher
        fetcher = Fetcher()
        response = fetcher.get(url)
        if response and hasattr(response, 'text'):
            return response.text[:10000]
        elif response and hasattr(response, 'content'):
            return response.content.decode('utf-8', errors='ignore')[:10000]
        return ""
    except Exception:
        # Fallback to requests with stealth headers
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            }
            r = requests.get(url, headers=headers, timeout=15)
            return r.text[:10000] if r.status_code == 200 else ""
        except Exception:
            return ""


def _fetch_undetected_chrome(url: str) -> str:
    """Fetch with undetected-chromedriver (bypasses advanced anti-bot)."""
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        driver = uc.Chrome(options=options, version_main=None)
        driver.get(url)
        import time
        time.sleep(3)
        content = driver.page_source
        driver.quit()
        return content[:10000]
    except Exception:
        return ""


def _autoscrape_prices(url: str, sample_prices: list[str] | None = None) -> list[dict]:
    """Use AutoScraper to learn and extract prices from any page."""
    try:
        from autoscraper import AutoScraper
        scraper = AutoScraper()
        samples = sample_prices or ["$99.99", "AED 1,299", "199.00"]
        results = scraper.build(url, samples)
        prices = []
        for r in (results or []):
            extracted = _extract_prices_from_text(str(r))
            prices.extend(extracted)
        return prices[:10]
    except Exception:
        return []


@handle_tool_errors("research_price_history")
async def research_price_history(
    url: str,
    product_name: str = "",
) -> dict[str, Any]:
    """Get price history hints for a product by checking cached versions.

    Uses Wayback Machine and Google Cache to find historical prices
    for comparison with current price.

    Args:
        url: Product page URL.
        product_name: Product name for search fallback.

    Returns:
        Dict with current price, historical references if found,
        and price trend estimation.
    """
    import requests

    current_price = None
    try:
        from loom.tools.research.price_extractor import research_price_extract
        result = await research_price_extract(url=url)
        if result.get("structured_price"):
            current_price = result["structured_price"]["price"]
        elif result.get("all_prices"):
            current_price = result["all_prices"][0]["price"]
    except Exception:
        pass

    wayback_price = None
    try:
        wb_url = f"https://web.archive.org/web/2024/{url}"
        r = requests.get(wb_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            wb_prices = _extract_prices_from_text(r.text[:3000])
            if wb_prices:
                wayback_price = wb_prices[0]["price"]
    except Exception:
        pass

    trend = "unknown"
    if current_price and wayback_price:
        if current_price > wayback_price * 1.05:
            trend = "increasing"
        elif current_price < wayback_price * 0.95:
            trend = "decreasing"
        else:
            trend = "stable"

    return {
        "url": url,
        "product_name": product_name,
        "current_price": current_price,
        "historical_price": wayback_price,
        "trend": trend,
        "price_change_pct": round((current_price - wayback_price) / wayback_price * 100, 1) if current_price and wayback_price else None,
    }
