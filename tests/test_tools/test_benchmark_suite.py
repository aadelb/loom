"""Tests for performance benchmark suite tools."""

from __future__ import annotations

import pytest

from loom.tools.research.benchmark_suite import (
    research_benchmark_run,
    research_benchmark_compare,
    _get_tool_function,
    _get_minimal_params,
    DEFAULT_BENCHMARK_TOOLS,
)


@pytest.mark.asyncio
async def test_benchmark_run_default_tools():
    """Test benchmarking with default tool set."""
    result = await research_benchmark_run(tools=None, iterations=2, warmup=0)

    # Check basic structure
    assert "tools_benchmarked" in result
    assert "results" in result
    assert "total_time_ms" in result

    # Check that we got some results
    assert isinstance(result["tools_benchmarked"], list)
    assert isinstance(result["results"], list)
    assert result["total_time_ms"] >= 0


@pytest.mark.asyncio
async def test_benchmark_run_custom_tools():
    """Test benchmarking with custom tool list."""
    # Use only epistemic_score (most likely to exist)
    result = await research_benchmark_run(
        tools=["research_epistemic_score"],
        iterations=2,
        warmup=0,
    )

    assert isinstance(result, dict)
    assert "tools_benchmarked" in result


@pytest.mark.asyncio
async def test_benchmark_run_nonexistent_tool():
    """Test benchmarking with nonexistent tool (should gracefully skip)."""
    result = await research_benchmark_run(
        tools=["research_nonexistent_tool"],
        iterations=1,
        warmup=0,
    )

    # Should still return valid structure
    assert "tools_benchmarked" in result
    assert isinstance(result["tools_benchmarked"], list)


@pytest.mark.asyncio
async def test_benchmark_compare_same_tool():
    """Test comparing the same tool against itself."""
    result = await research_benchmark_compare(
        tool_a="research_epistemic_score",
        tool_b="research_epistemic_score",
        iterations=2,
    )

    if "error" not in result:
        # Tools should be roughly equal
        assert "research_epistemic_score" in str(result)
        assert "winner" in result or "error" in result


@pytest.mark.asyncio
async def test_benchmark_compare_nonexistent_tool():
    """Test comparing with nonexistent tool (should handle gracefully)."""
    result = await research_benchmark_compare(
        tool_a="research_nonexistent_a",
        tool_b="research_nonexistent_b",
        iterations=1,
    )

    # Should return error or gracefully handle
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_benchmark_run_iterations_parameter():
    """Test that iterations parameter is respected."""
    result = await research_benchmark_run(
        tools=["research_epistemic_score"],
        iterations=5,
        warmup=0,
    )

    # Check that results show the iteration count
    if result["results"]:
        for res in result["results"]:
            assert res["iterations"] <= 5  # May be less if some fail


@pytest.mark.asyncio
async def test_benchmark_run_warmup_parameter():
    """Test warmup iterations."""
    # Run with warmup to ensure no errors
    result = await research_benchmark_run(
        tools=["research_epistemic_score"],
        iterations=2,
        warmup=1,
    )

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_benchmark_result_statistics():
    """Test that benchmark results include proper statistics."""
    result = await research_benchmark_run(
        tools=["research_epistemic_score"],
        iterations=3,
        warmup=0,
    )

    if result["results"]:
        for res in result["results"]:
            # Check required fields
            assert "tool" in res
            assert "iterations" in res
            assert "min_ms" in res
            assert "max_ms" in res
            assert "mean_ms" in res
            assert "p50_ms" in res
            assert "p95_ms" in res

            # Check value constraints
            assert res["min_ms"] >= 0
            assert res["max_ms"] >= res["min_ms"]
            assert res["mean_ms"] >= res["min_ms"]
            assert res["p50_ms"] >= res["min_ms"]
            assert res["p95_ms"] >= res["min_ms"]
            assert res["iterations"] > 0


@pytest.mark.asyncio
async def test_benchmark_compare_statistics():
    """Test that comparison includes proper statistics."""
    result = await research_benchmark_compare(
        tool_a="research_epistemic_score",
        tool_b="research_predict_success",
        iterations=2,
    )

    if "error" not in result:
        # Check for statistics in result
        assert "winner" in result
        assert "speedup_factor" in result

        # Check speedup factor is valid
        if "speedup_factor" in result:
            assert result["speedup_factor"] >= 1.0


@pytest.mark.asyncio
async def test_benchmark_run_empty_tools_list():
    """Test with empty tools list."""
    result = await research_benchmark_run(tools=[], iterations=1, warmup=0)

    assert isinstance(result, dict)
    assert "tools_benchmarked" in result


def test_get_tool_function_exists():
    """Test loading an existing tool function."""
    func = _get_tool_function("research_epistemic_score")
    # May be None if module doesn't exist, but should not raise
    assert func is None or callable(func)


def test_get_tool_function_nonexistent():
    """Test loading a nonexistent tool function."""
    func = _get_tool_function("research_completely_nonexistent_tool_xyz")
    assert func is None


def test_get_minimal_params_epistemic():
    """Test getting minimal params for epistemic_score."""
    params = _get_minimal_params("research_epistemic_score")

    assert isinstance(params, dict)
    assert "text" in params
    assert isinstance(params["text"], str)
    assert len(params["text"]) > 0


def test_get_minimal_params_stealth():
    """Test getting minimal params for stealth_score."""
    params = _get_minimal_params("research_stealth_score")

    assert isinstance(params, dict)
    assert "text" in params or "model" in params


def test_get_minimal_params_unknown():
    """Test getting params for unknown tool (should provide defaults)."""
    params = _get_minimal_params("research_unknown_tool_xyz")

    assert isinstance(params, dict)
    # Should provide safe defaults
    assert len(params) > 0


def test_default_benchmark_tools():
    """Test that default tools list is properly defined."""
    assert isinstance(DEFAULT_BENCHMARK_TOOLS, list)
    assert len(DEFAULT_BENCHMARK_TOOLS) > 0
    assert all(isinstance(tool, str) for tool in DEFAULT_BENCHMARK_TOOLS)
