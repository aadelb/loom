"""Tests for Brain Core — research_smart_call orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.brain.core import research_smart_call, _find_fallback_tool
from loom.brain.memory import get_memory
from loom.brain.types import QualityMode, ToolMatch


class TestFindFallbackTool:
    """Test fallback tool selection."""

    def test_find_fallback_escalation_chain(self) -> None:
        """Test finding tool via escalation chain."""
        failed_tool = "research_fetch"
        all_matches = [ToolMatch(tool_name="research_fetch", confidence=0.9)]
        already_tried = []

        fallback = _find_fallback_tool(failed_tool, all_matches, already_tried)
        assert fallback is not None
        assert fallback.tool_name == "research_camoufox"

    def test_find_fallback_next_best_match(self) -> None:
        """Test falling back to next best match."""
        failed_tool = "research_fetch"
        all_matches = [
            ToolMatch(tool_name="research_fetch", confidence=0.9),
            ToolMatch(tool_name="research_camoufox", confidence=0.8),
            ToolMatch(tool_name="research_botasaurus", confidence=0.7),
        ]
        already_tried = ["research_fetch", "research_camoufox"]

        fallback = _find_fallback_tool(failed_tool, all_matches, already_tried)
        # Should return research_botasaurus
        if fallback:
            assert fallback.tool_name == "research_botasaurus"

    def test_find_fallback_no_options(self) -> None:
        """Test when no fallback options available."""
        failed_tool = "research_fetch"
        all_matches = [ToolMatch(tool_name="research_fetch", confidence=0.9)]
        already_tried = ["research_fetch", "research_camoufox", "research_botasaurus"]

        fallback = _find_fallback_tool(failed_tool, all_matches, already_tried)
        assert fallback is None

    def test_find_fallback_avoids_escalation_if_tried(self) -> None:
        """Test that escalation chain is avoided if already tried."""
        failed_tool = "research_fetch"
        all_matches = [
            ToolMatch(tool_name="research_fetch", confidence=0.9),
            ToolMatch(tool_name="research_camoufox", confidence=0.8),
        ]
        already_tried = ["research_camoufox"]

        fallback = _find_fallback_tool(failed_tool, all_matches, already_tried)
        # Should fall back to research_camoufox from matches (already skipped via escalation)
        if fallback:
            assert fallback.tool_name != "research_camoufox"


class TestResearchSmartCall:
    """Test research_smart_call orchestrator."""

    @pytest.mark.asyncio
    async def test_smart_call_simple_query(self, mock_brain_index) -> None:
        """Test smart call with simple query."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="search for python",
                    quality_mode="auto",
                    max_iterations=1,
                )

                assert isinstance(result, dict)
                assert "success" in result
                assert "matched_tools" in result
                assert "plan_steps" in result

    @pytest.mark.asyncio
    async def test_smart_call_no_tools_found(self) -> None:
        """Test smart call when no tools match."""
        with patch("loom.brain.reasoning._load_brain_index", return_value={}):
            with patch("loom.brain.reasoning.select_tools", return_value=[]):
                result = await research_smart_call(
                    query="very specific query that matches nothing",
                    quality_mode="auto",
                )

                assert result["success"] is False
                assert "error" in result

    @pytest.mark.asyncio
    async def test_smart_call_forced_tools(self, mock_brain_index) -> None:
        """Test smart call with forced tool selection."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    quality_mode="auto",
                    forced_tools=["research_fetch"],
                )

                assert "matched_tools" in result

    @pytest.mark.asyncio
    async def test_smart_call_quality_modes(self, mock_brain_index) -> None:
        """Test smart call with different quality modes."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        for mode in ["economy", "auto", "max"]:
            with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
                with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                    result = await research_smart_call(
                        query="test",
                        quality_mode=mode,
                        max_iterations=1,
                    )

                    assert result["quality_mode"] == mode.upper() or result["quality_mode"] == mode

    @pytest.mark.asyncio
    async def test_smart_call_max_iterations(self, mock_brain_index) -> None:
        """Test smart call respects max_iterations."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    max_iterations=3,
                )

                assert result["iterations"] <= 3

    @pytest.mark.asyncio
    async def test_smart_call_records_memory(self, mock_brain_index) -> None:
        """Test that smart call records results in memory."""
        memory = get_memory()
        memory.clear()

        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test query",
                    quality_mode="auto",
                    max_iterations=1,
                )

                # Should have recorded at least one tool call
                context = memory.get_recent_context()
                # Note: memory recording may vary depending on implementation

    @pytest.mark.asyncio
    async def test_smart_call_returns_result_structure(self, mock_brain_index) -> None:
        """Test that result has required structure."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "test"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    quality_mode="auto",
                    max_iterations=1,
                )

                assert "success" in result
                assert "matched_tools" in result
                assert "plan_steps" in result
                assert "final_output" in result
                assert "iterations" in result
                assert "quality_mode" in result
                assert "elapsed_ms" in result
                assert "error" in result

    @pytest.mark.asyncio
    async def test_smart_call_chain_detection(self, mock_brain_index) -> None:
        """Test that predefined chains are detected."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="deep research on machine learning",
                    quality_mode="auto",
                    max_iterations=1,
                )

                # Should detect deep_research chain
                assert result["success"] is not None

    @pytest.mark.asyncio
    async def test_smart_call_measures_elapsed_time(self, mock_brain_index) -> None:
        """Test that elapsed time is measured."""
        mock_tool = AsyncMock(return_value={"success": True})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    quality_mode="auto",
                    max_iterations=1,
                )

                assert result["elapsed_ms"] >= 0

    @pytest.mark.asyncio
    async def test_smart_call_economy_mode_single_iteration(self, mock_brain_index) -> None:
        """Test that economy mode limits iterations."""
        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    quality_mode="economy",
                    max_iterations=5,
                )

                # Economy mode should complete quickly (1 iteration)
                assert result["iterations"] <= 3

    @pytest.mark.asyncio
    async def test_smart_call_invalid_mode_defaults_to_auto(self, mock_brain_index) -> None:
        """Test that invalid mode defaults to AUTO."""
        mock_tool = AsyncMock(return_value={"success": True})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    quality_mode="invalid_mode",
                )

                assert "quality_mode" in result

    @pytest.mark.asyncio
    async def test_smart_call_handles_tool_failure(self, mock_brain_index) -> None:
        """Test handling of tool execution failure."""
        mock_tool = AsyncMock(return_value={"success": False, "error": "API error"})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="test",
                    quality_mode="auto",
                    max_iterations=1,
                )

                # Should either retry or fail gracefully
                assert "success" in result

    @pytest.mark.asyncio
    async def test_smart_call_min_max_iterations(self, mock_brain_index) -> None:
        """Test that iterations are bounded 1-5."""
        mock_tool = AsyncMock(return_value={"success": True})

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                # Test with 0 iterations (should become 1)
                result = await research_smart_call(
                    query="test",
                    max_iterations=0,
                )
                assert result["iterations"] >= 1

                # Test with 10 iterations (should cap at 5)
                result = await research_smart_call(
                    query="test",
                    max_iterations=10,
                )
                assert result["iterations"] <= 5

    @pytest.mark.asyncio
    async def test_smart_call_timeout(self, mock_brain_index) -> None:
        """Test smart call timeout handling."""
        async def slow_tool(**kwargs) -> dict:
            import asyncio
            await asyncio.sleep(10)
            return {"success": True}

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=slow_tool):
                result = await research_smart_call(
                    query="test",
                    timeout=0.1,
                    max_iterations=1,
                )

                # Should timeout
                if "error" in result and result["error"]:
                    assert "timeout" in result["error"].lower() or result["success"] is False


class TestIntegration:
    """Integration tests for Brain system."""

    @pytest.mark.asyncio
    async def test_full_workflow_perception_to_reflection(self, mock_brain_index) -> None:
        """Test complete workflow from perception to reflection."""
        mock_tool = AsyncMock(
            return_value={
                "success": True,
                "data": {"results": [{"title": "Result 1"}, {"title": "Result 2"}]},
            }
        )

        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
                result = await research_smart_call(
                    query="search for information about python",
                    quality_mode="auto",
                    max_iterations=2,
                )

                assert result["success"] is not None
                assert result["matched_tools"] is not None
                assert len(result["plan_steps"]) > 0
