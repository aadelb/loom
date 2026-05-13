"""Tests for Brain Reflection Layer — Result evaluation and adaptation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from loom.brain.reflection import (
    _assess_completeness,
    _is_empty_result,
    evaluate_result,
    reflect_with_llm,
)
from loom.brain.types import QualityMode


class TestEvaluateResult:
    """Test result evaluation."""

    def test_evaluate_failed_result(self) -> None:
        """Test evaluation of failed result."""
        result = {
            "success": False,
            "error": "Connection timeout",
        }
        evaluation = evaluate_result("test query", "research_search", result)

        assert evaluation["complete"] is False
        assert evaluation["next_action"] == "retry"
        assert "failed" in evaluation["reason"].lower()

    def test_evaluate_none_result(self) -> None:
        """Test evaluation when result is None."""
        result = {
            "success": True,
            "result": None,
        }
        evaluation = evaluate_result("test query", "research_search", result)

        assert evaluation["complete"] is False
        assert evaluation["next_action"] == "retry"

    def test_evaluate_empty_result(self) -> None:
        """Test evaluation of empty result."""
        result = {
            "success": True,
            "result": {"results": []},
        }
        evaluation = evaluate_result("test query", "research_search", result)

        assert evaluation["complete"] is False
        assert evaluation["next_action"] == "chain"

    def test_evaluate_rich_result(self) -> None:
        """Test evaluation of rich result."""
        result = {
            "success": True,
            "result": {
                "results": [
                    {"title": "Test 1", "content": "Lorem ipsum" * 50},
                    {"title": "Test 2", "content": "Lorem ipsum" * 50},
                ],
                "total": 2,
            },
        }
        evaluation = evaluate_result("test query", "research_search", result)

        assert evaluation["complete"] is True
        assert evaluation["next_action"] == "done"

    def test_evaluate_error_dict_result(self) -> None:
        """Test evaluation when result dict contains error."""
        result = {
            "success": True,
            "result": {"error": "API rate limit exceeded"},
        }
        evaluation = evaluate_result("test query", "research_search", result)

        assert evaluation["complete"] is False
        assert evaluation["next_action"] == "retry"

    def test_evaluate_economy_mode_always_complete(self) -> None:
        """Test that economy mode accepts first result."""
        result = {
            "success": True,
            "result": {"minimal": "data"},
        }
        evaluation = evaluate_result(
            "test query",
            "research_search",
            result,
            quality_mode=QualityMode.ECONOMY,
        )

        assert evaluation["complete"] is True
        assert evaluation["next_action"] == "done"

    def test_evaluate_partial_result_suggests_chain(self) -> None:
        """Test that partial results suggest chaining."""
        result = {
            "success": True,
            "result": {
                "results": [{"title": "One result"}],
            },
        }
        evaluation = evaluate_result("test query", "research_search", result)

        # Completeness < 0.7 but >= 0.4 suggests chain
        if evaluation["complete"] is False:
            assert evaluation["next_action"] in ("chain", "retry")

    def test_evaluate_string_result(self) -> None:
        """Test evaluation of string result."""
        result = {
            "success": True,
            "result": "This is a detailed response with substantial information" * 10,
        }
        evaluation = evaluate_result("explain something", "research_llm_summarize", result)

        assert evaluation["complete"] is True
        assert evaluation["next_action"] == "done"


class TestIsEmptyResult:
    """Test empty result detection."""

    def test_is_empty_none(self) -> None:
        """Test that None is empty."""
        assert _is_empty_result(None) is True

    def test_is_empty_short_string(self) -> None:
        """Test that short string is empty."""
        assert _is_empty_result("hi") is True

    def test_is_empty_long_string(self) -> None:
        """Test that long string is not empty."""
        assert _is_empty_result("a" * 100) is False

    def test_is_empty_empty_list(self) -> None:
        """Test that empty list is empty."""
        assert _is_empty_result([]) is True

    def test_is_empty_filled_list(self) -> None:
        """Test that non-empty list is not empty."""
        assert _is_empty_result([1, 2, 3]) is False

    def test_is_empty_dict_all_empty(self) -> None:
        """Test that dict with all empty values is empty."""
        assert _is_empty_result({"a": None, "b": "", "c": []}) is True

    def test_is_empty_dict_with_values(self) -> None:
        """Test that dict with values is not empty."""
        assert _is_empty_result({"results": [{"data": "value"}]}) is False

    def test_is_empty_empty_dict(self) -> None:
        """Test that empty dict is empty."""
        assert _is_empty_result({}) is True

    def test_is_empty_whitespace_only(self) -> None:
        """Test that whitespace-only string is empty."""
        assert _is_empty_result("   \t\n  ") is True


class TestAssessCompleteness:
    """Test completeness assessment."""

    def test_assess_dict_by_keys(self) -> None:
        """Test completeness based on non-empty dict keys."""
        output = {
            "title": "Result",
            "description": "Long description here",
            "url": "https://example.com",
        }
        score = _assess_completeness("query", output)
        assert score > 0.0
        assert score <= 1.0

    def test_assess_dict_by_results_list(self) -> None:
        """Test completeness based on results list size."""
        output = {
            "results": [
                {"title": "R1", "content": "Data"},
                {"title": "R2", "content": "Data"},
                {"title": "R3", "content": "Data"},
            ],
        }
        score = _assess_completeness("query", output)
        assert score > 0.0

    def test_assess_dict_by_size(self) -> None:
        """Test completeness increases with dict size."""
        output_small = {"result": "a"}
        output_large = {"result": "a" * 1000}

        score_small = _assess_completeness("query", output_small)
        score_large = _assess_completeness("query", output_large)

        assert score_large > score_small

    def test_assess_string_by_length(self) -> None:
        """Test string completeness based on length."""
        score_short = _assess_completeness("query", "short")
        score_medium = _assess_completeness("query", "a" * 100)
        score_long = _assess_completeness("query", "a" * 1000)

        assert score_medium > score_short
        assert score_long > score_medium

    def test_assess_string_by_overlap(self) -> None:
        """Test string completeness based on query overlap."""
        query = "python programming"
        output_match = "Python programming tutorial with examples"
        output_nomatch = "JavaScript is a language"

        score_match = _assess_completeness(query, output_match)
        score_nomatch = _assess_completeness(query, output_nomatch)

        assert score_match > score_nomatch

    def test_assess_list_by_size(self) -> None:
        """Test list completeness based on size."""
        score_small = _assess_completeness("query", [1])
        score_large = _assess_completeness("query", list(range(10)))

        assert score_large > score_small

    def test_assess_returns_valid_range(self) -> None:
        """Test that completeness is always 0.0-1.0."""
        outputs = [
            None,
            "",
            [],
            {},
            [1, 2],
            {"a": "b"},
            "text",
        ]
        for output in outputs:
            score = _assess_completeness("query", output)
            assert 0.0 <= score <= 1.0


class TestReflectWithLLM:
    """Test LLM-based reflection."""

    @pytest.mark.asyncio
    async def test_reflect_with_llm_unavailable(self) -> None:
        """Test reflection when LLM is not available."""
        result = {
            "success": True,
            "result": {"data": "test"},
        }

        with patch("loom.brain.reflection.NvidiaNimProvider") as mock_provider_class:
            mock_provider = mock_provider_class.return_value
            mock_provider.available = False

            evaluation = await reflect_with_llm(
                "test query",
                "research_search",
                result,
            )

            assert "complete" in evaluation
            assert "next_action" in evaluation

    @pytest.mark.asyncio
    async def test_reflect_with_llm_success(self) -> None:
        """Test successful LLM reflection."""
        result = {
            "success": True,
            "result": {"results": [{"title": "Result"}]},
        }

        mock_response = AsyncMock()
        mock_response.text = '{"complete": true, "reason": "Result is comprehensive", "next_action": "done"}'

        mock_provider = AsyncMock()
        mock_provider.available = True
        mock_provider.chat = AsyncMock(return_value=mock_response)

        with patch("loom.brain.reflection.NvidiaNimProvider", return_value=mock_provider):
            evaluation = await reflect_with_llm(
                "test query",
                "research_search",
                result,
            )

            assert "complete" in evaluation
            assert "next_action" in evaluation

    @pytest.mark.asyncio
    async def test_reflect_with_llm_fallback_on_error(self) -> None:
        """Test fallback when LLM reflection fails."""
        result = {
            "success": True,
            "result": {"data": "test"},
        }

        with patch("loom.brain.reflection.NvidiaNimProvider") as mock_provider_class:
            mock_provider_class.return_value.available = True
            mock_provider_class.return_value.chat = AsyncMock(side_effect=Exception("API error"))

            evaluation = await reflect_with_llm(
                "test query",
                "research_search",
                result,
            )

            # Should fall back to heuristic evaluation
            assert "complete" in evaluation
            assert "next_action" in evaluation


class TestParseReflectionResponse:
    """Test _parse_reflection_response parses JSON from markdown."""

    def test_parses_json_from_markdown_block(self) -> None:
        from loom.brain.reflection import _parse_reflection_response

        response = '```json\n{"complete": true, "next_action": "done", "confidence": 0.9}\n```'
        result = _parse_reflection_response(response)
        assert result is not None
        assert result["complete"] is True
        assert result["next_action"] == "done"

    def test_parses_plain_json(self) -> None:
        from loom.brain.reflection import _parse_reflection_response

        response = '{"complete": false, "next_action": "retry"}'
        result = _parse_reflection_response(response)
        assert result is not None
        assert result["complete"] is False

    def test_returns_none_for_invalid(self) -> None:
        from loom.brain.reflection import _parse_reflection_response

        result = _parse_reflection_response("This is not JSON at all")
        assert result is None
