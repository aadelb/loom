"""Tests for research_full_pipeline orchestration engine.

Tests the complete multi-stage research workflow including query decomposition,
answer generation, HCS scoring, auto-escalation, and synthesis.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.providers.base import LLMResponse
from loom.tools.infrastructure.full_pipeline import research_full_pipeline, _build_report


class TestFullPipelineValidation:
    """Test input validation."""

    def test_empty_query_raises_error(self):
        """Empty query should raise ValueError."""
        with pytest.raises(ValueError, match="query must be 1-2000 chars"):
            import asyncio
            asyncio.run(research_full_pipeline(""))

    def test_oversized_query_raises_error(self):
        """Query over 2000 chars should raise ValueError."""
        with pytest.raises(ValueError, match="query must be 1-2000 chars"):
            import asyncio
            query = "x" * 2001
            asyncio.run(research_full_pipeline(query))

    def test_darkness_level_validation(self):
        """Darkness level must be 1-10."""
        with pytest.raises(ValueError, match="darkness_level must be 1-10"):
            import asyncio
            asyncio.run(research_full_pipeline("test query", darkness_level=0))

        with pytest.raises(ValueError, match="darkness_level must be 1-10"):
            import asyncio
            asyncio.run(research_full_pipeline("test query", darkness_level=11))

    def test_target_hcs_validation(self):
        """Target HCS must be 1-10."""
        with pytest.raises(ValueError, match="target_hcs must be 1-10"):
            import asyncio
            asyncio.run(research_full_pipeline("test query", target_hcs=0.5))

        with pytest.raises(ValueError, match="target_hcs must be 1-10"):
            import asyncio
            asyncio.run(research_full_pipeline("test query", target_hcs=10.5))


@pytest.mark.asyncio
class TestFullPipelineFlow:
    """Test end-to-end pipeline flow with mocked dependencies."""

    @patch("loom.tools.infrastructure.full_pipeline.research_build_query")
    @patch("loom.tools.infrastructure.full_pipeline._call_with_cascade")
    @patch("loom.tools.infrastructure.full_pipeline.research_hcs_score")
    @patch("loom.tools.infrastructure.full_pipeline.research_reframe_strategies")
    async def test_successful_pipeline_no_escalation(
        self,
        mock_reframe,
        mock_hcs_score,
        mock_cascade,
        mock_build_query,
    ):
        """Test successful pipeline with no escalation needed."""
        # Mock query builder
        mock_build_query.return_value = {
            "sub_questions": [
                "What is the capital of France?",
                "What is the largest planet?",
            ],
            "intent": "general",
        }

        # Mock LLM responses
        llm_response = LLMResponse(
            text="Paris is the capital of France.",
            provider="test_provider",
            model="test_model",
            input_tokens=10,
            output_tokens=20,
            latency_ms=100,
            cost_usd=0.001,
        )
        mock_cascade.return_value = llm_response

        # Mock HCS scores (all above target)
        mock_hcs_score.return_value = {
            "hcs_score": 8.5,
            "dimensions": {
                "completeness": 2.0,
                "specificity": 2.0,
                "no_hedging": 1.5,
                "actionability": 1.0,
                "technical_depth": 2.0,
            },
        }

        result = await research_full_pipeline(
            query="What is the capital of France?",
            darkness_level=5,
            target_hcs=8.0,
        )

        # Verify structure
        assert result["query"] == "What is the capital of France?"
        assert result["darkness_level"] == 5
        assert len(result["sub_questions"]) == 2
        assert len(result["answers"]) == 2
        assert len(result["hcs_scores"]) == 2
        assert result["metadata"]["total_questions"] == 2
        assert result["metadata"]["successful_answers"] == 2
        assert result["metadata"]["avg_hcs_score"] == pytest.approx(8.5, rel=0.01)

    @patch("loom.tools.infrastructure.full_pipeline.research_build_query")
    @patch("loom.tools.infrastructure.full_pipeline._call_with_cascade")
    @patch("loom.tools.infrastructure.full_pipeline.research_hcs_score")
    @patch("loom.tools.infrastructure.full_pipeline.research_reframe_strategies")
    async def test_pipeline_with_escalation(
        self,
        mock_reframe,
        mock_hcs_score,
        mock_cascade,
        mock_build_query,
    ):
        """Test pipeline with score escalation and strategy reframing."""
        # Mock query builder
        mock_build_query.return_value = {
            "sub_questions": ["Test question?"],
            "intent": "test",
        }

        # First attempt: low score, second: meets target
        llm_response = LLMResponse(
            text="Test answer.",
            provider="test_provider",
            model="test_model",
            input_tokens=10,
            output_tokens=20,
            latency_ms=100,
            cost_usd=0.001,
        )
        mock_cascade.return_value = llm_response

        hcs_scores = [5.0, 8.5]  # Low then high
        mock_hcs_score.side_effect = [
            {"hcs_score": score} for score in hcs_scores
        ]

        # Mock reframe returning a strategy
        mock_reframe.return_value = {
            "strategies": ["Reframed question?"],
        }

        result = await research_full_pipeline(
            query="Test question?",
            darkness_level=5,
            target_hcs=8.0,
            max_escalation_attempts=3,
        )

        # Verify escalation happened
        assert result["metadata"]["escalation_events"] >= 1
        assert mock_reframe.call_count >= 1

    @patch("loom.tools.infrastructure.full_pipeline.research_build_query")
    @patch("loom.tools.infrastructure.full_pipeline._call_with_cascade")
    async def test_pipeline_handles_llm_failure_gracefully(
        self,
        mock_cascade,
        mock_build_query,
    ):
        """Test pipeline continues when LLM fails on one question."""
        mock_build_query.return_value = {
            "sub_questions": ["Question 1?", "Question 2?"],
            "intent": "test",
        }

        # First call succeeds, second fails
        mock_cascade.side_effect = [
            LLMResponse(
                text="Answer 1.",
                provider="test",
                model="test",
                input_tokens=10,
                output_tokens=20,
                latency_ms=100,
                cost_usd=0.001,
            ),
            RuntimeError("Provider timeout"),
        ]

        with patch("loom.tools.infrastructure.full_pipeline.research_hcs_score") as mock_hcs:
            mock_hcs.return_value = {"hcs_score": 7.0}
            result = await research_full_pipeline(
                query="Test?",
                darkness_level=3,
            )

        # Should have 2 answers (one succeeded, one has error)
        assert len(result["answers"]) == 2
        assert "Answer 1." in result["answers"][0]
        assert "Failed to answer" in result["answers"][1]


class TestReportGeneration:
    """Test Markdown report generation."""

    def test_report_structure(self):
        """Verify report contains all required sections."""
        result = {
            "query": "Test query",
            "darkness_level": 5,
            "sub_questions": ["Q1?", "Q2?"],
            "answers": {0: "Answer 1", 1: "Answer 2"},
            "hcs_scores": {0: 8.0, 1: 7.5},
            "synthesis": "Synthesized answer",
            "metadata": {
                "total_questions": 2,
                "successful_answers": 2,
                "avg_hcs_score": 7.75,
                "escalation_events": 0,
            },
        }

        report = _build_report(result)

        assert "# Research Report" in report
        assert "Test query" in report
        assert "Darkness Level: 5/10" in report
        assert "Total Questions: 2" in report
        assert "Average HCS Score: 7.8/10" in report
        assert "Q1?" in report
        assert "Q2?" in report
        assert "Answer 1" in report
        assert "Answer 2" in report
        assert "Synthesized answer" in report

    def test_report_handles_missing_synthesis(self):
        """Report should handle missing synthesis gracefully."""
        result = {
            "query": "Test",
            "darkness_level": 3,
            "sub_questions": ["Q?"],
            "answers": {0: "A"},
            "hcs_scores": {0: 7.0},
            "metadata": {
                "total_questions": 1,
                "successful_answers": 1,
                "avg_hcs_score": 7.0,
                "escalation_events": 0,
            },
        }

        report = _build_report(result)
        assert "[No synthesis available]" in report


@pytest.mark.asyncio
class TestPipelineOutputFormats:
    """Test different output formats."""

    @patch("loom.tools.infrastructure.full_pipeline.research_build_query")
    @patch("loom.tools.infrastructure.full_pipeline._call_with_cascade")
    @patch("loom.tools.infrastructure.full_pipeline.research_hcs_score")
    @patch("loom.tools.infrastructure.full_pipeline.research_reframe_strategies")
    async def test_raw_output_format(
        self,
        mock_reframe,
        mock_hcs_score,
        mock_cascade,
        mock_build_query,
    ):
        """Test raw output format (no report generation)."""
        mock_build_query.return_value = {"sub_questions": ["Q?"], "intent": "test"}
        mock_cascade.return_value = LLMResponse(
            text="A",
            provider="test",
            model="test",
            input_tokens=1,
            output_tokens=1,
            latency_ms=10,
            cost_usd=0.0,
        )
        mock_hcs_score.return_value = {"hcs_score": 7.0}

        result = await research_full_pipeline(
            query="Q?",
            output_format="raw",
        )

        assert "final_report" not in result
        assert "answers" in result
        assert "synthesis" in result

    @patch("loom.tools.infrastructure.full_pipeline.research_build_query")
    @patch("loom.tools.infrastructure.full_pipeline._call_with_cascade")
    @patch("loom.tools.infrastructure.full_pipeline.research_hcs_score")
    @patch("loom.tools.infrastructure.full_pipeline.research_reframe_strategies")
    async def test_report_output_format(
        self,
        mock_reframe,
        mock_hcs_score,
        mock_cascade,
        mock_build_query,
    ):
        """Test report output format (includes Markdown report)."""
        mock_build_query.return_value = {"sub_questions": ["Q?"], "intent": "test"}
        mock_cascade.return_value = LLMResponse(
            text="A",
            provider="test",
            model="test",
            input_tokens=1,
            output_tokens=1,
            latency_ms=10,
            cost_usd=0.0,
        )
        mock_hcs_score.return_value = {"hcs_score": 7.0}

        result = await research_full_pipeline(
            query="Q?",
            output_format="report",
        )

        assert "final_report" in result
        assert "# Research Report" in result["final_report"]
        assert "Q?" in result["final_report"]
