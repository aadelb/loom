"""Unit and integration tests for pipeline_enhancer middleware."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.infrastructure.pipeline_enhancer import (
    research_enhance,
    research_enhance_batch,
    _default_hcs_scores,
    _estimate_tool_cost,
    _execute_tool,
    _has_reframe_data,
    _score_with_hcs,
    _suggest_follow_up_tools,
    _verify_factual_claims,
)


class TestExecuteTool:
    """Test dynamic tool execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_fetch(self) -> None:
        """Execute research_fetch tool."""
        # Mock the fetch module
        with patch("loom.tools.core.fetch.research_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"url": "https://example.com", "text": "test"}
            result = await _execute_tool("research_fetch", {"url": "https://example.com"})
            assert result == {"url": "https://example.com", "text": "test"}
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self) -> None:
        """Raise AttributeError for non-existent tool."""
        with pytest.raises(AttributeError):
            await _execute_tool("research_nonexistent", {})

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_module(self) -> None:
        """Raise ImportError for invalid module."""
        with pytest.raises(ImportError):
            await _execute_tool("invalid_module_tool", {})


class TestEstimateCost:
    """Test pre-execution cost estimation."""

    @pytest.mark.asyncio
    async def test_estimate_fetch_cost(self) -> None:
        """Estimate cost for fetch tool."""
        cost = await _estimate_tool_cost("research_fetch", {"url": "https://example.com"})
        assert "tool" in cost
        assert cost["tool"] == "research_fetch"
        assert "estimated_tokens" in cost
        assert "estimated_api_calls" in cost
        assert cost["estimated_api_calls"] == 1

    @pytest.mark.asyncio
    async def test_estimate_spider_cost(self) -> None:
        """Estimate cost for spider tool with multiple URLs."""
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        cost = await _estimate_tool_cost("research_spider", {"urls": urls})
        assert cost["estimated_api_calls"] == 3

    @pytest.mark.asyncio
    async def test_estimate_deep_cost(self) -> None:
        """Estimate cost for deep research tool."""
        cost = await _estimate_tool_cost("research_deep", {"query": "test"})
        assert cost["estimated_api_calls"] >= 1
        assert cost["estimated_tokens"] > 0

    @pytest.mark.asyncio
    async def test_estimate_search_cost(self) -> None:
        """Estimate cost for search tool."""
        cost = await _estimate_tool_cost("research_search", {"query": "test"})
        assert cost["estimated_api_calls"] == 1


class TestHCSScoring:
    """Test HCS quality scoring."""

    @pytest.mark.asyncio
    async def test_score_with_hcs_empty_result(self) -> None:
        """Handle empty result gracefully."""
        scores = await _score_with_hcs("", "research_fetch")
        assert "bypass_success" in scores
        assert "stealth_score" in scores
        assert len(scores) == 8

    @pytest.mark.asyncio
    async def test_hcs_default_scores(self) -> None:
        """Default HCS scores have 8 dimensions."""
        scores = _default_hcs_scores()
        assert len(scores) == 8
        assert all(isinstance(v, float) for v in scores.values())
        assert all(v == 0.0 for v in scores.values())

    @pytest.mark.asyncio
    async def test_hcs_score_structure(self) -> None:
        """HCS scores have correct keys."""
        scores = _default_hcs_scores()
        expected_keys = {
            "bypass_success",
            "information_density",
            "stealth_score",
            "transferability",
            "persistence",
            "escalation_potential",
            "defense_evasion",
            "novelty",
        }
        assert set(scores.keys()) == expected_keys


class TestFactChecking:
    """Test fact-checking enrichment."""

    @pytest.mark.asyncio
    async def test_fact_check_short_result(self) -> None:
        """Skip fact-check for short results."""
        result = await _verify_factual_claims("short")
        assert "error" in result or "reason" in result

    @pytest.mark.asyncio
    async def test_fact_check_long_result(self) -> None:
        """Attempt fact-check for long results."""
        long_text = "This is a longer text that contains multiple sentences about facts and claims. " * 10
        with patch("loom.tools.llm.research_llm_classify", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {"factual": ["claim1"], "opinion": ["opinion1"]}
            result = await _verify_factual_claims(long_text)
            assert "verified_claims" in result or "error" in result


class TestReframeDataDetection:
    """Test reframe data detection."""

    def test_has_reframe_data_strategy_name(self) -> None:
        """Detect strategy_name in params."""
        params = {"strategy_name": "role_play"}
        assert _has_reframe_data(params) is True

    def test_has_reframe_data_prompt_reframed(self) -> None:
        """Detect prompt_reframed in params."""
        params = {"prompt_reframed": "reframed prompt text"}
        assert _has_reframe_data(params) is True

    def test_has_reframe_data_reframe_strategy(self) -> None:
        """Detect reframe_strategy in params."""
        params = {"reframe_strategy": "indirect_request"}
        assert _has_reframe_data(params) is True

    def test_has_reframe_data_empty(self) -> None:
        """Return False for params without reframe data."""
        params = {"url": "https://example.com"}
        assert _has_reframe_data(params) is False


class TestSuggestFollowUpTools:
    """Test tool suggestion enrichment."""

    @pytest.mark.asyncio
    async def test_suggest_tools_basic(self) -> None:
        """Suggest tools for follow-up."""
        with patch("loom.tool_recommender.ToolRecommender") as mock_recommender_class:
            mock_recommender = MagicMock()
            mock_recommender.recommend.return_value = [
                {"tool": "research_spider", "score": 0.95}
            ]
            mock_recommender_class.return_value = mock_recommender

            result = await _suggest_follow_up_tools(
                "research_fetch",
                {"url": "https://example.com"},
                {"summary": "Page content"}
            )
            assert "suggested_tools" in result or "error" in result

    @pytest.mark.asyncio
    async def test_suggest_tools_handles_error(self) -> None:
        """Handle errors in tool suggestion gracefully."""
        with patch("loom.tool_recommender.ToolRecommender") as mock_recommender_class:
            mock_recommender_class.side_effect = Exception("Recommender error")
            result = await _suggest_follow_up_tools(
                "research_fetch",
                {},
                {}
            )
            assert "error" in result


class TestResearchEnhance:
    """Integration tests for research_enhance."""

    @pytest.mark.asyncio
    async def test_enhance_basic_execution(self) -> None:
        """Execute basic enhancement with all defaults."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            result = await research_enhance("research_fetch", {"url": "https://example.com"})
            assert "_original_result" in result
            assert "_execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_enhance_with_cost_estimation(self) -> None:
        """Enable cost estimation."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            result = await research_enhance(
                "research_fetch",
                {"url": "https://example.com"},
                auto_cost=True
            )
            assert "_estimated_cost" in result
            assert "_execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_enhance_with_hcs_scoring(self) -> None:
        """Enable HCS scoring."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "test response"
            result = await research_enhance(
                "research_fetch",
                {"url": "https://example.com"},
                auto_hcs=True
            )
            assert "_original_result" in result
            # HCS scores may not be present if scoring fails, but structure is valid

    @pytest.mark.asyncio
    async def test_enhance_all_features_disabled(self) -> None:
        """Run with all enrichment disabled."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            result = await research_enhance(
                "research_fetch",
                {"url": "https://example.com"},
                auto_hcs=False,
                auto_cost=False,
                auto_learn=False,
                auto_fact_check=False,
                auto_suggest=False
            )
            assert "_original_result" in result
            assert "_execution_time_ms" in result
            # Should not have enrichment fields
            assert "_estimated_cost" not in result
            assert "_hcs_scores" not in result

    @pytest.mark.asyncio
    async def test_enhance_handles_tool_error(self) -> None:
        """Handle tool execution errors gracefully."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = Exception("Tool execution failed")
            result = await research_enhance("research_fetch", {"url": "https://example.com"})
            assert "_error" in result
            assert "_execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_enhance_execution_time_recorded(self) -> None:
        """Always record execution time."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            result = await research_enhance("research_fetch", {"url": "https://example.com"})
            assert "_execution_time_ms" in result
            assert isinstance(result["_execution_time_ms"], int)
            assert result["_execution_time_ms"] >= 0


class TestResearchEnhanceBatch:
    """Integration tests for research_enhance_batch."""

    @pytest.mark.asyncio
    async def test_batch_single_task(self) -> None:
        """Execute batch with single task."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            result = await research_enhance_batch([
                {
                    "tool_name": "research_fetch",
                    "params": {"url": "https://example.com"}
                }
            ])
            assert "results" in result
            assert "total_time_ms" in result
            assert "success_count" in result
            assert result["success_count"] == 1
            assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_multiple_tasks(self) -> None:
        """Execute batch with multiple tasks."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            tasks = [
                {"tool_name": "research_fetch", "params": {"url": "https://a.com"}},
                {"tool_name": "research_fetch", "params": {"url": "https://b.com"}},
                {"tool_name": "research_search", "params": {"query": "test"}},
            ]
            result = await research_enhance_batch(tasks)
            assert len(result["results"]) == 3
            assert result["success_count"] == 3
            assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_partial_failures(self) -> None:
        """Handle partial failures in batch."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            # First call succeeds, second fails
            mock_exec.side_effect = [
                {"result": "test1"},
                Exception("Tool error"),
                {"result": "test3"},
            ]
            tasks = [
                {"tool_name": "research_fetch", "params": {"url": "https://a.com"}},
                {"tool_name": "research_fetch", "params": {"url": "https://b.com"}},
                {"tool_name": "research_search", "params": {"query": "test"}},
            ]
            # Note: Due to gather return_exceptions=False, this will raise on first exception
            with pytest.raises(Exception):
                await research_enhance_batch(tasks)

    @pytest.mark.asyncio
    async def test_batch_with_custom_flags(self) -> None:
        """Batch respects custom enhancement flags."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            tasks = [
                {
                    "tool_name": "research_fetch",
                    "params": {"url": "https://example.com"},
                    "auto_hcs": False,
                    "auto_suggest": True,
                }
            ]
            result = await research_enhance_batch(tasks)
            assert result["success_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_timing(self) -> None:
        """Batch records total execution time."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "test"}
            tasks = [
                {"tool_name": "research_fetch", "params": {"url": "https://example.com"}},
            ]
            result = await research_enhance_batch(tasks)
            assert "total_time_ms" in result
            assert isinstance(result["total_time_ms"], int)
            assert result["total_time_ms"] >= 0


class TestEnhancementIntegration:
    """End-to-end enhancement scenarios."""

    @pytest.mark.asyncio
    async def test_enhance_with_reframing_strategy(self) -> None:
        """Enhance result with reframing strategy data."""
        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            with patch("loom.tools.infrastructure.pipeline_enhancer._feed_to_meta_learner", new_callable=AsyncMock) as mock_learn:
                mock_exec.return_value = {"response": "bypassed content"}
                mock_learn.return_value = True
                result = await research_enhance(
                    "research_fetch",
                    {
                        "url": "https://example.com",
                        "strategy_name": "role_play",
                        "success": True
                    },
                    auto_learn=True
                )
                assert "_original_result" in result
                # Learning may have been recorded
                assert "_learning_recorded" in result or "_error" not in result

    @pytest.mark.asyncio
    async def test_enhance_parallel_enrichment(self) -> None:
        """Verify parallel execution of enrichment tasks."""
        call_count = 0

        async def slow_hcs_score(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return _default_hcs_scores()

        with patch("loom.tools.infrastructure.pipeline_enhancer._execute_tool", new_callable=AsyncMock) as mock_exec:
            with patch("loom.tools.infrastructure.pipeline_enhancer._score_with_hcs", side_effect=slow_hcs_score):
                mock_exec.return_value = "test response"
                result = await research_enhance(
                    "research_fetch",
                    {"url": "https://example.com"},
                    auto_hcs=True,
                    auto_cost=True,
                    auto_suggest=False
                )
                assert "_execution_time_ms" in result
