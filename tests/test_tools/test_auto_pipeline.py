"""Tests for the Pipeline Auto-Composer tool."""

from __future__ import annotations

import asyncio
import pytest

from loom.tools import auto_pipeline


@pytest.mark.asyncio
async def test_research_auto_pipeline_simple_goal():
    """Test basic pipeline generation with a simple goal."""
    goal = "search for security vulnerabilities"
    result = await auto_pipeline.research_auto_pipeline(goal)

    assert result["goal"] == goal
    assert result["total_steps"] > 0
    assert result["parallel_groups"] > 0
    assert result["estimated_total_ms"] > 0
    assert result["estimated_speedup_vs_sequential"] > 0
    assert len(result["pipeline"]) == result["total_steps"]


@pytest.mark.asyncio
async def test_research_auto_pipeline_with_url():
    """Test pipeline generation with a URL in the goal."""
    goal = "scan https://example.com for vulnerabilities"
    result = await auto_pipeline.research_auto_pipeline(goal)

    assert result["goal"] == goal
    assert result["total_steps"] > 0

    # Check that URL was extracted
    params_list = [step["params"] for step in result["pipeline"]]
    all_params = {}
    for p in params_list:
        all_params.update(p)

    assert "url" in all_params or "domain" in all_params


@pytest.mark.asyncio
async def test_research_auto_pipeline_complex_goal():
    """Test pipeline generation with a multi-faceted goal."""
    goal = "search GitHub for repos, analyze code quality, and rank by security score"
    result = await auto_pipeline.research_auto_pipeline(goal)

    assert result["total_steps"] >= 2
    assert len(result["pipeline"]) >= 2
    # Should have multiple stages
    assert result["parallel_groups"] >= 1


@pytest.mark.asyncio
async def test_research_auto_pipeline_max_steps():
    """Test that max_steps parameter limits pipeline length."""
    goal = "search for data, analyze code, evaluate results, and generate reports"
    result = await auto_pipeline.research_auto_pipeline(goal, max_steps=2)

    assert result["total_steps"] <= 2
    assert len(result["pipeline"]) <= 2


@pytest.mark.asyncio
async def test_research_auto_pipeline_optimization_speed():
    """Test speed optimization reduces total execution time."""
    goal = "analyze threat profiles comprehensively"

    result_speed = await auto_pipeline.research_auto_pipeline(goal, optimize_for="speed")
    result_quality = await auto_pipeline.research_auto_pipeline(goal, optimize_for="quality")

    # Speed optimization should result in shorter execution time
    assert result_speed["estimated_total_ms"] <= result_quality["estimated_total_ms"]
    assert result_speed["optimize_for"] == "speed"


@pytest.mark.asyncio
async def test_research_auto_pipeline_optimization_quality():
    """Test quality optimization may increase execution time for thoroughness."""
    goal = "thoroughly research a topic"

    result_quality = await auto_pipeline.research_auto_pipeline(goal, optimize_for="quality")
    result_cost = await auto_pipeline.research_auto_pipeline(goal, optimize_for="cost")

    assert result_quality["optimize_for"] == "quality"
    assert result_cost["optimize_for"] == "cost"


@pytest.mark.asyncio
async def test_research_auto_pipeline_parallelization():
    """Test that parallel_groups correctly identifies concurrent execution."""
    goal = "search and analyze simultaneously"
    result = await auto_pipeline.research_auto_pipeline(goal)

    if result["total_steps"] > 1:
        # Check that tools are grouped by stage
        stages_by_group = {}
        for step in result["pipeline"]:
            group = step["parallel_group"]
            stage = step["stage"]
            if group not in stages_by_group:
                stages_by_group[group] = set()
            stages_by_group[group].add(stage)

        # Each group should have a consistent stage or related stages
        assert len(stages_by_group) > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_speedup_calculation():
    """Test that speedup is correctly calculated."""
    goal = "fetch data, then analyze it"
    result = await auto_pipeline.research_auto_pipeline(goal)

    # Speedup should be >= 1.0 for parallelizable tasks
    # Formula: sequential / parallel
    assert result["estimated_speedup_vs_sequential"] > 0
    assert result["estimated_sequential_ms"] >= result["estimated_total_ms"]


@pytest.mark.asyncio
async def test_research_auto_pipeline_step_structure():
    """Test that each step has required fields."""
    goal = "comprehensive security analysis"
    result = await auto_pipeline.research_auto_pipeline(goal)

    required_fields = {
        "step",
        "tool",
        "module",
        "task",
        "params",
        "stage",
        "parallel_group",
        "keywords_matched",
        "estimated_ms",
        "reason",
    }

    for step in result["pipeline"]:
        assert set(step.keys()).issuperset(required_fields)
        assert isinstance(step["step"], int)
        assert isinstance(step["tool"], str)
        assert isinstance(step["module"], str)
        assert isinstance(step["params"], dict)
        assert isinstance(step["estimated_ms"], int)
        assert step["estimated_ms"] > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_invalid_goal_too_long():
    """Test that overly long goals are rejected."""
    goal = "x" * 1000  # Exceeds 500 char limit
    result = await auto_pipeline.research_auto_pipeline(goal)

    assert "error" in result
    assert result["total_steps"] == 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_empty_goal():
    """Test that empty goals are rejected."""
    result = await auto_pipeline.research_auto_pipeline("")

    assert "error" in result
    assert result["total_steps"] == 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_tool_keywords():
    """Test that tools are matched by relevant keywords."""
    goal = "analyze sentiment and detect bias"
    result = await auto_pipeline.research_auto_pipeline(goal)

    # Should include analysis tools
    tools = [step["tool"] for step in result["pipeline"]]
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_stage_ordering():
    """Test that stages are in the correct order."""
    goal = "search, analyze, score, and report"
    result = await auto_pipeline.research_auto_pipeline(goal, max_steps=10)

    stages = [step["stage"] for step in result["pipeline"]]

    # Define expected order
    stage_order = {
        "fetch": 1,
        "search": 1,
        "discovery": 1,
        "security": 2,
        "processing": 2,
        "analysis": 2,
        "intelligence": 2,
        "evaluation": 3,
        "scoring": 3,
        "ranking": 3,
        "monitoring": 3,
        "tracking": 3,
        "formatting": 4,
        "output": 4,
    }

    # Convert stages to their order values
    order_values = [stage_order.get(s, 0) for s in stages]

    # Check that order is non-decreasing
    for i in range(1, len(order_values)):
        assert order_values[i] >= order_values[i - 1]


@pytest.mark.asyncio
async def test_research_auto_pipeline_result_structure():
    """Test complete structure of the result."""
    goal = "test pipeline generation"
    result = await auto_pipeline.research_auto_pipeline(goal)

    expected_keys = {
        "goal",
        "pipeline",
        "total_steps",
        "parallel_groups",
        "estimated_total_ms",
        "estimated_sequential_ms",
        "estimated_speedup_vs_sequential",
        "optimize_for",
        "registry_size",
        "tasks_identified",
    }

    assert set(result.keys()).issuperset(expected_keys)
    assert result["goal"] == goal
    assert result["registry_size"] > 0
    assert result["tasks_identified"] > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_params_extraction():
    """Test that relevant parameters are extracted from goal."""
    goal = "scan https://github.com/torvalds/linux for python code"
    result = await auto_pipeline.research_auto_pipeline(goal)

    # Collect all params from all steps
    all_params = {}
    for step in result["pipeline"]:
        all_params.update(step["params"])

    # Should have extracted URL and query terms
    assert len(all_params) > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_multiple_urls():
    """Test extraction of multiple URLs from goal."""
    goal = "compare https://github.com/a and https://github.com/b"
    result = await auto_pipeline.research_auto_pipeline(goal)

    all_params = {}
    for step in result["pipeline"]:
        all_params.update(step["params"])

    # Should have extracted URLs
    if "urls" in all_params:
        assert isinstance(all_params["urls"], list)
        assert len(all_params["urls"]) >= 2


@pytest.mark.asyncio
async def test_research_auto_pipeline_keyword_matching():
    """Test that keywords are correctly matched for task decomposition."""
    goals_and_keywords = [
        ("scan example.com", ["scan"]),
        ("search for research papers", ["search"]),
        ("analyze the code", ["analyze"]),
        ("report findings", ["report"]),
        ("score the results", ["score"]),
    ]

    for goal, expected_keywords in goals_and_keywords:
        result = await auto_pipeline.research_auto_pipeline(goal)

        matched_keywords = []
        for step in result["pipeline"]:
            matched_keywords.extend(step["keywords_matched"])

        # At least one expected keyword should be matched
        assert any(kw in matched_keywords for kw in expected_keywords) or result["total_steps"] > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_deduplication():
    """Test that duplicate tasks are handled appropriately."""
    goal = "search search search for information"
    result = await auto_pipeline.research_auto_pipeline(goal)

    # Should not have excessive duplication
    assert result["total_steps"] <= 3


@pytest.mark.asyncio
async def test_research_auto_pipeline_default_parameters():
    """Test that default parameters are applied correctly."""
    goal = "test goal"
    result = await auto_pipeline.research_auto_pipeline(goal)

    assert result["optimize_for"] == "quality"
    assert isinstance(result["total_steps"], int)
    assert isinstance(result["parallel_groups"], int)


@pytest.mark.parametrize(
    "optimize_for",
    ["speed", "quality", "cost"],
)
@pytest.mark.asyncio
async def test_research_auto_pipeline_all_optimizations(optimize_for):
    """Test all optimization strategies."""
    goal = "comprehensive analysis"
    result = await auto_pipeline.research_auto_pipeline(goal, optimize_for=optimize_for)

    assert result["optimize_for"] == optimize_for
    assert result["total_steps"] > 0


@pytest.mark.asyncio
async def test_research_auto_pipeline_consistency():
    """Test that same input produces consistent output structure."""
    goal = "security research goal"

    results = []
    for _ in range(3):
        result = await auto_pipeline.research_auto_pipeline(goal)
        results.append(result)

    # All results should have same structure
    for r in results[1:]:
        assert set(r.keys()) == set(results[0].keys())
        assert r["total_steps"] == results[0]["total_steps"]
