"""Internal cost tracking — provider costs vs customer revenue.

Tracks estimated provider costs for each LLM and search provider call,
computes revenue from customer tier/credit usage, calculates profit margins,
and alerts when margins fall below 20%.

Cost Model:
- LLM providers: Groq and NVIDIA NIM are free; DeepSeek, Gemini, Moonshot,
  OpenAI, and Anthropic have token-based costs.
- Search providers: Exa, Tavily, Brave, Firecrawl have per-call or token costs;
  free providers (DDGS, etc.) have zero cost.

Revenue Model:
- Free tier: $0
- Pro tier: $99/month ÷ 10,000 credits = $0.0099/credit
- Team tier: $299/month ÷ 50,000 credits = $0.00598/credit
- Enterprise tier: $999/month ÷ 200,000 credits = $0.004995/credit

Margin calculation: (revenue - cost) / max(revenue, 0.001) ≥ 20% healthy
"""

from __future__ import annotations

from typing import Any


# Estimated cost per tool call by LLM provider (USD)
LLM_PROVIDER_COSTS: dict[str, float] = {
    "groq": 0.0,  # Free tier
    "nvidia_nim": 0.0,  # Free tier (integrate.api.nvidia.com)
    "deepseek": 0.0005,  # ~$0.55/1M tokens → $0.0005/call estimate
    "gemini": 0.002,  # ~$2/1M tokens → $0.002/call estimate
    "moonshot": 0.001,  # ~$1/1M tokens → $0.001/call estimate
    "openai": 0.01,  # ~$10/1M tokens (gpt-5-mini) → $0.01/call estimate
    "anthropic": 0.015,  # ~$15/1M tokens (claude-opus) → $0.015/call estimate
    "vllm": 0.0,  # Self-hosted, no cost
}

# Estimated cost per search call by provider (USD)
SEARCH_PROVIDER_COSTS: dict[str, float] = {
    "exa": 0.001,  # ~$1/1K queries
    "tavily": 0.001,  # ~$1/1K queries
    "firecrawl": 0.0005,  # ~$0.50/1K pages
    "brave": 0.001,  # ~$1/1K queries
    "ddgs": 0.0,  # Free (DuckDuckGo)
    "arxiv": 0.0,  # Free (arXiv API)
    "wikipedia": 0.0,  # Free
    "hn_reddit": 0.0,  # Free
    "newsapi": 0.0001,  # Negligible
    "coindesk": 0.0,  # Free
    "coinmarketcap": 0.0,  # Free (free tier)
    "binance": 0.0,  # Free
    "ahmia": 0.0,  # Free (Tor search)
    "darksearch": 0.0,  # Free
    "ummro": 0.0,  # Internal RAG
    "onionsearch": 0.0,  # Free
    "torcrawl": 0.0,  # Free
    "darkweb_cti": 0.0,  # Free
    "robin_osint": 0.0,  # Free
    "investing": 0.0,  # Free tier
    "youtube": 0.0,  # Free (YouTube API)
}

# Revenue per credit by customer tier (USD/credit)
REVENUE_PER_CREDIT: dict[str, float] = {
    "free": 0.0,  # Free tier pays $0
    "pro": 0.0099,  # $99/month ÷ 10,000 credits
    "team": 0.00598,  # $299/month ÷ 50,000 credits
    "enterprise": 0.004995,  # $999/month ÷ 200,000 credits
}


def estimate_call_cost(provider: str, provider_type: str = "llm") -> float:
    """Estimate USD cost of a single call to a provider.

    Args:
        provider: Provider name (groq, openai, exa, tavily, etc.)
        provider_type: One of 'llm' or 'search'

    Returns:
        Estimated USD cost of one call
    """
    if provider_type == "llm":
        return LLM_PROVIDER_COSTS.get(provider, 0.005)
    elif provider_type == "search":
        return SEARCH_PROVIDER_COSTS.get(provider, 0.001)
    else:
        return 0.005  # Default fallback


def estimate_revenue(tier: str, credits_used: int) -> float:
    """Estimate revenue from credits used by a customer tier.

    Args:
        tier: Customer tier (free, pro, team, enterprise)
        credits_used: Number of credits consumed

    Returns:
        Estimated USD revenue (rounded to 4 decimal places)
    """
    rate = REVENUE_PER_CREDIT.get(tier, 0.0)
    return round(credits_used * rate, 4)


def compute_margin(
    tier: str,
    credits_used: int,
    provider_costs: float,
) -> dict[str, Any]:
    """Compute profit margin for a customer.

    Calculates revenue from credits, subtracts provider costs, and computes
    margin percentage. Flags margins < 20% as unhealthy and < 0 as negative.

    Args:
        tier: Customer tier (free, pro, team, enterprise)
        credits_used: Total credits used by customer
        provider_costs: Total USD cost of provider calls (LLM + search)

    Returns:
        Dict with:
        - revenue: USD revenue from customer
        - cost: USD cost of provider calls
        - profit: USD profit (revenue - cost)
        - margin_percent: Profit margin as percentage
        - healthy: True if margin ≥ 20%
        - alert: None if healthy, or "low_margin" (0-20%) or "negative" (<0)
    """
    revenue = estimate_revenue(tier, credits_used)
    profit = revenue - provider_costs

    # Calculate margin percentage
    # If revenue > 0, calculate actual margin
    # If revenue == 0 and profit < 0, treat as negative
    # If revenue == 0 and profit == 0, margin is 0%
    if revenue > 0:
        margin_pct = round((profit / revenue) * 100, 1)
    elif profit < 0:
        # When revenue is 0 but there's a cost, treat as deeply negative
        margin_pct = -100.0
    else:
        # revenue == 0 and profit == 0
        margin_pct = 0.0

    # Determine health status
    alert = None
    if profit < 0:
        alert = "negative"
    elif 0 <= margin_pct < 20:
        alert = "low_margin"

    return {
        "revenue": round(revenue, 4),
        "cost": round(provider_costs, 4),
        "profit": round(profit, 4),
        "margin_percent": margin_pct,
        "healthy": margin_pct >= 20,
        "alert": alert,
    }


def aggregate_provider_costs(calls: list[dict[str, Any]]) -> float:
    """Aggregate total cost from a list of provider calls.

    Each call dict should have:
    - provider: Provider name
    - provider_type: 'llm' or 'search'

    Args:
        calls: List of call dicts with provider info

    Returns:
        Total USD cost (rounded to 4 decimal places)
    """
    total = sum(
        estimate_call_cost(call.get("provider", ""), call.get("provider_type", "llm"))
        for call in calls
    )
    return round(total, 4)


def check_margin_health(
    tier: str,
    credits_used: int,
    provider_costs: float,
    min_margin: int = 20,
) -> dict[str, Any]:
    """Check if customer margin meets minimum threshold.

    Args:
        tier: Customer tier
        credits_used: Total credits used
        provider_costs: Total provider costs
        min_margin: Minimum acceptable margin percentage (default 20)

    Returns:
        Dict with:
        - margin_info: Full margin computation dict
        - meets_minimum: True if margin ≥ min_margin
        - action: None if healthy, or recommended action (e.g., "review_pricing")
    """
    margin_info = compute_margin(tier, credits_used, provider_costs)
    margin_pct = margin_info["margin_percent"]
    meets_minimum = margin_pct >= min_margin

    action = None
    if margin_pct < 0:
        action = "immediate_review"
    elif margin_pct < min_margin:
        action = "review_pricing"

    return {
        "margin_info": margin_info,
        "meets_minimum": meets_minimum,
        "action": action,
    }
