"""Global Price Finder — find ALL prices per country with source URLs.

Given a product, searches multiple countries simultaneously and returns
a structured per-country breakdown of all available prices and store URLs.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.price_global")

_COUNTRY_CONFIG = {
    "uk": {"keywords": "buy uk", "currency": "GBP", "symbol": "£"},
    "uae": {"keywords": "buy uae dubai", "currency": "AED", "symbol": "AED"},
    "us": {"keywords": "buy usa", "currency": "USD", "symbol": "$"},
    "sa": {"keywords": "buy saudi arabia", "currency": "SAR", "symbol": "SAR"},
    "eg": {"keywords": "buy egypt", "currency": "EGP", "symbol": "EGP"},
    "de": {"keywords": "kaufen deutschland", "currency": "EUR", "symbol": "€"},
    "in": {"keywords": "buy india", "currency": "INR", "symbol": "₹"},
}


def _search_country(product: str, country: str) -> list[dict]:
    """Search for product prices in a specific country."""
    from ddgs import DDGS

    cfg = _COUNTRY_CONFIG.get(country, {"keywords": "buy", "currency": "USD", "symbol": "$"})
    query = f"{product} price {cfg['keywords']}"

    try:
        results = DDGS().text(query, max_results=7)
    except Exception:
        return []

    sources = []
    for r in results:
        title = r.get("title", "")
        url = r.get("href", "")
        body = r.get("body", "")
        all_text = title + " " + body

        price_matches = re.findall(
            r"[£$€₹]\s?[\d,]+\.?\d*|[\d,]+\.?\d*\s*(?:AED|GBP|USD|EUR|SAR|EGP|INR)",
            all_text,
        )

        parsed_prices = []
        for pm in price_matches:
            try:
                from price_parser import Price
                p = Price.fromstring(pm)
                if p.amount and float(p.amount) > 50:
                    parsed_prices.append({
                        "amount": float(p.amount),
                        "currency": p.currency or cfg["currency"],
                        "raw": pm,
                    })
            except Exception:
                clean = re.sub(r"[^0-9.]", "", pm.replace(",", ""))
                try:
                    val = float(clean)
                    if val > 50:
                        parsed_prices.append({
                            "amount": val,
                            "currency": cfg["currency"],
                            "raw": pm,
                        })
                except ValueError:
                    pass

        sources.append({
            "store": title[:80],
            "url": url,
            "prices": parsed_prices,
            "country": country,
            "currency": cfg["currency"],
        })

    return sources


@handle_tool_errors("research_price_global")
async def research_price_global(
    product: str,
    countries: list[str] | None = None,
) -> dict[str, Any]:
    """Find ALL available prices for a product across multiple countries.

    Searches each country independently and returns a structured breakdown
    with store names, URLs, and prices per country.

    Args:
        product: Product name/model to search (e.g., "AMD 9975WX 32C/64T").
        countries: List of country codes to search (default: uk, uae, us).
                   Available: uk, uae, us, sa, eg, de, in.

    Returns:
        Dict with product, per-country results (stores + prices + URLs),
        cheapest per country, and global cheapest.
    """
    start = time.time()
    target_countries = countries or ["uk", "uae", "us"]

    all_results: dict[str, list[dict]] = {}

    for country in target_countries:
        country_sources = await asyncio.to_thread(_search_country, product, country)
        all_results[country] = country_sources

    cheapest_per_country = {}
    global_cheapest = None

    for country, sources in all_results.items():
        all_prices = []
        for src in sources:
            for p in src.get("prices", []):
                all_prices.append({
                    "amount": p["amount"],
                    "currency": p["currency"],
                    "store": src["store"],
                    "url": src["url"],
                })

        if all_prices:
            cheapest = min(all_prices, key=lambda x: x["amount"])
            cheapest_per_country[country] = cheapest
            if global_cheapest is None or cheapest["amount"] < global_cheapest["amount"]:
                global_cheapest = {**cheapest, "country": country}

    return {
        "product": product,
        "countries_searched": target_countries,
        "results": all_results,
        "cheapest_per_country": cheapest_per_country,
        "global_cheapest": global_cheapest,
        "total_sources": sum(len(s) for s in all_results.values()),
        "total_prices_found": sum(
            sum(len(src.get("prices", [])) for src in sources)
            for sources in all_results.values()
        ),
        "duration_ms": round((time.time() - start) * 1000),
    }
