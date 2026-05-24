"""Dubai real estate research tools — Bayut, Property Finder, Dubizzle.

Primary engine: Camoufox stealth browser (bypasses CAPTCHA/anti-bot).
Extracts property listings, prices, agent info, and market data.
Supports: Bayut.com, PropertyFinder.ae, Dubizzle.com.

Env vars:
  REALESTATE_HEADLESS — Run Camoufox headless (default: true)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any
from urllib.parse import quote, urljoin

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.realestate_research")

_HEADLESS = os.environ.get("REALESTATE_HEADLESS", "true").lower() == "true"

_SITES = {
    "bayut": {
        "base": "https://www.bayut.com",
        "sale": "/for-sale/property/{location}/",
        "rent": "/to-rent/property/{location}/",
        "search_params": "?beds_in={beds}&price_min={price_min}&price_max={price_max}&area_min={area_min}",
    },
    "propertyfinder": {
        "base": "https://www.propertyfinder.ae",
        "sale": "/en/buy/properties-for-sale.html?l={location_id}",
        "rent": "/en/rent/properties-for-rent.html?l={location_id}",
    },
    "dubizzle": {
        "base": "https://dubai.dubizzle.com",
        "sale": "/property-for-sale/residential/",
        "rent": "/property-for-rent/residential/",
    },
}


async def _camoufox_fetch(url: str, wait_secs: int = 8) -> str:
    """Fetch a page using Camoufox stealth browser."""
    try:
        from camoufox.async_api import AsyncCamoufox

        async with AsyncCamoufox(headless=_HEADLESS) as browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(wait_secs)
            content = await page.content()
            await page.close()
            return content
    except ImportError:
        logger.warning("camoufox not installed")
        return ""
    except Exception as e:
        logger.warning("Camoufox fetch failed: %s", e)
        return ""


def _extract_bayut_listings(html: str) -> list[dict[str, Any]]:
    """Extract property listings from Bayut HTML."""
    listings = []

    article_pattern = re.compile(
        r'<article[^>]*>(.*?)</article>', re.DOTALL
    )
    for article in article_pattern.findall(html):
        listing: dict[str, Any] = {}

        price_match = re.search(r'AED\s*([\d,]+)', article)
        if price_match:
            listing["price"] = int(price_match.group(1).replace(",", ""))
            listing["currency"] = "AED"

        title_match = re.search(r'aria-label="([^"]+)"', article)
        if title_match:
            listing["title"] = title_match.group(1)

        beds_match = re.search(r'(\d+)\s*Bed', article)
        if beds_match:
            listing["bedrooms"] = int(beds_match.group(1))

        baths_match = re.search(r'(\d+)\s*Bath', article)
        if baths_match:
            listing["bathrooms"] = int(baths_match.group(1))

        area_match = re.search(r'([\d,]+)\s*sqft', article)
        if area_match:
            listing["area_sqft"] = int(area_match.group(1).replace(",", ""))

        link_match = re.search(r'href="(/property/[^"]+)"', article)
        if link_match:
            listing["url"] = f"https://www.bayut.com{link_match.group(1)}"

        location_match = re.search(r'<span[^>]*>([^<]*(?:Dubai|Abu Dhabi|Sharjah|Ajman)[^<]*)</span>', article)
        if location_match:
            listing["location"] = location_match.group(1).strip()

        if listing.get("price") or listing.get("title"):
            listings.append(listing)

    return listings


def _extract_propertyfinder_listings(html: str) -> list[dict[str, Any]]:
    """Extract listings from Property Finder HTML."""
    listings = []

    card_pattern = re.compile(r'data-testid="property-card"[^>]*>(.*?)</(?:article|div>)', re.DOTALL)
    for card in card_pattern.findall(html):
        listing: dict[str, Any] = {}

        price_match = re.search(r'AED\s*([\d,]+)', card)
        if price_match:
            listing["price"] = int(price_match.group(1).replace(",", ""))
            listing["currency"] = "AED"

        title_match = re.search(r'<h2[^>]*>([^<]+)</h2>', card)
        if title_match:
            listing["title"] = title_match.group(1).strip()

        beds_match = re.search(r'(\d+)\s*(?:Bed|BR)', card)
        if beds_match:
            listing["bedrooms"] = int(beds_match.group(1))

        area_match = re.search(r'([\d,]+)\s*(?:sqft|sq\.?\s*ft)', card)
        if area_match:
            listing["area_sqft"] = int(area_match.group(1).replace(",", ""))

        link_match = re.search(r'href="(/en/[^"]*property[^"]*)"', card)
        if link_match:
            listing["url"] = f"https://www.propertyfinder.ae{link_match.group(1)}"

        if listing.get("price") or listing.get("title"):
            listings.append(listing)

    return listings


@handle_tool_errors("research_bayut_search")
async def research_bayut_search(
    location: str = "dubai",
    purpose: str = "for-sale",
    bedrooms: int = 0,
    price_min: int = 0,
    price_max: int = 0,
    property_type: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Search Bayut.com for property listings in UAE.

    Args:
        location: Area (dubai, abu-dhabi, sharjah, ajman, dubai-marina, palm-jumeirah, etc.)
        purpose: "for-sale" or "to-rent"
        bedrooms: Filter by bedrooms (0=any, 1-7)
        price_min: Minimum price in AED (0=no min)
        price_max: Maximum price in AED (0=no max)
        property_type: Filter: apartment, villa, townhouse, penthouse, land
        limit: Max results (1-50, default 20)

    Returns:
        Dict with listings: title, price, bedrooms, bathrooms, area_sqft, location, url
    """
    if isinstance(location, list):
        location = str(location[0]) if location else "dubai"
    if isinstance(location, dict):
        location = "dubai"

    location = location.lower().replace(" ", "-")
    purpose = "to-rent" if "rent" in str(purpose).lower() else "for-sale"

    url = f"https://www.bayut.com/{purpose}/property/{location}/"
    params = []
    if bedrooms > 0:
        params.append(f"beds_in={bedrooms}")
    if price_min > 0:
        params.append(f"price_min={price_min}")
    if price_max > 0:
        params.append(f"price_max={price_max}")
    if property_type:
        params.append(f"category_exct={property_type}")
    if params:
        url += "?" + "&".join(params)

    html = await _camoufox_fetch(url, wait_secs=10)
    if not html or "Captcha" in html[:2000]:
        return {
            "location": location,
            "purpose": purpose,
            "source": "bayut",
            "listings": [],
            "count": 0,
            "error": "Bayut CAPTCHA — try again or use residential proxy",
        }

    listings = _extract_bayut_listings(html)
    return {
        "location": location,
        "purpose": purpose,
        "source": "bayut_camoufox",
        "listings": listings[:limit],
        "count": len(listings),
        "url": url,
    }


@handle_tool_errors("research_bayut_property")
async def research_bayut_property(
    url: str,
) -> dict[str, Any]:
    """Get detailed info for a specific Bayut property listing.

    Args:
        url: Full Bayut property URL (e.g. "https://www.bayut.com/property/details-XXXXX.html")

    Returns:
        Dict with title, price, bedrooms, bathrooms, area, description, agent, photos
    """
    if isinstance(url, list):
        url = str(url[0]) if url else ""
    if isinstance(url, dict):
        url = str(url)

    if not url.startswith("http"):
        url = f"https://www.bayut.com/property/details-{url}.html"

    html = await _camoufox_fetch(url, wait_secs=8)
    if not html or "Captcha" in html[:2000]:
        return {"url": url, "error": "CAPTCHA blocked", "source": "bayut"}

    property_data: dict[str, Any] = {"url": url, "source": "bayut_camoufox"}

    title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    if title_match:
        property_data["title"] = title_match.group(1).strip()

    price_match = re.search(r'AED\s*([\d,]+)', html)
    if price_match:
        property_data["price"] = int(price_match.group(1).replace(",", ""))

    desc_match = re.search(r'<div[^>]*data-testid="description[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if desc_match:
        property_data["description"] = re.sub(r'<[^>]+>', '', desc_match.group(1))[:500]

    beds_match = re.search(r'(\d+)\s*Bed', html)
    if beds_match:
        property_data["bedrooms"] = int(beds_match.group(1))

    baths_match = re.search(r'(\d+)\s*Bath', html)
    if baths_match:
        property_data["bathrooms"] = int(baths_match.group(1))

    area_match = re.search(r'([\d,]+)\s*sqft', html)
    if area_match:
        property_data["area_sqft"] = int(area_match.group(1).replace(",", ""))

    agent_match = re.search(r'data-testid="agent-name"[^>]*>([^<]+)', html)
    if agent_match:
        property_data["agent_name"] = agent_match.group(1).strip()

    photos = re.findall(r'src="(https://images\.bayut\.com/[^"]+)"', html)
    property_data["photos"] = list(set(photos))[:10]

    return property_data


@handle_tool_errors("research_property_search")
async def research_property_search(
    query: str,
    location: str = "dubai",
    purpose: str = "for-sale",
    bedrooms: int = 0,
    price_max: int = 0,
    source: str = "bayut",
    limit: int = 20,
) -> dict[str, Any]:
    """Search UAE real estate across Bayut, Property Finder, and Dubizzle.

    Args:
        query: Search query (e.g. "sea view apartment", "villa palm jumeirah")
        location: Area (dubai, abu-dhabi, marina, palm-jumeirah, etc.)
        purpose: "for-sale" or "to-rent"
        bedrooms: Filter by bedrooms (0=any)
        price_max: Max price AED (0=no limit)
        source: "bayut", "propertyfinder", "dubizzle", or "all"
        limit: Max results per source

    Returns:
        Dict with combined listings from selected sources
    """
    if isinstance(query, list):
        query = " ".join(str(x) for x in query)
    if isinstance(query, dict):
        query = str(query)
    if isinstance(location, list):
        location = str(location[0]) if location else "dubai"

    results: dict[str, Any] = {
        "query": query,
        "location": location,
        "purpose": purpose,
        "sources_checked": [],
        "listings": [],
        "total_count": 0,
    }

    if source in ("bayut", "all"):
        bayut_result = await research_bayut_search(
            location=location,
            purpose=purpose,
            bedrooms=bedrooms,
            price_max=price_max,
            limit=limit,
        )
        results["sources_checked"].append("bayut")
        if bayut_result.get("listings"):
            results["listings"].extend(bayut_result["listings"])

    if source in ("propertyfinder", "all"):
        pf_url = f"https://www.propertyfinder.ae/en/search?c=1&fu=0&l={quote(location)}&ob=mr&page=1&rp=y&t={1 if 'sale' in purpose else 2}"
        html = await _camoufox_fetch(pf_url, wait_secs=10)
        if html and "Captcha" not in html[:2000]:
            pf_listings = _extract_propertyfinder_listings(html)
            results["sources_checked"].append("propertyfinder")
            results["listings"].extend(pf_listings[:limit])

    if source in ("dubizzle", "all"):
        dub_purpose = "property-for-sale" if "sale" in purpose else "property-for-rent"
        dub_url = f"https://dubai.dubizzle.com/{dub_purpose}/residential/?keywords={quote(query)}"
        html = await _camoufox_fetch(dub_url, wait_secs=10)
        if html and len(html) > 5000:
            results["sources_checked"].append("dubizzle")

    results["total_count"] = len(results["listings"])
    return results


@handle_tool_errors("research_bayut_market")
async def research_bayut_market(
    location: str = "dubai",
) -> dict[str, Any]:
    """Get real estate market overview for a Dubai area.

    Scrapes aggregate data from Bayut: price ranges, popular areas,
    property type distribution.

    Args:
        location: Area to analyze (dubai, marina, palm-jumeirah, etc.)

    Returns:
        Dict with market overview: avg_price, price_range, popular_types
    """
    if isinstance(location, list):
        location = str(location[0]) if location else "dubai"

    sale_result = await research_bayut_search(location=location, purpose="for-sale", limit=50)
    rent_result = await research_bayut_search(location=location, purpose="to-rent", limit=50)

    sale_listings = sale_result.get("listings", [])
    rent_listings = rent_result.get("listings", [])

    sale_prices = [l["price"] for l in sale_listings if l.get("price")]
    rent_prices = [l["price"] for l in rent_listings if l.get("price")]

    market: dict[str, Any] = {
        "location": location,
        "source": "bayut_camoufox",
        "sale": {
            "count": len(sale_listings),
            "avg_price": int(sum(sale_prices) / len(sale_prices)) if sale_prices else 0,
            "min_price": min(sale_prices) if sale_prices else 0,
            "max_price": max(sale_prices) if sale_prices else 0,
        },
        "rent": {
            "count": len(rent_listings),
            "avg_price": int(sum(rent_prices) / len(rent_prices)) if rent_prices else 0,
            "min_price": min(rent_prices) if rent_prices else 0,
            "max_price": max(rent_prices) if rent_prices else 0,
        },
    }

    bed_counts = {}
    for l in sale_listings:
        beds = l.get("bedrooms", 0)
        bed_counts[beds] = bed_counts.get(beds, 0) + 1
    market["bedroom_distribution"] = bed_counts

    return market
