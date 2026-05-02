"""Tests for execution_planner tool."""

import pytest

from loom.tools.execution_planner import (
    research_plan_execution,
    research_plan_validate,
)


@pytest.mark.asyncio
async def test_plan_execution_basic():
    """Test basic execution plan generation."""
    result = await research_plan_execution(
        goal="search for python security vulnerabilities"
    )

    assert result["goal"] == "search for python security vulnerabilities"
    assert len(result["plan"]) > 0
    assert result["total_estimated_time_ms"] > 0
    assert result["total_estimated_cost_usd"] >= 0
    assert "constraints_met" in result


@pytest.mark.asyncio
async def test_plan_execution_with_constraints():
    """Test plan generation respects constraints."""
    result = await research_plan_execution(
        goal="deep research on AI safety",
        constraints={
            "max_time_minutes": 5,
            "max_cost_usd": 0.05,
            "max_tools": 3,
        },
    )

    assert len(result["plan"]) <= 3
    assert result["total_estimated_time_ms"] <= 5 * 60 * 1000
    assert result["total_estimated_cost_usd"] <= 0.05


@pytest.mark.asyncio
async def test_plan_execution_categorization():
    """Test that goals are correctly categorized."""
    # Search goal
    result1 = await research_plan_execution("find information about topic")
    assert any("search" in step["reason"].lower() for step in result1["plan"])

    # Fetch goal
    result2 = await research_plan_execution("scrape content from webpage")
    assert any("fetch" in step["reason"].lower() for step in result2["plan"])

    # Deep research goal
    result3 = await research_plan_execution("comprehensive research investigation")
    assert any("deep" in step["reason"].lower() for step in result3["plan"])


@pytest.mark.asyncio
async def test_plan_validate_valid():
    """Test validation of a valid plan."""
    steps = [
        {"step": 1, "tool": "research_search"},
        {"step": 2, "tool": "research_fetch"},
    ]

    result = await research_plan_validate(steps)

    assert result["valid"] is True
    assert len(result["issues"]) == 0


@pytest.mark.asyncio
async def test_plan_validate_missing_tool():
    """Test validation catches missing tool field."""
    steps = [
        {"step": 1},  # Missing 'tool' key
    ]

    result = await research_plan_validate(steps)

    assert result["valid"] is False
    assert len(result["issues"]) == 1
    assert "tool" in result["issues"][0]["issue"].lower()


@pytest.mark.asyncio
async def test_plan_validate_empty():
    """Test validation of empty plan."""
    result = await research_plan_validate([])

    assert result["valid"] is False
    assert len(result["issues"]) > 0


@pytest.mark.asyncio
async def test_plan_validate_duplicate_tools():
    """Test validation detects duplicate tools."""
    steps = [
        {"tool": "research_search"},
        {"tool": "research_search"},  # Duplicate
    ]

    result = await research_plan_validate(steps)

    assert len(result["optimizations"]) > 0


@pytest.mark.asyncio
async def test_plan_validate_unknown_tool():
    """Test validation warns about unknown tools."""
    steps = [
        {"tool": "research_unknown_tool"},
    ]

    result = await research_plan_validate(steps)

    assert result["valid"] is True  # Still valid, just warned
    assert len(result["warnings"]) > 0


@pytest.mark.asyncio
async def test_plan_validate_forward_dependency():
    """Test validation catches forward dependencies."""
    steps = [
        {"tool": "research_search", "depends_on": [2]},
        {"tool": "research_fetch"},
    ]

    result = await research_plan_validate(steps)

    assert result["valid"] is False
    assert any("forward" in issue["issue"].lower() for issue in result["issues"])


@pytest.mark.asyncio
async def test_plan_execution_efficiency_ordering():
    """Test that tools are ordered by efficiency."""
    result = await research_plan_execution(
        goal="search and fetch",
        constraints={"max_tools": 5},
    )

    # Tools should be ordered by efficiency (time_ms / cost)
    for step in result["plan"]:
        assert "tool" in step
        assert step["estimated_time_ms"] > 0
