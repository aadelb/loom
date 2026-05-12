"""Cost estimator — predict API costs BEFORE executing tools."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.cost_estimator")

# Module-level tracking for cost accumulation
_cost_history: list[dict[str, Any]] = []

# Cost per provider (USD per 1M tokens)
COST_MAP: dict[str, dict[str, float]] = {
    "groq": {"input": 0.0, "output": 0.0},
    "nvidia_nim": {"input": 0.0, "output": 0.0},
    "deepseek": {"input": 0.14, "output": 0.28},
    "gemini": {"input": 1.25, "output": 5.00},
    "moonshot": {"input": 0.50, "output": 0.50},
    "openai": {"input": 2.50, "output": 10.00},
    "anthropic": {"input": 3.00, "output": 15.00},
}

# Token estimation by tool type
TOKEN_ESTIMATES: dict[str, int] = {
    # Search tools: minimal LLM usage
    "search": 500,
    "deep": 2000,
    "spider": 1500,
    "fetch": 100,
    # LLM tools: full response generation
    "llm": 2000,
    "ask_all_llms": 2000,
    "chat": 2000,
    "classify": 1500,
    "extract": 1500,
    "summarize": 1500,
    "translate": 1500,
    "expand": 1500,
    "embed": 500,
    "answer": 2000,
    # Analysis tools: moderate LLM usage
    "analyze": 1000,
    "profile": 1000,
    "detect": 1000,
}


def _estimate_tokens(tool_name: str, params: dict[str, Any] | None = None) -> int:
    """Estimate token count for a tool call based on tool type and params.

    Args:
        tool_name: Name of the tool (e.g., 'research_fetch', 'research_search')
        params: Optional parameter dict for more accurate estimation

    Returns:
        Estimated token count
    """
    # Extract tool type from name
    tool_type = tool_name.replace("research_", "").split("_")[0]

    base_tokens = TOKEN_ESTIMATES.get(tool_type, 1000)

    # Adjust based on input size if params provided
    if params:
        # Check for explicit token count
        if "max_tokens" in params:
            return params["max_tokens"]

        # Adjust based on URL/text input sizes
        if "url" in params:
            base_tokens += 200
        if "urls" in params:
            base_tokens += 200 * len(params.get("urls", []))
        if "prompt" in params:
            prompt_len = len(params.get("prompt", ""))
            base_tokens += max(0, prompt_len // 4)  # ~4 chars per token
        if "query" in params:
            query_len = len(params.get("query", ""))
            base_tokens += max(0, query_len // 4)

    return max(100, base_tokens)


def _select_provider(provider: str) -> str:
    """Select provider, defaulting to 'auto' (cheapest available).

    Args:
        provider: Provider name or 'auto'

    Returns:
        Selected provider name
    """
    if provider != "auto":
        return provider

    # Auto-select cheapest provider
    # Free providers first: groq, nvidia_nim
    for free_provider in ["groq", "nvidia_nim"]:
        if free_provider in COST_MAP:
            return free_provider

    # Fall back to cheapest paid provider
    min_cost = float("inf")
    cheapest = "anthropic"
    for prov, costs in COST_MAP.items():
        avg_cost = (costs["input"] + costs["output"]) / 2
        if avg_cost < min_cost:
            min_cost = avg_cost
            cheapest = prov

    return cheapest


def _calculate_cost(
    provider: str, input_tokens: int, output_tokens: int
) -> float:
    """Calculate USD cost for token usage.

    Args:
        provider: Provider name
        input_tokens: Input token count
        output_tokens: Output token count

    Returns:
        USD cost (float)
    """
    if provider not in COST_MAP:
        provider = "anthropic"  # safe default

    costs = COST_MAP[provider]
    in_cost = (input_tokens / 1_000_000) * costs["input"]
    out_cost = (output_tokens / 1_000_000) * costs["output"]

    return in_cost + out_cost


def _find_free_alternatives(tool_name: str) -> list[str]:
    """Find free/cheaper alternatives for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        List of free alternative providers
    """
    alternatives = []

    # For LLM tools, suggest free providers
    if any(x in tool_name for x in ["llm", "chat", "ask", "classify", "extract"]):
        alternatives.append("groq (free)")
        alternatives.append("nvidia_nim (free)")

    # For fetch/search tools (no LLM cost)
    if any(x in tool_name for x in ["fetch", "spider", "search"]):
        alternatives.append("No LLM cost")

    return alternatives


@handle_tool_errors("research_estimate_cost")
async def research_estimate_cost(
    tool_name: str,
    params: dict[str, Any] | None = None,
    provider: str = "auto",
) -> dict[str, Any]:
    """Estimate the cost of a tool call BEFORE executing it.

    Predicts API costs based on tool type, parameters, and LLM provider.
    Useful for budget planning and selecting cost-effective providers.

    Args:
        tool_name: Name of the tool (e.g., 'research_fetch', 'research_search')
        params: Optional dict of tool parameters for more accurate estimation
        provider: LLM provider ('auto', 'groq', 'nvidia_nim', 'deepseek',
                  'gemini', 'moonshot', 'openai', 'anthropic')

    Returns:
        Dict with:
            - tool: tool name
            - provider: selected provider
            - estimated_tokens: dict with input/output token counts
            - estimated_cost_usd: float, total estimated cost
            - free_alternatives: list of free/cheap options
            - cost_per_1m: cost per 1M tokens for reference
    """
    try:
        if params is None:
            params = {}

        selected_provider = _select_provider(provider)
        estimated_tokens = _estimate_tokens(tool_name, params)

        # Assume 70% input, 30% output for LLM calls
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)

        estimated_cost = _calculate_cost(selected_provider, input_tokens, output_tokens)
        free_alts = _find_free_alternatives(tool_name)

        # Track in history
        _cost_history.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": tool_name,
            "provider": selected_provider,
            "estimated_cost_usd": estimated_cost,
        })

        return {
            "tool": tool_name,
            "provider": selected_provider,
            "estimated_tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": estimated_tokens,
            },
            "estimated_cost_usd": round(estimated_cost, 6),
            "free_alternatives": free_alts,
            "cost_per_1m_tokens": {
                "input": COST_MAP[selected_provider]["input"],
                "output": COST_MAP[selected_provider]["output"],
            },
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_estimate_cost"}


@handle_tool_errors("research_cost_summary")
async def research_cost_summary(period: str = "today") -> dict[str, Any]:
    """Summarize estimated costs accumulated across tool calls.

    Returns aggregated cost metrics for budget tracking and cost
    optimization analysis.

    Args:
        period: Time period ('today', 'session', 'all')

    Returns:
        Dict with:
            - period: time period analyzed
            - total_estimated_usd: total cost for period
            - by_provider: dict of costs per provider
            - total_calls: number of cost estimates
            - avg_cost_per_call: average USD per tool call
            - cheapest_provider: provider with lowest avg cost
            - most_expensive_tool: tool with highest total cost
    """
    try:
        if not _cost_history:
            return {
                "period": period,
                "total_estimated_usd": 0.0,
                "by_provider": {},
                "total_calls": 0,
                "avg_cost_per_call": 0.0,
                "cheapest_provider": None,
                "most_expensive_tool": None,
            }

        # Filter by period
        now = datetime.now(UTC)
        filtered = _cost_history

        if period == "today":
            filtered = [
                item for item in _cost_history
                if datetime.fromisoformat(item["timestamp"]).date() == now.date()
            ]

        # Aggregate stats
        total_cost = sum(item["estimated_cost_usd"] for item in filtered)
        provider_costs: dict[str, float] = {}
        tool_costs: dict[str, float] = {}

        for item in filtered:
            prov = item["provider"]
            tool = item["tool"]
            cost = item["estimated_cost_usd"]

            provider_costs[prov] = provider_costs.get(prov, 0.0) + cost
            tool_costs[tool] = tool_costs.get(tool, 0.0) + cost

        cheapest_prov = min(provider_costs, key=provider_costs.get) if provider_costs else None
        expensive_tool = max(tool_costs, key=tool_costs.get) if tool_costs else None

        return {
            "period": period,
            "total_estimated_usd": round(total_cost, 6),
            "by_provider": {k: round(v, 6) for k, v in provider_costs.items()},
            "total_calls": len(filtered),
            "avg_cost_per_call": round(total_cost / len(filtered), 6) if filtered else 0.0,
            "cheapest_provider": cheapest_prov,
            "most_expensive_tool": expensive_tool,
            "tool_breakdown": {k: round(v, 6) for k, v in tool_costs.items()},
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_cost_summary"}
