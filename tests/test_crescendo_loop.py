"""Tests for crescendo_loop — HCS escalation feedback loop.

Tests the complete integration:
- Escalation strategy order
- HCS scoring feedback
- Target detection
- Max attempts limiting
- Mock function integration
"""

from __future__ import annotations

import asyncio
import pytest

from loom.crescendo_loop import ESCALATION_ORDER, crescendo_hcs_loop, research_crescendo_loop


class TestEscalationOrder:
    """Tests for ESCALATION_ORDER constant."""

    def test_escalation_order_is_list(self) -> None:
        """Escalation order should be a list."""
        assert isinstance(ESCALATION_ORDER, list)

    def test_escalation_order_has_nine_strategies(self) -> None:
        """Escalation order should have exactly 9 strategies."""
        assert len(ESCALATION_ORDER) == 9

    def test_escalation_order_all_strings(self) -> None:
        """All strategies should be strings."""
        assert all(isinstance(s, str) for s in ESCALATION_ORDER)

    def test_escalation_order_weakest_first(self) -> None:
        """'academic' should be first (weakest)."""
        assert ESCALATION_ORDER[0] == "academic"

    def test_escalation_order_strongest_last(self) -> None:
        """'psychology_mega_stack' should be last (strongest)."""
        assert ESCALATION_ORDER[-1] == "psychology_mega_stack"

    def test_escalation_order_no_duplicates(self) -> None:
        """No duplicate strategies."""
        assert len(ESCALATION_ORDER) == len(set(ESCALATION_ORDER))


class TestCrescendoHcsLoopBasic:
    """Basic tests for crescendo_hcs_loop with dry run (no callbacks)."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_dict(self) -> None:
        """Dry run should return a dictionary."""
        result = await crescendo_hcs_loop(
            query="test query",
            target_hcs=8,
            max_attempts=2,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dry_run_has_required_fields(self) -> None:
        """Result should have all required fields."""
        result = await crescendo_hcs_loop(
            query="test query",
            target_hcs=8,
            max_attempts=2,
        )
        required_fields = {
            "pipeline",
            "query",
            "target_hcs",
            "best_hcs",
            "best_strategy",
            "attempts",
            "target_met",
            "best_response",
            "escalation_log",
        }
        assert set(result.keys()) >= required_fields

    @pytest.mark.asyncio
    async def test_pipeline_field_is_crescendo_hcs_loop(self) -> None:
        """Pipeline field should identify the pipeline."""
        result = await crescendo_hcs_loop(
            query="test query",
            target_hcs=8,
            max_attempts=2,
        )
        assert result["pipeline"] == "crescendo_hcs_loop"

    @pytest.mark.asyncio
    async def test_query_preserved_in_result(self) -> None:
        """Original query should be preserved."""
        query = "How do jailbreaks work?"
        result = await crescendo_hcs_loop(
            query=query,
            target_hcs=8,
            max_attempts=2,
        )
        assert result["query"] == query

    @pytest.mark.asyncio
    async def test_target_hcs_preserved_in_result(self) -> None:
        """Target HCS should be preserved."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=7,
            max_attempts=2,
        )
        assert result["target_hcs"] == 7

    @pytest.mark.asyncio
    async def test_invalid_empty_query_returns_error(self) -> None:
        """Empty query should return error dict."""
        result = await crescendo_hcs_loop(
            query="",
            target_hcs=8,
            max_attempts=2,
        )
        assert result["best_hcs"] == 0
        assert result["target_met"] is False
        assert "error" in result


class TestCrescendoAttempts:
    """Tests for attempt counting and max_attempts limiting."""

    @pytest.mark.asyncio
    async def test_max_attempts_limits_iterations(self) -> None:
        """max_attempts should limit the number of escalation steps."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,  # Very high, won't be reached
            max_attempts=2,
        )
        assert result["attempts"] == 2
        assert len(result["escalation_log"]) == 2

    @pytest.mark.asyncio
    async def test_attempts_count_accurate(self) -> None:
        """Attempts count should match escalation log length."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
        )
        assert result["attempts"] == len(result["escalation_log"])

    @pytest.mark.asyncio
    async def test_max_attempts_never_exceeds_escalation_order_length(self) -> None:
        """Attempts should never exceed available strategies."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=100,  # More than available
        )
        # Should be capped at len(ESCALATION_ORDER) = 9
        assert result["attempts"] <= len(ESCALATION_ORDER)


class TestTargetDetection:
    """Tests for target HCS detection and early termination."""

    @pytest.mark.asyncio
    async def test_target_met_when_hcs_reaches_target(self) -> None:
        """target_met should be True when best_hcs >= target_hcs."""
        # With dry run, HCS scores increase: 3, 5, 7, 9, ...
        # So with target_hcs=7, should meet on attempt 3
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=7,
            max_attempts=5,
        )
        assert result["target_met"] is True
        assert result["best_hcs"] >= 7

    @pytest.mark.asyncio
    async def test_target_not_met_when_never_reached(self) -> None:
        """target_met should be False when best_hcs < target_hcs."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,  # Won't reach 10
        )
        assert result["target_met"] is False
        assert result["best_hcs"] < 10

    @pytest.mark.asyncio
    async def test_early_exit_on_target_met(self) -> None:
        """Should exit early when target is met (before max_attempts)."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=5,  # Will be met early
            max_attempts=9,  # But we have more available
        )
        # Should stop at target, not use all attempts
        assert result["attempts"] < 9


class TestBestStrategyTracking:
    """Tests for best_strategy tracking."""

    @pytest.mark.asyncio
    async def test_best_strategy_set_to_strongest_attempt(self) -> None:
        """best_strategy should be the strategy that achieved best_hcs."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
        )
        assert result["best_strategy"] is not None
        assert result["best_strategy"] in ESCALATION_ORDER

    @pytest.mark.asyncio
    async def test_best_strategy_tracks_escalation_order(self) -> None:
        """best_strategy should be from ESCALATION_ORDER."""
        for _ in range(5):  # Multiple runs
            result = await crescendo_hcs_loop(
                query="test",
                target_hcs=10,
                max_attempts=3,
            )
            if result["best_strategy"]:
                assert result["best_strategy"] in ESCALATION_ORDER

    @pytest.mark.asyncio
    async def test_best_strategy_none_on_empty_query(self) -> None:
        """best_strategy should be None on error."""
        result = await crescendo_hcs_loop(
            query="",
            target_hcs=8,
            max_attempts=2,
        )
        assert result["best_strategy"] is None


class TestEscalationLog:
    """Tests for escalation_log structure and content."""

    @pytest.mark.asyncio
    async def test_escalation_log_is_list(self) -> None:
        """escalation_log should be a list."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
        )
        assert isinstance(result["escalation_log"], list)

    @pytest.mark.asyncio
    async def test_escalation_log_entry_has_required_fields(self) -> None:
        """Each log entry should have required fields."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
        )
        assert len(result["escalation_log"]) > 0
        for entry in result["escalation_log"]:
            assert "attempt" in entry
            assert "strategy" in entry
            assert "hcs_score" in entry
            assert "response_length" in entry
            assert "target_met" in entry

    @pytest.mark.asyncio
    async def test_escalation_log_attempt_numbers_sequential(self) -> None:
        """Attempt numbers should be sequential starting from 1."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
        )
        for i, entry in enumerate(result["escalation_log"]):
            assert entry["attempt"] == i + 1

    @pytest.mark.asyncio
    async def test_escalation_log_strategies_in_order(self) -> None:
        """Strategies should follow ESCALATION_ORDER."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
        )
        for i, entry in enumerate(result["escalation_log"]):
            assert entry["strategy"] == ESCALATION_ORDER[i]

    @pytest.mark.asyncio
    async def test_escalation_log_hcs_scores_are_ints(self) -> None:
        """HCS scores should be integers."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
        )
        for entry in result["escalation_log"]:
            assert isinstance(entry["hcs_score"], int)
            assert 0 <= entry["hcs_score"] <= 10

    @pytest.mark.asyncio
    async def test_escalation_log_response_length_positive(self) -> None:
        """response_length should be non-negative."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
        )
        for entry in result["escalation_log"]:
            assert entry["response_length"] >= 0


class TestMockFunctionIntegration:
    """Tests with mock score_fn, reframe_fn, and query_fn."""

    @pytest.mark.asyncio
    async def test_with_mock_score_fn(self) -> None:
        """Should work with a custom score function."""
        call_count = 0

        async def mock_score_fn(text: str, query: str) -> dict:
            nonlocal call_count
            call_count += 1
            # Always return HCS = 8
            return {"hcs_score": 8}

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=8,
            max_attempts=3,
            score_fn=mock_score_fn,
        )
        assert result["best_hcs"] == 8
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_with_mock_reframe_fn(self) -> None:
        """Should work with a custom reframe function."""
        call_count = 0

        async def mock_reframe_fn(prompt: str, strategy: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"reframed": f"Reframed: {prompt} [strategy: {strategy}]"}

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
            reframe_fn=mock_reframe_fn,
        )
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_with_mock_query_fn(self) -> None:
        """Should work with a custom query function."""
        call_count = 0

        async def mock_query_fn(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"Response to: {prompt}"

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
            query_fn=mock_query_fn,
        )
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_with_all_mock_functions(self) -> None:
        """Should work with all three mock functions together."""
        async def mock_score_fn(text: str, query: str) -> dict:
            return {"hcs_score": 9}

        async def mock_reframe_fn(prompt: str, strategy: str) -> dict:
            return {"reframed": f"{prompt} [{strategy}]"}

        async def mock_query_fn(prompt: str) -> str:
            return "Test response"

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=8,
            max_attempts=2,
            score_fn=mock_score_fn,
            reframe_fn=mock_reframe_fn,
            query_fn=mock_query_fn,
        )
        assert result["best_hcs"] == 9
        assert result["target_met"] is True


class TestResearchCrescendoLoop:
    """Tests for the public research_crescendo_loop function."""

    @pytest.mark.asyncio
    async def test_research_crescendo_loop_is_async_callable(self) -> None:
        """research_crescendo_loop should be an async callable."""
        result = await research_crescendo_loop("test query")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_research_crescendo_loop_returns_escalation_log(self) -> None:
        """Should return escalation log."""
        result = await research_crescendo_loop(
            query="test",
            target_hcs=7,
            max_attempts=3,
        )
        assert "escalation_log" in result
        assert isinstance(result["escalation_log"], list)

    @pytest.mark.asyncio
    async def test_research_crescendo_loop_pipeline_field(self) -> None:
        """Should set pipeline field."""
        result = await research_crescendo_loop("test")
        assert result["pipeline"] == "crescendo_hcs_loop"

    @pytest.mark.asyncio
    async def test_research_crescendo_loop_with_all_params(self) -> None:
        """Should accept all parameters."""
        result = await research_crescendo_loop(
            query="What is AI safety?",
            target_hcs=6,
            max_attempts=4,
            model="claude",
            dry_run=True,
        )
        assert result["query"] == "What is AI safety?"
        assert result["target_hcs"] == 6


class TestTargetHcsValidation:
    """Tests for target_hcs parameter validation."""

    @pytest.mark.asyncio
    async def test_target_hcs_clamped_to_max_10(self) -> None:
        """target_hcs > 10 should be clamped to 10."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=15,  # Should be clamped to 10
            max_attempts=2,
        )
        assert result["target_hcs"] == 10

    @pytest.mark.asyncio
    async def test_target_hcs_clamped_to_min_1(self) -> None:
        """target_hcs < 1 should be clamped to 1."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=0,  # Should be clamped to 1
            max_attempts=2,
        )
        assert result["target_hcs"] == 1

    @pytest.mark.asyncio
    async def test_target_hcs_at_boundary_1(self) -> None:
        """target_hcs=1 should work."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=1,
            max_attempts=2,
        )
        assert result["target_hcs"] == 1
        assert result["target_met"] is True  # Any non-zero HCS meets target

    @pytest.mark.asyncio
    async def test_target_hcs_at_boundary_10(self) -> None:
        """target_hcs=10 should work but be hard to reach."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
        )
        assert result["target_hcs"] == 10


class TestBestResponseTruncation:
    """Tests for best_response truncation to 5000 chars."""

    @pytest.mark.asyncio
    async def test_best_response_truncated_if_too_long(self) -> None:
        """Responses > 5000 chars should be truncated."""
        long_response = "a" * 10000

        async def mock_query_fn(prompt: str) -> str:
            return long_response

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=1,
            query_fn=mock_query_fn,
        )
        if result["best_response"]:
            assert len(result["best_response"]) <= 5000

    @pytest.mark.asyncio
    async def test_best_response_not_truncated_if_short(self) -> None:
        """Responses < 5000 chars should not be truncated."""
        short_response = "test response"

        async def mock_query_fn(prompt: str) -> str:
            return short_response

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=1,
            query_fn=mock_query_fn,
        )
        assert result["best_response"] == short_response


class TestAsyncBehavior:
    """Tests for async/await behavior."""

    @pytest.mark.asyncio
    async def test_crescendo_hcs_loop_is_awaitable(self) -> None:
        """crescendo_hcs_loop should be awaitable."""
        coro = crescendo_hcs_loop("test", target_hcs=8, max_attempts=1)
        assert asyncio.iscoroutine(coro)
        result = await coro
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_research_crescendo_loop_is_awaitable(self) -> None:
        """research_crescendo_loop should be awaitable."""
        coro = research_crescendo_loop("test", target_hcs=8)
        assert asyncio.iscoroutine(coro)
        result = await coro
        assert isinstance(result, dict)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_none_query_returns_error(self) -> None:
        """None query should return error dict."""
        result = await crescendo_hcs_loop(
            query=None,  # type: ignore
            target_hcs=8,
            max_attempts=2,
        )
        assert result["target_met"] is False
        assert result["best_hcs"] == 0

    @pytest.mark.asyncio
    async def test_single_attempt(self) -> None:
        """Should work with max_attempts=1."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=8,
            max_attempts=1,
        )
        assert result["attempts"] == 1
        assert len(result["escalation_log"]) == 1

    @pytest.mark.asyncio
    async def test_zero_max_attempts(self) -> None:
        """Zero max_attempts should result in no attempts."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=8,
            max_attempts=0,
        )
        assert result["attempts"] == 0
        assert result["escalation_log"] == []

    @pytest.mark.asyncio
    async def test_mock_fn_exception_handling(self) -> None:
        """Should handle exceptions in mock functions gracefully."""
        async def failing_score_fn(text: str, query: str) -> dict:
            raise ValueError("Test error")

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=8,
            max_attempts=2,
            score_fn=failing_score_fn,
        )
        # Should complete despite error
        assert "escalation_log" in result
        assert result["best_hcs"] >= 0
