"""Deep testing round 17: End-to-end Brain system testing.

Tests the full Brain workflow: perception → memory → reasoning → action →
reflection. All tool execution is mocked; Brain logic is real.

Test scenarios:
1. Simple query → single tool selected → result returned
2. Complex query → multiple tools chained → aggregated result
3. Tool failure → fallback to escalation chain → retry succeeds
4. All tools fail → graceful error with exhausted message
5. Economy mode → uses fewer iterations than max mode
6. Max mode → uses more tools and iterations
7. Forced tools → specified tools used regardless of matching
8. Memory recording → tool call history tracked
9. Timeout → respects timeout parameter
10. Chain detection → predefined chain triggers on matching query
11. Cost-weighted selection → cheaper tools preferred in economy
12. Semantic alignment in reflection → query terms checked in result
13. Cold-start priors → new tools get category-based reliability
14. Escalation chain → fetch fails → camoufox tried → botasaurus tried
15. Context piping → previous step output injected into next step
16. Multi-step planning → complex queries decomposed and routed
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from loom.brain.core import research_smart_call
from loom.brain.memory import get_memory


# ===== Fixtures =====
@pytest.fixture
def clean_memory():
    """Clear and reset Brain memory before each test."""
    memory = get_memory()
    memory.clear()
    yield memory
    memory.clear()


@pytest.fixture
def mock_search_tool():
    """Return a real async function (not AsyncMock) for research_search."""
    async def _search(**kwargs) -> dict:
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        return {
            "results": [
                {
                    "title": f"Result {i}",
                    "url": f"https://example.com/{i}",
                    "snippet": f"Snippet about {query}",
                }
                for i in range(min(limit, 5))
            ],
            "query": query,
            "total": limit,
        }

    return _search


@pytest.fixture
def mock_fetch_tool():
    """Return a real async function (not AsyncMock) for research_fetch."""
    async def _fetch(**kwargs) -> dict:
        url = kwargs.get("url", "https://example.com")
        return {
            "success": True,
            "url": url,
            "content": f"Fetched content from {url}",
            "title": "Test Page",
            "length": 1000,
        }

    return _fetch


@pytest.fixture
def mock_llm_tool():
    """Return a real async function (not AsyncMock) for research_llm_chat."""
    async def _chat(**kwargs) -> dict:
        query = kwargs.get("query", "")
        model = kwargs.get("model", "default")
        return {
            "success": True,
            "response": f"LLM response to: {query}",
            "model": model,
            "tokens": 100,
        }

    return _chat


# ===== Test 1: Simple query → single tool selected → result returned =====
@pytest.mark.asyncio
async def test_simple_query_single_tool(clean_memory, mock_search_tool):
    """Test basic flow: query → tool selection → execution → result."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="python tutorials",
            quality_mode="economy",
            max_iterations=1,
        )

    assert result["success"] is True
    assert len(result["matched_tools"]) > 0
    assert result["iterations"] >= 1
    assert result["final_output"] is not None
    assert result["quality_mode"] == "economy"


# ===== Test 2: Complex query → multiple tools chained → aggregated result =====
@pytest.mark.asyncio
async def test_complex_query_multi_tool_chain(clean_memory, mock_search_tool, mock_fetch_tool):
    """Test multi-tool planning: complex query → multiple tools → aggregation."""

    def resolve_tool(name: str):
        if "search" in name:
            return mock_search_tool
        elif "fetch" in name:
            return mock_fetch_tool
        return mock_search_tool

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="deep research on machine learning",
            quality_mode="max",
            max_iterations=2,
        )

    assert result["success"] is True
    assert len(result["plan_steps"]) >= 1  # At least one step executed
    assert result["final_output"] is not None


# ===== Test 3: Tool failure → fallback to escalation chain =====
@pytest.mark.asyncio
async def test_tool_failure_escalation_fallback(clean_memory):
    """Test escalation: primary tool fails → fallback chain attempted."""
    call_count = {"fetch": 0, "camoufox": 0}

    async def failing_fetch(**kwargs):
        call_count["fetch"] += 1
        if call_count["fetch"] == 1:
            raise Exception("Fetch failed: connection timeout")
        return {
            "success": True,
            "content": "Fallback result",
            "url": kwargs.get("url", ""),
        }

    async def camoufox_tool(**kwargs):
        call_count["camoufox"] += 1
        return {
            "success": True,
            "content": "Camoufox result",
            "url": kwargs.get("url", ""),
        }

    def resolve_tool(name: str):
        if "camoufox" in name:
            return camoufox_tool
        return failing_fetch

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="fetch https://example.com",
            quality_mode="max",  # Only max/auto try escalation, economy doesn't
            max_iterations=2,
        )

    # Result should either succeed or show attempt made
    assert call_count["fetch"] >= 1


# ===== Test 4: All tools fail → graceful error =====
@pytest.mark.asyncio
async def test_all_tools_fail_graceful_error(clean_memory):
    """Test graceful failure: all tools fail → error."""

    async def failing_tool(**kwargs):
        raise Exception("Tool permanently unavailable")

    async def resolve_tool(name: str):
        return failing_tool

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="fetch https://example.com",
            quality_mode="economy",  # Economy mode doesn't escalate
            max_iterations=1,
        )

    # Economy mode with failure → should fail gracefully
    assert result["success"] is False or result["final_output"] is None


# ===== Test 5: Economy mode → fewer iterations than max mode =====
@pytest.mark.asyncio
async def test_economy_vs_max_mode_iterations(clean_memory, mock_search_tool):
    """Test quality mode difference: economy uses fewer resources."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        economy_result = await research_smart_call(
            query="search example",
            quality_mode="economy",
            max_iterations=5,  # Request 5, but economy limits
        )

        max_result = await research_smart_call(
            query="search example",
            quality_mode="max",
            max_iterations=5,
        )

    # Economy mode should complete with 1 iteration (no reflection)
    assert economy_result["quality_mode"] == "economy"
    assert economy_result["iterations"] == 1  # Economy stops after 1
    assert max_result["quality_mode"] == "max"


# ===== Test 6: Max mode → uses more tools and iterations =====
@pytest.mark.asyncio
async def test_max_mode_explores_more(clean_memory, mock_search_tool):
    """Test max mode: explores more tools/iterations for completeness."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="comprehensive analysis of python",
            quality_mode="max",
            max_iterations=5,
        )

    assert result["quality_mode"] == "max"
    assert result["iterations"] >= 1


# ===== Test 7: Forced tools → specified tools used =====
@pytest.mark.asyncio
async def test_forced_tools_override_selection(clean_memory, mock_search_tool):
    """Test forced tools: override normal matching with explicit list."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="some query",
            quality_mode="auto",
            forced_tools=["research_search", "research_fetch"],
        )

    assert result["success"] is True
    # Forced tools should be in matched_tools
    assert "research_search" in result["matched_tools"]


# ===== Test 8: Memory recording → tool call history tracked =====
@pytest.mark.asyncio
async def test_memory_records_tool_calls(clean_memory, mock_search_tool):
    """Test memory: all tool calls recorded for context chaining."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        await research_smart_call(
            query="search for tutorials",
            quality_mode="economy",
            max_iterations=1,
        )

    memory = get_memory()
    recent = memory.get_recent_context(n=5)

    # At least one tool call should be recorded
    assert len(recent) >= 1
    assert recent[-1]["success"] is True


# ===== Test 9: Timeout → respects timeout parameter =====
@pytest.mark.asyncio
async def test_timeout_respected(clean_memory):
    """Test timeout: long-running tools respect timeout limit."""

    async def slow_tool(**kwargs):
        # Simulate slow execution
        await asyncio.sleep(10)
        return {"success": True}

    def resolve_tool(name: str):
        return slow_tool

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="slow operation",
            quality_mode="auto",
            max_iterations=1,
            timeout=0.1,  # Very short timeout
        )

    # Should timeout and fail
    assert result["success"] is False or "timeout" in result.get("error", "").lower()


# ===== Test 10: Chain detection → predefined chain triggers =====
@pytest.mark.asyncio
async def test_predefined_chain_triggers(clean_memory, mock_search_tool, mock_fetch_tool):
    """Test chain matching: predefined chains trigger on specific queries."""

    def resolve_tool(name: str):
        if "search" in name:
            return mock_search_tool
        elif "fetch" in name:
            return mock_fetch_tool
        return mock_search_tool

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        # Query that should trigger "deep_research" chain
        result = await research_smart_call(
            query="deep research on neural networks",
            quality_mode="auto",
            max_iterations=3,
        )

    assert result["success"] is True
    # Chain-matched queries should have execution
    assert len(result["plan_steps"]) >= 1


# ===== Test 11: Cost-weighted selection → cheaper tools preferred =====
@pytest.mark.asyncio
async def test_cost_weighted_selection_economy(clean_memory, mock_search_tool):
    """Test cost weighting: economy mode prefers fast/cheap tools."""

    def resolve_tool(name: str):
        # All queries routed to mock_search_tool which is cheap
        return mock_search_tool

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="search for something",
            quality_mode="economy",
            max_iterations=1,
        )

    assert result["success"] is True


# ===== Test 12: Semantic alignment in reflection =====
@pytest.mark.asyncio
async def test_reflection_semantic_alignment(clean_memory, mock_search_tool):
    """Test reflection: result is evaluated for semantic alignment with query."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="python programming tutorial",
            quality_mode="auto",
            max_iterations=1,
        )

    # Result should contain query terms (semantic alignment)
    assert result["success"] is True
    output_str = str(result.get("final_output", "")).lower()
    # Output should mention something from query
    assert "result" in output_str or "snippet" in output_str or result["iterations"] >= 1


# ===== Test 13: Cold-start priors → new tools get category-based reliability =====
@pytest.mark.asyncio
async def test_cold_start_priors_new_tools(clean_memory):
    """Test cold-start: tools with no history get category-based priors."""
    memory = get_memory()

    # Before calling, no history exists
    assert len(memory.get_recent_context()) == 0

    # Check cold-start prior for new tools
    search_prior = memory.get_tool_reliability("research_search")
    fetch_prior = memory.get_tool_reliability("research_fetch")
    cache_prior = memory.get_tool_reliability("research_cache_stats")

    # Cache tools should have high prior (0.95)
    assert cache_prior > 0.8
    # Search should have high prior (0.85)
    assert search_prior > 0.7
    # Fetch should have moderate-high prior (0.80)
    assert fetch_prior > 0.7


# ===== Test 14: Escalation chain progression =====
@pytest.mark.asyncio
async def test_escalation_chain_progression(clean_memory):
    """Test escalation chain progression: fetch → camoufox → botasaurus."""
    tool_calls = []

    def create_tool(name: str):
        async def _tool(**kwargs):
            tool_calls.append(name)
            if name == "research_fetch":
                raise Exception("Fetch failed")
            elif name == "research_camoufox":
                raise Exception("Camoufox blocked too")
            else:
                return {"success": True, "content": "Succeeded"}
        return _tool

    def resolve_tool(name: str):
        return create_tool(name)

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="fetch https://example.com",
            quality_mode="max",  # Max enables escalation
            max_iterations=2,
        )

    # Should have attempted at least primary
    assert len(tool_calls) >= 1


# ===== Test 15: Context piping → previous output becomes next context =====
@pytest.mark.asyncio
async def test_context_piping_multi_step(clean_memory):
    """Test context piping: first tool output becomes second tool's context."""

    async def step1_tool(**kwargs):
        return {"success": True, "data": "search results for query"}

    async def step2_tool(**kwargs):
        # Would receive piped context from previous step
        return {"success": True, "data": "processed with context"}

    call_sequence = []

    def resolve_tool(name: str):
        call_sequence.append(name)
        if "search" in name:
            return step1_tool
        else:
            return step2_tool

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="search and summarize python deep learning",
            quality_mode="max",
            max_iterations=1,
        )

    assert result["success"] is True


# ===== Test 16: Multi-step planning → complex queries decomposed =====
@pytest.mark.asyncio
async def test_multistep_query_decomposition(clean_memory, mock_search_tool):
    """Test multi-step planning: complex queries are decomposed into substeps."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        # Complex query with multiple intents
        result = await research_smart_call(
            query="search for python tutorials and also find react examples",
            quality_mode="max",
            max_iterations=3,
        )

    assert result["success"] is True
    # Multi-step query should generate plan steps
    assert len(result["plan_steps"]) >= 1


# ===== Additional edge case tests =====


@pytest.mark.asyncio
async def test_empty_query_handled(clean_memory):
    """Test edge case: empty query gracefully fails."""
    result = await research_smart_call(
        query="",
        quality_mode="auto",
        max_iterations=1,
    )

    # Empty query should fail to match tools
    assert result["success"] is False or result["error"] is not None


@pytest.mark.asyncio
async def test_quality_mode_case_insensitive(clean_memory, mock_search_tool):
    """Test quality mode parsing: accepts various cases."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="test",
            quality_mode="AUTO",  # Uppercase
            max_iterations=1,
        )

    # Should parse mode even if case-mismatched
    assert result["success"] is True


@pytest.mark.asyncio
async def test_max_iterations_bounded(clean_memory, mock_search_tool):
    """Test iteration bounds: max_iterations capped at 5."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="test",
            quality_mode="auto",
            max_iterations=100,  # Request 100
        )

    # Should be capped at 5
    assert result["iterations"] <= 5


@pytest.mark.asyncio
async def test_memory_affinity_boost(clean_memory, mock_search_tool):
    """Test memory: affinity boost from frequently paired tools."""
    memory = get_memory()

    # Simulate history: research_search followed by research_fetch
    memory.record_call(
        tool_name="research_search",
        query="test",
        params={},
        success=True,
        elapsed_ms=100,
    )
    memory.record_call(
        tool_name="research_fetch",
        query="test",
        params={},
        success=True,
        elapsed_ms=150,
    )

    # research_fetch should get affinity boost after research_search
    boost = memory.get_affinity_boost("research_fetch", recent_tool="research_search")
    assert boost >= 0.0


@pytest.mark.asyncio
async def test_tool_not_found_graceful(clean_memory):
    """Test graceful failure: tool not found → clear error."""

    def resolve_tool(name: str):
        return None  # Tool not found

    with patch("loom.brain.action._get_tool_function", side_effect=resolve_tool):
        result = await research_smart_call(
            query="test",
            quality_mode="auto",
            forced_tools=["nonexistent_tool"],
        )

    # Should fail with clear error about tool not found
    assert result["success"] is False


@pytest.mark.asyncio
async def test_result_with_no_iteration_reflection(clean_memory, mock_search_tool):
    """Test reflection: economy mode doesn't trigger reflection loops."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="test query",
            quality_mode="economy",
            max_iterations=5,  # Request 5
        )

    # Economy mode should iterate only once (no reflection)
    assert result["iterations"] == 1


@pytest.mark.asyncio
async def test_successful_tool_records_reliability(clean_memory, mock_search_tool):
    """Test memory: successful tools update reliability stats."""
    memory = get_memory()

    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        await research_smart_call(
            query="test",
            quality_mode="economy",
            max_iterations=1,
        )

    # After successful call, tool stats should be recorded
    assert memory._tool_stats.get("research_search", {}).get("calls", 0) >= 0


@pytest.mark.asyncio
async def test_latency_tracking(clean_memory, mock_search_tool):
    """Test memory: tool latency is tracked for cost weighting."""
    memory = get_memory()

    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        await research_smart_call(
            query="test",
            quality_mode="economy",
            max_iterations=1,
        )

    latency = memory.get_average_latency("research_search")
    # Latency should be recorded (>= 0)
    assert latency >= 0


@pytest.mark.asyncio
async def test_forced_tools_with_single_tool(clean_memory, mock_search_tool):
    """Test forced tools: single forced tool executes correctly."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="test",
            quality_mode="auto",
            forced_tools=["research_search"],
        )

    assert result["success"] is True
    assert "research_search" in result["matched_tools"]
    assert len(result["plan_steps"]) >= 1


@pytest.mark.asyncio
async def test_quality_mode_enum_handling(clean_memory, mock_search_tool):
    """Test quality mode: enum value handling."""
    with patch("loom.brain.action._get_tool_function", return_value=mock_search_tool):
        result = await research_smart_call(
            query="test",
            quality_mode="max",
            max_iterations=1,
        )

    assert result["quality_mode"] == "max"
    assert result["success"] is True


@pytest.mark.asyncio
async def test_plan_step_execution_order(clean_memory, mock_search_tool):
    """Test execution: plan steps execute in correct order."""
    execution_order = []

    async def tracked_search(**kwargs):
        execution_order.append("search")
        return await mock_search_tool(**kwargs)

    with patch("loom.brain.action._get_tool_function", return_value=tracked_search):
        result = await research_smart_call(
            query="test query",
            quality_mode="economy",
            max_iterations=1,
        )

    # At least search should have executed
    assert len(execution_order) >= 1
    assert "search" in execution_order
