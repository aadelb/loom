"""Tests for Brain Memory Layer — Session context and usage patterns."""

from __future__ import annotations

import pytest

from loom.brain.memory import BrainMemory, ToolUsageRecord, get_memory


class TestBrainMemory:
    """Test memory system."""

    @pytest.fixture
    def memory(self) -> BrainMemory:
        """Create a fresh memory instance for testing."""
        mem = BrainMemory()
        yield mem
        mem.clear()

    def test_record_call_success(self, memory: BrainMemory) -> None:
        """Test recording a successful tool call."""
        memory.record_call(
            tool_name="research_search",
            query="test query",
            params={"q": "test"},
            success=True,
            elapsed_ms=100,
        )
        assert len(memory._history) == 1
        record = memory._history[0]
        assert record.tool_name == "research_search"
        assert record.success is True

    def test_record_call_failure(self, memory: BrainMemory) -> None:
        """Test recording a failed tool call."""
        memory.record_call(
            tool_name="research_fetch",
            query="test url",
            params={"url": "https://example.com"},
            success=False,
            elapsed_ms=50,
            error="Connection timeout",
        )
        assert len(memory._history) == 1
        record = memory._history[0]
        assert record.success is False
        assert record.error == "Connection timeout"

    def test_get_recent_context_empty(self, memory: BrainMemory) -> None:
        """Test getting recent context when no history."""
        context = memory.get_recent_context(n=5)
        assert context == []

    def test_get_recent_context_partial(self, memory: BrainMemory) -> None:
        """Test getting recent context with partial history."""
        memory.record_call("tool1", "q1", {}, True, 100)
        memory.record_call("tool2", "q2", {}, True, 200)

        context = memory.get_recent_context(n=5)
        assert len(context) == 2
        assert context[0]["tool"] == "tool1"
        assert context[1]["tool"] == "tool2"

    def test_get_recent_context_limit(self, memory: BrainMemory) -> None:
        """Test that get_recent_context respects limit parameter."""
        for i in range(10):
            memory.record_call(f"tool{i}", f"query{i}", {}, True, 100 * i)

        context = memory.get_recent_context(n=3)
        assert len(context) == 3
        # Should return the most recent 3
        assert context[-1]["tool"] == "tool9"

    def test_tool_reliability_unknown_tool(self, memory: BrainMemory) -> None:
        """Test reliability for unknown tool returns 0.5."""
        reliability = memory.get_tool_reliability("unknown_tool")
        assert reliability == 0.5

    def test_tool_reliability_perfect(self, memory: BrainMemory) -> None:
        """Test reliability calculation for 100% success rate."""
        memory.record_call("tool", "q", {}, True, 100)
        memory.record_call("tool", "q", {}, True, 100)
        memory.record_call("tool", "q", {}, True, 100)

        reliability = memory.get_tool_reliability("tool")
        assert reliability == 1.0

    def test_tool_reliability_partial(self, memory: BrainMemory) -> None:
        """Test reliability calculation for partial success."""
        memory.record_call("tool", "q", {}, True, 100)
        memory.record_call("tool", "q", {}, True, 100)
        memory.record_call("tool", "q", {}, False, 100)

        reliability = memory.get_tool_reliability("tool")
        assert reliability == pytest.approx(2.0 / 3.0)

    def test_suggested_next_tools_empty(self, memory: BrainMemory) -> None:
        """Test suggested next tools with no history."""
        suggestions = memory.get_suggested_next_tools("research_search")
        assert suggestions == []

    def test_suggested_next_tools_chain(self, memory: BrainMemory) -> None:
        """Test suggested next tools based on historical co-occurrence."""
        # Create a chain: search -> fetch -> summarize
        memory.record_call("research_search", "q", {}, True, 100)
        memory.record_call("research_fetch", "q", {}, True, 100)
        memory.record_call("research_llm_summarize", "q", {}, True, 100)

        # Repeat to increase confidence
        memory.record_call("research_search", "q", {}, True, 100)
        memory.record_call("research_fetch", "q", {}, True, 100)

        suggestions = memory.get_suggested_next_tools("research_search")
        assert "research_fetch" in suggestions

    def test_suggested_next_tools_top_k(self, memory: BrainMemory) -> None:
        """Test that top_k parameter limits results."""
        # Create multiple chains
        memory.record_call("toolA", "q", {}, True, 100)
        memory.record_call("toolB", "q", {}, True, 100)
        memory.record_call("toolA", "q", {}, True, 100)
        memory.record_call("toolC", "q", {}, True, 100)

        suggestions = memory.get_suggested_next_tools("toolA", top_k=1)
        assert len(suggestions) <= 1

    def test_average_latency_unknown(self, memory: BrainMemory) -> None:
        """Test average latency for unknown tool returns 0.0."""
        latency = memory.get_average_latency("unknown_tool")
        assert latency == 0.0

    def test_average_latency_calculation(self, memory: BrainMemory) -> None:
        """Test average latency calculation."""
        memory.record_call("tool", "q", {}, True, 100)
        memory.record_call("tool", "q", {}, True, 200)
        memory.record_call("tool", "q", {}, True, 300)

        latency = memory.get_average_latency("tool")
        assert latency == pytest.approx(200.0)

    def test_affinity_boost_no_history(self, memory: BrainMemory) -> None:
        """Test affinity boost with no recent tool."""
        boost = memory.get_affinity_boost("tool")
        assert boost == 0.0

    def test_affinity_boost_no_pair(self, memory: BrainMemory) -> None:
        """Test affinity boost when tools never paired."""
        memory.record_call("tool1", "q", {}, True, 100)
        memory.record_call("tool2", "q", {}, True, 100)

        boost = memory.get_affinity_boost("tool3", recent_tool="tool1")
        assert boost == 0.0

    def test_affinity_boost_positive(self, memory: BrainMemory) -> None:
        """Test affinity boost with frequent pairing."""
        # Create frequent pairing: tool1 -> tool2
        for _ in range(5):
            memory.record_call("tool1", "q", {}, True, 100)
            memory.record_call("tool2", "q", {}, True, 100)

        boost = memory.get_affinity_boost("tool2", recent_tool="tool1")
        assert boost > 0.0
        assert boost <= 0.3  # Max boost is 0.3

    def test_affinity_boost_uses_last_tool(self, memory: BrainMemory) -> None:
        """Test affinity boost uses most recent tool when not specified."""
        memory.record_call("toolA", "q", {}, True, 100)
        memory.record_call("toolB", "q", {}, True, 100)
        memory.record_call("toolA", "q", {}, True, 100)
        memory.record_call("toolB", "q", {}, True, 100)

        # Should use toolB (most recent)
        boost = memory.get_affinity_boost("toolA")
        assert boost > 0.0

    def test_clear_resets_state(self, memory: BrainMemory) -> None:
        """Test that clear resets all memory."""
        memory.record_call("tool", "q", {}, True, 100)
        memory.record_call("tool", "q", {}, True, 100)

        memory.clear()

        assert len(memory._history) == 0
        assert len(memory._tool_stats) == 0
        assert len(memory._tool_pairs) == 0

    def test_max_history_truncation(self, memory: BrainMemory) -> None:
        """Test that history is truncated to MAX_HISTORY."""
        # Record more than _MAX_HISTORY (100) calls
        for i in range(150):
            memory.record_call(f"tool{i % 5}", f"q{i}", {}, True, 100)

        assert len(memory._history) <= 100

    def test_tool_pairs_tracking(self, memory: BrainMemory) -> None:
        """Test that tool pair co-occurrence is tracked."""
        memory.record_call("search", "q", {}, True, 100)
        memory.record_call("fetch", "q", {}, True, 100)
        memory.record_call("search", "q", {}, True, 100)
        memory.record_call("fetch", "q", {}, True, 100)

        assert memory._tool_pairs[("search", "fetch")] == 2

    def test_get_memory_singleton(self) -> None:
        """Test that get_memory returns singleton."""
        mem1 = get_memory()
        mem2 = get_memory()
        assert mem1 is mem2

    def test_tool_usage_record_timestamp(self) -> None:
        """Test that ToolUsageRecord has timestamp."""
        record = ToolUsageRecord(
            tool_name="test",
            query="q",
            params={},
            success=True,
        )
        assert record.timestamp > 0


class TestToolUsageRecord:
    """Test ToolUsageRecord dataclass."""

    def test_create_record(self) -> None:
        """Test creating a usage record."""
        record = ToolUsageRecord(
            tool_name="research_search",
            query="test",
            params={"q": "test"},
            success=True,
            elapsed_ms=100,
        )
        assert record.tool_name == "research_search"
        assert record.query == "test"
        assert record.success is True
        assert record.elapsed_ms == 100
        assert record.error is None

    def test_create_record_with_error(self) -> None:
        """Test creating a failed record."""
        record = ToolUsageRecord(
            tool_name="research_fetch",
            query="url",
            params={"url": "https://example.com"},
            success=False,
            elapsed_ms=50,
            error="Timeout",
        )
        assert record.success is False
        assert record.error == "Timeout"
