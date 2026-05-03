"""Tests for optimization path planner."""
import json
import tempfile
from pathlib import Path

import pytest

from loom.optimization_path import OptimizationPathPlanner



pytestmark = pytest.mark.asyncio
class TestOptimizationPathPlanner:
    async def test_plan_with_defaults(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test query", "gpt-4")
        assert "path" in result
        assert "total_steps" in result
        assert "success_probability" in result
        assert result["total_steps"] > 0
        assert result["total_steps"] <= 5

    async def test_plan_returns_valid_path(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test", "claude", current_hcs=0.0, target_hcs=8.0)
        for step in result["path"]:
            assert "step" in step
            assert "strategy" in step
            assert "expected_hcs_before" in step
            assert "expected_hcs_after" in step
            assert "confidence" in step
            assert "estimated_cost_usd" in step

    async def test_hcs_increases_along_path(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test", "gpt-4")
        prev_hcs = 0.0
        for step in result["path"]:
            assert step["expected_hcs_after"] >= step["expected_hcs_before"]
            prev_hcs = step["expected_hcs_after"]

    async def test_cost_estimation(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test", "gpt-4")
        cost = planner.estimate_cost(result["path"])
        assert cost["total_cost_usd"] >= 0
        assert cost["steps"] == len(result["path"])

    async def test_plan_with_high_current_hcs(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test", "gpt-4", current_hcs=9.0, target_hcs=8.0)
        assert result["total_steps"] == 0 or result["final_expected_hcs"] >= 8.0

    async def test_plan_with_empirical_data(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for i in range(20):
                entry = {
                    "model": "test-model",
                    "strategy": "ethical_anchor",
                    "success": i % 2 == 0,
                    "hcs": 5.0 + (i % 5),
                }
                f.write(json.dumps(entry) + "\n")
            f.flush()
            planner = OptimizationPathPlanner(tracker_path=f.name)
            result = planner.plan("test", "test-model")
            assert result["data_source"] in ("empirical", "default_rankings")

    async def test_plan_data_source_default(self):
        planner = OptimizationPathPlanner(tracker_path="/nonexistent/path.jsonl")
        result = planner.plan("test", "gpt-4")
        assert result["data_source"] == "default_rankings"

    async def test_success_probability_range(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test", "gpt-4")
        assert 0.0 <= result["success_probability"] <= 1.0

    async def test_reasoning_not_empty(self):
        planner = OptimizationPathPlanner()
        result = planner.plan("test", "gpt-4")
        assert len(result["reasoning"]) > 0
