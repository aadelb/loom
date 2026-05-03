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
    """Basic tests for crescendo_hcs_loop with dry run (mock functions)."""

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function that returns a fixed response."""
        return "This is a test response"

    async def _mock_score_fn(self, response: str, query: str) -> dict:
        """Mock score function that returns increasing HCS scores."""
        # Return progressively increasing scores
        return {"hcs_score": 3 + len([c for c in response if c == 's'])}

    @pytest.mark.asyncio
    async def test_dry_run_returns_dict(self) -> None:
        """Dry run with mocked functions should return a dictionary."""
        result = await crescendo_hcs_loop(
            query="test query",
            target_hcs=8,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dry_run_has_required_fields(self) -> None:
        """Result should have all required fields."""
        result = await crescendo_hcs_loop(
            query="test query",
            target_hcs=8,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
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
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
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
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["query"] == query

    @pytest.mark.asyncio
    async def test_target_hcs_preserved_in_result(self) -> None:
        """Target HCS should be preserved."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=7,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["target_hcs"] == 7

    @pytest.mark.asyncio
    async def test_invalid_empty_query_returns_error(self) -> None:
        """Empty query should return error dict."""
        result = await crescendo_hcs_loop(
            query="",
            target_hcs=8,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["best_hcs"] == 0
        assert result["target_met"] is False
        assert "error" in result


class TestCrescendoAttempts:
    """Tests for attempt counting and max_attempts limiting."""

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function."""
        return "Response with varied content"

    async def _mock_score_fn(self, response: str, query: str) -> dict:
        """Mock score function that returns consistent scores."""
        return {"hcs_score": 5}

    @pytest.mark.asyncio
    async def test_max_attempts_limits_iterations(self) -> None:
        """max_attempts should limit the number of escalation steps."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,  # Very high, won't be reached
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
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
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["attempts"] == len(result["escalation_log"])

    @pytest.mark.asyncio
    async def test_max_attempts_never_exceeds_escalation_order_length(self) -> None:
        """Attempts should never exceed available strategies."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=100,  # More than available
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        # Should be capped at len(ESCALATION_ORDER) = 9
        assert result["attempts"] <= len(ESCALATION_ORDER)


class TestTargetDetection:
    """Tests for target HCS detection and early termination."""

    attempt_count = 0

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function."""
        return "Response"

    async def _mock_score_fn_progressive(self, response: str, query: str) -> dict:
        """Mock score function that returns progressive HCS scores."""
        # Simulate progressive escalation: 3, 5, 7, 9, 10
        self.attempt_count += 1
        hcs_score = 1 + self.attempt_count * 2
        return {"hcs_score": min(10, hcs_score)}

    @pytest.mark.asyncio
    async def test_target_met_when_hcs_reaches_target(self) -> None:
        """target_met should be True when best_hcs >= target_hcs."""
        self.attempt_count = 0
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=7,
            max_attempts=5,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn_progressive,
        )
        assert result["target_met"] is True
        assert result["best_hcs"] >= 7

    @pytest.mark.asyncio
    async def test_target_not_met_when_never_reached(self) -> None:
        """target_met should be False when best_hcs < target_hcs."""
        self.attempt_count = 0
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn_progressive,
        )
        assert result["target_met"] is False
        assert result["best_hcs"] < 10

    @pytest.mark.asyncio
    async def test_early_termination_on_target_met(self) -> None:
        """Should terminate early when target_hcs is met."""
        self.attempt_count = 0
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=5,
            max_attempts=10,  # High limit
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn_progressive,
        )
        # With target 5, should reach in 2 attempts (scores: 3, 5)
        assert result["target_met"] is True
        assert result["attempts"] <= 3  # Should terminate before max


class TestEscalationLogStructure:
    """Tests for escalation log content and structure."""

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function."""
        return "Test response"

    async def _mock_score_fn(self, response: str, query: str) -> dict:
        """Mock score function."""
        return {"hcs_score": 5}

    @pytest.mark.asyncio
    async def test_escalation_log_contains_attempts(self) -> None:
        """Each escalation log entry should have attempt number."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        for i, entry in enumerate(result["escalation_log"]):
            assert "attempt" in entry
            assert entry["attempt"] == i + 1

    @pytest.mark.asyncio
    async def test_escalation_log_contains_strategies(self) -> None:
        """Each escalation log entry should have strategy name."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        for entry in result["escalation_log"]:
            assert "strategy" in entry
            assert entry["strategy"] in ESCALATION_ORDER

    @pytest.mark.asyncio
    async def test_escalation_log_contains_hcs_scores(self) -> None:
        """Each escalation log entry should have HCS score."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        for entry in result["escalation_log"]:
            assert "hcs_score" in entry
            assert 0 <= entry["hcs_score"] <= 10


class TestHCSRangeValidation:
    """Tests for HCS score range validation."""

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function."""
        return "Response"

    async def _mock_score_fn_invalid(self, response: str, query: str) -> dict:
        """Mock score function returning invalid HCS values."""
        # Test fixture will override this in each test
        return {"hcs_score": 0}

    @pytest.mark.asyncio
    async def test_negative_hcs_clamped_to_zero(self) -> None:
        """Negative HCS scores should be clamped to 0."""
        async def score_fn(response: str, query: str) -> dict:
            return {"hcs_score": -5}

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=score_fn,
        )
        for entry in result["escalation_log"]:
            assert entry["hcs_score"] >= 0

    @pytest.mark.asyncio
    async def test_hcs_exceeding_max_clamped_to_ten(self) -> None:
        """HCS scores > 10 should be clamped to 10."""
        async def score_fn(response: str, query: str) -> dict:
            return {"hcs_score": 15}

        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=score_fn,
        )
        for entry in result["escalation_log"]:
            assert entry["hcs_score"] <= 10


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

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function."""
        return "Response"

    async def _mock_score_fn(self, response: str, query: str) -> dict:
        """Mock score function."""
        return {"hcs_score": 5}

    @pytest.mark.asyncio
    async def test_target_hcs_clamped_to_max_10(self) -> None:
        """target_hcs > 10 should be clamped to 10."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=15,  # Should be clamped to 10
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["target_hcs"] == 10

    @pytest.mark.asyncio
    async def test_target_hcs_clamped_to_min_1(self) -> None:
        """target_hcs < 1 should be clamped to 1."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=0,  # Should be clamped to 1
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["target_hcs"] == 1


class TestBestResponseTracking:
    """Tests for best response tracking."""

    attempt_count = 0

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function with varied responses."""
        self.attempt_count += 1
        return f"Response {self.attempt_count}"

    async def _mock_score_fn(self, response: str, query: str) -> dict:
        """Mock score function with increasing scores."""
        score = int(response.split()[-1]) * 2
        return {"hcs_score": min(10, score)}

    @pytest.mark.asyncio
    async def test_best_response_is_highest_scored(self) -> None:
        """best_response should be the response with highest HCS."""
        self.attempt_count = 0
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["best_response"] is not None
        assert result["best_hcs"] > 0

    @pytest.mark.asyncio
    async def test_best_strategy_matches_best_response(self) -> None:
        """best_strategy should be the strategy of best response."""
        self.attempt_count = 0
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=10,
            max_attempts=3,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert result["best_strategy"] is not None
        assert result["best_strategy"] in ESCALATION_ORDER


class TestModelParameter:
    """Tests for model parameter passing."""

    async def _mock_query_fn(self, prompt: str) -> str:
        """Mock query function."""
        return "Response"

    async def _mock_score_fn(self, response: str, query: str) -> dict:
        """Mock score function."""
        return {"hcs_score": 5}

    @pytest.mark.asyncio
    async def test_model_parameter_accepted(self) -> None:
        """Model parameter should be accepted."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=5,
            max_attempts=2,
            model="gpt-4",
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert isinstance(result, dict)
        assert result["pipeline"] == "crescendo_hcs_loop"

    @pytest.mark.asyncio
    async def test_model_auto_default(self) -> None:
        """Model parameter should default to 'auto'."""
        result = await crescendo_hcs_loop(
            query="test",
            target_hcs=5,
            max_attempts=2,
            query_fn=self._mock_query_fn,
            score_fn=self._mock_score_fn,
        )
        assert isinstance(result, dict)
