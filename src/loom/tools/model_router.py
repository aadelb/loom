"""Intelligent model router for cost optimization.

Classifies queries by complexity and routes them to appropriate cost tiers:
- Simple (free models): Short factual queries, translations, classifications
- Medium (cheap models): Analysis, summarization, moderate reasoning
- Complex (expensive models): Multi-step reasoning, creative synthesis, long-form generation

Estimated savings: 70% cost reduction by routing simple queries to free models.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

logger = logging.getLogger("loom.tools.model_router")

# ============================================================================
# Cost Tier Definitions
# ============================================================================

MODEL_ROUTING = {
    "simple": {
        "providers": ["groq", "nvidia"],
        "tier": "free",
        "max_tokens": 400,
        "description": "Free tier models for quick, factual queries",
    },
    "medium": {
        "providers": ["deepseek", "gemini"],
        "tier": "cheap",
        "max_tokens": 1000,
        "description": "Budget-friendly models for moderate reasoning",
    },
    "complex": {
        "providers": ["openai", "anthropic"],
        "tier": "expensive",
        "max_tokens": 2000,
        "description": "Premium models for complex multi-step reasoning",
    },
}

# Estimated cost per 1M input tokens (rough approximation)
PROVIDER_COSTS = {
    "groq": 0.0,  # Free tier
    "nvidia": 0.0,  # Free tier
    "deepseek": 0.14,  # Cheap
    "gemini": 0.075,  # Cheap
    "moonshot": 0.2,  # Mid-range
    "openai": 0.5,  # Expensive (GPT-4)
    "anthropic": 1.0,  # Expensive (Claude)
}

# ============================================================================
# Query Complexity Classification
# ============================================================================

# Markers for simple queries
SIMPLE_MARKERS = {
    "translate": 2.0,
    "classify": 2.0,
    "label": 2.0,
    "category": 1.5,
    "sentiment": 1.5,
    "summary": 1.0,
    "what is": 0.5,
    "define": 1.0,
    "lookup": 1.5,
    "fact": 1.0,
    "find": 0.5,
}

# Markers for complex queries
COMPLEX_MARKERS = {
    "explain": 1.5,
    "analyze": 2.0,
    "creative": 3.0,
    "generate": 2.5,
    "write": 2.5,
    "compose": 2.5,
    "design": 2.5,
    "strategy": 2.5,
    "research": 2.0,
    "compare": 1.5,
    "evaluate": 2.0,
    "reasoning": 3.0,
    "debate": 2.5,
    "argue": 2.5,
    "synthesis": 2.5,
    "novel": 3.0,
    "original": 3.0,
    "complex": 2.0,
    "difficult": 1.5,
}

# Instruction density markers (more instructions = more complex)
INSTRUCTION_MARKERS = [
    r"step\s*\d+",  # Numbered steps
    r"first.*then.*finally",  # Sequencing
    r"break.*down",  # Decomposition
    r"consider.*factors",  # Multi-factor
    r"multiple.*perspectives",  # Multiple viewpoints
    r"trade.*off",  # Trade-offs
    r"pros.*cons",  # Balanced analysis
    r"iteratively",  # Iteration
    r"recursively",  # Recursion
    r"chain.*thought",  # Complex reasoning
]


def classify_query_complexity(query: str) -> Literal["simple", "medium", "complex"]:
    """Classify query complexity based on heuristics.

    Analyzes word count, question markers, instruction density, and
    semantic keywords to determine appropriate cost tier.

    Args:
        query: the user query to classify

    Returns:
        Literal["simple", "medium", "complex"] indicating cost tier

    Examples:
        >>> classify_query_complexity("translate hello to French")
        'simple'
        >>> classify_query_complexity("analyze market trends")
        'medium'
        >>> classify_query_complexity("design a novel payment system considering...")
        'complex'
    """
    if not query or not isinstance(query, str):
        return "medium"  # Default to safe middle ground

    query_lower = query.lower()
    query_words = query_lower.split()
    word_count = len(query_words)

    # ── Score-based classification ──
    complexity_score = 0.0

    # 1. Word count heuristic (longer often = more complex)
    if word_count < 5:
        complexity_score -= 2.0
    elif word_count < 15:
        complexity_score -= 1.0
    elif word_count < 30:
        complexity_score += 0.5
    elif word_count < 100:
        complexity_score += 1.5
    else:  # 100+ words
        complexity_score += 2.5

    # 2. Question type analysis
    if query_lower.startswith("what is "):
        complexity_score -= 1.5
    elif query_lower.startswith(("when ", "where ", "which ")):
        complexity_score -= 1.0
    elif query_lower.startswith("how"):
        complexity_score += 0.5
    elif query_lower.startswith("why"):
        complexity_score += 1.5

    # 3. Simple keyword markers (reduce score)
    for marker, weight in SIMPLE_MARKERS.items():
        if marker in query_lower:
            complexity_score -= weight
            break  # Only apply strongest simple marker

    # 4. Complex keyword markers (increase score)
    complex_marker_count = 0
    for marker, weight in COMPLEX_MARKERS.items():
        if marker in query_lower:
            complexity_score += weight
            complex_marker_count += 1
    # Apply diminishing returns for multiple complex markers
    if complex_marker_count > 2:
        complexity_score *= 0.8

    # 5. Instruction density (multiple instructions = complex)
    instruction_count = sum(
        1 for pattern in INSTRUCTION_MARKERS
        if re.search(pattern, query_lower)
    )
    complexity_score += instruction_count * 1.5

    # 6. Punctuation analysis
    if query.count("?") > 1:
        complexity_score += 1.0  # Multiple questions = exploration
    if query.count(";") > 0:
        complexity_score += 1.0  # Semicolons indicate structure
    if query.count(",") > 4:
        complexity_score += 1.5  # Many clauses = complex

    # 7. Special patterns
    if re.search(r"if\s+\w+\s+then", query_lower):
        complexity_score += 2.0  # Conditional logic
    if re.search(r"(?:and|or)\s+(?:and|or)", query_lower):
        complexity_score += 1.0  # Boolean expressions

    # ── Classify based on final score ──
    logger.debug(
        "query_complexity_classified word_count=%d score=%.1f query_len=%d",
        word_count,
        complexity_score,
        len(query),
    )

    if complexity_score < -1.0:
        return "simple"
    elif complexity_score > 2.0:
        return "complex"
    else:
        return "medium"


def estimate_token_count(text: str) -> int:
    """Rough estimate of token count (for cost calculation).

    Uses simple heuristic: ~4 characters per token (typical for English).
    More accurate for cost estimation than character count.

    Args:
        text: input text

    Returns:
        Estimated token count
    """
    # Rough estimate: 1 token ≈ 4 characters
    # More accurate: average is 4.5 chars/token, but 4 is conservative
    return max(1, len(text) // 4)


def estimate_response_tokens(complexity: Literal["simple", "medium", "complex"]) -> int:
    """Estimate expected response length based on complexity.

    Args:
        complexity: query complexity tier

    Returns:
        Estimated output tokens
    """
    estimates = {
        "simple": 100,  # Short factual answer
        "medium": 300,  # Moderate analysis
        "complex": 800,  # Long-form synthesis
    }
    return estimates[complexity]


def estimate_call_cost(
    complexity: Literal["simple", "medium", "complex"],
    provider: str,
    query: str,
    response_tokens: int | None = None,
) -> float:
    """Estimate cost in USD for a single LLM call.

    Args:
        complexity: query complexity tier
        provider: provider name
        query: the query text (for input token estimation)
        response_tokens: override expected output tokens

    Returns:
        Estimated cost in USD
    """
    if provider not in PROVIDER_COSTS:
        return 0.01  # Default conservative estimate

    cost_per_1m = PROVIDER_COSTS[provider]
    if cost_per_1m == 0.0:
        return 0.0  # Free tier

    input_tokens = estimate_token_count(query)
    output_tokens = response_tokens or estimate_response_tokens(complexity)
    total_tokens = input_tokens + output_tokens

    # Cost in USD for this call
    return (total_tokens / 1_000_000) * cost_per_1m


async def research_route_to_model(
    query: str,
    override_complexity: str = "",
) -> dict[str, Any]:
    """Route a query to the optimal cost tier and provider.

    Analyzes query complexity and returns routing recommendation with
    cost estimates. Useful for cost-aware agent orchestration.

    Args:
        query: the user query to route
        override_complexity: force a complexity tier ("simple", "medium", "complex")

    Returns:
        Dict with keys:
            - complexity: detected complexity tier
            - recommended_provider: best provider for this tier
            - alternatives: other providers in this tier
            - tier_cost: estimated cost tier (free/cheap/expensive)
            - estimated_input_tokens: estimated input tokens
            - estimated_output_tokens: estimated output tokens
            - estimated_cost_usd: estimated call cost
            - tier_config: configuration for this tier
            - explanation: human-readable explanation of routing

    Example:
        >>> result = await research_route_to_model("translate hello to French")
        >>> result["complexity"]
        'simple'
        >>> result["recommended_provider"]
        'groq'
        >>> result["estimated_cost_usd"]
        0.0
    """
    try:
        # Determine complexity
        if override_complexity and override_complexity in MODEL_ROUTING:
            complexity = override_complexity
        else:
            complexity = classify_query_complexity(query)

        tier_config = MODEL_ROUTING[complexity]
        providers = tier_config["providers"]
        recommended = providers[0] if providers else "groq"
        alternatives = providers[1:] if len(providers) > 1 else []

        # Estimate tokens and cost
        input_tokens = estimate_token_count(query)
        output_tokens = estimate_response_tokens(complexity)
        estimated_cost = estimate_call_cost(complexity, recommended, query, output_tokens)

        result = {
            "complexity": complexity,
            "recommended_provider": recommended,
            "alternatives": alternatives,
            "tier_cost": tier_config["tier"],
            "estimated_input_tokens": input_tokens,
            "estimated_output_tokens": output_tokens,
            "estimated_total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(estimated_cost, 5),
            "tier_config": {
                "tier": tier_config["tier"],
                "providers": tier_config["providers"],
                "max_tokens": tier_config["max_tokens"],
                "description": tier_config["description"],
            },
            "explanation": (
                f"Query classified as {complexity} (tier: {tier_config['tier']}) "
                f"— routing to {recommended}. "
                f"Estimated cost: ${estimated_cost:.5f}. "
                f"Alternative providers: {', '.join(alternatives) if alternatives else 'none'}"
            ),
        }

        logger.info(
            "query_routed complexity=%s provider=%s cost=$%.5f tokens=%d+%d",
            complexity,
            recommended,
            estimated_cost,
            input_tokens,
            output_tokens,
        )

        return result
    except Exception as exc:
        logger.error("research_route_to_model failed: %s", exc)
        return {
            "error": str(exc),
            "tool": "research_route_to_model",
        }


def get_starting_provider(complexity: Literal["simple", "medium", "complex"]) -> str:
    """Get the first provider to try for a given complexity tier.

    Args:
        complexity: query complexity

    Returns:
        Provider name to start cascade with
    """
    return MODEL_ROUTING[complexity]["providers"][0]


def get_provider_tier(provider: str) -> str:
    """Get cost tier for a provider.

    Args:
        provider: provider name

    Returns:
        Cost tier: "free", "cheap", or "expensive"
    """
    for tier_name, tier_info in MODEL_ROUTING.items():
        if provider in tier_info["providers"]:
            return tier_info["tier"]
    return "expensive"  # Unknown = treat as expensive


def should_skip_provider(
    provider: str,
    complexity: Literal["simple", "medium", "complex"],
) -> bool:
    """Check if provider should be skipped for this complexity tier.

    Returns True if provider is in a higher cost tier than the query complexity,
    allowing the router to skip expensive providers for cheap queries.

    Args:
        provider: provider name
        complexity: query complexity

    Returns:
        True if provider should be skipped (cost-prohibitive)
    """
    tier_cost = get_provider_tier(provider)
    query_tier = MODEL_ROUTING[complexity]["tier"]

    tier_order = {"free": 0, "cheap": 1, "expensive": 2}
    provider_level = tier_order.get(tier_cost, 2)
    query_level = tier_order.get(query_tier, 1)

    # Skip provider if it's significantly more expensive than needed
    # Allow 1-level jump (e.g., use cheap for medium, use expensive for cheap)
    # but don't jump 2+ levels (e.g., don't use expensive for simple)
    return provider_level > query_level + 1
