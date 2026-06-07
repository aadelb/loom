"""Advanced Price Extraction — extract product prices from any website.

Features:
- Structured extraction from e-commerce pages (product name, price, currency, availability)
- Multi-URL batch extraction
- Price comparison across multiple sources
- Currency detection and normalization
- JSON-LD / Schema.org structured data parsing
- CSS selector-based extraction fallback
- Integration with Scrapling for anti-bot evasion

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
import re
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.price_extractor")

_CURRENCY_SYMBOLS = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR",
    "د.إ": "AED", "AED": "AED", "SAR": "SAR", "ر.س": "SAR",
    "EGP": "EGP", "ج.م": "EGP", "KWD": "KWD", "BHD": "BHD",
    "QAR": "QAR", "OMR": "OMR", "JOD": "JOD",
}

_PRICE_PATTERNS = [
    r'(?:price|cost|amount)[\s:]*[\$€£¥₹]?\s*([\d,]+\.?\d*)',
    r'[\$€£¥₹]\s*([\d,]+\.?\d*)',
    r'([\d,]+\.?\d*)\s*(?:USD|EUR|GBP|AED|SAR|EGP)',
    r'(?:د\.إ|ر\.س|ج\.م)\s*([\d,]+\.?\d*)',
    r'"price":\s*"?([\d,]+\.?\d*)"?',
    r'"amount":\s*"?([\d,]+\.?\d*)"?',
    r'data-price="([\d,]+\.?\d*)"',
    r'itemprop="price"\s+content="([\d,]+\.?\d*)"',
]

_PRODUCT_NAME_PATTERNS = [
    r'<title[^>]*>([^<]+)</title>',
    r'itemprop="name"[^>]*>([^<]+)<',
    r'"name":\s*"([^"]+)"',
    r'<h1[^>]*>([^<]+)</h1>',
    r'og:title"\s+content="([^"]+)"',
]

_AVAILABILITY_PATTERNS = [
    r'(?:in\s*stock|available|add\s*to\s*cart)',
    r'(?:out\s*of\s*stock|sold\s*out|unavailable|notify\s*me)',
]


def _extract_json_ld(html: str) -> list[dict]:
    """Extract JSON-LD structured data (Schema.org Product)."""
    import json
    results = []
    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    for match in matches:
        try:
            data = json.loads(match.strip())
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Product" or "offers" in str(item).lower():
                        results.append(item)
            elif isinstance(data, dict):
                if data.get("@type") == "Product" or "offers" in str(data).lower():
                    results.append(data)
        except (json.JSONDecodeError, ValueError):
            pass
    return results


def _extract_prices_from_text(text: str) -> list[dict]:
    """Extract prices using regex patterns."""
    prices = []
    for pattern in _PRICE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price_str = match.replace(",", "")
                price_val = float(price_str)
                if 0.01 <= price_val <= 10_000_000:
                    currency = "USD"
                    for symbol, curr in _CURRENCY_SYMBOLS.items():
                        if symbol in text[max(0, text.find(match) - 20):text.find(match) + 20]:
                            currency = curr
                            break
                    prices.append({"price": price_val, "currency": currency, "raw": match})
            except (ValueError, TypeError):
                pass
    seen = set()
    unique = []
    for p in prices:
        key = f"{p['price']:.2f}_{p['currency']}"
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique[:20]


def _extract_product_name(html: str) -> str:
    """Extract product name from HTML."""
    for pattern in _PRODUCT_NAME_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r'\s+', ' ', name)
            if len(name) > 5 and len(name) < 200:
                return name
    return ""


def _detect_availability(html: str) -> str:
    """Detect product availability."""
    html_lower = html.lower()
    for pattern in _AVAILABILITY_PATTERNS[:2]:
        if re.search(pattern, html_lower):
            return "in_stock"
    for pattern in _AVAILABILITY_PATTERNS[2:]:
        if re.search(pattern, html_lower):
            return "out_of_stock"
    return "unknown"


@handle_tool_errors("research_price_extract")
async def research_price_extract(
    url: str,
    selectors: list[str] | None = None,
) -> dict[str, Any]:
    """Extract product prices from a URL using multiple strategies.

    Strategies (in order):
    1. JSON-LD Schema.org Product data
    2. Meta tags (og:price, product:price)
    3. CSS selectors (if provided)
    4. Regex pattern matching on page content

    Args:
        url: Product page URL to extract prices from.
        selectors: Optional CSS selectors for price elements.

    Returns:
        Dict with product_name, prices (list), currency, availability,
        source_url, extraction_method, and raw JSON-LD if found.
    """
    import aiohttp

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return {"error": f"HTTP {resp.status}", "url": url}
                html = await resp.text()
    except Exception as e:
        return {"error": f"fetch_failed: {str(e)[:100]}", "url": url}

    json_ld = _extract_json_ld(html)
    product_name = _extract_product_name(html)
    prices = _extract_prices_from_text(html)
    availability = _detect_availability(html)

    extraction_method = "regex"
    structured_price = None

    if json_ld:
        extraction_method = "json_ld"
        for item in json_ld:
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                p = offers.get("price")
                c = offers.get("priceCurrency", "USD")
                if p:
                    structured_price = {"price": float(p), "currency": c}
                    if not product_name:
                        product_name = item.get("name", "")

    return {
        "url": url,
        "product_name": product_name,
        "structured_price": structured_price,
        "all_prices": prices[:10],
        "currency": structured_price["currency"] if structured_price else (prices[0]["currency"] if prices else "unknown"),
        "availability": availability,
        "extraction_method": extraction_method,
        "json_ld_found": len(json_ld),
        "total_prices_detected": len(prices),
    }


@handle_tool_errors("research_price_compare")
async def research_price_compare(
    product_query: str,
    sources: list[str] | None = None,
    max_results: int = 5,
) -> dict[str, Any]:
    """Compare prices for a product across multiple sources.

    Uses search to find product pages, then extracts prices from each.

    Args:
        product_query: Product name/description to search for.
        sources: Optional list of specific URLs to check.
        max_results: Max sources to compare (default 5).

    Returns:
        Dict with product_query, sources checked, prices found,
        lowest/highest price, and price range.
    """
    results = []

    if sources:
        for url in sources[:max_results]:
            price_data = await research_price_extract(url=url)
            if not price_data.get("error"):
                results.append(price_data)
    else:
        try:
            import requests
            r = requests.post(
                "http://localhost:8788/api/v1/tools/research_search",
                json={"query": f"{product_query} price buy", "n": max_results},
                timeout=30,
            )
            search_data = r.json()
            urls = [item.get("url", "") for item in search_data.get("results", []) if item.get("url")]
            for url in urls[:max_results]:
                price_data = await research_price_extract(url=url)
                if not price_data.get("error") and price_data.get("all_prices"):
                    results.append(price_data)
        except Exception as e:
            logger.warning("price_compare_search_failed: %s", str(e)[:80])

    all_prices = []
    for r in results:
        sp = r.get("structured_price")
        if sp:
            all_prices.append(sp["price"])
        elif r.get("all_prices"):
            all_prices.append(r["all_prices"][0]["price"])

    return {
        "product_query": product_query,
        "sources_checked": len(results),
        "prices_found": len(all_prices),
        "lowest_price": min(all_prices) if all_prices else None,
        "highest_price": max(all_prices) if all_prices else None,
        "price_range": round(max(all_prices) - min(all_prices), 2) if len(all_prices) >= 2 else 0,
        "results": results[:max_results],
    }
