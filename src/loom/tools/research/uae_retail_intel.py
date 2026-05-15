"""UAE retail price intelligence tools for supermarket sourcing.

Tools for finding cheapest wholesale/retail suppliers in UAE emirates
(Dubai, Sharjah, Ajman, UAQ) for supermarket inventory optimization.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.llm_client import query_llm
except ImportError:
    query_llm = None

try:
    from loom.tools.core.fetch import research_fetch
except ImportError:
    research_fetch = None

try:
    from loom.tools.core.search import research_search
except ImportError:
    research_search = None

logger = logging.getLogger("loom.tools.uae_retail_intel")

UAE_WHOLESALE_MARKETS = {
    "dubai": [
        {"name": "Dubai Waterfront Market (Deira)", "type": "wholesale", "categories": ["vegetables", "fruits", "fish", "meat"], "distance_from_ajman_km": 25},
        {"name": "Al Aweer Market (Dubai)", "type": "wholesale", "categories": ["vegetables", "fruits"], "distance_from_ajman_km": 45},
        {"name": "Dragon Mart", "type": "wholesale", "categories": ["household", "stationery", "electronics", "packaging"], "distance_from_ajman_km": 35},
        {"name": "Deira Spice Souk", "type": "wholesale", "categories": ["spices", "dry_goods", "nuts"], "distance_from_ajman_km": 22},
        {"name": "Al Ras Wholesale (Naif)", "type": "wholesale", "categories": ["fmcg", "snacks", "beverages", "canned"], "distance_from_ajman_km": 20},
        {"name": "Al Khaleej Hypermarket Wholesale", "type": "cash_carry", "categories": ["grocery", "beverages", "snacks"], "distance_from_ajman_km": 18},
        {"name": "West Zone Wholesale", "type": "cash_carry", "categories": ["grocery", "frozen", "dairy"], "distance_from_ajman_km": 22},
        {"name": "Baniyas Square Wholesale Area", "type": "wholesale", "categories": ["rice", "oil", "flour", "sugar", "pulses"], "distance_from_ajman_km": 20},
    ],
    "sharjah": [
        {"name": "Sharjah Fruit & Vegetable Market", "type": "wholesale", "categories": ["vegetables", "fruits"], "distance_from_ajman_km": 8},
        {"name": "Industrial Area 1-6 Wholesale", "type": "wholesale", "categories": ["fmcg", "rice", "oil", "pulses"], "distance_from_ajman_km": 12},
        {"name": "Sharjah Cooperative Society", "type": "cooperative", "categories": ["grocery", "dairy", "frozen", "fresh"], "distance_from_ajman_km": 10},
        {"name": "Al Jubail Market Sharjah", "type": "wholesale", "categories": ["fish", "meat", "vegetables"], "distance_from_ajman_km": 15},
        {"name": "National Paints Roundabout Warehouses", "type": "warehouse", "categories": ["beverages", "snacks", "canned", "cleaning"], "distance_from_ajman_km": 10},
    ],
    "ajman": [
        {"name": "Ajman China Mall", "type": "wholesale", "categories": ["household", "stationery", "packaging"], "distance_from_ajman_km": 3},
        {"name": "Ajman Market (Souk)", "type": "retail_wholesale", "categories": ["vegetables", "fruits", "spices"], "distance_from_ajman_km": 2},
        {"name": "Al Jurf Industrial Area", "type": "warehouse", "categories": ["fmcg", "beverages", "snacks"], "distance_from_ajman_km": 8},
    ],
    "umm_al_quwain": [
        {"name": "UAQ Free Zone Warehouses", "type": "warehouse", "categories": ["dry_goods", "beverages", "canned"], "distance_from_ajman_km": 20},
        {"name": "Barracuda Market UAQ", "type": "wholesale", "categories": ["fish", "seafood"], "distance_from_ajman_km": 22},
    ],
}

UAE_DISTRIBUTORS = [
    {"name": "Al Islami Foods", "categories": ["frozen_chicken", "meat", "ready_meals"], "min_order_aed": 500, "delivery": True},
    {"name": "Agthia (Al Ain Water, Grand Mills)", "categories": ["water", "flour", "animal_feed"], "min_order_aed": 1000, "delivery": True},
    {"name": "Unilever Gulf (Lipton, Knorr, Lux)", "categories": ["tea", "soups", "personal_care"], "min_order_aed": 2000, "delivery": True},
    {"name": "Al Rawabi Dairy", "categories": ["milk", "laban", "juice", "yogurt"], "min_order_aed": 300, "delivery": True},
    {"name": "National Food Industries", "categories": ["chips", "snacks", "biscuits"], "min_order_aed": 500, "delivery": True},
    {"name": "Shan Foods Distributor", "categories": ["spices", "masala", "recipe_mixes"], "min_order_aed": 300, "delivery": True},
    {"name": "MDH/Everest Spices Distributor", "categories": ["spices", "masala"], "min_order_aed": 500, "delivery": True},
    {"name": "Pepsi/Coca-Cola Distributor", "categories": ["beverages", "soft_drinks", "water"], "min_order_aed": 1000, "delivery": True},
    {"name": "Al Ain Farms", "categories": ["dairy", "poultry", "eggs"], "min_order_aed": 200, "delivery": True},
    {"name": "IFFCO (Noor Oil, Tiffany)", "categories": ["cooking_oil", "biscuits", "frozen"], "min_order_aed": 1000, "delivery": True},
    {"name": "Arla Foods (Puck, Lurpak)", "categories": ["cheese", "butter", "cream"], "min_order_aed": 500, "delivery": True},
    {"name": "Hayat Kimya (Molfix, Papia)", "categories": ["diapers", "tissue", "cleaning"], "min_order_aed": 800, "delivery": True},
]

CATEGORY_ALIASES = {
    "vegetables": ["vegetables", "veggies", "fresh produce", "sabzi", "khodrawat"],
    "fruits": ["fruits", "fresh fruits", "fawakeh"],
    "rice": ["rice", "basmati", "chawal", "arz"],
    "oil": ["cooking oil", "vegetable oil", "sunflower oil", "zait"],
    "spices": ["spices", "masala", "baharat", "shan", "mdh"],
    "dairy": ["milk", "laban", "yogurt", "cheese", "dairy", "halib"],
    "frozen": ["frozen food", "frozen chicken", "frozen vegetables"],
    "snacks": ["chips", "biscuits", "snacks", "namkeen", "wafers"],
    "beverages": ["drinks", "juice", "water", "soft drinks", "mashroobat"],
    "cleaning": ["cleaning", "detergent", "soap", "tissue"],
    "eggs": ["eggs", "bayd", "anda"],
    "bread": ["bread", "paratha", "roti", "khubz"],
    "pulses": ["dal", "lentils", "chickpeas", "beans", "hububat"],
    "flour": ["atta", "flour", "maida", "daqiq"],
    "meat": ["meat", "chicken", "lahm", "dajaj", "gosht"],
    "glycerin": ["glycerin", "glycerine", "glycerol", "soap base"],
}


@handle_tool_errors("research_uae_price_compare")
async def research_uae_price_compare(
    product: str,
    category: str = "",
    max_distance_km: int = 30,
    include_online: bool = True,
) -> dict[str, Any]:
    """Find cheapest sources for a product/category across UAE markets near Ajman.

    Searches wholesale markets, distributors, and online platforms for the
    best prices on specific products or product categories.

    Args:
        product: Product name or description (e.g., "basmati rice 5kg", "onions", "glycerin")
        category: Category filter (vegetables, rice, oil, spices, dairy, etc.)
        max_distance_km: Maximum distance from Ajman center (default 30km)
        include_online: Include online wholesale platforms in results

    Returns:
        Dict with sourcing recommendations, nearby markets, distributors,
        and estimated price ranges.
    """
    resolved_category = _resolve_category(product, category)

    nearby_markets = []
    for emirate, markets in UAE_WHOLESALE_MARKETS.items():
        for market in markets:
            if market["distance_from_ajman_km"] <= max_distance_km:
                if not resolved_category or any(
                    cat in market["categories"] for cat in _expand_category(resolved_category)
                ):
                    nearby_markets.append({
                        **market,
                        "emirate": emirate,
                    })

    nearby_markets.sort(key=lambda m: m["distance_from_ajman_km"])

    relevant_distributors = []
    for dist in UAE_DISTRIBUTORS:
        if not resolved_category or any(
            cat in dist["categories"] for cat in _expand_category(resolved_category)
        ):
            relevant_distributors.append(dist)

    online_sources = []
    if include_online:
        online_sources = _get_online_sources(product, resolved_category)

    sourcing_tips = _get_sourcing_tips(product, resolved_category)

    result = {
        "product": product,
        "category": resolved_category,
        "base_location": "Ajman, Liwara 1",
        "max_distance_km": max_distance_km,
        "nearby_markets": nearby_markets[:10],
        "distributors": relevant_distributors[:8],
        "online_platforms": online_sources,
        "sourcing_tips": sourcing_tips,
        "total_options": len(nearby_markets) + len(relevant_distributors) + len(online_sources),
    }

    if query_llm:
        try:
            llm_result = await query_llm(
                f"You are a UAE retail sourcing expert. For a supermarket in Ajman targeting all communities "
                f"(Arab, South Asian, Filipino, African — maximize profit by serving everyone), "
                f"recommend the cheapest places to buy '{product}' (category: {resolved_category}). "
                f"Focus on wholesale markets within 30km of Ajman. Include estimated price ranges in AED. "
                f"Consider: Dubai Waterfront Market, Sharjah Fruit Market, Naif wholesale area, "
                f"Industrial Area distributors. Be specific with market names and areas.",
                system="You are a UAE retail supply chain expert. Focus on maximizing profit margins for supermarkets serving diverse communities in the Northern Emirates.",
                temperature=0.3,
                max_tokens=800,
            )
            if llm_result.get("text"):
                result["ai_recommendation"] = llm_result["text"]
        except Exception:
            pass

    return result


@handle_tool_errors("research_uae_wholesale_markets")
async def research_uae_wholesale_markets(
    category: str = "",
    emirate: str = "",
    max_distance_km: int = 50,
) -> dict[str, Any]:
    """List wholesale markets near Ajman filtered by category and emirate.

    Args:
        category: Filter by product category (vegetables, spices, fmcg, etc.)
        emirate: Filter by emirate (dubai, sharjah, ajman, umm_al_quwain)
        max_distance_km: Maximum distance from Ajman (default 50km)

    Returns:
        Dict with markets list sorted by distance, with categories and types.
    """
    results = []
    for emi, markets in UAE_WHOLESALE_MARKETS.items():
        if emirate and emi != emirate.lower().replace(" ", "_"):
            continue
        for market in markets:
            if market["distance_from_ajman_km"] > max_distance_km:
                continue
            if category:
                expanded = _expand_category(category)
                if not any(cat in market["categories"] for cat in expanded):
                    continue
            results.append({**market, "emirate": emi})

    results.sort(key=lambda m: m["distance_from_ajman_km"])

    return {
        "base_location": "Ajman, Liwara 1",
        "category_filter": category or "all",
        "emirate_filter": emirate or "all",
        "max_distance_km": max_distance_km,
        "markets": results,
        "total": len(results),
    }


@handle_tool_errors("research_uae_distributor_find")
async def research_uae_distributor_find(
    product: str = "",
    category: str = "",
    max_order_aed: int = 5000,
    delivery_required: bool = True,
) -> dict[str, Any]:
    """Find UAE distributors that deliver to Ajman for specific products.

    Args:
        product: Specific product (e.g., "Shan masala", "Noor oil")
        category: Category (spices, dairy, beverages, etc.)
        max_order_aed: Maximum minimum order amount willing to commit
        delivery_required: Only show distributors that deliver to Ajman

    Returns:
        Dict with matching distributors, contact info hints, and order requirements.
    """
    resolved = _resolve_category(product, category)
    matches = []

    for dist in UAE_DISTRIBUTORS:
        if delivery_required and not dist["delivery"]:
            continue
        if dist["min_order_aed"] > max_order_aed:
            continue
        if resolved:
            expanded = _expand_category(resolved)
            if not any(cat in dist["categories"] for cat in expanded):
                continue
        matches.append(dist)

    matches.sort(key=lambda d: d["min_order_aed"])

    tips = []
    if resolved in ("spices", "masala"):
        tips.append("For Shan/MDH: contact distributor in Sharjah Industrial Area 5")
        tips.append("Bulk 100-pack boxes give 15-20% better margin than single packs")
    elif resolved in ("dairy", "milk"):
        tips.append("Al Rawabi and Al Ain Farms deliver daily to Ajman")
        tips.append("Minimum order 200-300 AED; fresh milk has 20-25% margin")
    elif resolved in ("vegetables", "fruits"):
        tips.append("Sharjah Fruit & Veg Market opens 4AM — best prices before 7AM")
        tips.append("Buy direct from farmers on Thu/Fri for 30-40% cheaper")

    return {
        "product": product,
        "category": resolved or "all",
        "delivery_to": "Ajman",
        "max_order_aed": max_order_aed,
        "distributors": matches,
        "total": len(matches),
        "sourcing_tips": tips,
    }


@handle_tool_errors("research_uae_price_search")
async def research_uae_price_search(
    product: str,
    compare_platforms: bool = True,
) -> dict[str, Any]:
    """Search online UAE platforms for current retail/wholesale prices.

    Searches Carrefour, Lulu, Union Coop, and wholesale platforms for
    current prices to estimate market rates and find best deals.

    Args:
        product: Product to search (e.g., "India Gate Basmati 5kg", "Noor Oil 1.5L")
        compare_platforms: Compare across multiple platforms

    Returns:
        Dict with price findings from online sources.
    """
    platforms = [
        {"name": "Carrefour UAE", "url": f"https://www.carrefouruae.com/mafuae/en/search?q={product.replace(' ', '+')}", "type": "hypermarket"},
        {"name": "Lulu Hypermarket", "url": f"https://www.luluhypermarket.com/en-ae/search?q={product.replace(' ', '+')}", "type": "hypermarket"},
        {"name": "Union Coop", "url": f"https://www.unioncoop.ae/search?q={product.replace(' ', '+')}", "type": "cooperative"},
        {"name": "Noon Daily", "url": f"https://www.noon.com/uae-en/search/?q={product.replace(' ', '+')}", "type": "online"},
        {"name": "Kibsons (wholesale)", "url": f"https://www.kibsons.com/search?q={product.replace(' ', '+')}", "type": "wholesale_online"},
    ]

    results = []
    if research_fetch:
        for platform in platforms[:3]:
            try:
                fetched = await research_fetch(url=platform["url"], mode="stealthy")
                if fetched and not fetched.get("error"):
                    content = fetched.get("text", fetched.get("content", ""))[:500]
                    results.append({
                        "platform": platform["name"],
                        "type": platform["type"],
                        "url": platform["url"],
                        "snippet": content[:200] if content else "No price data extracted",
                    })
            except Exception as e:
                results.append({
                    "platform": platform["name"],
                    "url": platform["url"],
                    "error": str(e)[:100],
                })

    if not results:
        results = [{"platform": p["name"], "url": p["url"], "type": p["type"], "note": "Visit URL for live prices"} for p in platforms]

    if query_llm:
        try:
            llm_result = await query_llm(
                f"What is the typical retail and wholesale price range in UAE (AED) for: {product}? "
                f"Give specific numbers. Compare: Carrefour price vs wholesale/bulk price vs market price. "
                f"Also suggest if this product is cheaper to buy from specific areas in Dubai/Sharjah.",
                system="You are a UAE grocery pricing expert. Give specific AED prices based on 2025-2026 market knowledge.",
                temperature=0.3,
                max_tokens=500,
            )
            if llm_result.get("text"):
                return {
                    "product": product,
                    "platforms": results,
                    "price_analysis": llm_result["text"],
                    "provider": llm_result.get("provider", ""),
                }
        except Exception:
            pass

    return {
        "product": product,
        "platforms": results,
        "note": "Visit platforms directly for live prices. Wholesale is typically 20-40% cheaper than retail.",
    }


@handle_tool_errors("research_uae_margin_calculator")
async def research_uae_margin_calculator(
    product: str,
    cost_aed: float,
    selling_price_aed: float,
    units_per_week: int = 10,
    wastage_pct: float = 0.0,
) -> dict[str, Any]:
    """Calculate profit margins and weekly profit for a supermarket product.

    Args:
        product: Product name
        cost_aed: Wholesale/purchase cost per unit in AED
        selling_price_aed: Retail selling price per unit in AED
        units_per_week: Expected weekly sales volume
        wastage_pct: Expected wastage percentage (for perishables)

    Returns:
        Dict with margin analysis, weekly/monthly profit, and recommendations.
    """
    gross_margin_pct = ((selling_price_aed - cost_aed) / selling_price_aed) * 100
    net_margin_pct = gross_margin_pct * (1 - wastage_pct / 100)
    profit_per_unit = selling_price_aed - cost_aed
    weekly_revenue = selling_price_aed * units_per_week
    weekly_profit = profit_per_unit * units_per_week * (1 - wastage_pct / 100)
    monthly_profit = weekly_profit * 4.3

    health = "excellent" if net_margin_pct >= 25 else "good" if net_margin_pct >= 15 else "low" if net_margin_pct >= 8 else "critical"

    recommendations = []
    if net_margin_pct < 10:
        recommendations.append("Margin too low for baqala. Consider bulk buying to reduce cost.")
        recommendations.append("Check if Sharjah Industrial Area has cheaper wholesale options.")
    if wastage_pct > 10:
        recommendations.append("High wastage — buy smaller quantities more frequently.")
        recommendations.append("Consider frozen alternatives for perishable items.")
    if units_per_week < 5:
        recommendations.append("Low velocity item — ensure it doesn't occupy premium shelf space.")

    return {
        "product": product,
        "cost_aed": cost_aed,
        "selling_price_aed": selling_price_aed,
        "gross_margin_pct": round(gross_margin_pct, 1),
        "net_margin_pct": round(net_margin_pct, 1),
        "profit_per_unit_aed": round(profit_per_unit, 2),
        "units_per_week": units_per_week,
        "wastage_pct": wastage_pct,
        "weekly_revenue_aed": round(weekly_revenue, 2),
        "weekly_profit_aed": round(weekly_profit, 2),
        "monthly_profit_aed": round(monthly_profit, 2),
        "margin_health": health,
        "recommendations": recommendations,
    }


@handle_tool_errors("research_uae_sourcing_plan")
async def research_uae_sourcing_plan(
    categories: list[str] | None = None,
    budget_aed: float = 5000.0,
    optimize_for: str = "margin",
) -> dict[str, Any]:
    """Generate a weekly sourcing plan for Almahba Supermarket.

    Creates an optimized buying route and schedule across UAE markets
    to minimize costs and maximize margins.

    Args:
        categories: Product categories to source (default: all essentials)
        budget_aed: Weekly sourcing budget in AED
        optimize_for: "margin" (highest profit), "cost" (lowest price), or "distance" (shortest route)

    Returns:
        Dict with day-by-day sourcing schedule, recommended markets, and budget allocation.
    """
    if not categories:
        categories = ["vegetables", "dairy", "rice", "spices", "snacks", "beverages", "eggs", "bread"]

    schedule = {
        "saturday": {
            "markets": ["Sharjah Fruit & Vegetable Market"],
            "categories": ["vegetables", "fruits"],
            "time": "5:00 AM - 7:00 AM",
            "tip": "Arrive early for freshest stock and best wholesale prices. Stock items popular across all communities.",
            "estimated_spend_aed": budget_aed * 0.25,
        },
        "monday": {
            "markets": ["Al Ras Wholesale (Naif)", "Baniyas Square"],
            "categories": ["rice", "oil", "flour", "pulses", "canned"],
            "time": "9:00 AM - 12:00 PM",
            "tip": "Buy staples in bulk (25kg rice, 5L oil). Stock variety for all communities: basmati + Egyptian rice + jasmine.",
            "estimated_spend_aed": budget_aed * 0.30,
        },
        "wednesday": {
            "markets": ["Sharjah Industrial Area", "National Paints Roundabout"],
            "categories": ["beverages", "snacks", "cleaning", "spices"],
            "time": "10:00 AM - 1:00 PM",
            "tip": "Compare 2-3 wholesalers for FMCG. Diversify snack brands for Arab, Asian, Filipino customers.",
            "estimated_spend_aed": budget_aed * 0.25,
        },
        "thursday": {
            "markets": ["Ajman Market", "Ajman China Mall"],
            "categories": ["household", "stationery", "local_produce"],
            "time": "10:00 AM - 12:00 PM",
            "tip": "Local Ajman sourcing. Household items from China Mall have 30-45% margin.",
            "estimated_spend_aed": budget_aed * 0.10,
        },
        "daily_delivery": {
            "distributors": ["Al Rawabi (dairy)", "Al Ain Farms (eggs)", "Bread supplier"],
            "categories": ["milk", "laban", "eggs", "bread"],
            "tip": "Daily delivery orders. Milk/bread are daily trip drivers with high margins.",
            "estimated_spend_aed": budget_aed * 0.10,
        },
    }

    optimization_tips = {
        "margin": [
            "Focus spice purchases at Deira Spice Souk — 25-35% margin on Shan/MDH",
            "Buy stationery/phone accessories at Dragon Mart — 30-45% margin",
            "Fresh produce from Sharjah market gives 20-35% margin vs 5-10% on staples",
        ],
        "cost": [
            "Sharjah markets are 15-20% cheaper than Dubai for vegetables",
            "Cash payments get 3-5% discount at most wholesale markets",
            "Buy near expiry FMCG at 50% off from Naif clearance stores",
        ],
        "distance": [
            "Sharjah Fruit Market is only 8km from Ajman — closest wholesale",
            "Ajman Market + China Mall cover basics without leaving the emirate",
            "Group Dubai trips to one day/week to save fuel costs",
        ],
    }

    return {
        "store": "Almahba Supermarket, Liwara 1, Ajman",
        "weekly_budget_aed": budget_aed,
        "optimize_for": optimize_for,
        "categories_covered": categories,
        "weekly_schedule": schedule,
        "optimization_tips": optimization_tips.get(optimize_for, optimization_tips["margin"]),
        "estimated_fuel_cost_aed": 80 if optimize_for == "distance" else 150,
        "key_principle": "Buy daily drivers (milk, bread, eggs) from distributors; buy margin items (spices, stationery) from wholesale markets.",
    }


def _resolve_category(product: str, category: str) -> str:
    if category:
        return category.lower().strip()
    product_lower = product.lower()
    for cat, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if alias in product_lower:
                return cat
    return ""


def _expand_category(category: str) -> list[str]:
    category = category.lower().strip()
    direct = [category]
    for cat, aliases in CATEGORY_ALIASES.items():
        if category in aliases or category == cat:
            direct.append(cat)
            if cat in ("vegetables", "fruits"):
                direct.append("fresh produce")
            elif cat in ("rice", "flour", "pulses"):
                direct.append("dry_goods")
            elif cat in ("spices",):
                direct.append("dry_goods")
    return list(set(direct))


def _get_online_sources(product: str, category: str) -> list[dict[str, str]]:
    sources = [
        {"name": "Kibsons.com", "type": "wholesale_online", "note": "Fresh produce delivery, good for bulk vegetables/fruits"},
        {"name": "Desertcart.ae", "type": "import", "note": "Hard-to-find imported items"},
        {"name": "Tradeling.com", "type": "b2b_marketplace", "note": "B2B wholesale platform for FMCG"},
        {"name": "Carrefour Business", "type": "cash_carry", "note": "Bulk packs at wholesale prices"},
    ]
    if category in ("vegetables", "fruits"):
        sources.insert(0, {"name": "BarakaBazaar.ae", "type": "wholesale", "note": "Farm-direct vegetables at wholesale"})
    return sources


def _get_sourcing_tips(product: str, category: str) -> list[str]:
    tips = ["Always compare 3+ suppliers before committing to regular orders"]
    if category in ("vegetables", "fruits"):
        tips.extend([
            "Sharjah Fruit Market (8km from Ajman) — cheapest vegetables in Northern Emirates",
            "Buy at 4-6 AM for best selection; prices rise 20% after 9 AM",
            "Thursday/Friday: direct farmer sales at lower prices",
            "Seasonal items (watermelon, mango) have 40-50% margin in peak season",
        ])
    elif category in ("rice", "flour", "pulses", "oil"):
        tips.extend([
            "Baniyas Square (Dubai) — bulk staples at lowest UAE prices",
            "Buy 25kg/50kg bags for maximum discount (15-20% less than 5kg bags)",
            "Repackage into 1kg/2kg portions for 30-40% markup",
        ])
    elif category in ("spices", "masala"):
        tips.extend([
            "Deira Spice Souk — wholesale spices at 50% of supermarket prices",
            "Shan/MDH distributors in Sharjah Industrial Area 5",
            "Small 50g packs have highest margin (25-35%) for baqala",
        ])
    elif category in ("glycerin", "glycerine"):
        tips.extend([
            "Chemical suppliers in Sharjah Industrial Area 3-4",
            "Al Quoz (Dubai) has glycerin/soap base wholesalers",
            "Buy food-grade from Deira pharmachem wholesalers",
            "500ml bottles retail at 8-12 AED; wholesale cost 3-5 AED",
        ])
    elif category in ("dairy", "milk"):
        tips.extend([
            "Al Rawabi delivers daily to Ajman — min order 300 AED",
            "Fresh milk (1L): cost ~3.5 AED, sell at 5-5.5 AED = 30% margin",
            "Laban (1L): cost ~2.5 AED, sell at 4 AED = 37% margin",
        ])
    return tips
