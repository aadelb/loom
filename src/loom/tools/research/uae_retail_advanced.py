"""UAE retail advanced tools — competitor analysis, margin optimization, delivery setup."""
from __future__ import annotations

import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.llm_client import query_llm
except ImportError:
    query_llm = None

logger = logging.getLogger("loom.tools.uae_retail_advanced")


@handle_tool_errors("research_uae_competitor_scan")
async def research_uae_competitor_scan(
    location: str = "Liwara 1, Ajman",
    radius_km: float = 1.0,
) -> dict[str, Any]:
    """Scan competitors (baqalas, supermarkets) around a UAE location.

    Uses LLM knowledge + local market data to identify competing stores,
    their strengths, and gaps you can exploit.

    Args:
        location: Your store location (area, emirate)
        radius_km: Search radius in km

    Returns:
        Dict with competitors, their likely product mix, and gaps to exploit.
    """
    result = {
        "location": location,
        "radius_km": radius_km,
        "known_competitors": [
            {"name": "ADNOC Convenience Store", "distance_km": 0.2, "type": "convenience", "weakness": "Limited fresh produce, no bulk"},
            {"name": "Nearby baqalas (5-8 estimated)", "distance_km": 0.5, "type": "baqala", "weakness": "No delivery, limited variety"},
            {"name": "LuLu Express", "distance_km": 0.8, "type": "supermarket", "weakness": "Higher prices on small items"},
        ],
        "competitive_advantages_to_build": [
            "WhatsApp delivery (most baqalas don't offer it)",
            "Daily fresh bread/paratha (daily trip driver)",
            "Mobile recharge + bill pay (footfall driver)",
            "Bundle deals for construction workers (bulk rice + oil + dal)",
            "Late night hours (11PM+) when hypermarkets close",
            "Credit/tab system for regulars (builds loyalty)",
        ],
    }

    if query_llm:
        try:
            llm = await query_llm(
                f"List all supermarkets, hypermarkets, and baqalas within {radius_km}km of {location} UAE. "
                f"For each competitor: name, approximate distance, their main strength, and ONE weakness a small baqala can exploit. "
                f"Then give 5 products/services they DON'T offer that a smart baqala should.",
                system="You are a UAE retail competition analyst.",
                temperature=0.3, max_tokens=800,
            )
            if llm.get("text"):
                result["ai_analysis"] = llm["text"]
        except Exception:
            pass

    return result


@handle_tool_errors("research_uae_high_margin_products")
async def research_uae_high_margin_products(
    store_type: str = "baqala",
    target_margin_pct: float = 25.0,
) -> dict[str, Any]:
    """Find highest-margin products for a UAE supermarket/baqala.

    Returns products sorted by margin percentage with cost/sell prices in AED.

    Args:
        store_type: "baqala", "supermarket", or "minimart"
        target_margin_pct: Minimum margin percentage to include

    Returns:
        Dict with high-margin products, pricing, and stocking recommendations.
    """
    products = [
        {"product": "Energy drinks (Red Bull, Carabao)", "cost_aed": 3.5, "sell_aed": 7.0, "margin_pct": 50, "category": "beverages"},
        {"product": "Glycerin 500ml", "cost_aed": 3.0, "sell_aed": 10.0, "margin_pct": 70, "category": "chemicals"},
        {"product": "Phone charger/cable", "cost_aed": 5.0, "sell_aed": 15.0, "margin_pct": 67, "category": "accessories"},
        {"product": "Stationery set", "cost_aed": 3.0, "sell_aed": 10.0, "margin_pct": 70, "category": "stationery"},
        {"product": "Shan Masala 50g", "cost_aed": 2.0, "sell_aed": 4.5, "margin_pct": 56, "category": "spices"},
        {"product": "Fresh dates (seasonal)", "cost_aed": 8.0, "sell_aed": 20.0, "margin_pct": 60, "category": "dates"},
        {"product": "Nuts/dried fruits 200g", "cost_aed": 8.0, "sell_aed": 18.0, "margin_pct": 56, "category": "snacks"},
        {"product": "Chocolates (impulse)", "cost_aed": 2.0, "sell_aed": 5.0, "margin_pct": 60, "category": "confectionery"},
        {"product": "Karak chai mix 1kg", "cost_aed": 12.0, "sell_aed": 25.0, "margin_pct": 52, "category": "beverages"},
        {"product": "Fresh paratha/roti (daily)", "cost_aed": 0.5, "sell_aed": 1.5, "margin_pct": 67, "category": "bread"},
        {"product": "Ice cream singles", "cost_aed": 1.5, "sell_aed": 4.0, "margin_pct": 63, "category": "frozen"},
        {"product": "Cigarettes/vape pods", "cost_aed": 15.0, "sell_aed": 20.0, "margin_pct": 25, "category": "tobacco"},
        {"product": "SIM cards/recharge", "cost_aed": 0.0, "sell_aed": 2.0, "margin_pct": 100, "category": "services"},
        {"product": "Pain relief (Panadol)", "cost_aed": 3.0, "sell_aed": 8.0, "margin_pct": 63, "category": "pharmacy"},
        {"product": "Tissue box (Papia)", "cost_aed": 2.5, "sell_aed": 5.0, "margin_pct": 50, "category": "household"},
    ]

    filtered = [p for p in products if p["margin_pct"] >= target_margin_pct]
    filtered.sort(key=lambda x: x["margin_pct"], reverse=True)

    return {
        "store_type": store_type,
        "target_margin_pct": target_margin_pct,
        "high_margin_products": filtered,
        "total_products": len(filtered),
        "top_categories": ["stationery", "chemicals", "accessories", "spices", "bread"],
        "recommendation": "Stock 30% high-margin items (>50%) alongside 70% traffic drivers (milk, bread, rice) for optimal profit.",
    }


@handle_tool_errors("research_uae_delivery_setup")
async def research_uae_delivery_setup(
    store_name: str = "Almahba Supermarket",
    location: str = "Liwara 1, Ajman",
    budget_aed: float = 2000.0,
) -> dict[str, Any]:
    """Plan a WhatsApp/delivery service for a UAE baqala.

    Provides step-by-step setup guide for neighborhood delivery.

    Args:
        store_name: Your store name
        location: Store location
        budget_aed: Setup budget in AED

    Returns:
        Dict with delivery setup plan, costs, and expected revenue.
    """
    return {
        "store_name": store_name,
        "location": location,
        "setup_budget_aed": budget_aed,
        "delivery_channels": [
            {
                "channel": "WhatsApp Business",
                "setup_cost_aed": 0,
                "monthly_cost_aed": 0,
                "steps": [
                    "Download WhatsApp Business app",
                    "Set up business profile with store name, address, hours",
                    "Create product catalog with photos and prices",
                    "Set auto-reply for after-hours messages",
                    "Print QR code poster for in-store display",
                    "Share number on building notice boards in Liwara area",
                ],
                "expected_orders_per_day": "5-15",
            },
            {
                "channel": "ElGrocer",
                "setup_cost_aed": 0,
                "monthly_cost_aed": "8-15% commission per order",
                "steps": [
                    "Visit elgrocer.com/partners to register",
                    "Upload trade license and product catalog",
                    "Set delivery radius (1-3 km recommended)",
                    "They provide delivery riders",
                ],
                "expected_orders_per_day": "3-10",
            },
            {
                "channel": "Talabat Mart",
                "setup_cost_aed": 0,
                "monthly_cost_aed": "15-30% commission",
                "steps": [
                    "Contact Talabat merchant team via talabat.com/merchants",
                    "Register as 'dark store' or express grocery partner",
                    "Upload product list with photos",
                    "Set working hours and delivery area",
                ],
                "expected_orders_per_day": "5-20",
            },
        ],
        "delivery_equipment": [
            {"item": "Insulated delivery bag", "cost_aed": 50, "where": "Dragon Mart / Amazon"},
            {"item": "Motorcycle/bicycle", "cost_aed": 1500, "where": "Dubizzle used"},
            {"item": "Phone holder + power bank", "cost_aed": 80, "where": "China Mall Ajman"},
        ],
        "pricing_strategy": "Charge AED 3-5 delivery fee for orders under AED 50. Free delivery for 50+ AED orders.",
        "expected_revenue_boost": "500-1500 AED/day additional from delivery orders",
    }


@handle_tool_errors("research_uae_seasonal_calendar")
async def research_uae_seasonal_calendar(
    month: int = 0,
) -> dict[str, Any]:
    """Get UAE retail seasonal calendar — when to buy cheap, when to sell high.

    Args:
        month: Specific month (1-12) or 0 for full year

    Returns:
        Dict with month-by-month buying/selling opportunities.
    """
    calendar = {
        1: {"buy_cheap": ["snacks (dead season)", "school supplies", "cleaning products"],
            "sell_high": ["winter vegetables", "soups", "hot drinks"],
            "event": "New Year clearance from hypermarkets"},
        2: {"buy_cheap": ["Valentine's chocolate (after 14th)", "flowers"],
            "sell_high": ["winter produce", "hot beverages"],
            "event": "Post-Valentine clearance"},
        3: {"buy_cheap": ["End-of-Q1 FMCG dumps from distributors", "cleaning supplies"],
            "sell_high": ["Ramadan prep items (if Ramadan approaching)"],
            "event": "Q1 distributor clearance week (last 5 days)"},
        4: {"buy_cheap": ["Summer items arriving (stock now)", "end-season winter items"],
            "sell_high": ["Ramadan essentials if active"],
            "event": "Ramadan (dates vary by year)"},
        5: {"buy_cheap": ["Post-Ramadan clearance (dates, oil, rice)"],
            "sell_high": ["Eid gifts, chocolates, perfumes"],
            "event": "Eid Al Fitr clearance"},
        6: {"buy_cheap": ["Pakistani mangoes flooding market (2-3 AED/kg)", "summer fruits"],
            "sell_high": ["Cold drinks", "ice cream", "water"],
            "event": "Mango season starts — BUY HEAVY"},
        7: {"buy_cheap": ["Mangoes at peak supply", "RAK dates starting", "summer clearance"],
            "sell_high": ["Cold beverages", "ice", "BBQ supplies"],
            "event": "Date harvest begins in RAK"},
        8: {"buy_cheap": ["Rice (new stock coming, old stock clearance)", "dates at peak"],
            "sell_high": ["Back-to-school prep starting", "stationery"],
            "event": "Rice wholesalers clear old stock"},
        9: {"buy_cheap": ["End-of-Q3 distributor dumps", "summer clearance"],
            "sell_high": ["School snacks at full price", "stationery", "juice boxes"],
            "event": "Back-to-school rush — SELL HIGH"},
        10: {"buy_cheap": ["Post-wedding catering surplus", "autumn produce"],
             "sell_high": ["Heating items", "soups starting"],
             "event": "Wedding season ends — buy surplus"},
        11: {"buy_cheap": ["White Friday (hypermarket clearance)", "everything on sale"],
             "sell_high": ["Daily essentials (people buy deals, not basics)"],
             "event": "White Friday / Black Friday week — BUY CLEARANCE"},
        12: {"buy_cheap": ["End-of-Q4 FMCG dumps", "National Day sales", "Christmas clearance"],
             "sell_high": ["Holiday items", "gift packs", "party supplies"],
             "event": "UAE National Day (2nd) + Year-end clearance"},
    }

    if month and 1 <= month <= 12:
        return {"month": month, **calendar[month]}

    return {
        "full_year_calendar": calendar,
        "golden_rules": [
            "Buy 2 months BEFORE peak demand (Ramadan, school, Eid)",
            "Visit distributors in last 5 days of each quarter for clearance",
            "Stock seasonal fruits (mangoes Jun-Aug, dates Jul-Oct) when prices crash",
            "White Friday week (November) = buy everything on clearance",
            "Never buy at peak — you're competing with hypermarket prices",
        ],
    }


@handle_tool_errors("research_uae_legal_check")
async def research_uae_legal_check(
    activity: str,
) -> dict[str, Any]:
    """Check if a sourcing/selling activity is legal in UAE for a baqala.

    Args:
        activity: Description of the activity to check (e.g., "sell near-expiry food",
                  "import from Oman", "repackage bulk items", "buy from fishing boats")

    Returns:
        Dict with legal status, requirements, and risks.
    """
    legal_db = {
        "near-expiry": {
            "legal": True,
            "conditions": [
                "Must clearly label expiry date visible to customer",
                "Cannot sell AFTER expiry date (municipality fine: AED 5,000-50,000)",
                "Must maintain cold chain for perishables",
                "Recommended: separate 'clearance' shelf with clear signage",
            ],
            "risk_level": "low",
        },
        "repackage": {
            "legal": True,
            "conditions": [
                "Must have food handling permit from Ajman Municipality",
                "Must label repackaged items with: weight, ingredients, your store name, date packed",
                "Must use food-grade packaging materials",
                "Cannot repackage expired items",
            ],
            "risk_level": "medium",
        },
        "import": {
            "legal": True,
            "conditions": [
                "Need trade license with 'general trading' or 'foodstuff trading' activity",
                "Food items need municipality approval + ESMA conformity",
                "Customs duty: 5% on most food items",
                "Need import code from Dubai/Ajman Customs",
                "Halal certification required for meat products",
            ],
            "risk_level": "medium",
        },
        "fishing boats": {
            "legal": True,
            "conditions": [
                "Can buy from licensed fishermen at designated fish markets",
                "Cannot buy directly at sea (coast guard regulation)",
                "Must maintain cold chain (ice/refrigeration)",
                "Fish market purchases are legal and common",
            ],
            "risk_level": "low",
        },
        "oman border": {
            "legal": True,
            "conditions": [
                "Personal import limit without duty: AED 3,000 per person per trip",
                "Commercial quantities need customs declaration",
                "Tobacco limit: 400 cigarettes or 2kg tobacco",
                "Alcohol: not permitted to bring into UAE",
                "Some food items need phytosanitary certificates",
            ],
            "risk_level": "low",
        },
        "expired food": {
            "legal": False,
            "conditions": [
                "ILLEGAL to sell expired food for human consumption",
                "Fine: AED 5,000 - 50,000 + store closure risk",
                "CAN sell expired food for animal feed (need separate license)",
                "CAN sell expired food for industrial use (soap, compost)",
            ],
            "risk_level": "high",
        },
        "construction camps": {
            "legal": True,
            "conditions": [
                "Standard baqala trade license covers B2B sales",
                "Need delivery vehicle registered for food transport",
                "Bulk sales invoicing required for tax purposes",
                "Camp may require food safety certificate from supplier",
            ],
            "risk_level": "low",
        },
    }

    activity_lower = activity.lower()
    for key, info in legal_db.items():
        if key in activity_lower:
            return {"activity": activity, **info}

    if query_llm:
        try:
            llm = await query_llm(
                f"Is this activity legal for a small supermarket (baqala) in Ajman, UAE? Activity: '{activity}'. "
                f"Answer with: legal (yes/no), conditions/requirements, UAE-specific regulations, and risk level (low/medium/high).",
                system="You are a UAE commercial law expert specializing in retail trade regulations in the Northern Emirates.",
                temperature=0.2, max_tokens=500,
            )
            if llm.get("text"):
                return {"activity": activity, "ai_analysis": llm["text"], "disclaimer": "Verify with Ajman Municipality for official ruling"}
        except Exception:
            pass

    return {"activity": activity, "status": "unknown", "recommendation": "Check with Ajman Municipality or a local trade lawyer"}


@handle_tool_errors("research_uae_bundle_optimizer")
async def research_uae_bundle_optimizer(
    products: list[str] | None = None,
    target_audience: str = "all",
) -> dict[str, Any]:
    """Generate profitable product bundle ideas for a UAE baqala.

    Creates bundle combinations that increase basket size and margins.

    Args:
        products: Specific products to include in bundles (optional)
        target_audience: "workers", "families", "students", or "all"

    Returns:
        Dict with bundle ideas, pricing, and expected uplift.
    """
    bundles = {
        "workers": [
            {"name": "Worker Daily Pack", "items": ["Rice 1kg", "Dal 500g", "Oil 500ml", "Bread"], "cost_aed": 12, "sell_aed": 18, "margin_pct": 33},
            {"name": "Lunch Box Combo", "items": ["Bread", "Cheese slice", "Juice 250ml", "Chips"], "cost_aed": 5, "sell_aed": 8, "margin_pct": 37},
            {"name": "Weekly Essentials", "items": ["Rice 5kg", "Oil 1.5L", "Sugar 1kg", "Tea 200g"], "cost_aed": 35, "sell_aed": 50, "margin_pct": 30},
        ],
        "families": [
            {"name": "Family Breakfast Pack", "items": ["Milk 1L", "Eggs 6", "Bread", "Cheese", "Jam"], "cost_aed": 18, "sell_aed": 28, "margin_pct": 36},
            {"name": "Cooking Essentials", "items": ["Onions 1kg", "Tomatoes 1kg", "Garlic", "Ginger", "Chili"], "cost_aed": 8, "sell_aed": 14, "margin_pct": 43},
            {"name": "Weekend BBQ Pack", "items": ["Chicken 1kg", "Charcoal", "Ketchup", "Bread 2x", "Drinks 6-pack"], "cost_aed": 30, "sell_aed": 45, "margin_pct": 33},
        ],
        "students": [
            {"name": "Study Fuel Pack", "items": ["Energy drink", "Chips", "Chocolate", "Water"], "cost_aed": 8, "sell_aed": 14, "margin_pct": 43},
            {"name": "School Lunch", "items": ["Sandwich", "Juice box", "Fruit", "Biscuit"], "cost_aed": 5, "sell_aed": 9, "margin_pct": 44},
        ],
        "all": [
            {"name": "Karak Kit", "items": ["Karak tea sachet 3x", "Milk 500ml", "Sugar sachet"], "cost_aed": 4, "sell_aed": 7, "margin_pct": 43},
            {"name": "Cleaning Bundle", "items": ["Detergent 1kg", "Dishwash 500ml", "Floor cleaner", "Sponge 3-pack"], "cost_aed": 15, "sell_aed": 25, "margin_pct": 40},
            {"name": "Ramadan Iftar Pack", "items": ["Dates 250g", "Laban 1L", "Samosa 6-pack", "Juice 1L"], "cost_aed": 12, "sell_aed": 20, "margin_pct": 40},
        ],
    }

    if target_audience == "all":
        all_bundles = []
        for audience_bundles in bundles.values():
            all_bundles.extend(audience_bundles)
    else:
        all_bundles = bundles.get(target_audience, bundles["all"])

    return {
        "target_audience": target_audience,
        "bundles": all_bundles,
        "total_bundles": len(all_bundles),
        "pricing_tips": [
            "Price bundles 10-15% below sum of individual items (perceived value)",
            "Display bundles near checkout for impulse buying",
            "Change bundles weekly to create urgency",
            "Print bundle cards with WhatsApp QR for reorder",
        ],
        "expected_basket_size_increase": "25-40%",
    }
