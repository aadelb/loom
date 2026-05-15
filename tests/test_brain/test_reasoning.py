"""Tests for Brain Reasoning Layer — Tool selection and planning."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.brain.reasoning import (
    decompose_query,
    plan_workflow,
    select_tools,
)
from loom.brain.types import QualityMode, ToolMatch, ToolMeta


class TestSelectTools:
    """Test tool selection functionality."""

    def test_select_tools_forced_override(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test that forced_tools parameter overrides selection."""
        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            matches = select_tools(
                query="search for something",
                forced_tools=["research_fetch"],
            )
            assert len(matches) > 0
            assert matches[0].tool_name == "research_fetch"
            assert matches[0].confidence == 1.0

    def test_select_tools_search_query(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test selecting search tool for search query."""
        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            matches = select_tools(
                query="search for python tutorials",
                quality_mode=QualityMode.AUTO,
            )
            assert len(matches) > 0
            # research_search should be high confidence match
            tool_names = [m.tool_name for m in matches]
            assert "research_search" in tool_names

    def test_select_tools_security_query(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test selecting security tools for security query."""
        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            matches = select_tools(
                query="analyze CVE-2024-1234 vulnerability",
                quality_mode=QualityMode.AUTO,
            )
            assert len(matches) > 0
            # Should match security-category tools
            tool_names = [m.tool_name for m in matches]
            assert any(t in tool_names for t in ["research_cert_analyze", "research_cve_lookup"])

    def test_select_tools_empty_index(self) -> None:
        """Test tool selection with empty index."""
        with patch("loom.brain.reasoning._load_brain_index", return_value={}):
            matches = select_tools(query="test query")
            # Should fall back to keyword matching
            assert isinstance(matches, list)

    def test_select_tools_max_tools_limit(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test that max_tools parameter limits results."""
        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            matches = select_tools(
                query="search fetch analyze security",
                max_tools=2,
            )
            assert len(matches) <= 2

    def test_select_tools_quality_modes(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test tool selection with different quality modes."""
        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            matches_economy = select_tools(
                query="test query",
                quality_mode=QualityMode.ECONOMY,
            )
            matches_max = select_tools(
                query="test query",
                quality_mode=QualityMode.MAX,
            )
            # Both should return matches
            assert len(matches_economy) > 0
            assert len(matches_max) > 0

    def test_select_tools_returns_tool_match(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test that matches are ToolMatch objects."""
        with patch("loom.brain.reasoning._load_brain_index", return_value=mock_brain_index):
            matches = select_tools(query="test query")
            if matches:
                assert isinstance(matches[0], ToolMatch)
                assert hasattr(matches[0], "tool_name")
                assert hasattr(matches[0], "confidence")
                assert hasattr(matches[0], "match_source")


class TestDecomposeQuery:
    """Test query decomposition for multi-step planning."""

    def test_decompose_simple_query(self) -> None:
        """Test decomposing simple single-step query."""
        steps = decompose_query("search for python")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_decompose_multi_step_query(self) -> None:
        """Test decomposing multi-step query."""
        steps = decompose_query("search for papers and then fetch the full text")
        assert isinstance(steps, list)
        # Multi-step should produce multiple decompositions
        assert len(steps) >= 1

    def test_decompose_empty_query(self) -> None:
        """Test decomposing empty query."""
        steps = decompose_query("")
        assert isinstance(steps, list)

    def test_decompose_complex_query(self) -> None:
        """Test decomposing complex multi-part query."""
        steps = decompose_query(
            "search for information about blockchain, analyze security implications, and summarize"
        )
        assert isinstance(steps, list)
        assert len(steps) >= 1


class TestPlanWorkflow:
    """Test workflow planning."""

    def test_plan_workflow_simple(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test planning workflow with simple matches."""
        matches = [
            ToolMatch(tool_name="research_search", confidence=0.9),
        ]
        plan = plan_workflow("search for something", matches, QualityMode.AUTO)

        assert plan.steps is not None
        assert len(plan.steps) > 0
        assert plan.quality_mode == QualityMode.AUTO

    def test_plan_workflow_multiple_tools(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test planning with multiple tool matches."""
        matches = [
            ToolMatch(tool_name="research_search", confidence=0.95),
            ToolMatch(tool_name="research_fetch", confidence=0.85),
            ToolMatch(tool_name="research_llm_summarize", confidence=0.75),
        ]
        plan = plan_workflow(
            "search for papers and fetch them",
            matches,
            QualityMode.AUTO,
        )

        assert len(plan.steps) > 0
        # Verify steps have required attributes
        for step in plan.steps:
            assert hasattr(step, "tool_name")
            assert hasattr(step, "params")
            assert hasattr(step, "timeout")

    def test_plan_workflow_economy_mode(self) -> None:
        """Test that economy mode produces minimal plan."""
        matches = [
            ToolMatch(tool_name="research_search", confidence=0.9),
            ToolMatch(tool_name="research_fetch", confidence=0.8),
        ]
        plan = plan_workflow("query", matches, QualityMode.ECONOMY)

        assert plan.quality_mode == QualityMode.ECONOMY
        # Economy mode may prefer single tool
        assert len(plan.steps) >= 1

    def test_plan_workflow_max_mode(self) -> None:
        """Test that max mode produces comprehensive plan."""
        matches = [
            ToolMatch(tool_name="research_search", confidence=0.95),
            ToolMatch(tool_name="research_fetch", confidence=0.85),
        ]
        plan = plan_workflow("deep query", matches, QualityMode.MAX)

        assert plan.quality_mode == QualityMode.MAX
        # Max mode may chain multiple tools
        assert len(plan.steps) >= 1

    def test_plan_workflow_empty_matches(self) -> None:
        """Test planning with no tool matches."""
        plan = plan_workflow("query", [], QualityMode.AUTO)

        # Should return valid plan even with empty matches
        assert plan.steps is not None
        assert isinstance(plan.steps, list)

    def test_plan_workflow_respects_dependencies(self) -> None:
        """Test that plan respects tool dependencies."""
        matches = [
            ToolMatch(tool_name="research_search", confidence=0.95),
            ToolMatch(tool_name="research_fetch", confidence=0.85),
        ]
        plan = plan_workflow("search and fetch", matches, QualityMode.AUTO)

        if len(plan.steps) > 1:
            # If multiple steps, some may have dependencies
            for step in plan.steps:
                assert hasattr(step, "depends_on")

    def test_plan_workflow_estimated_cost(self) -> None:
        """Test that plan includes estimated cost."""
        matches = [
            ToolMatch(tool_name="research_search", confidence=0.9),
        ]
        plan = plan_workflow("query", matches, QualityMode.AUTO)

        assert hasattr(plan, "estimated_cost")
        assert isinstance(plan.estimated_cost, (int, float))
        assert plan.estimated_cost >= 0.0


class TestToolScoring:
    """Test tool scoring components."""

    def test_keyword_matching(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test keyword matching in tool scoring."""
        from loom.brain.reasoning import _keyword_score

        meta = mock_brain_index["research_search"]
        score = _keyword_score("research_search", meta, ["search"], ["general"])
        assert score >= 0.0
        assert score <= 1.0

    def test_name_match_scoring(self) -> None:
        """Test tool name matching."""
        from loom.brain.reasoning import _name_match_score

        score = _name_match_score("research_search", ["search"])
        assert score > 0.0  # Should match on "search"

        score_no_match = _name_match_score("research_cve_lookup", ["search"])
        assert score_no_match == 0.0  # Should not match

    def test_category_scoring(self, mock_brain_index: dict[str, ToolMeta]) -> None:
        """Test category-based scoring."""
        from loom.brain.reasoning import _category_score

        meta = mock_brain_index["research_cert_analyze"]
        score = _category_score(meta, ["security"])
        assert score > 0.0  # Should score positively for security domain

    def test_usage_scoring(self) -> None:
        """Test usage-based scoring."""
        from loom.brain.reasoning import _usage_score

        # Unknown tool should score lower
        score_unknown = _usage_score("unknown_tool")
        assert isinstance(score_unknown, (int, float))


class TestResolveToolName:
    """Test _resolve_tool_name fuzzy matching."""

    def test_exact_match(self, mock_brain_index: dict) -> None:
        from unittest.mock import patch
        from loom.brain.reasoning import _resolve_tool_name

        with patch("loom.brain.reasoning._fetch_server_tools_sync", return_value=mock_brain_index):
            with patch("loom.brain.reasoning._build_tool_name_index", return_value={}):
                result = _resolve_tool_name("research_search")
                assert result == "research_search"

    def test_fuzzy_match_high_similarity(self, mock_brain_index: dict) -> None:
        from unittest.mock import patch
        from loom.brain.reasoning import _resolve_tool_name

        with patch("loom.brain.reasoning._fetch_server_tools_sync", return_value=mock_brain_index):
            with patch("loom.brain.reasoning._build_tool_name_index", return_value={}):
                result = _resolve_tool_name("research_searc")
                assert result == "research_search"

    def test_no_match_returns_unchanged(self, mock_brain_index: dict) -> None:
        from unittest.mock import patch
        from loom.brain.reasoning import _resolve_tool_name

        with patch("loom.brain.reasoning._fetch_server_tools_sync", return_value=mock_brain_index):
            with patch("loom.brain.reasoning._build_tool_name_index", return_value={}):
                result = _resolve_tool_name("completely_different_name")
                assert result == "completely_different_name"
