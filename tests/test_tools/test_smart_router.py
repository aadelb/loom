"""Unit tests for Smart Search Router — intent detection and tool routing."""

from __future__ import annotations

import pytest

from loom.tools.llm.smart_router import (
    research_route_query,
    research_route_batch,
)


class TestRouteQueryIntentDetection:
    """Tests for query intent detection and routing."""

    @pytest.mark.asyncio
    async def test_detect_academic_intent(self) -> None:
        """Academic queries route to arxiv provider."""
        result = await research_route_query("paper on neural networks arxiv")

        assert result["detected_intent"] == "academic"
        assert result["recommended_tool"] == "research_search"
        assert result["provider_hint"] == "arxiv"
        assert result["confidence"] > 0.2

    @pytest.mark.asyncio
    async def test_detect_code_intent(self) -> None:
        """Code/repo queries route to GitHub."""
        result = await research_route_query("github FastAPI python library")

        assert result["detected_intent"] == "code"
        assert result["recommended_tool"] == "research_github"
        assert result["provider_hint"] == "github"
        assert result["confidence"] > 0.2

    @pytest.mark.asyncio
    async def test_detect_news_intent(self) -> None:
        """News queries route to newsapi provider."""
        result = await research_route_query("latest news today breaking")

        assert result["detected_intent"] == "news"
        assert result["recommended_tool"] == "research_search"
        assert result["provider_hint"] == "newsapi"
        assert result["confidence"] > 0.2

    @pytest.mark.asyncio
    async def test_detect_dark_intent(self) -> None:
        """Dark web queries route to darknet forums."""
        result = await research_route_query("onion forums darknet site tor")

        assert result["detected_intent"] == "dark"
        assert result["recommended_tool"] == "research_dark_forum"
        assert result["provider_hint"] == "darkweb"
        assert result["confidence"] > 0.2

    @pytest.mark.asyncio
    async def test_detect_person_intent(self) -> None:
        """Person queries route to identity resolution."""
        result = await research_route_query("who is John Doe profile")

        assert result["detected_intent"] == "person"
        assert result["recommended_tool"] == "research_identity_resolve"
        assert result["confidence"] > 0.2

    @pytest.mark.asyncio
    async def test_detect_infrastructure_intent(self) -> None:
        """Infrastructure queries route to whois/dns."""
        result = await research_route_query("whois example.com dns lookup")

        assert result["detected_intent"] == "infrastructure"
        assert result["recommended_tool"] == "research_whois"
        assert result["provider_hint"] == "whois"
        assert result["confidence"] > 0.2

    @pytest.mark.asyncio
    async def test_fallback_to_general_intent(self) -> None:
        """Ambiguous queries fall back to general intent."""
        result = await research_route_query("random query with no specifics")

        assert result["detected_intent"] == "general"
        assert result["recommended_tool"] == "research_deep"

    @pytest.mark.asyncio
    async def test_force_intent_override(self) -> None:
        """Forcing intent overrides auto-detection."""
        result = await research_route_query(
            "example.com",
            intent="academic"
        )

        assert result["detected_intent"] == "academic"
        assert result["confidence"] == 1.0
        assert "forced" in result["routing_reason"].lower()

    @pytest.mark.asyncio
    async def test_invalid_forced_intent_returns_error(self) -> None:
        """Invalid forced intent returns error."""
        result = await research_route_query(
            "example.com",
            intent="invalid_intent"
        )

        assert "error" in result
        assert "unknown intent" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self) -> None:
        """Empty query returns error."""
        result = await research_route_query("")

        assert "error" in result
        assert result["recommended_tool"] is None

    @pytest.mark.asyncio
    async def test_none_query_returns_error(self) -> None:
        """None query returns error."""
        result = await research_route_query(None)

        assert "error" in result
        assert result["recommended_tool"] is None

    @pytest.mark.asyncio
    async def test_response_includes_alternatives(self) -> None:
        """Response includes alternative tools."""
        result = await research_route_query("github python repository")

        assert "alternative_tools" in result
        assert isinstance(result["alternative_tools"], list)
        assert len(result["alternative_tools"]) > 0

    @pytest.mark.asyncio
    async def test_response_includes_tips(self) -> None:
        """Response includes quick tips for intent."""
        result = await research_route_query("arxiv research paper")

        assert "quick_tips" in result
        assert isinstance(result["quick_tips"], list)
        assert len(result["quick_tips"]) > 0

    @pytest.mark.asyncio
    async def test_confidence_calculation(self) -> None:
        """Confidence score is between 0.0 and 1.0."""
        result = await research_route_query("random search")

        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["confidence"], float)

    @pytest.mark.asyncio
    async def test_case_insensitive_detection(self) -> None:
        """Intent detection is case-insensitive."""
        result_lower = await research_route_query("arxiv paper research")
        result_upper = await research_route_query("ARXIV PAPER RESEARCH")

        assert result_lower["detected_intent"] == result_upper["detected_intent"]

    @pytest.mark.asyncio
    async def test_whitespace_normalization(self) -> None:
        """Queries are properly normalized."""
        result = await research_route_query("  arxiv paper  \n  research  ")

        assert result["detected_intent"] == "academic"

    @pytest.mark.asyncio
    async def test_confidence_increases_with_keywords(self) -> None:
        """Confidence increases with more matching keywords."""
        single = await research_route_query("arxiv")
        multiple = await research_route_query("arxiv paper research publication journal")

        assert multiple["confidence"] > single["confidence"]


class TestRouteBatchProcessing:
    """Tests for batch routing functionality."""

    @pytest.mark.asyncio
    async def test_batch_routes_multiple_queries(self) -> None:
        """Batch routing processes multiple queries."""
        queries = [
            "github python repository",
            "arxiv research paper",
            "latest news today"
        ]
        result = await research_route_batch(queries)

        assert result["total_queries"] == 3
        assert len(result["routes"]) == 3
        assert all("detected_intent" in route for route in result["routes"])

    @pytest.mark.asyncio
    async def test_batch_aggregates_tool_distribution(self) -> None:
        """Batch returns tool distribution."""
        queries = [
            "github repo 1",
            "github repo 2",
            "arxiv paper"
        ]
        result = await research_route_batch(queries)

        assert "tool_distribution" in result
        assert isinstance(result["tool_distribution"], dict)
        assert "research_github" in result["tool_distribution"]
        assert result["tool_distribution"]["research_github"] >= 2

    @pytest.mark.asyncio
    async def test_batch_aggregates_intent_distribution(self) -> None:
        """Batch returns intent distribution."""
        queries = [
            "github repo",
            "arxiv paper",
            "news today"
        ]
        result = await research_route_batch(queries)

        assert "intent_distribution" in result
        assert "code" in result["intent_distribution"]
        assert "academic" in result["intent_distribution"]
        assert "news" in result["intent_distribution"]

    @pytest.mark.asyncio
    async def test_batch_empty_list_returns_error(self) -> None:
        """Empty batch list returns error."""
        result = await research_route_batch([])

        assert "error" in result
        assert result["total_queries"] == 0

    @pytest.mark.asyncio
    async def test_batch_invalid_input_returns_error(self) -> None:
        """Invalid input type returns error."""
        result = await research_route_batch("not a list")

        assert "error" in result
        assert result["total_queries"] == 0

    @pytest.mark.asyncio
    async def test_batch_summary_generated(self) -> None:
        """Batch returns helpful summary."""
        queries = [
            "github python",
            "github rust",
            "arxiv"
        ]
        result = await research_route_batch(queries)

        assert "recommendation_summary" in result
        assert "Routed" in result["recommendation_summary"]
        assert str(len(queries)) in result["recommendation_summary"]

    @pytest.mark.asyncio
    async def test_batch_skips_empty_strings(self) -> None:
        """Batch skips empty/invalid queries gracefully."""
        queries = [
            "github python",
            "",
            None,
            "arxiv paper"
        ]
        result = await research_route_batch(queries)

        assert result["total_queries"] == 2

    @pytest.mark.asyncio
    async def test_batch_tool_distribution_sorted(self) -> None:
        """Tool distribution is sorted by count descending."""
        queries = [
            "github repo",
            "github another",
            "github third",
            "arxiv paper"
        ]
        result = await research_route_batch(queries)

        tools_list = list(result["tool_distribution"].items())
        # Check if sorted by count descending
        counts = [count for _, count in tools_list]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    async def test_batch_large_query_list(self) -> None:
        """Batch handles large query lists."""
        queries = [f"query {i}" for i in range(100)]
        result = await research_route_batch(queries)

        assert result["total_queries"] == 100
        assert len(result["routes"]) == 100


class TestIntegration:
    """Integration tests for routing with various query patterns."""

    @pytest.mark.asyncio
    async def test_mixed_keywords_high_confidence(self) -> None:
        """Multiple keywords increase confidence."""
        single_keyword = await research_route_query("arxiv")
        multi_keyword = await research_route_query(
            "arxiv paper research publication scholar"
        )

        assert multi_keyword["confidence"] > single_keyword["confidence"]

    @pytest.mark.asyncio
    async def test_specific_urls_route_correctly(self) -> None:
        """URLs with specific domains route correctly."""
        github_result = await research_route_query("github.com/user/repo")
        assert github_result["detected_intent"] == "code"

        arxiv_result = await research_route_query("arxiv.org/abs/2301.00001")
        assert arxiv_result["detected_intent"] == "academic"

    @pytest.mark.asyncio
    async def test_response_consistency(self) -> None:
        """Same query produces consistent routing."""
        query = "github python library"
        result1 = await research_route_query(query)
        result2 = await research_route_query(query)

        assert result1["detected_intent"] == result2["detected_intent"]
        assert result1["recommended_tool"] == result2["recommended_tool"]
        assert result1["confidence"] == result2["confidence"]
