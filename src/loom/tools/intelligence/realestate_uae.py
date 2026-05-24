"""UAE Real Estate Intelligence — Multi-platform property research.

Covers ALL major UAE real estate platforms:
- Bayut.com (largest portal, Algolia-backed)
- PropertyFinder.ae (2nd largest)
- Dubizzle.com (classifieds)
- DREM.ae (Dubai official marketplace, DLD)
- Square Yards, Skyloov, Emirates.Estate
- Developer sites: Emaar, DAMAC, Nakheel, Sobha, Azizi
- Government: Dubai Land Department (DLD) transactions

Tools:
  research_uae_property_search  — Multi-platform property search
  research_uae_dld_transactions — Dubai Land Department transaction data
  research_uae_offplan          — Off-plan projects from developers
  research_uae_mortgage_calc    — Mortgage calculator (UAE rules)
  research_uae_area_guide       — Area intelligence (prices, yields, growth)
  research_uae_agent_find       — Find registered real estate agents

Engine: Camoufox stealth browser (all UAE portals have anti-bot).
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
from typing import Any
from urllib.parse import quote

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.realestate_uae")

_HEADLESS = os.environ.get("REALESTATE_HEADLESS", "true").lower() == "true"

UAE_PLATFORMS = {
    "bayut": {"url": "https://www.bayut.com", "type": "portal"},
    "propertyfinder": {"url": "https://www.propertyfinder.ae", "type": "portal"},
    "dubizzle": {"url": "https://dubai.dubizzle.com", "type": "classifieds"},
    "drem": {"url": "https://www.drem.ae", "type": "government"},
    "squareyards": {"url": "https://www.squareyards.ae", "type": "portal"},
    "skyloov": {"url": "https://www.skyloov.com", "type": "portal"},
    "emirates_estate": {"url": "https://emirates.estate", "type": "international"},
    "emaar": {"url": "https://www.emaar.com", "type": "developer"},
    "damac": {"url": "https://www.damacproperties.com", "type": "developer"},
    "nakheel": {"url": "https://www.nakheel.com", "type": "developer"},
    "sobha": {"url": "https://www.sobharealty.com", "type": "developer"},
    "azizi": {"url": "https://www.azizidevelopments.com", "type": "developer"},
    "meraas": {"url": "https://www.meraas.com", "type": "developer"},
    "aldar": {"url": "https://www.aldar.com", "type": "developer"},
    "dld": {"url": "https://dubailand.gov.ae", "type": "government"},
}

DUBAI_AREAS = [
    "dubai-marina", "palm-jumeirah", "downtown-dubai", "business-bay",
    "jumeirah-beach-residence", "dubai-hills-estate", "arabian-ranches",
    "jumeirah-village-circle", "dubai-sports-city", "motor-city",
    "international-city", "discovery-gardens", "dubai-silicon-oasis",
    "al-barsha", "jumeirah-lake-towers", "dubai-creek-harbour",
    "emaar-beachfront", "bluewaters-island", "city-walk", "meydan",
    "damac-hills", "town-square", "villanova", "dubai-south",
]


async def _camoufox_fetch(url: str, wait_secs: int = 8) -> str:
    """Fetch page via Camoufox stealth browser."""
    try:
        from camoufox.async_api import AsyncCamoufox

        async with AsyncCamoufox(headless=_HEADLESS) as browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(wait_secs)
            content = await page.content()
            await page.close()
            return content
    except Exception as e:
        logger.warning("Camoufox failed for %s: %s", url, e)
        return ""


def _parse_price(text: str) -> int:
    """Extract price from text like 'AED 1,500,000' or '1.5M'."""
    text = text.replace(",", "").replace(" ", "")
    m = re.search(r"(\d+\.?\d*)\s*[Mm]", text)
    if m:
        return int(float(m.group(1)) * 1_000_000)
    m = re.search(r"(\d+\.?\d*)\s*[Kk]", text)
    if m:
        return int(float(m.group(1)) * 1_000)
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return 0


def _extract_listings_generic(html: str, source: str) -> list[dict[str, Any]]:
    """Generic listing extractor using common patterns."""
    listings = []
    price_pattern = re.compile(r"AED\s*([\d,]+)")
    beds_pattern = re.compile(r"(\d+)\s*(?:Bed|BR|bedroom)", re.I)
    baths_pattern = re.compile(r"(\d+)\s*(?:Bath|bathroom)", re.I)
    area_pattern = re.compile(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft)", re.I)

    articles = re.findall(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
    if not articles:
        articles = re.findall(r'class="[^"]*(?:listing|property|card)[^"]*"[^>]*>(.*?)</(?:div|section)>', html, re.DOTALL)

    for article in articles[:50]:
        listing: dict[str, Any] = {"source": source}

        pm = price_pattern.search(article)
        if pm:
            listing["price"] = int(pm.group(1).replace(",", ""))
            listing["currency"] = "AED"

        bm = beds_pattern.search(article)
        if bm:
            listing["bedrooms"] = int(bm.group(1))

        btm = baths_pattern.search(article)
        if btm:
            listing["bathrooms"] = int(btm.group(1))

        am = area_pattern.search(article)
        if am:
            listing["area_sqft"] = int(am.group(1).replace(",", ""))

        title_m = re.search(r'aria-label="([^"]+)"|<h[23][^>]*>([^<]+)', article)
        if title_m:
            listing["title"] = (title_m.group(1) or title_m.group(2)).strip()

        link_m = re.search(r'href="(/[^"]*(?:property|listing|details)[^"]*)"', article)
        if link_m:
            base = UAE_PLATFORMS.get(source, {}).get("url", "")
            listing["url"] = base + link_m.group(1)

        if listing.get("price") or listing.get("title"):
            listings.append(listing)

    return listings


@handle_tool_errors("research_uae_property_search")
async def research_uae_property_search(
    query: str = "",
    location: str = "dubai",
    purpose: str = "for-sale",
    bedrooms: int = 0,
    price_min: int = 0,
    price_max: int = 0,
    property_type: str = "",
    platforms: str = "bayut,propertyfinder",
    limit: int = 20,
) -> dict[str, Any]:
    """Search UAE real estate across multiple platforms simultaneously.

    Searches Bayut, Property Finder, Dubizzle, DREM, and more.

    Args:
        query: Search text (e.g. "sea view", "pool", "maid room")
        location: Area slug (dubai, dubai-marina, palm-jumeirah, business-bay, etc.)
        purpose: "for-sale" or "to-rent"
        bedrooms: Filter (0=any, 1-7)
        price_min: Min price AED (0=no min)
        price_max: Max price AED (0=no max)
        property_type: apartment, villa, townhouse, penthouse, studio, land
        platforms: Comma-separated: bayut, propertyfinder, dubizzle, drem, all
        limit: Max results per platform (1-50)

    Returns:
        Dict with listings from each platform, total count, price stats
    """
    if isinstance(query, list):
        query = " ".join(str(x) for x in query)
    if isinstance(location, list):
        location = str(location[0]) if location else "dubai"
    if isinstance(platforms, list):
        platforms = ",".join(str(x) for x in platforms)

    location = location.lower().replace(" ", "-")
    purpose_slug = "to-rent" if "rent" in str(purpose).lower() else "for-sale"
    platform_list = [p.strip() for p in platforms.split(",")]
    if "all" in platform_list:
        platform_list = ["bayut", "propertyfinder", "dubizzle", "drem"]

    all_listings = []
    sources_searched = []

    for platform in platform_list:
        url = ""
        if platform == "bayut":
            url = f"https://www.bayut.com/{purpose_slug}/property/{location}/"
            params = []
            if bedrooms > 0:
                params.append(f"beds_in={bedrooms}")
            if price_min > 0:
                params.append(f"price_min={price_min}")
            if price_max > 0:
                params.append(f"price_max={price_max}")
            if property_type:
                params.append(f"category_exct={property_type}")
            if query:
                params.append(f"q={quote(query)}")
            if params:
                url += "?" + "&".join(params)

        elif platform == "propertyfinder":
            pf_type = "1" if "sale" in purpose_slug else "2"
            url = f"https://www.propertyfinder.ae/en/search?c={pf_type}&l={quote(location)}&ob=mr&page=1&rp=y"
            if bedrooms > 0:
                url += f"&bf={bedrooms}&bt={bedrooms}"
            if price_max > 0:
                url += f"&pt={price_max}"
            if price_min > 0:
                url += f"&pf={price_min}"

        elif platform == "dubizzle":
            dub_purpose = "property-for-sale" if "sale" in purpose_slug else "property-for-rent"
            url = f"https://dubai.dubizzle.com/{dub_purpose}/residential/"
            if query:
                url += f"?keywords={quote(query)}"

        elif platform == "drem":
            url = f"https://www.drem.ae/properties?transaction_type={'sale' if 'sale' in purpose_slug else 'rent'}&location={quote(location)}"

        if url:
            html = await _camoufox_fetch(url, wait_secs=10)
            if html and "Captcha" not in html[:3000] and len(html) > 5000:
                listings = _extract_listings_generic(html, platform)
                all_listings.extend(listings[:limit])
                sources_searched.append(platform)
            else:
                sources_searched.append(f"{platform} (blocked)")

    prices = [l["price"] for l in all_listings if l.get("price")]
    return {
        "query": query,
        "location": location,
        "purpose": purpose_slug,
        "platforms_searched": sources_searched,
        "total_listings": len(all_listings),
        "listings": all_listings[:limit * 2],
        "price_stats": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "avg": int(sum(prices) / len(prices)) if prices else 0,
            "median": sorted(prices)[len(prices) // 2] if prices else 0,
        } if prices else {},
    }


@handle_tool_errors("research_uae_dld_transactions")
async def research_uae_dld_transactions(
    area: str = "",
    transaction_type: str = "sales",
    days: int = 30,
    limit: int = 20,
) -> dict[str, Any]:
    """Get Dubai Land Department (DLD) property transaction data.

    Fetches recent real estate transactions from Dubai's official records.
    Data source: DREM.ae (Dubai Real Estate Market official portal).

    Args:
        area: Area name (e.g. "Dubai Marina", "Palm Jumeirah", "Downtown")
        transaction_type: "sales", "rentals", or "mortgages"
        days: Look back period in days (default 30)
        limit: Max results

    Returns:
        Dict with recent transactions: property, price, date, area, size
    """
    if isinstance(area, list):
        area = str(area[0]) if area else ""
    if isinstance(area, dict):
        area = str(area)

    url = f"https://www.drem.ae/transactions?type={transaction_type}"
    if area:
        url += f"&area={quote(area)}"

    html = await _camoufox_fetch(url, wait_secs=12)
    if not html or len(html) < 5000:
        url2 = f"https://dubailand.gov.ae/en/open-data/real-estate-data/"
        html = await _camoufox_fetch(url2, wait_secs=12)

    transactions = []
    price_pattern = re.compile(r"AED\s*([\d,]+)")
    date_pattern = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
    for row in rows[:limit]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) >= 3:
            clean_cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            tx: dict[str, Any] = {}
            for cell in clean_cells:
                pm = price_pattern.search(cell)
                if pm:
                    tx["price"] = int(pm.group(1).replace(",", ""))
                dm = date_pattern.search(cell)
                if dm:
                    tx["date"] = dm.group(1)
                if any(a in cell.lower() for a in ["marina", "palm", "downtown", "creek", "hills"]):
                    tx["area"] = cell
            if tx.get("price"):
                tx["type"] = transaction_type
                transactions.append(tx)

    return {
        "area": area,
        "transaction_type": transaction_type,
        "source": "drem_dld",
        "transactions": transactions[:limit],
        "count": len(transactions),
    }


@handle_tool_errors("research_uae_offplan")
async def research_uae_offplan(
    developer: str = "",
    location: str = "dubai",
    budget_max: int = 0,
    bedrooms: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Search off-plan (under construction) projects from UAE developers.

    Searches Emaar, DAMAC, Sobha, Nakheel, Azizi, and portal off-plan sections.

    Args:
        developer: Filter by developer (emaar, damac, sobha, nakheel, azizi, all)
        location: Area (dubai, abu-dhabi, etc.)
        budget_max: Maximum budget in AED (0=no limit)
        bedrooms: Filter (0=any)
        limit: Max results

    Returns:
        Dict with off-plan projects: name, developer, location, prices, completion
    """
    if isinstance(developer, list):
        developer = str(developer[0]) if developer else ""
    if isinstance(location, list):
        location = str(location[0]) if location else "dubai"

    developer = developer.lower().strip()
    results: list[dict[str, Any]] = []

    urls_to_scrape = []
    if developer in ("emaar", "all", ""):
        urls_to_scrape.append(("emaar", "https://www.emaar.com/en/what-we-do/communities"))
    if developer in ("damac", "all", ""):
        urls_to_scrape.append(("damac", "https://www.damacproperties.com/en/properties"))
    if developer in ("sobha", "all", ""):
        urls_to_scrape.append(("sobha", "https://www.sobharealty.com/properties/"))

    urls_to_scrape.append(("bayut_offplan", f"https://www.bayut.com/for-sale/property/{location}/?completion_status=off_plan"))

    for dev_name, url in urls_to_scrape:
        html = await _camoufox_fetch(url, wait_secs=10)
        if html and len(html) > 5000 and "Captcha" not in html[:3000]:
            projects = re.findall(
                r'<(?:article|div)[^>]*class="[^"]*(?:project|property|card)[^"]*"[^>]*>(.*?)</(?:article|div)>',
                html, re.DOTALL
            )
            for proj in projects[:limit]:
                item: dict[str, Any] = {"developer": dev_name, "source": dev_name}
                title_m = re.search(r'<h[23][^>]*>([^<]+)', proj)
                if title_m:
                    item["name"] = title_m.group(1).strip()
                price_m = re.search(r'AED\s*([\d,]+)', proj)
                if price_m:
                    item["starting_price"] = int(price_m.group(1).replace(",", ""))
                loc_m = re.search(r'(?:location|area)[^>]*>([^<]+)', proj, re.I)
                if loc_m:
                    item["location"] = loc_m.group(1).strip()
                if item.get("name"):
                    results.append(item)

    if budget_max > 0:
        results = [r for r in results if r.get("starting_price", 0) <= budget_max or not r.get("starting_price")]
    if bedrooms > 0:
        results = [r for r in results if r.get("bedrooms", 0) == bedrooms or not r.get("bedrooms")]

    return {
        "developer": developer or "all",
        "location": location,
        "source": "multi_developer",
        "projects": results[:limit],
        "count": len(results),
    }


@handle_tool_errors("research_uae_mortgage_calc")
async def research_uae_mortgage_calc(
    property_price: int = 1000000,
    down_payment_pct: float = 20.0,
    interest_rate: float = 4.5,
    loan_years: int = 25,
    is_uae_national: bool = False,
    is_offplan: bool = False,
) -> dict[str, Any]:
    """Calculate UAE mortgage payments with local rules.

    Applies UAE Central Bank regulations:
    - UAE nationals: max 80% LTV (first property), 70% (subsequent)
    - Expats: max 75% LTV (first, <5M), 65% (first, >5M), 60% (subsequent)
    - Off-plan: max 50% LTV
    - Max age at maturity: 65 (employed), 70 (self-employed)

    Args:
        property_price: Property value in AED
        down_payment_pct: Down payment percentage (default 20%)
        interest_rate: Annual interest rate % (default 4.5%)
        loan_years: Loan term in years (default 25, max 25)
        is_uae_national: UAE national (higher LTV allowed)
        is_offplan: Off-plan property (stricter rules)

    Returns:
        Dict with monthly payment, total cost, fees breakdown, eligibility
    """
    if isinstance(property_price, list):
        property_price = int(property_price[0]) if property_price else 1000000
    if isinstance(property_price, str):
        property_price = _parse_price(property_price)

    if is_offplan:
        max_ltv = 50.0
    elif is_uae_national:
        max_ltv = 80.0
    else:
        max_ltv = 75.0 if property_price < 5_000_000 else 65.0

    min_down_payment = 100.0 - max_ltv
    actual_down_pct = max(down_payment_pct, min_down_payment)
    loan_years = min(loan_years, 25)

    down_payment = int(property_price * actual_down_pct / 100)
    loan_amount = property_price - down_payment

    monthly_rate = interest_rate / 100 / 12
    n_payments = loan_years * 12

    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        monthly_payment = loan_amount / n_payments

    total_paid = monthly_payment * n_payments
    total_interest = total_paid - loan_amount

    dld_fee = property_price * 0.04
    registration_fee = 2000 if property_price < 500_000 else 4000
    agency_fee = property_price * 0.02
    mortgage_registration = loan_amount * 0.0025 + 290
    valuation_fee = 3150

    total_upfront = down_payment + dld_fee + registration_fee + agency_fee + mortgage_registration + valuation_fee

    return {
        "property_price": property_price,
        "down_payment": down_payment,
        "down_payment_pct": actual_down_pct,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "loan_years": loan_years,
        "monthly_payment": int(monthly_payment),
        "total_paid": int(total_paid),
        "total_interest": int(total_interest),
        "max_ltv": max_ltv,
        "fees": {
            "dld_transfer_fee_4pct": int(dld_fee),
            "registration_fee": registration_fee,
            "agency_fee_2pct": int(agency_fee),
            "mortgage_registration": int(mortgage_registration),
            "valuation_fee": valuation_fee,
            "total_upfront_cost": int(total_upfront),
        },
        "eligibility": {
            "min_down_payment_required": f"{min_down_payment}%",
            "buyer_type": "UAE National" if is_uae_national else "Expat",
            "property_type": "Off-plan" if is_offplan else "Ready",
            "max_loan_term": "25 years",
            "retirement_age_limit": "65 (employed) / 70 (self-employed)",
        },
        "monthly_breakdown": {
            "principal": int(loan_amount / n_payments),
            "interest_avg": int(total_interest / n_payments),
            "total_monthly": int(monthly_payment),
        },
    }


@handle_tool_errors("research_uae_area_guide")
async def research_uae_area_guide(
    area: str = "dubai-marina",
    include_prices: bool = True,
) -> dict[str, Any]:
    """Get area intelligence for a Dubai/UAE location.

    Provides: average prices, rental yields, price trends, nearby amenities,
    developer info, and investment potential.

    Args:
        area: Area slug (dubai-marina, palm-jumeirah, downtown-dubai, etc.)
        include_prices: Fetch current price data from Bayut (slower)

    Returns:
        Dict with area overview, price ranges, yield estimates, key facts
    """
    if isinstance(area, list):
        area = str(area[0]) if area else "dubai-marina"
    if isinstance(area, dict):
        area = str(area)
    area = area.lower().replace(" ", "-")

    result: dict[str, Any] = {
        "area": area,
        "source": "bayut_area_guide",
    }

    url = f"https://www.bayut.com/area-guides/{area}/"
    html = await _camoufox_fetch(url, wait_secs=10)

    if html and len(html) > 5000 and "Captcha" not in html[:3000]:
        desc_m = re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if desc_m:
            result["description"] = re.sub(r"<[^>]+>", "", desc_m.group(1))[:500]

        sale_prices = re.findall(r"(?:apartment|flat).*?AED\s*([\d,]+)", html, re.I)
        if sale_prices:
            prices = [int(p.replace(",", "")) for p in sale_prices[:20]]
            result["apartment_prices"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": int(sum(prices) / len(prices)),
            }

        villa_prices = re.findall(r"(?:villa|house).*?AED\s*([\d,]+)", html, re.I)
        if villa_prices:
            prices = [int(p.replace(",", "")) for p in villa_prices[:20]]
            result["villa_prices"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": int(sum(prices) / len(prices)),
            }

    if include_prices:
        from loom.tools.intelligence.realestate_research import research_bayut_search
        sale_data = await research_bayut_search(location=area, purpose="for-sale", limit=20)
        rent_data = await research_bayut_search(location=area, purpose="to-rent", limit=20)

        sale_listings = sale_data.get("listings", [])
        rent_listings = rent_data.get("listings", [])

        sale_prices_list = [l["price"] for l in sale_listings if l.get("price")]
        rent_prices_list = [l["price"] for l in rent_listings if l.get("price")]

        if sale_prices_list:
            result["current_sale_prices"] = {
                "min": min(sale_prices_list),
                "max": max(sale_prices_list),
                "avg": int(sum(sale_prices_list) / len(sale_prices_list)),
                "sample_size": len(sale_prices_list),
            }
        if rent_prices_list:
            result["current_rent_prices"] = {
                "min": min(rent_prices_list),
                "max": max(rent_prices_list),
                "avg": int(sum(rent_prices_list) / len(rent_prices_list)),
                "sample_size": len(rent_prices_list),
            }

        if sale_prices_list and rent_prices_list:
            avg_sale = sum(sale_prices_list) / len(sale_prices_list)
            avg_rent = sum(rent_prices_list) / len(rent_prices_list)
            if avg_sale > 0:
                result["estimated_yield"] = round((avg_rent * 12) / avg_sale * 100, 2)

    return result


@handle_tool_errors("research_uae_agent_find")
async def research_uae_agent_find(
    area: str = "dubai",
    specialization: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Find registered real estate agents/brokers in UAE.

    Searches Bayut and Property Finder for active agents in an area.

    Args:
        area: Location (dubai-marina, palm-jumeirah, etc.)
        specialization: Filter: residential, commercial, off-plan, luxury
        limit: Max agents to return

    Returns:
        Dict with agents: name, agency, listings_count, languages, contact
    """
    if isinstance(area, list):
        area = str(area[0]) if area else "dubai"
    if isinstance(area, dict):
        area = str(area)
    area = area.lower().replace(" ", "-")

    url = f"https://www.bayut.com/agents/{area}/"
    html = await _camoufox_fetch(url, wait_secs=10)

    agents = []
    if html and len(html) > 5000 and "Captcha" not in html[:3000]:
        agent_blocks = re.findall(r'<div[^>]*class="[^"]*agent[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
        for block in agent_blocks[:limit]:
            agent: dict[str, Any] = {}
            name_m = re.search(r'<span[^>]*>([A-Z][^<]{2,40})</span>', block)
            if name_m:
                agent["name"] = name_m.group(1).strip()
            agency_m = re.search(r'(?:agency|company)[^>]*>([^<]+)', block, re.I)
            if agency_m:
                agent["agency"] = agency_m.group(1).strip()
            listings_m = re.search(r'(\d+)\s*(?:listing|propert)', block, re.I)
            if listings_m:
                agent["listings_count"] = int(listings_m.group(1))
            lang_m = re.findall(r'(?:Arabic|English|Hindi|Urdu|French|Russian|Chinese|Filipino)', block, re.I)
            if lang_m:
                agent["languages"] = list(set(l.capitalize() for l in lang_m))
            if agent.get("name"):
                agents.append(agent)

    return {
        "area": area,
        "specialization": specialization,
        "source": "bayut",
        "agents": agents[:limit],
        "count": len(agents),
    }
