"""Tool recommender MCP tool implementation."""

from __future__ import annotations

import logging
from typing import Any

try:
    from loom.params import ToolRecommendParams
    from loom.tool_recommender import ToolRecommender
    _RECOMMENDER_AVAILABLE = True
except ImportError:
    _RECOMMENDER_AVAILABLE = False

log = logging.getLogger("loom.tools.tool_recommender_tool")

# Global recommender instance
_recommender: ToolRecommender | None = None


def _get_recommender() -> ToolRecommender:
    """Get or create the tool recommender instance."""
    global _recommender
    if _recommender is None:
        _recommender = ToolRecommender()
    return _recommender


async def research_recommend_tools(
    query: str,
    max_recommendations: int = 10,
    exclude_used: list[str] | None = None,
) -> dict[str, Any]:
    """Recommend relevant Loom tools based on a research query.

    This tool intelligently suggests which Loom tools are most relevant to
    your research task by analyzing your query text and matching it against
    tool categories and keywords.

    Usage:
        1. Describe your research goal: "Find information about AI safety vulnerabilities"
        2. Get relevant tool recommendations with relevance scores
        3. Exclude tools you've already tried with exclude_used parameter

    Args:
        query: Your research task or question (e.g., "I need to scrape a website")
        max_recommendations: How many tools to recommend (1-50, default 10)
        exclude_used: List of tool names to skip in recommendations

    Returns:
        Dictionary with:
        - recommendations: List of recommended tools with scores and examples
        - categories: Tool categories that match your query
        - total_available: Total number of tools in Loom
        - query_summary: Analysis of what the query indicates

    Examples:
        {
            "query": "scrape and analyze a website for security issues",
            "recommendations": [
                {
                    "tool_name": "research_fetch",
                    "category": "web_scraping",
                    "relevance_score": 0.95,
                    "reason": "Matches your mention of: scrape, website",
                    "usage_example": "Fetch and analyze content from https://example.com"
                },
                ...
            ],
            "categories": ["web_scraping", "security"],
            "total_available": 227
        }
    """
    try:
        # Validate parameters
        params = ToolRecommendParams(
            query=query,
            max_recommendations=max_recommendations,
            exclude_used=exclude_used or [],
        )

        recommender = _get_recommender()

        # Get recommendations
        recommendations = recommender.recommend(
            query=params.query,
            max_recommendations=params.max_recommendations,
            exclude_used=params.exclude_used,
        )

        # Get all categories for context
        all_categories = recommender.get_categories()
        total_tools = len(recommender.get_all_tools())

        # Identify which categories match the query
        matched_categories = set()
        query_lower = params.query.lower()
        for category, data in recommender.TOOL_CATALOG.items():
            for keyword in data["keywords"]:
                if keyword in query_lower:
                    matched_categories.add(category)
                    break

        log.info(
            "recommend_tools query_length=%s recommendations_count=%s excluded_count=%s matched_categories=%s",
            len(params.query),
            len(recommendations),
            len(params.exclude_used),
            len(matched_categories),
        )

        return {
            "query": params.query,
            "recommendations": [
                {
                    "tool_name": rec.tool_name,
                    "category": rec.category,
                    "relevance_score": rec.relevance_score,
                    "reason": rec.reason,
                    "usage_example": rec.usage_example,
                }
                for rec in recommendations
            ],
            "categories": sorted(matched_categories) or ["general"],
            "total_available": total_tools,
            "all_categories": all_categories,
            "excluded_tools": params.exclude_used,
        }

    except ValueError as e:
        log.error("validation_error error=%s", str(e))
        raise


# Export tool functions
__all__ = ["research_recommend_tools"]
