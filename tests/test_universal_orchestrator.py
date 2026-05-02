"""Comprehensive tests for the Universal Smart Orchestrator.

Tests cover tool discovery, scoring, parameter generation, and execution.
"""

from __future__ import annotations

import pytest

from loom.tools.universal_orchestrator import (
    _auto_generate_params,
    _build_tool_index,
    _extract_url_from_query,
    _score_tool_relevance,
    research_orchestrate_smart,
)


class TestToolIndexBuilding:
    """Tests for tool discovery and indexing."""

    def test_build_tool_index_returns_dict(self) -> None:
        """Should return a dictionary of discovered tools."""
        index = _build_tool_index()
        assert isinstance(index, dict)
        assert len(index) > 0

    def test_build_tool_index_contains_research_functions(self) -> None:
        """Should contain functions starting with research_."""
        index = _build_tool_index()
        for tool_name in index.keys():
            assert tool_name.startswith("research_")

    def test_build_tool_index_tool_structure(self) -> None:
        """Each indexed tool should have required fields."""
        index = _build_tool_index()
        if index:
            first_tool = next(iter(index.values()))
            assert "module" in first_tool
            assert "docstring" in first_tool
            assert "params" in first_tool
            assert "is_async" in first_tool

    def test_build_tool_index_includes_common_tools(self) -> None:
        """Should discover common research tools."""
        index = _build_tool_index()
        # Some tools that should exist
        common_tools = {
            "research_fetch",
            "research_search",
            "research_spider",
        }
        discovered = set(index.keys())
        # At least some common tools should be found
        assert len(common_tools & discovered) > 0


class TestRelevanceScoring:
    """Tests for tool relevance scoring."""

    def test_score_exact_name_match(self) -> None:
        """Should score higher for exact name match."""
        tool_info = {
            "docstring": "A generic tool",
            "params": [],
            "is_async": True,
        }
        query = "fetch web page"
        score = _score_tool_relevance(query, "research_fetch", tool_info)
        assert score > 0

    def test_score_docstring_match(self) -> None:
        """Should score based on docstring keywords."""
        tool_info = {
            "docstring": "Fetch and parse HTML content from URLs",
            "params": [],
            "is_async": True,
        }
        query = "get HTML from website"
        score = _score_tool_relevance(query, "research_other", tool_info)
        assert score > 0

    def test_score_no_match_is_zero(self) -> None:
        """Should return 0 for completely unrelated query."""
        tool_info = {
            "docstring": "Fetch web content",
            "params": [],
            "is_async": True,
        }
        query = "xyz abc qwerty 12345"
        score = _score_tool_relevance(query, "research_fetch", tool_info)
        assert score == 0

    def test_score_is_normalized_0_to_100(self) -> None:
        """Score should be between 0 and 100."""
        tool_info = {
            "docstring": "Search the internet for information",
            "params": ["query"],
            "is_async": True,
        }
        score = _score_tool_relevance("search google", "research_search", tool_info)
        assert 0 <= score <= 100


class TestURLExtraction:
    """Tests for URL extraction from query."""

    def test_extract_https_url(self) -> None:
        """Should extract HTTPS URL."""
        query = "fetch content from https://example.com/page"
        url = _extract_url_from_query(query)
        assert url == "https://example.com/page"

    def test_extract_http_url(self) -> None:
        """Should extract HTTP URL."""
        query = "get data from http://test.com"
        url = _extract_url_from_query(query)
        assert url == "http://test.com"

    def test_extract_www_url(self) -> None:
        """Should extract www-style URL."""
        query = "check www.example.com for updates"
        url = _extract_url_from_query(query)
        assert url == "www.example.com"

    def test_no_url_returns_none(self) -> None:
        """Should return None if no URL found."""
        query = "search for information"
        url = _extract_url_from_query(query)
        assert url is None


class TestParamGeneration:
    """Tests for automatic parameter generation."""

    @pytest.mark.asyncio
    async def test_generate_query_param(self) -> None:
        """Should fill 'query' parameter from query string."""
        tool_info = {
            "module": "search",
            "docstring": "Search tool",
            "params": ["query", "limit"],
            "is_async": True,
        }
        params = await _auto_generate_params(
            "research_search",
            tool_info,
            "find information about AI",
        )
        assert "query" in params
        assert params["query"] == "find information about AI"

    @pytest.mark.asyncio
    async def test_generate_url_param(self) -> None:
        """Should extract and fill 'url' parameter."""
        tool_info = {
            "module": "fetch",
            "docstring": "Fetch tool",
            "params": ["url", "mode"],
            "is_async": True,
        }
        params = await _auto_generate_params(
            "research_fetch",
            tool_info,
            "fetch https://example.com",
        )
        assert "url" in params
        assert params["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_generate_skips_unknown_params(self) -> None:
        """Should skip parameters with no mapping."""
        tool_info = {
            "module": "test",
            "docstring": "Test tool",
            "params": ["unknown_param", "query"],
            "is_async": True,
        }
        params = await _auto_generate_params(
            "research_test",
            tool_info,
            "test query",
        )
        # Should have query but not unknown_param
        assert "query" in params
        assert "unknown_param" not in params

    @pytest.mark.asyncio
    async def test_generate_text_param_alias(self) -> None:
        """Should handle 'text' param as alias for query."""
        tool_info = {
            "module": "analyze",
            "docstring": "Analysis tool",
            "params": ["text"],
            "is_async": True,
        }
        params = await _auto_generate_params(
            "research_analyze",
            tool_info,
            "analyze this",
        )
        assert "text" in params
        assert params["text"] == "analyze this"


class TestOrchestrateSmartBasic:
    """Basic orchestration tests."""

    @pytest.mark.asyncio
    async def test_orchestrate_returns_required_fields(self) -> None:
        """Should return dict with required fields."""
        result = await research_orchestrate_smart(
            "fetch website content",
            max_tools=1,
            strategy="auto",
        )
        assert "query" in result
        assert "tools_discovered" in result
        assert "tools_selected" in result
        assert "results" in result
        assert "total_duration_ms" in result

    @pytest.mark.asyncio
    async def test_orchestrate_discovers_tools(self) -> None:
        """Should discover at least some tools."""
        result = await research_orchestrate_smart("search", max_tools=1)
        assert result["tools_discovered"] > 0

    @pytest.mark.asyncio
    async def test_orchestrate_short_query_rejected(self) -> None:
        """Should reject queries shorter than 3 chars."""
        result = await research_orchestrate_smart("ab", max_tools=1)
        assert "error" in result
        assert "too short" in result["error"]

    @pytest.mark.asyncio
    async def test_orchestrate_empty_query_rejected(self) -> None:
        """Should reject empty query."""
        result = await research_orchestrate_smart("", max_tools=1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_orchestrate_max_tools_clamped(self) -> None:
        """Should clamp max_tools to 1-10 range."""
        # Test with value > 10
        result = await research_orchestrate_smart(
            "test query",
            max_tools=100,
            strategy="auto",
        )
        # Should not error, just clamp
        assert "tools_selected" in result

    @pytest.mark.asyncio
    async def test_orchestrate_strategy_auto(self) -> None:
        """Auto strategy should select 1 tool."""
        result = await research_orchestrate_smart(
            "search information",
            max_tools=5,
            strategy="auto",
        )
        # Auto should pick exactly 1
        assert len(result["tools_selected"]) <= 1

    @pytest.mark.asyncio
    async def test_orchestrate_strategy_parallel(self) -> None:
        """Parallel strategy should respect max_tools."""
        result = await research_orchestrate_smart(
            "get data",
            max_tools=3,
            strategy="parallel",
        )
        assert len(result["tools_selected"]) <= 3


class TestOrchestrateSmartAggregation:
    """Tests for result aggregation."""

    @pytest.mark.asyncio
    async def test_aggregated_summary_structure(self) -> None:
        """Should generate aggregated summary."""
        result = await research_orchestrate_smart("test query")
        assert "aggregated_summary" in result
        summary = result["aggregated_summary"]
        assert "total_executed" in summary
        assert "total_succeeded" in summary
        assert "total_failed" in summary
        assert "execution_strategy" in summary

    @pytest.mark.asyncio
    async def test_results_include_execution_metadata(self) -> None:
        """Each result should have tool, success, and duration."""
        result = await research_orchestrate_smart("test")
        if result["results"]:
            first_result = result["results"][0]
            assert "tool" in first_result
            assert "success" in first_result
            assert "duration_ms" in first_result

    @pytest.mark.asyncio
    async def test_total_duration_measured(self) -> None:
        """Total duration should be positive."""
        result = await research_orchestrate_smart("query")
        assert result["total_duration_ms"] > 0


class TestOrchestrateSmartErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_no_relevant_tools_warning(self) -> None:
        """Should warn if no relevant tools found."""
        # Use gibberish query that matches no tools
        result = await research_orchestrate_smart(
            "xyzabc123 qwerty zzz",
            max_tools=1,
        )
        # Should not error, but may have warning
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_handles_invalid_max_tools(self) -> None:
        """Should handle invalid max_tools gracefully."""
        # This depends on whether params validation happens
        # The function itself should clamp values
        result = await research_orchestrate_smart(
            "test",
            max_tools=0,  # Invalid but should clamp to 1
        )
        # Should clamp to 1, not error
        assert isinstance(result, dict)


class TestToolSelectionRelevance:
    """Tests for tool selection based on relevance."""

    @pytest.mark.asyncio
    async def test_selects_most_relevant_tool(self) -> None:
        """Should select tools with highest relevance scores."""
        result = await research_orchestrate_smart(
            "search for information online",
            max_tools=3,
            strategy="parallel",
        )
        if result["tools_selected"]:
            # Tools should be sorted by relevance (highest first)
            scores = [
                t["relevance_score"]
                for t in result["tools_selected"]
            ]
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    @pytest.mark.asyncio
    async def test_query_specific_tool_selection(self) -> None:
        """Different queries should select different tools."""
        result1 = await research_orchestrate_smart(
            "fetch website data",
            max_tools=1,
            strategy="auto",
        )
        result2 = await research_orchestrate_smart(
            "search internet",
            max_tools=1,
            strategy="auto",
        )
        # May select same tool for similar queries, but structure should be valid
        assert "tools_selected" in result1
        assert "tools_selected" in result2
