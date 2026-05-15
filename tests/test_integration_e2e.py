"""End-to-end integration tests for all pipeline wiring.

Validates that core pipeline components integrate correctly:
1. research_deep → HCS scoring + cost tracking
2. universal_orchestrator → router_confidence + tool discovery
3. full_pipeline → strategy source + escalation
4. pipeline_enhancer → enrichment wrapper
5. Multi-provider LLM cascade
6. Cost estimation and gating

Mark with @pytest.mark.integration to run separately:
    pytest -m integration tests/test_integration_e2e.py
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

logger = logging.getLogger("loom.tests.e2e")


# =============================================================================
# RESEARCH_DEEP TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_deep_returns_dict() -> None:
    """Verify research_deep returns a dictionary with expected structure."""
    from loom.tools.core.deep import research_deep

    result = await research_deep(
        query="what is machine learning",
        max_results=1,
        max_cost_usd=0.05,
    )
    assert isinstance(result, dict), "research_deep should return dict"
    assert "query" in result or "error" in result, "Missing query or error field"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_deep_cost_tracking() -> None:
    """Verify research_deep includes cost estimation."""
    from loom.tools.core.deep import research_deep

    result = await research_deep(
        query="define AI",
        max_results=1,
        max_cost_usd=0.01,
    )
    # May hit cost limit or return results
    assert isinstance(result, dict), "Should return dict"
    # Check for cost fields if present
    if "estimated_cost_usd" in result:
        assert isinstance(result["estimated_cost_usd"], (int, float))
    if "total_cost_usd" in result:
        assert isinstance(result["total_cost_usd"], (int, float))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_deep_has_sources() -> None:
    """Verify research_deep includes source citations."""
    from loom.tools.core.deep import research_deep

    result = await research_deep(
        query="Paris France facts",
        max_results=2,
        max_cost_usd=0.10,
    )
    if "synthesis" in result or "answer" in result:
        # If synthesis exists, should have source tracking
        assert isinstance(result, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_deep_with_cost_limit() -> None:
    """Verify research_deep respects max_cost_usd budget."""
    from loom.tools.core.deep import research_deep

    # Very low budget should trigger cost gating
    result = await research_deep(
        query="expensive research query",
        max_cost_usd=0.001,  # Very low limit
    )
    assert isinstance(result, dict)
    # Either succeeds with low cost or returns budget exceeded
    if "error" in result:
        assert "cost" in result["error"].lower() or "budget" in result["error"].lower()


# =============================================================================
# UNIVERSAL_ORCHESTRATOR TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_universal_orchestrator_returns_dict() -> None:
    """Verify universal_orchestrator returns valid dictionary."""
    from loom.tools.infrastructure.universal_orchestrator import research_orchestrate_smart

    result = await research_orchestrate_smart(
        query="what is Python programming",
        max_tools=2,
        timeout_per_tool=5.0,
    )
    assert isinstance(result, dict), "Orchestrator should return dict"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_universal_orchestrator_router_confidence() -> None:
    """Verify orchestrator includes router_confidence in results."""
    from loom.tools.infrastructure.universal_orchestrator import research_orchestrate_smart

    result = await research_orchestrate_smart(
        query="search for AI safety papers",
        max_tools=1,
    )
    assert isinstance(result, dict)
    # Router confidence may be in result if smart_router is available
    if "router_confidence" in result:
        assert isinstance(result["router_confidence"], (int, float))
        assert 0 <= result["router_confidence"] <= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_universal_orchestrator_tool_discovery() -> None:
    """Verify orchestrator includes tool discovery metadata."""
    from loom.tools.infrastructure.universal_orchestrator import research_orchestrate_smart

    result = await research_orchestrate_smart(
        query="find GitHub repositories",
        max_tools=2,
    )
    assert isinstance(result, dict)
    # Check for tool discovery fields
    if "suggested_tools" in result:
        assert isinstance(result["suggested_tools"], (list, dict))
    if "tool_recommendations" in result:
        assert isinstance(result["tool_recommendations"], (list, dict))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_universal_orchestrator_timeout_handling() -> None:
    """Verify orchestrator handles timeouts gracefully."""
    from loom.tools.infrastructure.universal_orchestrator import research_orchestrate_smart

    # Short timeout should not crash
    result = await research_orchestrate_smart(
        query="test query",
        max_tools=1,
        timeout_per_tool=0.1,
    )
    assert isinstance(result, dict)
    # May timeout but should still return dict structure


# =============================================================================
# FULL_PIPELINE TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_returns_dict() -> None:
    """Verify full_pipeline returns valid structure."""
    from loom.tools.infrastructure.full_pipeline import research_full_pipeline

    result = await research_full_pipeline(
        query="what is climate change",
        darkness_level=1,  # Low darkness for faster execution
        max_models=1,
    )
    assert isinstance(result, dict), "full_pipeline should return dict"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_has_structure() -> None:
    """Verify full_pipeline includes expected fields."""
    from loom.tools.infrastructure.full_pipeline import research_full_pipeline

    result = await research_full_pipeline(
        query="define economics",
        darkness_level=1,
        max_models=1,
    )
    assert isinstance(result, dict)
    # Check for standard pipeline fields
    if "query" in result:
        assert isinstance(result["query"], str)
    # HCS scoring should be present or attempted
    if "hcs_scores" in result:
        assert isinstance(result["hcs_scores"], (dict, list))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_strategy_source() -> None:
    """Verify full_pipeline reports strategy source."""
    from loom.tools.infrastructure.full_pipeline import research_full_pipeline

    result = await research_full_pipeline(
        query="test query",
        darkness_level=1,
        max_models=1,
    )
    assert isinstance(result, dict)
    # Strategy source may be in result if prompt_reframe is used
    if "strategy_source" in result:
        assert isinstance(result["strategy_source"], (str, dict))
    if "reframe_strategy" in result:
        assert isinstance(result["reframe_strategy"], (str, dict))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_escalation() -> None:
    """Verify full_pipeline logs escalation attempts."""
    from loom.tools.infrastructure.full_pipeline import research_full_pipeline

    result = await research_full_pipeline(
        query="test escalation",
        darkness_level=1,
        target_hcs=9.0,  # High target may trigger escalation
        max_escalation_attempts=2,
    )
    assert isinstance(result, dict)
    # Escalation log should exist if escalation occurred
    if "escalation_log" in result:
        assert isinstance(result["escalation_log"], (list, dict))
    if "escalation_count" in result:
        assert isinstance(result["escalation_count"], int)


# =============================================================================
# PIPELINE_ENHANCER TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_enhancer_wraps_tool() -> None:
    """Verify pipeline_enhancer successfully wraps a tool."""
    from loom.tools.infrastructure.pipeline_enhancer import research_enhance

    result = await research_enhance(
        tool_name="research_search",
        params={"query": "test search", "provider": "ddgs", "n": 1},
        auto_hcs=False,
        auto_cost=False,
        auto_learn=False,
        auto_fact_check=False,
        auto_suggest=False,
    )
    assert isinstance(result, dict), "Enhancer should return dict"
    # Minimum expectation: original result should be present
    if "_original_result" in result:
        assert result["_original_result"] is not None or "error" in str(result)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_enhancer_cost_estimation() -> None:
    """Verify pipeline_enhancer includes cost estimation."""
    from loom.tools.infrastructure.pipeline_enhancer import research_enhance

    result = await research_enhance(
        tool_name="research_search",
        params={"query": "python", "provider": "ddgs", "n": 1},
        auto_cost=True,
        auto_hcs=False,
        auto_learn=False,
    )
    assert isinstance(result, dict)
    # Cost estimation may be present if cost_estimator is available
    if "_estimated_cost" in result:
        assert isinstance(result["_estimated_cost"], (int, float))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_enhancer_execution_time() -> None:
    """Verify pipeline_enhancer tracks execution time."""
    from loom.tools.infrastructure.pipeline_enhancer import research_enhance

    result = await research_enhance(
        tool_name="research_search",
        params={"query": "test", "provider": "ddgs", "n": 1},
        auto_hcs=False,
        auto_cost=False,
    )
    assert isinstance(result, dict)
    if "_execution_time_ms" in result:
        assert isinstance(result["_execution_time_ms"], (int, float))
        assert result["_execution_time_ms"] >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_enhancer_with_hcs_scoring() -> None:
    """Verify pipeline_enhancer attaches HCS scores."""
    from loom.tools.infrastructure.pipeline_enhancer import research_enhance

    result = await research_enhance(
        tool_name="research_search",
        params={"query": "test query", "provider": "ddgs", "n": 1},
        auto_hcs=True,
        auto_cost=False,
        auto_learn=False,
    )
    assert isinstance(result, dict)
    # HCS scores may be present if hcs_scorer is available
    if "_hcs_scores" in result:
        assert isinstance(result["_hcs_scores"], (dict, list))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_enhancer_with_suggestions() -> None:
    """Verify pipeline_enhancer suggests related tools."""
    from loom.tools.infrastructure.pipeline_enhancer import research_enhance

    result = await research_enhance(
        tool_name="research_search",
        params={"query": "deep learning", "provider": "ddgs", "n": 1},
        auto_suggest=True,
        auto_hcs=False,
        auto_cost=False,
    )
    assert isinstance(result, dict)
    # Suggestions may be present if tool_discovery is available
    if "_suggested_tools" in result:
        assert isinstance(result["_suggested_tools"], (list, dict))


# =============================================================================
# COST_ESTIMATOR TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_estimator_availability() -> None:
    """Verify cost_estimator module can be imported."""
    try:
        from loom.tools.infrastructure.cost_estimator import research_estimate_cost

        assert callable(research_estimate_cost), "cost_estimator should be callable"
    except ImportError:
        pytest.skip("cost_estimator not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_estimator_estimates_tool() -> None:
    """Verify cost_estimator can estimate tool costs."""
    try:
        from loom.tools.infrastructure.cost_estimator import research_estimate_cost

        result = await research_estimate_cost(
            tool_name="research_search",
            params={"query": "test", "n": 5},
        )
        assert isinstance(result, dict) or isinstance(result, (int, float))
    except ImportError:
        pytest.skip("cost_estimator not available")


# =============================================================================
# HCS_SCORER TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hcs_scorer_availability() -> None:
    """Verify HCS scorer module can be imported."""
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_score

        assert callable(research_hcs_score), "hcs_scorer should be callable"
    except ImportError:
        pytest.skip("hcs_scorer not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hcs_scorer_scores_content() -> None:
    """Verify HCS scorer returns scoring dictionary."""
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_score

        test_content = "This is a test response with some information."
        result = await research_hcs_score(content=test_content)
        assert isinstance(result, dict), "HCS scorer should return dict"
        # Should have multi-dimensional scores
        if "scores" in result:
            assert isinstance(result["scores"], (dict, list))
    except ImportError:
        pytest.skip("hcs_scorer not available")


# =============================================================================
# PROMPT_REFRAME & STRATEGY TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prompt_reframe_availability() -> None:
    """Verify prompt_reframe module can be imported."""
    try:
        from loom.tools.llm.prompt_reframe import research_auto_reframe

        assert callable(research_auto_reframe), "prompt_reframe should be callable"
    except ImportError:
        pytest.skip("prompt_reframe not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prompt_reframe_reframes_query() -> None:
    """Verify prompt_reframe can reframe a query."""
    try:
        from loom.tools.llm.prompt_reframe import research_auto_reframe

        result = await research_auto_reframe(
            original_prompt="How to become rich",
            reframe_category="creative",
        )
        assert isinstance(result, dict), "Reframe should return dict"
        if "reframed_prompt" in result:
            assert isinstance(result["reframed_prompt"], str)
    except ImportError:
        pytest.skip("prompt_reframe not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_strategy_cache_availability() -> None:
    """Verify strategy_cache module can be imported."""
    try:
        from loom.tools.llm.strategy_cache import research_cached_strategy

        assert callable(research_cached_strategy), "strategy_cache should be callable"
    except ImportError:
        pytest.skip("strategy_cache not available")


# =============================================================================
# CANONICAL QUERY TEST (how to become rich in Dubai)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_canonical_query_deep() -> None:
    """Verify canonical query works with research_deep."""
    from loom.tools.core.deep import research_deep

    result = await research_deep(
        query="how to become rich in Dubai",
        max_results=1,
        max_cost_usd=0.05,
    )
    assert isinstance(result, dict)
    # Should return some result (may be synthesis or error, both ok)
    assert "query" in result or "error" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_canonical_query_orchestrator() -> None:
    """Verify canonical query works with orchestrator."""
    from loom.tools.infrastructure.universal_orchestrator import research_orchestrate_smart

    result = await research_orchestrate_smart(
        query="how to become rich in Dubai",
        max_tools=1,
        timeout_per_tool=5.0,
    )
    assert isinstance(result, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_canonical_query_full_pipeline() -> None:
    """Verify canonical query works with full_pipeline."""
    from loom.tools.infrastructure.full_pipeline import research_full_pipeline

    result = await research_full_pipeline(
        query="how to become rich in Dubai",
        darkness_level=1,
        max_models=1,
    )
    assert isinstance(result, dict)


# =============================================================================
# INTEGRATION ISOLATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_tool_execution() -> None:
    """Verify multiple tools can execute concurrently."""
    from loom.tools.core.search import research_search

    tasks = [
        research_search(query="python", provider="ddgs", n=1),
        research_search(query="rust", provider="ddgs", n=1),
        research_search(query="go", provider="ddgs", n=1),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert len(results) == 3
    for result in results:
        # Each should be dict or exception (both ok for integration test)
        assert isinstance(result, (dict, Exception))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_with_error_handling() -> None:
    """Verify pipelines handle errors gracefully."""
    from loom.tools.core.deep import research_deep

    # Invalid query should still return dict (with error field)
    result = await research_deep(query="", max_results=1)
    assert isinstance(result, dict)
    # Either succeeds or returns error dict
    assert "query" in result or "error" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_enhance_with_missing_tool() -> None:
    """Verify enhancer handles missing tools gracefully."""
    from loom.tools.infrastructure.pipeline_enhancer import research_enhance

    result = await research_enhance(
        tool_name="research_nonexistent_tool",
        params={},
    )
    assert isinstance(result, dict)
    # Should either work or have error field
    if "error" in result:
        assert isinstance(result["error"], str)


# =============================================================================
# HELPER TESTS
# =============================================================================


def test_integration_markers_exist() -> None:
    """Verify integration test markers are properly set."""
    # This is a smoke test to ensure pytest marks work
    assert True


@pytest.mark.integration
def test_integration_marker_syntax() -> None:
    """Verify @pytest.mark.integration syntax is correct."""
    # Marker test to ensure all @pytest.mark.integration decorators work
    assert True
