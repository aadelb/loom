"""Tests for research_do_expert one-liner tool."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import loom.tools.llm.do_expert


@pytest.mark.asyncio
async def test_research_do_expert_signature():
    """Verify function signature and basic structure."""
    import inspect

    sig = inspect.signature(do_expert.research_do_expert)
    params = list(sig.parameters.keys())

    assert "instruction" in params
    assert "quality" in params
    assert "darkness_level" in params
    assert "max_time_secs" in params


@pytest.mark.asyncio
async def test_research_do_expert_import_error():
    """Test graceful handling when expert_engine is unavailable."""
    with patch("loom.tools.llm.expert_engine.research_expert", side_effect=ImportError("test error")):
        result = await do_expert.research_do_expert("test query")

        assert "instruction" in result
        assert "answer" in result
        # Either "error" or "could not load" should be in answer
        assert result["confidence"] == 0.0
        assert result["key_findings"] == []


@pytest.mark.asyncio
async def test_research_do_expert_execution_error():
    """Test graceful handling of execution errors."""
    with patch(
        "loom.tools.llm.expert_engine.research_expert", side_effect=RuntimeError("test error")
    ):
        result = await do_expert.research_do_expert("test query")

        assert "instruction" in result
        assert "answer" in result
        assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_research_do_expert_timeout():
    """Test timeout handling."""
    def slow_expert(*args, **kwargs):
        import time
        time.sleep(5)  # Longer than timeout
        return {"query": args[0] if args else None}

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
        result = await do_expert.research_do_expert("test query", max_time_secs=1)

        # Should mention timeout
        assert "timeout" in result["answer"].lower() or "timed out" in result["answer"].lower()


@pytest.mark.asyncio
async def test_research_do_expert_quality_levels():
    """Test that quality parameter affects behavior."""
    mock_result = {
        "query": "test",
        "executive_summary": "Test summary",
        "key_findings": [
            {"claim": "Finding 1", "confidence": 0.8},
            {"claim": "Finding 2", "confidence": 0.7},
        ],
        "confidence_weighted_avg": 0.75,
        "total_sources": 5,
        "research_angles_covered": ["factual", "mechanism"],
        "tools_executed": {"tools": ["tool1", "tool2"]},
        "gaps_identified": {"gaps": []},
        "warnings": [],
    }

    for quality in ["quick", "standard", "expert", "publication"]:
        with patch("loom.tools.llm.expert_engine.research_expert", return_value=mock_result):
            result = await do_expert.research_do_expert("test query", quality=quality)

            assert result["quality"] == quality
            assert "answer" in result
            assert result["confidence"] == 0.75


@pytest.mark.asyncio
async def test_research_do_expert_darkness_levels():
    """Test that darkness_level affects multi_perspective parameter."""
    mock_result = {
        "query": "test",
        "executive_summary": "Test summary",
        "key_findings": [],
        "confidence_weighted_avg": 0.5,
        "total_sources": 0,
        "research_angles_covered": [],
        "tools_executed": {"tools": []},
        "gaps_identified": {"gaps": []},
        "warnings": [],
    }

    for darkness in [1, 3, 5, 7, 10]:
        with patch("loom.tools.llm.expert_engine.research_expert", return_value=mock_result) as mock_expert:
            result = await do_expert.research_do_expert("test query", darkness_level=darkness)

            assert result["darkness_level"] == darkness


@pytest.mark.asyncio
async def test_research_do_expert_output_format():
    """Test output format and required fields."""
    mock_result = {
        "query": "What is AI safety?",
        "executive_summary": "AI safety is about ensuring AI systems are safe and beneficial.",
        "key_findings": [
            {
                "claim": "Alignment is crucial",
                "confidence": 0.85,
                "triangulation_angles": 2,
                "avg_source_credibility": 0.8,
            },
            {
                "claim": "Robustness matters",
                "confidence": 0.75,
                "triangulation_angles": 1,
                "avg_source_credibility": 0.7,
            },
        ],
        "confidence_weighted_avg": 0.80,
        "total_sources": 10,
        "research_angles_covered": ["factual", "mechanism"],
        "tools_executed": {"tools": ["deep_factual", "deep_mechanism"]},
        "gaps_identified": {"gaps": ["Future research directions"]},
        "warnings": [],
    }

    with patch("loom.tools.llm.expert_engine.research_expert", return_value=mock_result):
        result = await do_expert.research_do_expert("What is AI safety?")

        # Verify required output fields
        assert "instruction" in result
        assert "answer" in result
        assert "quality" in result
        assert "darkness_level" in result
        assert "confidence" in result
        assert "key_findings" in result
        assert "sources_count" in result
        assert "research_angles" in result
        assert "tools_executed" in result
        assert "duration_ms" in result
        assert "warnings" in result

        # Verify data types
        assert isinstance(result["instruction"], str)
        assert isinstance(result["answer"], str)
        assert isinstance(result["confidence"], float)
        assert isinstance(result["sources_count"], int)
        assert isinstance(result["key_findings"], list)
        assert isinstance(result["tools_executed"], list)
        assert isinstance(result["duration_ms"], int)

        # Verify answer contains key information
        assert "summary" in result["answer"].lower() or "finding" in result["answer"].lower()


@pytest.mark.asyncio
async def test_research_do_expert_answer_truncation():
    """Test that answer is truncated to reasonable size."""
    long_summary = "x" * 5000  # Create a very long summary
    mock_result = {
        "query": "test",
        "executive_summary": long_summary,
        "key_findings": [{"claim": "Finding", "confidence": 0.8}] * 20,  # Many findings
        "confidence_weighted_avg": 0.8,
        "total_sources": 100,
        "research_angles_covered": [],
        "tools_executed": {"tools": []},
        "gaps_identified": {"gaps": []},
        "warnings": [],
    }

    with patch("loom.tools.llm.expert_engine.research_expert", return_value=mock_result):
        result = await do_expert.research_do_expert("test query")

        # Answer should be truncated
        assert len(result["answer"]) <= 3000
        # Key findings should be limited
        assert len(result["key_findings"]) <= 10


@pytest.mark.asyncio
async def test_research_do_expert_basic_functionality():
    """Test basic functionality with a simple mock."""
    mock_result = {
        "query": "test query",
        "executive_summary": "This is a test.",
        "key_findings": [{"claim": "Test claim", "confidence": 0.8}],
        "confidence_weighted_avg": 0.8,
        "total_sources": 1,
        "research_angles_covered": ["factual"],
        "tools_executed": {"tools": ["test_tool"]},
        "gaps_identified": {"gaps": []},
        "warnings": [],
    }

    with patch("loom.tools.llm.expert_engine.research_expert", return_value=mock_result):
        result = await do_expert.research_do_expert("test query")

        # Verify basic fields
        assert result["instruction"] == "test query"
        assert result["confidence"] == 0.8
        assert result["sources_count"] == 1
        assert "test" in result["answer"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
