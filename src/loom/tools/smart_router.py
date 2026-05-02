"""Smart Search Router — Route queries to optimal providers based on intent detection."""

from __future__ import annotations

import re
from typing import Any


# Intent detection keyword mappings
_INTENT_KEYWORDS: dict[str, list[str]] = {
    "academic": [
        "paper", "research", "study", "arxiv", "journal", "publication",
        "peer-reviewed", "doi:", "doi.org", "scholar", "academic"
    ],
    "code": [
        "github", "repo", "repository", "function", "library", "package",
        "source code", "git", "code", "algorithm", "implementation",
        "codebase", "commit", "pull request", "issue:"
    ],
    "news": [
        "latest", "today", "breaking", "news", "current", "recent",
        "today's", "this week", "this month", "announcement", "alert"
    ],
    "dark": [
        "onion", "tor", "darknet", "dark web", "forum", ".onion",
        "darkweb", "dark-web", "underground", "hidden service"
    ],
    "person": [
        "who is", "profile", "biography", "about", "@", "person:",
        "people:", "researcher:", "author:", "developer:", "contact"
    ],
    "infrastructure": [
        "whois", "dns", "ip", "ipv4", "ipv6", "domain", "cert",
        "certificate", ".com", ".org", ".net", "nameserver", "ip address"
    ],
    "identity": [
        "identity", "locate", "find person", "phone", "email lookup",
        "reverse lookup", "username", "social media", "profile"
    ]
}

# Confidence thresholds for intent detection
_CONFIDENCE_HIGH = 0.9
_CONFIDENCE_MEDIUM = 0.7


def _detect_intent(query: str) -> tuple[str, float, str]:
    """Detect query intent and return intent type, confidence, and reason.

    Args:
        query: The search query string

    Returns:
        Tuple of (intent, confidence, reason)
    """
    query_lower = query.lower()
    scores: dict[str, float] = {}

    for intent, keywords in _INTENT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        scores[intent] = matches / len(keywords) if keywords else 0.0

    if not scores or max(scores.values()) == 0:
        return "general", 0.5, "No specific intent keywords detected"

    best_intent = max(scores, key=scores.get)
    confidence = scores[best_intent]

    if confidence >= _CONFIDENCE_HIGH:
        return best_intent, confidence, f"Strong match on {best_intent} keywords"
    elif confidence >= _CONFIDENCE_MEDIUM:
        return best_intent, confidence, f"Moderate match on {best_intent} keywords"

    return "general", 0.5, "Low confidence on any single intent"


def _get_recommended_tool(intent: str) -> tuple[str, str, list[str]]:
    """Get recommended tool and alternatives for detected intent.

    Args:
        intent: The detected intent type

    Returns:
        Tuple of (tool_name, provider_hint, alternatives_list)
    """
    routing_map: dict[str, tuple[str, str, list[str]]] = {
        "academic": (
            "research_search",
            "arxiv",
            ["research_deep", "research_search_wikipedia"]
        ),
        "code": (
            "research_github",
            "github",
            ["research_search", "research_deep"]
        ),
        "news": (
            "research_search",
            "newsapi",
            ["research_search_hackernews", "research_deep"]
        ),
        "dark": (
            "research_dark_forum",
            "darkweb",
            ["research_search_onionsearch", "research_search_torcrawl"]
        ),
        "person": (
            "research_identity_resolve",
            "identity",
            ["research_social_intel", "research_deep"]
        ),
        "infrastructure": (
            "research_whois",
            "whois",
            ["research_domain_intel", "research_search"]
        ),
        "identity": (
            "research_identity_resolve",
            "identity",
            ["research_social_intel", "research_search"]
        ),
        "general": (
            "research_deep",
            "general",
            ["research_search", "research_spider"]
        ),
    }

    return routing_map.get(intent, routing_map["general"])


async def research_route_query(
    query: str,
    intent: str = "auto",
) -> dict[str, Any]:
    """Route a query to the optimal search tool/provider.

    Analyzes query intent and recommends the best tool and provider
    for executing the search, with confidence scoring and alternatives.

    Args:
        query: The search query string
        intent: Force intent type ("auto", "academic", "code", "news", "dark",
                "person", "infrastructure", "identity", "general")

    Returns:
        Dict with keys:
            - query: The input query
            - detected_intent: Auto-detected or forced intent
            - recommended_tool: Best tool for this query
            - provider_hint: Recommended provider
            - confidence: Confidence score (0.0-1.0)
            - routing_reason: Explanation of routing decision
            - alternative_tools: List of alternative tools to try
            - quick_tips: Practical suggestions for best results
    """
    if not query or not isinstance(query, str):
        return {
            "query": query,
            "error": "Query must be a non-empty string",
            "detected_intent": None,
            "recommended_tool": None,
        }

    query_clean = query.strip()

    if intent == "auto":
        detected_intent, confidence, reason = _detect_intent(query_clean)
    else:
        if intent not in _INTENT_KEYWORDS and intent != "general":
            return {
                "query": query_clean,
                "error": f"Unknown intent: {intent}",
                "detected_intent": None,
                "recommended_tool": None,
            }
        detected_intent = intent
        confidence = 1.0
        reason = f"Intent forced to: {intent}"

    tool, provider, alternatives = _get_recommended_tool(detected_intent)

    tips_map: dict[str, list[str]] = {
        "academic": [
            "Include paper titles or arxiv IDs for better results",
            "Use DOI or researcher names for targeted searches",
            "Consider date range filters for recent publications"
        ],
        "code": [
            "Specify language (Python, Rust, JavaScript, etc.)",
            "Include repo name or author for better precision",
            "Use GitHub search syntax for advanced queries"
        ],
        "news": [
            "Specify date range for recent vs. historical news",
            "Use provider=newsapi for current news sources",
            "Include source domain if targeting specific outlets"
        ],
        "dark": [
            "Tor connectivity required for darknet searches",
            "Use onion site names or aliases for accuracy",
            "Consider language preferences (Arabic, Chinese, etc.)"
        ],
        "person": [
            "Include full name or username for better accuracy",
            "Combine with location or organization for specificity",
            "Use email or phone if available for verification"
        ],
        "infrastructure": [
            "Use IP address or domain name directly",
            "Include TLD for domain-based searches",
            "Certificate analysis useful for SSL/TLS research"
        ],
        "general": [
            "Use research_deep for comprehensive multi-stage research",
            "Combine with research_spider for batch URL processing",
            "Leverage research_search for quick semantic searches"
        ],
    }

    return {
        "query": query_clean,
        "detected_intent": detected_intent,
        "recommended_tool": tool,
        "provider_hint": provider,
        "confidence": round(confidence, 2),
        "routing_reason": reason,
        "alternative_tools": alternatives,
        "quick_tips": tips_map.get(detected_intent, []),
    }


async def research_route_batch(
    queries: list[str],
) -> dict[str, Any]:
    """Route multiple queries in batch and return routing statistics.

    Efficiently routes a list of queries and returns aggregated
    routing statistics with tool distribution and recommendations.

    Args:
        queries: List of query strings to route

    Returns:
        Dict with keys:
            - routes: List of routing results for each query
            - tool_distribution: Dict of tool -> count
            - intent_distribution: Dict of intent -> count
            - total_queries: Total number of queries routed
            - recommendation_summary: Text summary of routing decisions
    """
    if not queries:
        return {
            "error": "Queries list cannot be empty",
            "routes": [],
            "total_queries": 0,
        }

    if not isinstance(queries, list):
        return {
            "error": "Queries must be a list",
            "routes": [],
            "total_queries": 0,
        }

    routes = []
    tool_counts: dict[str, int] = {}
    intent_counts: dict[str, int] = {}

    for query in queries:
        if isinstance(query, str) and query.strip():
            route_result = await research_route_query(query, intent="auto")
            routes.append(route_result)

            if "recommended_tool" in route_result and route_result["recommended_tool"]:
                tool = route_result["recommended_tool"]
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

            if "detected_intent" in route_result and route_result["detected_intent"]:
                intent = route_result["detected_intent"]
                intent_counts[intent] = intent_counts.get(intent, 0) + 1

    if tool_counts:
        top_tool = max(tool_counts, key=tool_counts.get)
        summary = (
            f"Routed {len(routes)} queries to {len(tool_counts)} tools. "
            f"Most common: {top_tool} ({tool_counts[top_tool]} queries)"
        )
    else:
        summary = f"Routed {len(routes)} queries with mixed/failed results"

    return {
        "routes": routes,
        "tool_distribution": dict(sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)),
        "intent_distribution": dict(sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)),
        "total_queries": len(routes),
        "recommendation_summary": summary,
    }
