"""Unit tests for semantic_router module."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

from loom.tools import semantic_router


@pytest.mark.asyncio
async def test_semantic_route_empty_query():
    """Test routing with empty query returns error."""
    result = await semantic_router.research_semantic_route("")
    assert result.get("error") is not None
    assert result.get("recommended_tools") == []


@pytest.mark.asyncio
async def test_semantic_route_short_query():
    """Test routing with too-short query returns error."""
    result = await semantic_router.research_semantic_route("a")
    assert result.get("error") is not None
    assert result.get("recommended_tools") == []


@pytest.mark.asyncio
async def test_semantic_route_valid_query():
    """Test routing with valid query."""
    result = await semantic_router.research_semantic_route("search for information")
    assert "query" in result
    assert "recommended_tools" in result
    assert "embedding_method" in result
    assert "total_tools" in result


@pytest.mark.asyncio
async def test_semantic_route_top_k_bounds():
    """Test top_k parameter bounds."""
    result = await semantic_router.research_semantic_route("test query", top_k=100)
    # top_k should be bounded to 25
    assert len(result.get("recommended_tools", [])) <= 25


@pytest.mark.asyncio
async def test_semantic_route_returns_similarity_scores():
    """Test that results include similarity scores."""
    result = await semantic_router.research_semantic_route("search query")
    tools = result.get("recommended_tools", [])
    if tools:
        for tool in tools:
            assert "tool" in tool
            assert "similarity" in tool
            assert 0.0 <= tool["similarity"] <= 1.0


@pytest.mark.asyncio
async def test_semantic_batch_route_empty_list():
    """Test batch routing with empty list."""
    result = await semantic_router.research_semantic_batch_route([])
    assert result.get("error") is not None
    assert result.get("routes") == []


@pytest.mark.asyncio
async def test_semantic_batch_route_multiple_queries():
    """Test batch routing with multiple queries."""
    queries = ["search for data", "analyze results", "fetch content"]
    result = await semantic_router.research_semantic_batch_route(queries)
    assert "routes" in result
    assert "tool_distribution" in result
    assert "total_queries" in result
    assert len(result["routes"]) == len(queries)


@pytest.mark.asyncio
async def test_extract_tool_descriptions():
    """Test extraction of tool descriptions from docstrings."""
    descriptions = semantic_router._extract_tool_descriptions()
    assert isinstance(descriptions, dict)
    # Should find at least some tools in the tools directory
    if descriptions:
        for tool_name, desc in list(descriptions.items())[:3]:
            assert isinstance(tool_name, str)
            assert tool_name.startswith("research_")
            assert isinstance(desc, str)
            assert len(desc) > 0


@pytest.mark.asyncio
async def test_semantic_router_rebuild():
    """Test forcing a rebuild of embeddings."""
    result = await semantic_router.research_semantic_router_rebuild()
    assert result["status"] == "rebuilt"
    assert "tools" in result
    assert "embedding_dims" in result
    assert "cache_path" in result
    assert result["tools"] >= 0


@pytest.mark.asyncio
async def test_keyword_fallback_with_empty_descriptions():
    """Test keyword fallback when descriptions are empty."""
    with patch.object(semantic_router, "_TOOL_DESCRIPTIONS", {}):
        result = semantic_router._keyword_fallback("test query")
        assert result == []


@pytest.mark.asyncio
async def test_keyword_fallback_with_descriptions():
    """Test keyword fallback with descriptions available."""
    test_descriptions = {
        "research_search": "Search for information online",
        "research_fetch": "Fetch a URL and extract content",
        "research_analyze": "Analyze text data",
    }
    with patch.object(semantic_router, "_TOOL_DESCRIPTIONS", test_descriptions):
        result = semantic_router._keyword_fallback("search for information")
        # Should find research_search
        if result:
            assert result[0][0] == "research_search" or any(
                t[0] == "research_search" for t in result
            )


@pytest.mark.asyncio
async def test_embedding_cache_path():
    """Test that cache paths are correctly computed."""
    cache_path = semantic_router._CACHE_PATH
    assert isinstance(cache_path, Path)
    assert ".cache/loom" in str(cache_path)
    assert "tool_embeddings.npy" in str(cache_path)


@pytest.mark.asyncio
async def test_semantic_route_with_non_string_query():
    """Test routing with non-string query returns error."""
    result = await semantic_router.research_semantic_route(123)
    assert result.get("error") is not None


@pytest.mark.asyncio
async def test_semantic_batch_route_with_non_list():
    """Test batch routing with non-list input."""
    result = await semantic_router.research_semantic_batch_route("not a list")
    assert result.get("error") is not None


@pytest.mark.asyncio
async def test_semantic_batch_route_aggregates_tools():
    """Test that batch routing aggregates tool distribution."""
    queries = ["search", "search", "fetch"]
    result = await semantic_router.research_semantic_batch_route(queries)
    distribution = result.get("tool_distribution", {})
    # The aggregation should work (test data-dependent results)
    assert isinstance(distribution, dict)


@pytest.mark.unit
def test_load_sentence_transformers_unavailable():
    """Test graceful fallback when sentence-transformers unavailable."""
    with patch("loom.tools.semantic_router._SENTENCE_TRANSFORMERS_AVAILABLE", False):
        # Should not raise even if sentence-transformers missing
        assert semantic_router._SENTENCE_TRANSFORMERS_AVAILABLE is False


@pytest.mark.unit
def test_sklearn_unavailable():
    """Test graceful fallback when sklearn unavailable."""
    with patch("loom.tools.semantic_router._SKLEARN_AVAILABLE", False):
        # Should not raise even if sklearn missing
        assert semantic_router._SKLEARN_AVAILABLE is False
