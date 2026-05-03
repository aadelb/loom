"""Test parameter auto-correction system for MCP tools.

Tests the fuzzy matching and auto-correction functionality that maps
misspelled parameter names to correct parameter names.
"""

import asyncio
from typing import Any

import pytest

from loom.server import _fuzzy_correct_params


def dummy_tool(query: str, max_results: int = 10, timeout: float = 30.0) -> dict:
    """Dummy tool for testing parameter correction."""
    return {"query": query, "max_results": max_results, "timeout": timeout}


async def async_dummy_tool(query: str, max_results: int = 10) -> dict:
    """Async dummy tool for testing parameter correction."""
    return {"query": query, "max_results": max_results}


class TestFuzzyCorrectParams:
    """Test _fuzzy_correct_params function."""

    def test_correct_params_unchanged(self):
        """Test that correctly spelled params are not modified."""
        kwargs = {"query": "test", "max_results": 5}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == kwargs
        assert corrections == {}

    def test_fuzzy_match_search_query_to_query(self):
        """Test fuzzy matching: search_query -> query."""
        kwargs = {"search_query": "AI", "max_results": 5}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {"query": "AI", "max_results": 5}
        assert corrections == {"search_query": "query"}

    def test_fuzzy_match_num_results_to_max_results(self):
        """Test fuzzy matching: num_results -> max_results."""
        kwargs = {"query": "test", "num_results": 3}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {"query": "test", "max_results": 3}
        assert corrections == {"num_results": "max_results"}

    def test_multiple_fuzzy_matches(self):
        """Test correcting multiple misspelled parameters."""
        kwargs = {"search_query": "AI", "num_results": 5, "timeout": 60.0}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {"query": "AI", "max_results": 5, "timeout": 60.0}
        assert corrections == {
            "search_query": "query",
            "num_results": "max_results",
        }

    def test_no_match_dropped_parameter(self):
        """Test that unmatched parameters are dropped and reported."""
        kwargs = {"query": "test", "completely_random_param": 123}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {"query": "test"}
        assert corrections == {"completely_random_param": None}

    def test_mixed_correct_and_incorrect(self):
        """Test mix of correct and incorrect parameters."""
        kwargs = {
            "query": "correct",
            "search_query": "also_provided",
            "max_results": 10,
            "unknown_param": "dropped",
        }
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {"query": "also_provided", "max_results": 10}
        assert corrections == {
            "search_query": "query",
            "unknown_param": None,
        }

    def test_async_function(self):
        """Test fuzzy correction with async functions."""
        kwargs = {"search_query": "test", "num_results": 5}
        corrected, corrections = _fuzzy_correct_params(async_dummy_tool, kwargs)

        assert corrected == {"query": "test", "max_results": 5}
        assert corrections == {
            "search_query": "query",
            "num_results": "max_results",
        }

    def test_empty_kwargs(self):
        """Test with empty kwargs."""
        kwargs = {}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {}
        assert corrections == {}

    def test_case_sensitivity(self):
        """Test that matching is case-sensitive."""
        kwargs = {"Query": "test"}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert corrected == {"query": "test"}
        assert corrections == {"Query": "query"}

    def test_cutoff_threshold(self):
        """Test that very dissimilar names are dropped (cutoff=0.5)."""
        def custom_tool(result_count: int = 10) -> dict:
            return {"result_count": result_count}

        kwargs = {"xyz": 5}
        corrected, corrections = _fuzzy_correct_params(custom_tool, kwargs)

        assert corrected == {}
        assert corrections == {"xyz": None}

    def test_return_types(self):
        """Test return types are correct."""
        kwargs = {"search_query": "test", "max_results": 5}
        corrected, corrections = _fuzzy_correct_params(dummy_tool, kwargs)

        assert isinstance(corrected, dict)
        assert isinstance(corrections, dict)
        for key, val in corrections.items():
            assert isinstance(key, str)
            assert val is None or isinstance(val, str)


class TestWrapToolIntegration:
    """Integration tests for _wrap_tool with parameter correction."""

    @pytest.mark.asyncio
    async def test_async_tool_with_corrections_in_response(self):
        """Test that async tool includes _param_corrections in response."""
        from loom.server import _wrap_tool

        async def sample_async_tool(query: str, limit: int = 10) -> dict:
            return {"results": [query] * limit}

        wrapped = _wrap_tool(sample_async_tool)
        result = await wrapped(search_query="test", num_limit=5)

        assert "_param_corrections" in result
        assert result["_param_corrections"]["search_query"] == "query"
        assert result["_param_corrections"]["num_limit"] == "limit"

    def test_sync_tool_with_corrections_in_response(self):
        """Test that sync tool includes _param_corrections in response."""
        from loom.server import _wrap_tool

        def sample_sync_tool(query: str, limit: int = 10) -> dict:
            return {"results": [query] * limit}

        wrapped = _wrap_tool(sample_sync_tool)
        result = wrapped(search_query="test", num_limit=5)

        assert "_param_corrections" in result
        assert result["_param_corrections"]["search_query"] == "query"
        assert result["_param_corrections"]["num_limit"] == "limit"

    @pytest.mark.asyncio
    async def test_async_tool_no_corrections(self):
        """Test that async tool without corrections has no metadata."""
        from loom.server import _wrap_tool

        async def sample_async_tool(query: str, limit: int = 10) -> dict:
            return {"results": [query] * limit}

        wrapped = _wrap_tool(sample_async_tool)
        result = await wrapped(query="test", limit=5)

        assert "_param_corrections" not in result

    def test_sync_tool_non_dict_return(self):
        """Test that non-dict returns are not modified."""
        from loom.server import _wrap_tool

        def sample_sync_tool(query: str) -> str:
            return f"Query: {query}"

        wrapped = _wrap_tool(sample_sync_tool)
        result = wrapped(search_query="test")

        assert isinstance(result, str)
        assert result == "Query: test"
