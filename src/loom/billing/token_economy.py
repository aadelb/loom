"""Token economy middleware for tool cost deduction.

Provides:
- Tool cost lookup by category (free, basic, medium, heavy, premium)
- Pre-execution credit balance checks
- Post-execution credit deduction
- Balance queries and usage tracking
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


# Tool cost mapping by category
TOOL_COSTS: dict[str, int] = {
    # Free tools (0 credits)
    "cache_stats": 0,
    "cache_clear": 0,
    "health_check": 0,
    "config_get": 0,
    "config_set": 0,
    "session_list": 0,

    # Basic tools (1 credit) - lightweight analysis
    "search": 1,
    "text_analyze": 1,
    "detect_language": 1,
    "llm_classify": 1,
    "sentiment_deep": 1,
    "stylometry": 1,
    "geoip_local": 1,
    "fact_checker": 1,
    "llm_embed": 1,
    "llm_extract": 1,
    "llm_translate": 1,
    "llm_summarize": 1,
    "llm_answer": 1,
    "llm_expand": 1,
    "wayback": 1,

    # Medium tools (5 credits) - moderate I/O and processing
    "fetch": 5,
    "spider": 5,
    "markdown": 5,
    "whois": 5,
    "dns_lookup": 5,
    "screenshot": 5,
    "github": 5,
    "cert_analyze": 5,
    "security_headers": 5,
    "breach_check": 5,
    "pdf_extract": 5,
    "rss_fetch": 5,
    "rss_monitor": 5,
    "social_search": 5,
    "metadata_forensics": 5,
    "passive_recon": 5,
    "ip_reputation": 5,
    "cve_lookup": 5,
    "domain_intel": 5,
    "ip_intel": 5,
    "urlhaus_lookup": 5,
    "image_intel": 5,
    "video_intel": 5,
    "audio_intel": 5,

    # Heavy tools (10 credits) - intensive processing or multi-stage
    "deep": 10,
    "ask_all_models": 10,
    "prompt_reframe": 10,
    "auto_reframe": 10,
    "adaptive_reframe": 10,
    "camoufox": 10,
    "botasaurus": 10,
    "multi_search": 10,
    "infra_correlator": 10,
    "dead_content": 10,
    "invisible_web": 10,
    "js_intel": 10,
    "knowledge_graph": 10,
    "change_monitor": 10,
    "social_graph": 10,
    "threat_profile": 10,
    "leak_scan": 10,
    "stego_detect": 10,
    "crypto_trace": 10,
    "model_profile": 10,
    "model_sentiment": 10,
    "consensus_build": 10,
    "crescendo_loop": 10,
    "reid_pipeline": 10,

    # Premium tools (20 credits) - dangerous, specialized, or resource-intensive
    "dark_forum": 20,  # Darkweb access
    "onion_discover": 20,  # Tor crawling
    "sandbox_run": 20,  # Code execution
    "full_pipeline": 20,  # Multi-stage orchestration
    "orchestrate_smart": 20,  # Complex orchestration
}

# Default cost for unknown tools
DEFAULT_COST = 2


def get_tool_cost(tool_name: str) -> int:
    """Get credit cost for a tool.

    Strips research_ prefix and looks up cost in TOOL_COSTS table.
    Falls back to DEFAULT_COST for unknown tools.

    Args:
        tool_name: Tool name (with or without research_ prefix)

    Returns:
        Credit cost (int >= 0)
    """
    # Normalize tool name: strip research_ prefix
    clean_name = tool_name.replace("research_", "", 1)

    # Try exact match first
    if clean_name in TOOL_COSTS:
        return TOOL_COSTS[clean_name]

    # Try partial match by checking prefixes
    for prefix, cost in sorted(TOOL_COSTS.items(), key=lambda x: -len(x[0])):
        if clean_name.startswith(prefix):
            return cost

    # Default fallback
    return DEFAULT_COST


def check_balance(user_id: str, current_balance: int, tool_name: str) -> dict[str, Any]:
    """Check if user has sufficient credits for a tool.

    Args:
        user_id: User identifier
        current_balance: Current credit balance
        tool_name: Tool name to check cost for

    Returns:
        Dict with:
        - sufficient: True if balance >= cost, False otherwise
        - required: Cost of the tool
        - balance: Current balance
        - shortfall: If insufficient, amount needed (0 if sufficient)
    """
    cost = get_tool_cost(tool_name)
    sufficient = current_balance >= cost
    shortfall = max(0, cost - current_balance)

    return {
        "sufficient": sufficient,
        "required": cost,
        "balance": current_balance,
        "shortfall": shortfall,
    }


def deduct_credits(
    user_id: str,
    current_balance: int,
    tool_name: str,
) -> dict[str, Any]:
    """Deduct credits for tool execution.

    Performs the actual credit deduction. Assumes balance has already
    been checked. Returns new balance (never negative).

    Args:
        user_id: User identifier
        current_balance: Current credit balance
        tool_name: Tool name being executed

    Returns:
        Dict with:
        - success: True if deduction succeeded
        - balance_before: Balance before deduction
        - cost_charged: Credits deducted
        - balance_after: Balance after deduction
        - tool_name: Tool that was charged
    """
    cost = get_tool_cost(tool_name)
    balance_after = max(0, current_balance - cost)

    log.info(
        "credit_deduction",
        user_id=user_id,
        tool_name=tool_name,
        cost=cost,
        balance_before=current_balance,
        balance_after=balance_after,
    )

    return {
        "success": True,
        "balance_before": current_balance,
        "cost_charged": cost,
        "balance_after": balance_after,
        "tool_name": tool_name,
    }


def get_balance(user_id: str, current_balance: int) -> dict[str, Any]:
    """Get detailed balance information for a user.

    Args:
        user_id: User identifier
        current_balance: Current credit balance

    Returns:
        Dict with:
        - user_id: User identifier
        - balance: Current credit balance
        - usage_summary: Breakdown of tool usage (would require history)
    """
    return {
        "user_id": user_id,
        "balance": current_balance,
    }
