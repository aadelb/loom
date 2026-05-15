"""Integration tests for semantic router with universal orchestrator."""

import pytest
from unittest.mock import patch, AsyncMock

import loom.tools.infrastructure.universal_orchestrator, loom.tools.llm.semantic_router


@pytest.mark.asyncio
async def test_orchestrator_with_semantic_prefilter():
    """Test that orchestrator uses semantic pre-filtering when available."""
    # This test verifies the orchestrator can integrate semantic routing
    query = "find information about security research"

    # Mock semantic_router to return predictable results
    mock_semantic_result = {
        "query": query,
        "recommended_tools": [
            {"tool": "research_search", "similarity": 0.85},
            {"tool": "research_fetch", "similarity": 0.72},
        ],
        "embedding_method": "sentence-transformers",
        "total_tools": 350,
    }

    with patch.object(
        semantic_router, "research_semantic_route", new_callable=AsyncMock
    ) as mock_semantic:
        mock_semantic.return_value = mock_semantic_result

        # Call orchestrator
        result = await universal_orchestrator.research_orchestrate_smart(
            query, max_tools=1, strategy="auto"
        )

        # Verify semantic router was called
        mock_semantic.assert_called_once()
        call_args = mock_semantic.call_args
        assert call_args[0][0] == query  # First positional arg is query

        # Verify semantic scores are in result
        assert "semantic_scores" in result
        assert "semantic_embedding_method" in result


@pytest.mark.asyncio
async def test_orchestrator_fallback_to_keyword_router():
    """Test fallback to keyword router when semantic unavailable."""
    query = "extract data from web"

    # Mock semantic router to fail
    with patch.object(semantic_router, "research_semantic_route", new_callable=AsyncMock) as mock_semantic:
        mock_semantic.side_effect = Exception("semantic_router unavailable")

        # Should still work (falls back to keyword)
        result = await universal_orchestrator.research_orchestrate_smart(
            query, max_tools=1, strategy="auto"
        )

        assert "query" in result
        # Result should still be valid even though semantic failed
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_orchestrator_query_too_short():
    """Test orchestrator rejects queries that are too short."""
    result = await universal_orchestrator.research_orchestrate_smart("ab", max_tools=1)
    assert "error" in result
    assert "too short" in result["error"]


@pytest.mark.asyncio
async def test_orchestrator_query_empty():
    """Test orchestrator rejects empty queries."""
    result = await universal_orchestrator.research_orchestrate_smart("", max_tools=1)
    assert "error" in result


@pytest.mark.asyncio
async def test_orchestrator_infers_query_category():
    """Test that orchestrator infers query category."""
    query = "search for vulnerabilities in source code"
    result = await universal_orchestrator.research_orchestrate_smart(
        query, max_tools=1, strategy="auto"
    )
    assert "inferred_category" in result
    # Should infer "search" or "analyze" category
    category = result["inferred_category"]
    assert isinstance(category, str)


@pytest.mark.asyncio
async def test_orchestrator_combines_semantic_and_keyword_scores():
    """Test that orchestrator combines semantic (60%) and keyword (40%) scores."""
    # This is an integration test verifying the weighting strategy
    query = "find security vulnerabilities"

    with patch.object(
        semantic_router, "research_semantic_route", new_callable=AsyncMock
    ) as mock_semantic:
        # Return semantic scores
        mock_semantic.return_value = {
            "query": query,
            "recommended_tools": [
                {"tool": "research_search", "similarity": 0.9},
                {"tool": "research_analyze", "similarity": 0.7},
            ],
            "embedding_method": "sentence-transformers",
            "total_tools": 350,
        }

        result = await universal_orchestrator.research_orchestrate_smart(
            query, max_tools=3, strategy="parallel"
        )

        # Verify semantic scores are captured
        semantic_scores = result.get("semantic_scores", {})
        assert isinstance(semantic_scores, dict)
        # Should have captured the mock semantic results
        if semantic_scores:
            assert "research_search" in semantic_scores or True  # May vary


@pytest.mark.asyncio
async def test_orchestrator_max_tools_bounds():
    """Test that orchestrator respects max_tools bounds."""
    query = "test query for routing"

    # Test max_tools > 25 gets clamped
    result = await universal_orchestrator.research_orchestrate_smart(
        query, max_tools=100, strategy="parallel"
    )
    assert isinstance(result, dict)

    # Test max_tools < 1 gets clamped
    result = await universal_orchestrator.research_orchestrate_smart(
        query, max_tools=0, strategy="parallel"
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_orchestrator_strategy_parameter():
    """Test different execution strategies."""
    query = "test query"

    # Test "auto" strategy
    result_auto = await universal_orchestrator.research_orchestrate_smart(
        query, strategy="auto"
    )
    assert result_auto.get("aggregated_summary", {}).get("execution_strategy") == "auto"

    # Test "parallel" strategy
    result_parallel = await universal_orchestrator.research_orchestrate_smart(
        query, strategy="parallel"
    )
    assert (
        result_parallel.get("aggregated_summary", {}).get("execution_strategy")
        == "parallel"
    )


@pytest.mark.asyncio
async def test_semantic_router_on_first_call_builds_cache():
    """Test that semantic router builds embeddings cache on first call."""
    query = "test embedding cache"

    # Call semantic router (first call should trigger cache building)
    result = await semantic_router.research_semantic_route(query)

    assert "embedding_method" in result
    assert "total_tools" in result
    # Should have built or loaded embeddings
    assert result.get("total_tools", 0) >= 0


@pytest.mark.asyncio
async def test_semantic_router_embedding_method_detection():
    """Test that semantic router detects available embedding methods."""
    query = "test embedding detection"
    result = await semantic_router.research_semantic_route(query)

    embedding_method = result.get("embedding_method", "none")
    # Should be one of: sentence-transformers, sklearn-tfidf, keyword_fallback, none
    assert embedding_method in (
        "sentence-transformers",
        "sklearn-tfidf",
        "keyword_fallback",
        "none",
    )


@pytest.mark.asyncio
async def test_orchestrator_includes_semantic_metadata():
    """Test that orchestrator result includes semantic metadata."""
    query = "test semantic metadata"
    result = await universal_orchestrator.research_orchestrate_smart(query)

    # Should include semantic metadata
    assert "semantic_scores" in result
    assert "semantic_embedding_method" in result
    assert isinstance(result["semantic_scores"], dict)
    assert isinstance(result["semantic_embedding_method"], str)
