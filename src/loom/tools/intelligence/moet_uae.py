"""UAE Ministry of Economy & Tourism (MOET) integration.

Tools for accessing UAE government economic data:
- Essential goods price monitoring (9 categories)
- Consumer protection information
- Trade and business regulations
- Price increase requests tracking

Source: www.moet.gov.ae
Engine: Camoufox stealth browser (Liferay CMS with JS rendering)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.moet_uae")

UAE_ESSENTIAL_GOODS_CATEGORIES = {
    "rice": {"ar": "أرز", "unit": "kg", "typical_range": (3, 12)},
    "sugar": {"ar": "سكر", "unit": "kg", "typical_range": (3, 8)},
    "cooking_oil": {"ar": "زيت طهي", "unit": "liter", "typical_range": (8, 25)},
    "milk": {"ar": "حليب", "unit": "liter", "typical_range": (4, 12)},
    "flour": {"ar": "طحين", "unit": "kg", "typical_range": (2, 8)},
    "eggs": {"ar": "بيض", "unit": "30 pcs", "typical_range": (12, 30)},
    "chicken": {"ar": "دجاج", "unit": "kg", "typical_range": (10, 25)},
    "bread": {"ar": "خبز", "unit": "pack", "typical_range": (1, 5)},
    "bottled_water": {"ar": "مياه معبأة", "unit": "1.5L", "typical_range": (0.5, 3)},
}

MOET_URLS = {
    "prices_platform": "https://www.moet.gov.ae/en/essential-goods-prices-platform",
    "consumer_protection": "https://www.moet.gov.ae/en/consumer-protection",
    "consumer_complaints": "https://www.moet.gov.ae/en/consumer-complaints1",
    "price_increase_request": "https://www.moet.gov.ae/en/request-for-price-increase",
    "trade_legislations": "https://www.moet.gov.ae/en/consumer-protection-legislations",
    "main": "https://www.moet.gov.ae/en",
}


async def _camoufox_fetch(url: str, wait_secs: int = 10) -> str:
    """Fetch page via Camoufox stealth browser."""
    try:
        from camoufox.async_api import AsyncCamoufox

        async with AsyncCamoufox(headless=True) as browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(wait_secs)
            content = await page.content()
            await page.close()
            return content
    except Exception as e:
        logger.warning("Camoufox failed for %s: %s", url, e)
        return ""


@handle_tool_errors("research_moet_prices")
async def research_moet_prices(
    category: str = "all",
    emirate: str = "",
) -> dict[str, Any]:
    """Get UAE essential goods prices from Ministry of Economy platform.

    Monitors prices of 9 essential commodity categories regulated by the UAE
    government to prevent price gouging.

    Args:
        category: Filter by category: rice, sugar, cooking_oil, milk, flour,
                  eggs, chicken, bread, bottled_water, or "all"
        emirate: Filter by emirate: dubai, abu_dhabi, sharjah, ajman, etc.

    Returns:
        Dict with current prices, price ranges, and category details
    """
    if isinstance(category, list):
        category = str(category[0]) if category else "all"
    if isinstance(category, dict):
        category = str(category)

    html = await _camoufox_fetch(MOET_URLS["prices_platform"], wait_secs=12)

    prices_data: dict[str, Any] = {
        "source": "moet.gov.ae",
        "platform": "Essential Goods Prices Platform",
        "category_filter": category,
        "emirate_filter": emirate,
        "categories": {},
    }

    if html and len(html) > 10000:
        price_matches = re.findall(
            r'(?:AED|درهم)\s*([\d.]+)',
            html,
        )
        product_matches = re.findall(
            r'(?:rice|sugar|oil|milk|flour|egg|chicken|bread|water'
            r'|أرز|سكر|زيت|حليب|طحين|بيض|دجاج|خبز|مياه)[^<]{0,100}',
            html, re.I,
        )

        if price_matches:
            prices_data["raw_prices_found"] = len(price_matches)
            prices_data["prices_aed"] = [float(p) for p in price_matches[:20]]

        if product_matches:
            prices_data["products_found"] = len(product_matches)

    if category == "all":
        for cat, info in UAE_ESSENTIAL_GOODS_CATEGORIES.items():
            prices_data["categories"][cat] = {
                "name_ar": info["ar"],
                "unit": info["unit"],
                "typical_price_range_aed": {
                    "min": info["typical_range"][0],
                    "max": info["typical_range"][1],
                },
                "regulated": True,
            }
    elif category in UAE_ESSENTIAL_GOODS_CATEGORIES:
        info = UAE_ESSENTIAL_GOODS_CATEGORIES[category]
        prices_data["categories"][category] = {
            "name_ar": info["ar"],
            "unit": info["unit"],
            "typical_price_range_aed": {
                "min": info["typical_range"][0],
                "max": info["typical_range"][1],
            },
            "regulated": True,
        }

    prices_data["regulation_info"] = {
        "authority": "Ministry of Economy & Tourism (MOET)",
        "policy": "New pricing policy effective 2025",
        "categories_regulated": 9,
        "penalty_for_violation": "Fines up to AED 1,000,000",
        "complaint_hotline": "600-522-225",
        "report_url": MOET_URLS["consumer_complaints"],
    }

    return prices_data


@handle_tool_errors("research_moet_consumer")
async def research_moet_consumer(
    topic: str = "protection",
) -> dict[str, Any]:
    """Get UAE consumer protection info from Ministry of Economy.

    Args:
        topic: "protection", "complaints", "legislations", "price_increase"

    Returns:
        Dict with consumer protection information, complaint procedures,
        and relevant legislation
    """
    if isinstance(topic, list):
        topic = str(topic[0]) if topic else "protection"
    if isinstance(topic, dict):
        topic = str(topic)

    url_map = {
        "protection": MOET_URLS["consumer_protection"],
        "complaints": MOET_URLS["consumer_complaints"],
        "legislations": MOET_URLS["trade_legislations"],
        "price_increase": MOET_URLS["price_increase_request"],
    }

    url = url_map.get(topic, MOET_URLS["consumer_protection"])
    html = await _camoufox_fetch(url, wait_secs=10)

    result: dict[str, Any] = {
        "topic": topic,
        "source": "moet.gov.ae",
        "url": url,
    }

    if html and len(html) > 5000:
        text_blocks = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        content = []
        for block in text_blocks:
            clean = re.sub(r'<[^>]+>', '', block).strip()
            if len(clean) > 30 and "cookie" not in clean.lower():
                content.append(clean)

        if content:
            result["content"] = content[:20]
            result["content_length"] = sum(len(c) for c in content)

        links = re.findall(r'href="([^"]*)"[^>]*>([^<]+)', html)
        relevant_links = [
            {"url": url if url.startswith("http") else f"https://www.moet.gov.ae{url}", "text": text.strip()}
            for url, text in links
            if any(kw in text.lower() for kw in ["consumer", "complaint", "rights", "protection", "regulation"])
        ]
        if relevant_links:
            result["related_links"] = relevant_links[:10]

    result["contact"] = {
        "hotline": "600-522-225",
        "whatsapp": "+971-4-777-1777",
        "website": "https://www.moet.gov.ae",
        "app_ios": "https://apps.apple.com/ae/app/ministry-of-economy-dashboards/id1458324701",
    }

    return result


@handle_tool_errors("research_moet_services")
async def research_moet_services(
    service: str = "overview",
) -> dict[str, Any]:
    """Get information about UAE Ministry of Economy services.

    Covers: trade licenses, trademarks, patents, commercial agencies,
    foreign companies, consumer protection, and economic data.

    Args:
        service: Service type: "overview", "trademarks", "patents",
                 "commercial_agencies", "foreign_companies", "trade_licenses"

    Returns:
        Dict with service details, requirements, and procedures
    """
    if isinstance(service, list):
        service = str(service[0]) if service else "overview"
    if isinstance(service, dict):
        service = str(service)

    service_urls = {
        "overview": "https://www.moet.gov.ae/en/services",
        "trademarks": "https://www.moet.gov.ae/en/trademarks-services",
        "patents": "https://www.moet.gov.ae/en/patents-industrial-designs",
        "commercial_agencies": "https://www.moet.gov.ae/en/commercial-agencies",
        "foreign_companies": "https://www.moet.gov.ae/en/foreign-companies",
        "trade_licenses": "https://www.moet.gov.ae/en/certificate-of-origin",
    }

    url = service_urls.get(service, service_urls["overview"])
    html = await _camoufox_fetch(url, wait_secs=10)

    result: dict[str, Any] = {
        "service": service,
        "source": "moet.gov.ae",
        "url": url,
    }

    if html and len(html) > 5000:
        title_m = re.search(r'<title>([^<]+)', html)
        if title_m:
            result["title"] = re.sub(r'\s*\|.*$', '', title_m.group(1)).strip()

        text_blocks = re.findall(r'<(?:p|li|h[2-4])[^>]*>(.*?)</(?:p|li|h[2-4])>', html, re.DOTALL)
        content = []
        for block in text_blocks:
            clean = re.sub(r'<[^>]+>', '', block).strip()
            if len(clean) > 20 and "cookie" not in clean.lower() and "javascript" not in clean.lower():
                content.append(clean)
        if content:
            result["content"] = content[:30]

        service_links = re.findall(r'href="([^"]*service[^"]*)"[^>]*>([^<]+)', html, re.I)
        if service_links:
            result["available_services"] = [
                {"url": f"https://www.moet.gov.ae{u}" if not u.startswith("http") else u, "name": t.strip()}
                for u, t in service_links[:15]
            ]

    result["ministry_info"] = {
        "name": "Ministry of Economy & Tourism",
        "name_ar": "وزارة الاقتصاد والسياحة",
        "country": "United Arab Emirates",
        "hotline": "600-522-225",
        "headquarters": "Abu Dhabi, UAE",
        "website": "https://www.moet.gov.ae",
    }

    return result
