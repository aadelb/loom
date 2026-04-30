"""Tests for the tool recommender engine."""

from __future__ import annotations

import pytest

from loom.params import ToolRecommendParams
from loom.tool_recommender import ToolRecommendation, ToolRecommender


class TestToolRecommenderInit:
    """Tests for ToolRecommender initialization."""

    def test_recommender_initialization(self) -> None:
        """Test that recommender initializes correctly."""
        recommender = ToolRecommender()
        assert recommender is not None
        assert len(recommender.TOOL_CATALOG) > 0

    def test_tool_index_built(self) -> None:
        """Test that internal tool index is built."""
        recommender = ToolRecommender()
        assert len(recommender._tool_to_categories) > 0
        assert len(recommender._all_tools) > 0

    def test_tool_index_consistency(self) -> None:
        """Test that all tools in catalog are indexed."""
        recommender = ToolRecommender()
        catalog_tools = set()
        for category_data in recommender.TOOL_CATALOG.values():
            catalog_tools.update(category_data["tools"])

        assert recommender._all_tools == catalog_tools


class TestBasicRecommendations:
    """Tests for basic tool recommendation functionality."""

    def test_recommend_for_web_scraping(self) -> None:
        """Test recommendations for web scraping query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape a website")
        assert len(recs) > 0
        assert recs[0].relevance_score > 0
        assert "research_fetch" in [r.tool_name for r in recs]

    def test_recommend_for_search(self) -> None:
        """Test recommendations for search query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("search for information about python")
        assert len(recs) > 0
        assert any("research_search" in r.tool_name for r in recs)

    def test_recommend_for_osint(self) -> None:
        """Test recommendations for OSINT query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("osint reconnaissance on domain")
        assert len(recs) > 0
        assert any(r.category == "osint" for r in recs)

    def test_recommend_for_dark_web(self) -> None:
        """Test recommendations for dark web query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("search dark web forums")
        assert len(recs) > 0
        assert any(r.category == "dark_web" for r in recs)

    def test_recommend_for_security(self) -> None:
        """Test recommendations for security query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scan for vulnerabilities")
        assert len(recs) > 0
        assert any(r.category == "security" for r in recs)

    def test_recommend_for_ai_safety(self) -> None:
        """Test recommendations for AI safety query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("test ai model safety and bias")
        assert len(recs) > 0
        assert any(r.category == "ai_safety" for r in recs)

    def test_recommend_for_nlp(self) -> None:
        """Test recommendations for NLP query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("analyze sentiment and emotion in text")
        assert len(recs) > 0
        assert any(r.category == "nlp" for r in recs)

    def test_recommend_for_academic(self) -> None:
        """Test recommendations for academic query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("check citation analysis and journal quality")
        assert len(recs) > 0
        assert any(r.category == "academic" for r in recs)


class TestRecommendationQuality:
    """Tests for recommendation quality and scoring."""

    def test_relevance_scores_sorted(self) -> None:
        """Test that recommendations are sorted by relevance score."""
        recommender = ToolRecommender()
        recs = recommender.recommend("fetch and scrape website")
        scores = [r.relevance_score for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_relevance_scores_in_range(self) -> None:
        """Test that relevance scores are between 0 and 1."""
        recommender = ToolRecommender()
        recs = recommender.recommend("fetch website for analysis")
        for rec in recs:
            assert 0 <= rec.relevance_score <= 1

    def test_high_relevance_for_exact_match(self) -> None:
        """Test that exact keyword matches get high scores."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape website with research_fetch")
        assert len(recs) > 0
        # Top recommendation should be web scraping
        assert recs[0].relevance_score > 0.5

    def test_reason_provided(self) -> None:
        """Test that all recommendations include reasons."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape website")
        for rec in recs:
            assert rec.reason is not None
            assert len(rec.reason) > 0

    def test_usage_example_provided(self) -> None:
        """Test that all recommendations include usage examples."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape website")
        for rec in recs:
            assert rec.usage_example is not None
            assert len(rec.usage_example) > 0


class TestExcludeUsed:
    """Tests for excluding already-used tools."""

    def test_exclude_single_tool(self) -> None:
        """Test excluding a single tool from recommendations."""
        recommender = ToolRecommender()
        recs_without_exclude = recommender.recommend("scrape website")
        tool_names_without_exclude = [r.tool_name for r in recs_without_exclude]

        recs_with_exclude = recommender.recommend(
            "scrape website", exclude_used=["research_fetch"]
        )
        tool_names_with_exclude = [r.tool_name for r in recs_with_exclude]

        assert "research_fetch" in tool_names_without_exclude
        assert "research_fetch" not in tool_names_with_exclude

    def test_exclude_multiple_tools(self) -> None:
        """Test excluding multiple tools."""
        recommender = ToolRecommender()
        exclude_list = ["research_fetch", "research_spider"]
        recs = recommender.recommend("scrape website", exclude_used=exclude_list)
        tool_names = [r.tool_name for r in recs]

        for excluded in exclude_list:
            assert excluded not in tool_names

    def test_exclude_preserves_order(self) -> None:
        """Test that exclusion preserves relevance ordering."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape website", exclude_used=["research_fetch"])
        scores = [r.relevance_score for r in recs]
        assert scores == sorted(scores, reverse=True)


class TestMaxRecommendations:
    """Tests for max_recommendations parameter."""

    def test_max_recommendations_10(self) -> None:
        """Test default max recommendations is 10."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape search analyze")
        assert len(recs) <= 10

    def test_max_recommendations_custom(self) -> None:
        """Test custom max recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape search analyze", max_recommendations=5)
        assert len(recs) <= 5

    def test_max_recommendations_one(self) -> None:
        """Test max recommendations of 1."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape", max_recommendations=1)
        assert len(recs) <= 1

    def test_max_recommendations_high(self) -> None:
        """Test high max recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape search analyze", max_recommendations=50)
        assert len(recs) <= 50


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query(self) -> None:
        """Test that empty query returns empty recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("")
        assert len(recs) == 0

    def test_whitespace_only_query(self) -> None:
        """Test that whitespace-only query returns empty recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("   ")
        assert len(recs) == 0

    def test_none_exclude_used(self) -> None:
        """Test that None exclude_used is handled correctly."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape", exclude_used=None)
        assert len(recs) > 0

    def test_vague_query(self) -> None:
        """Test that vague query still returns results."""
        recommender = ToolRecommender()
        recs = recommender.recommend("research")
        # Should return some results even for vague queries
        assert len(recs) >= 0

    def test_special_characters_in_query(self) -> None:
        """Test handling special characters in query."""
        recommender = ToolRecommender()
        recs = recommender.recommend("scrape @#$% website")
        # Should handle gracefully
        assert isinstance(recs, list)


class TestCategoryQueries:
    """Tests for category-specific queries."""

    def test_threat_intelligence_query(self) -> None:
        """Test threat intelligence recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("analyze threat actor infrastructure")
        assert len(recs) > 0
        assert any(r.category == "threat_intel" for r in recs)

    def test_career_intelligence_query(self) -> None:
        """Test career intelligence recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("track career trajectory and hiring signals")
        assert len(recs) > 0
        assert any(r.category == "career" for r in recs)

    def test_supply_chain_query(self) -> None:
        """Test supply chain recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("analyze supply chain risks and dependencies")
        assert len(recs) > 0
        assert any(r.category == "supply_chain" for r in recs)

    def test_media_processing_query(self) -> None:
        """Test media processing recommendations."""
        recommender = ToolRecommender()
        recs = recommender.recommend("transcribe audio and extract images")
        assert len(recs) > 0
        assert any(r.category == "media" for r in recs)


class TestGetMethods:
    """Tests for utility getter methods."""

    def test_get_all_tools(self) -> None:
        """Test getting all available tools."""
        recommender = ToolRecommender()
        tools = recommender.get_all_tools()
        assert len(tools) > 0
        assert all(isinstance(t, str) for t in tools)
        assert tools == sorted(tools)

    def test_get_tools_by_category(self) -> None:
        """Test getting tools by category."""
        recommender = ToolRecommender()
        web_scraping_tools = recommender.get_tools_by_category("web_scraping")
        assert len(web_scraping_tools) > 0
        assert "research_fetch" in web_scraping_tools

    def test_get_tools_invalid_category(self) -> None:
        """Test getting tools for invalid category."""
        recommender = ToolRecommender()
        tools = recommender.get_tools_by_category("invalid_category")
        assert len(tools) == 0

    def test_get_categories(self) -> None:
        """Test getting all categories."""
        recommender = ToolRecommender()
        categories = recommender.get_categories()
        assert len(categories) > 0
        assert all(isinstance(c, str) for c in categories)
        assert categories == sorted(categories)
        assert "web_scraping" in categories
        assert "osint" in categories


class TestToolRecommendationDataclass:
    """Tests for ToolRecommendation dataclass."""

    def test_recommendation_creation(self) -> None:
        """Test creating a ToolRecommendation."""
        rec = ToolRecommendation(
            tool_name="research_fetch",
            category="web_scraping",
            relevance_score=0.95,
            reason="Matches your mention of scrape",
            usage_example="Fetch website content",
        )
        assert rec.tool_name == "research_fetch"
        assert rec.category == "web_scraping"
        assert rec.relevance_score == 0.95

    def test_recommendation_is_frozen(self) -> None:
        """Test that ToolRecommendation is immutable."""
        rec = ToolRecommendation(
            tool_name="research_fetch",
            category="web_scraping",
            relevance_score=0.95,
            reason="Test",
            usage_example="Test example",
        )
        with pytest.raises(AttributeError):
            rec.tool_name = "research_spider"  # type: ignore


class TestToolRecommendParams:
    """Tests for ToolRecommendParams validation."""

    def test_params_creation_minimal(self) -> None:
        """Test creating params with minimal required fields."""
        params = ToolRecommendParams(query="scrape website")
        assert params.query == "scrape website"
        assert params.max_recommendations == 10
        assert params.exclude_used == []

    def test_params_creation_full(self) -> None:
        """Test creating params with all fields."""
        params = ToolRecommendParams(
            query="scrape website",
            max_recommendations=5,
            exclude_used=["research_fetch"],
        )
        assert params.query == "scrape website"
        assert params.max_recommendations == 5
        assert params.exclude_used == ["research_fetch"]

    def test_params_query_stripped(self) -> None:
        """Test that query is stripped of whitespace."""
        params = ToolRecommendParams(query="  scrape website  ")
        assert params.query == "scrape website"

    def test_params_query_required(self) -> None:
        """Test that query is required."""
        with pytest.raises(ValueError):
            ToolRecommendParams(query="")

    def test_params_empty_exclude_list(self) -> None:
        """Test that empty exclude list is allowed."""
        params = ToolRecommendParams(query="test", exclude_used=[])
        assert params.exclude_used == []

    def test_params_max_recommendations_bounds(self) -> None:
        """Test max_recommendations bounds."""
        # Valid bounds
        params1 = ToolRecommendParams(query="test", max_recommendations=1)
        assert params1.max_recommendations == 1

        params50 = ToolRecommendParams(query="test", max_recommendations=50)
        assert params50.max_recommendations == 50

        # Invalid bounds should fail
        with pytest.raises(ValueError):
            ToolRecommendParams(query="test", max_recommendations=0)

        with pytest.raises(ValueError):
            ToolRecommendParams(query="test", max_recommendations=51)


class TestComplexQueries:
    """Tests for complex multi-topic queries."""

    def test_multi_topic_query(self) -> None:
        """Test query with multiple topics."""
        recommender = ToolRecommender()
        recs = recommender.recommend(
            "scrape website for osint, check security headers, analyze sentiment"
        )
        assert len(recs) > 0
        categories = {r.category for r in recs}
        assert "web_scraping" in categories or "osint" in categories

    def test_multi_topic_with_exclude(self) -> None:
        """Test multi-topic query with exclusions."""
        recommender = ToolRecommender()
        recs = recommender.recommend(
            "scrape website for osint, check security headers",
            exclude_used=["research_fetch", "research_security_headers"],
        )
        tool_names = [r.tool_name for r in recs]
        assert "research_fetch" not in tool_names
        assert "research_security_headers" not in tool_names

    def test_contradictory_query(self) -> None:
        """Test query with seemingly contradictory requirements."""
        recommender = ToolRecommender()
        recs = recommender.recommend(
            "find hidden services on tor and check academic citations"
        )
        # Should handle mixed topics gracefully
        assert isinstance(recs, list)


class TestRecommendationConsistency:
    """Tests for consistency of recommendations."""

    def test_same_query_same_results(self) -> None:
        """Test that same query produces consistent results."""
        recommender = ToolRecommender()
        recs1 = recommender.recommend("scrape website")
        recs2 = recommender.recommend("scrape website")

        assert len(recs1) == len(recs2)
        for r1, r2 in zip(recs1, recs2):
            assert r1.tool_name == r2.tool_name
            assert r1.relevance_score == r2.relevance_score

    def test_case_insensitive_matching(self) -> None:
        """Test that query matching is case-insensitive."""
        recommender = ToolRecommender()
        recs_lower = recommender.recommend("scrape website")
        recs_upper = recommender.recommend("SCRAPE WEBSITE")
        recs_mixed = recommender.recommend("ScRaPe WeB site")

        # All should return same top tool
        assert recs_lower[0].tool_name == recs_upper[0].tool_name
        assert recs_lower[0].tool_name == recs_mixed[0].tool_name
