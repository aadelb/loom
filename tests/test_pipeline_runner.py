"""Tests for pipeline_runner module.

Tests run_pipeline, run_parallel_stages, and PipelineResult.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.pipeline_runner import PipelineResult, StageResult, run_parallel_stages, run_pipeline


class TestStageResult:
    """Test StageResult dataclass."""

    def test_stage_result_success(self) -> None:
        """Test StageResult for successful stage."""
        result = StageResult(
            name="fetch",
            success=True,
            data={"items": [1, 2, 3]},
            elapsed_ms=150,
        )
        assert result.name == "fetch"
        assert result.success is True
        assert result.data == {"items": [1, 2, 3]}
        assert result.elapsed_ms == 150
        assert result.error == ""

    def test_stage_result_failure(self) -> None:
        """Test StageResult for failed stage."""
        result = StageResult(
            name="process",
            success=False,
            error="Connection timeout",
            elapsed_ms=5000,
        )
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.data is None


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_pipeline_result_success_property(self) -> None:
        """Test PipelineResult.success property."""
        result = PipelineResult()
        result.failed = 0
        assert result.success is True

        result.failed = 1
        assert result.success is False

    def test_pipeline_result_get_stage(self) -> None:
        """Test getting stage by name."""
        result = PipelineResult()
        stage1 = StageResult(name="stage1", success=True)
        stage2 = StageResult(name="stage2", success=False)
        result.stages = [stage1, stage2]

        found = result.get_stage("stage1")
        assert found == stage1

        not_found = result.get_stage("nonexistent")
        assert not_found is None

    def test_pipeline_result_to_dict(self) -> None:
        """Test PipelineResult.to_dict conversion."""
        result = PipelineResult()
        result.stages = [
            StageResult(name="s1", success=True, elapsed_ms=100),
            StageResult(name="s2", success=False, error="failed", elapsed_ms=200),
        ]
        result.completed = 1
        result.failed = 1
        result.total_elapsed_ms = 300

        d = result.to_dict()
        assert d["success"] is False
        assert d["completed"] == 1
        assert d["failed"] == 1
        assert d["total_elapsed_ms"] == 300
        assert len(d["stages"]) == 2


class TestRunPipeline:
    """Test run_pipeline function."""

    @pytest.mark.asyncio
    async def test_run_pipeline_single_stage(self) -> None:
        """Test pipeline with single stage."""
        async def stage1(ctx: dict[str, Any]) -> Any:
            return {"result": "success"}

        result = await run_pipeline([("stage1", stage1)])
        assert result.success is True
        assert result.completed == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_run_pipeline_multiple_stages(self) -> None:
        """Test pipeline with multiple stages."""
        async def stage1(ctx: dict[str, Any]) -> Any:
            return {"data": "from stage 1"}

        async def stage2(ctx: dict[str, Any]) -> Any:
            return {"data": "from stage 2"}

        result = await run_pipeline([
            ("stage1", stage1),
            ("stage2", stage2),
        ])
        assert result.completed == 2
        assert result.failed == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_pipeline_stage_receives_context(self) -> None:
        """Test that stages receive and can modify context."""
        async def stage1(ctx: dict[str, Any]) -> Any:
            ctx["shared"] = "value1"
            return {"result": 1}

        async def stage2(ctx: dict[str, Any]) -> Any:
            # Should have access to stage1's result
            assert "stage1" in ctx
            ctx["shared"] = "value2"
            return {"result": 2}

        result = await run_pipeline([
            ("stage1", stage1),
            ("stage2", stage2),
        ])
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_pipeline_stage_failure(self) -> None:
        """Test pipeline stage failure."""
        async def good_stage(ctx: dict[str, Any]) -> Any:
            return {"status": "ok"}

        async def bad_stage(ctx: dict[str, Any]) -> Any:
            raise ValueError("stage failed")

        result = await run_pipeline([
            ("good", good_stage),
            ("bad", bad_stage),
        ])
        assert result.failed == 1
        assert result.completed == 1
        assert result.success is False

        bad_result = result.get_stage("bad")
        assert bad_result is not None
        assert bad_result.success is False
        assert "stage failed" in bad_result.error

    @pytest.mark.asyncio
    async def test_run_pipeline_stop_on_failure(self) -> None:
        """Test stop_on_failure=True skips remaining stages."""
        call_order: list[str] = []

        async def stage1(ctx: dict[str, Any]) -> Any:
            call_order.append("stage1")
            raise RuntimeError("failed")

        async def stage2(ctx: dict[str, Any]) -> Any:
            call_order.append("stage2")
            return {"x": 1}

        result = await run_pipeline(
            [("stage1", stage1), ("stage2", stage2)],
            stop_on_failure=True,
        )
        assert result.failed == 1
        assert result.skipped == 1
        assert "stage1" in call_order
        assert "stage2" not in call_order

    @pytest.mark.asyncio
    async def test_run_pipeline_continue_on_failure(self) -> None:
        """Test stop_on_failure=False continues after failure."""
        call_order: list[str] = []

        async def stage1(ctx: dict[str, Any]) -> Any:
            call_order.append("stage1")
            raise RuntimeError("failed")

        async def stage2(ctx: dict[str, Any]) -> Any:
            call_order.append("stage2")
            return {"x": 1}

        result = await run_pipeline(
            [("stage1", stage1), ("stage2", stage2)],
            stop_on_failure=False,
        )
        assert result.failed == 1
        assert result.completed == 1
        assert "stage1" in call_order
        assert "stage2" in call_order

    @pytest.mark.asyncio
    async def test_run_pipeline_timeout(self) -> None:
        """Test stage timeout."""
        async def slow_stage(ctx: dict[str, Any]) -> Any:
            await asyncio.sleep(5)
            return {"done": True}

        result = await run_pipeline(
            [("slow", slow_stage)],
            timeout_per_stage=0.1,
        )
        assert result.failed == 1
        stage = result.get_stage("slow")
        assert stage is not None
        assert "timeout" in stage.error

    @pytest.mark.asyncio
    async def test_run_pipeline_elapsed_time(self) -> None:
        """Test elapsed time calculation."""
        async def quick_stage(ctx: dict[str, Any]) -> Any:
            return {"done": True}

        result = await run_pipeline([("quick", quick_stage)])
        assert result.total_elapsed_ms >= 0
        stage = result.get_stage("quick")
        assert stage is not None
        assert stage.elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_run_pipeline_with_initial_context(self) -> None:
        """Test pipeline with initial context."""
        initial_context = {"initial": "value"}

        async def stage1(ctx: dict[str, Any]) -> Any:
            assert ctx["initial"] == "value"
            return {"added": True}

        result = await run_pipeline([("stage1", stage1)], context=initial_context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_pipeline_context_isolation(self) -> None:
        """Test that context changes persist across stages."""
        async def stage1(ctx: dict[str, Any]) -> Any:
            return {"value": 100}

        async def stage2(ctx: dict[str, Any]) -> Any:
            # stage1 result should be available as context["stage1"]
            assert "stage1" in ctx
            assert ctx["stage1"]["value"] == 100
            return {"value": 200}

        result = await run_pipeline([
            ("stage1", stage1),
            ("stage2", stage2),
        ])
        assert result.success is True


class TestRunParallelStages:
    """Test run_parallel_stages function."""

    @pytest.mark.asyncio
    async def test_run_parallel_stages_concurrent(self) -> None:
        """Test that stages run concurrently."""
        execution_times: dict[str, tuple[float, float]] = {}
        start_time = asyncio.get_event_loop().time()

        async def stage1(ctx: dict[str, Any]) -> Any:
            t = asyncio.get_event_loop().time() - start_time
            await asyncio.sleep(0.1)
            execution_times["stage1"] = (t, asyncio.get_event_loop().time() - start_time)
            return {"s": 1}

        async def stage2(ctx: dict[str, Any]) -> Any:
            t = asyncio.get_event_loop().time() - start_time
            await asyncio.sleep(0.1)
            execution_times["stage2"] = (t, asyncio.get_event_loop().time() - start_time)
            return {"s": 2}

        result = await run_parallel_stages([
            ("stage1", stage1),
            ("stage2", stage2),
        ])
        assert result.completed == 2
        # Total time should be ~0.1s (concurrent), not 0.2s (sequential)
        assert result.total_elapsed_ms < 200

    @pytest.mark.asyncio
    async def test_run_parallel_stages_max_concurrency(self) -> None:
        """Test max_concurrency limits concurrent execution."""
        concurrent_count = 0
        max_concurrent = 0

        async def stage(ctx: dict[str, Any]) -> Any:
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            return {"x": 1}

        stages = [(f"s{i}", stage) for i in range(6)]
        result = await run_parallel_stages(stages, max_concurrency=2)
        assert result.completed == 6
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_run_parallel_stages_failure(self) -> None:
        """Test failure handling in parallel stages."""
        async def good(ctx: dict[str, Any]) -> Any:
            return {"ok": True}

        async def bad(ctx: dict[str, Any]) -> Any:
            raise RuntimeError("error")

        result = await run_parallel_stages([
            ("good", good),
            ("bad", bad),
        ])
        assert result.completed == 1
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_run_parallel_stages_timeout(self) -> None:
        """Test timeout in parallel stages."""
        async def slow(ctx: dict[str, Any]) -> Any:
            await asyncio.sleep(10)
            return {}

        result = await run_parallel_stages(
            [("slow", slow)],
            timeout=0.1,
        )
        assert result.failed == 1
        stage = result.get_stage("slow")
        assert stage is not None
        assert stage.success is False

    @pytest.mark.asyncio
    async def test_run_parallel_stages_result_stored_in_context(self) -> None:
        """Test that stage results are stored in context."""
        async def s1(ctx: dict[str, Any]) -> Any:
            return {"value": 1}

        async def s2(ctx: dict[str, Any]) -> Any:
            return {"value": 2}

        ctx: dict[str, Any] = {}
        result = await run_parallel_stages(
            [("s1", s1), ("s2", s2)],
            context=ctx,
        )
        assert ctx["s1"] == {"value": 1}
        assert ctx["s2"] == {"value": 2}

    @pytest.mark.asyncio
    async def test_run_parallel_stages_empty(self) -> None:
        """Test empty stages list."""
        result = await run_parallel_stages([])
        assert result.completed == 0
        assert result.failed == 0
        assert result.success is True
