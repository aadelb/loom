"""Subscription tier definitions and enforcement.

Defines four tiers with different credit allowances, pricing, feature access,
and rate limits. Provides utilities for tier validation and upgrade/downgrade paths.

Tier structure:
- Free: 500 credits/month, $0, 40 tools, 10 req/min, basic features
- Pro: 10K credits/month, $99, 150 tools, 60 req/min, advanced features
- Team: 50K credits/month, $299, 190 tools, 300 req/min, dark web + AI safety
- Enterprise: 200K credits/month, $999, 220 tools, 1000 req/min, all tools
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Tier:
    """Immutable subscription tier definition."""

    name: str
    monthly_credits: int
    price_usd: int
    tools_limit: int
    rate_limit_per_min: int
    features: list[str]


TIERS: dict[str, Tier] = {
    "free": Tier(
        name="Free",
        monthly_credits=500,
        price_usd=0,
        tools_limit=40,
        rate_limit_per_min=10,
        features=[
            "basic_search",
            "single_engine",
            "2_llm_providers",
        ],
    ),
    "pro": Tier(
        name="Pro",
        monthly_credits=10_000,
        price_usd=99,
        tools_limit=150,
        rate_limit_per_min=60,
        features=[
            "all_search_engines",
            "6_llm_providers",
            "cloudflare_bypass",
            "osint",
            "50_strategies",
        ],
    ),
    "team": Tier(
        name="Team",
        monthly_credits=50_000,
        price_usd=299,
        tools_limit=190,
        rate_limit_per_min=300,
        features=[
            "dark_web",
            "ai_safety",
            "career_intel",
            "200_strategies",
            "team_roles",
        ],
    ),
    "enterprise": Tier(
        name="Enterprise",
        monthly_credits=200_000,
        price_usd=999,
        tools_limit=220,
        rate_limit_per_min=1000,
        features=[
            "all_tools",
            "826_strategies",
            "on_prem",
            "sla_99_9",
            "audit_logs",
            "compliance_exports",
        ],
    ),
}


def get_tier(name: str) -> Tier:
    """Get tier by name. Defaults to free for unknown tiers.

    Args:
        name: Tier name (case-insensitive)

    Returns:
        Tier object, or free tier if not found
    """
    return TIERS.get(name.lower(), TIERS["free"])


def can_access_tool(tier_name: str, tool_index: int) -> bool:
    """Check if tier allows access to tool at given index.

    Tools are indexed 0-166 (167 total tools). Tiers grant access
    to the first N tools based on tools_limit.

    Args:
        tier_name: Subscription tier name
        tool_index: Zero-based tool index

    Returns:
        True if tier has access, False otherwise
    """
    tier = get_tier(tier_name)
    return tool_index < tier.tools_limit


def check_upgrade_path(current: str, target: str) -> dict[str, Any]:
    """Check upgrade/downgrade between tiers.

    Returns information about the transition: direction (upgrade/downgrade/same),
    price difference, credit difference, and tool limit difference.

    Args:
        current: Current tier name
        target: Target tier name

    Returns:
        Dictionary with upgrade path information:
        - from: Current tier display name
        - to: Target tier display name
        - direction: "upgrade", "downgrade", or "same"
        - price_diff: Monthly price difference in USD
        - credit_diff: Monthly credit difference
        - tool_diff: Tool limit difference
    """
    current_tier = get_tier(current)
    target_tier = get_tier(target)
    tier_order = ["free", "pro", "team", "enterprise"]
    current_idx = (
        tier_order.index(current.lower())
        if current.lower() in tier_order
        else 0
    )
    target_idx = (
        tier_order.index(target.lower())
        if target.lower() in tier_order
        else 0
    )

    if target_idx > current_idx:
        direction = "upgrade"
    elif target_idx < current_idx:
        direction = "downgrade"
    else:
        direction = "same"

    return {
        "from": current_tier.name,
        "to": target_tier.name,
        "direction": direction,
        "price_diff": target_tier.price_usd - current_tier.price_usd,
        "credit_diff": target_tier.monthly_credits - current_tier.monthly_credits,
        "tool_diff": target_tier.tools_limit - current_tier.tools_limit,
    }
