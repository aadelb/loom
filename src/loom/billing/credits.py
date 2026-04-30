"""Credit-based billing system for tools.

Provides:
- Credit weights per tool (light, medium, heavy)
- Balance checking before execution
- Credit deduction tracking
"""

from __future__ import annotations

# Credit weights per tool (after stripping research_ prefix)
CREDIT_WEIGHTS: dict[str, int] = {
    # Light tools (1 credit)
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
    # Medium tools (3 credits)
    "fetch": 3,
    "spider": 3,
    "markdown": 3,
    "whois": 3,
    "dns_lookup": 3,
    "screenshot": 3,
    "github": 3,
    "cert_analyze": 3,
    "security_headers": 3,
    "breach_check": 3,
    "pdf_extract": 3,
    "rss_fetch": 3,
    "social_search": 3,
    "metadata_forensics": 3,
    "passive_recon": 3,
    "ip_reputation": 3,
    "cve_lookup": 3,
    # Heavy tools (10 credits)
    "deep": 10,
    "dark_forum": 10,
    "ask_all_models": 10,
    "prompt_reframe": 10,
    "auto_reframe": 10,
    "adaptive_reframe": 10,
    "camoufox": 10,
    "botasaurus": 10,
    "onion_discover": 10,
    "multi_search": 10,
    "infra_correlator": 10,
    "dead_content": 10,
    "invisible_web": 10,
    "js_intel": 10,
    "knowledge_graph": 10,
}

DEFAULT_WEIGHT = 2  # Unknown tools cost 2 credits


def get_tool_cost(tool_name: str) -> int:
    """Get credit cost for a tool.

    Strips research_ prefix and looks up in CREDIT_WEIGHTS table.
    Falls back to DEFAULT_WEIGHT for unknown tools.

    Args:
        tool_name: Tool name (with or without research_ prefix)

    Returns:
        Credit cost (1, 2, 3, or 10)
    """
    clean = tool_name.replace("research_", "", 1)
    return CREDIT_WEIGHTS.get(clean, DEFAULT_WEIGHT)


def check_balance(credits: int, tool_name: str) -> bool:
    """Check if customer has sufficient credits for a tool.

    Args:
        credits: Current credit balance
        tool_name: Tool name to check cost for

    Returns:
        True if credits >= cost, False otherwise
    """
    cost = get_tool_cost(tool_name)
    return credits >= cost


def deduct(credits: int, tool_name: str) -> tuple[int, int]:
    """Deduct credits for a tool execution.

    Args:
        credits: Current credit balance
        tool_name: Tool name being executed

    Returns:
        Tuple of (remaining_credits, cost_charged)
        remaining_credits will be at least 0 (no negative balances)
    """
    cost = get_tool_cost(tool_name)
    remaining = max(0, credits - cost)
    return remaining, cost
