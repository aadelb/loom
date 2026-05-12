"""Multi-stage pipeline execution engine."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger("loom.pipeline_runner")

Stage = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class StageResult:
    """Result from a single pipeline stage."""

    name: str
    success: bool
    data: Any = None
    error: str = ""
    elapsed_ms: int = 0


@dataclass
class PipelineResult:
    """Result from a complete pipeline run."""

    stages: list[StageResult] = field(default_factory=list)
    total_elapsed_ms: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def success(self) -> bool:
        return self.failed == 0

    def get_stage(self, name: str) -> StageResult | None:
        return next((s for s in self.stages if s.name == name), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "stages": [
                {"name": s.name, "success": s.success, "error": s.error, "elapsed_ms": s.elapsed_ms}
                for s in self.stages
            ],
            "total_elapsed_ms": self.total_elapsed_ms,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


async def run_pipeline(
    stages: list[tuple[str, Stage]],
    context: dict[str, Any] | None = None,
    *,
    stop_on_failure: bool = True,
    timeout_per_stage: float = 120.0,
) -> PipelineResult:
    """Execute pipeline of named async stages sequentially.

    Each stage receives the shared context dict and can read/write to it.
    Stage results are stored in context under the stage name.
    """
    context = context or {}
    result = PipelineResult()
    t0 = time.monotonic()
    failed = False

    for name, stage_fn in stages:
        if failed and stop_on_failure:
            result.stages.append(StageResult(name=name, success=False, error="skipped"))
            result.skipped += 1
            continue

        stage_t0 = time.monotonic()
        try:
            data = await asyncio.wait_for(stage_fn(context), timeout=timeout_per_stage)
            elapsed = int((time.monotonic() - stage_t0) * 1000)
            context[name] = data
            result.stages.append(StageResult(name=name, success=True, data=data, elapsed_ms=elapsed))
            result.completed += 1
        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - stage_t0) * 1000)
            msg = f"timeout after {timeout_per_stage}s"
            result.stages.append(StageResult(name=name, success=False, error=msg, elapsed_ms=elapsed))
            result.failed += 1
            failed = True
        except Exception as exc:
            elapsed = int((time.monotonic() - stage_t0) * 1000)
            logger.error("pipeline_stage_failed stage=%s error=%s", name, exc)
            result.stages.append(StageResult(name=name, success=False, error=str(exc), elapsed_ms=elapsed))
            result.failed += 1
            failed = True

    result.total_elapsed_ms = int((time.monotonic() - t0) * 1000)
    return result


async def run_parallel_stages(
    stages: list[tuple[str, Stage]],
    context: dict[str, Any] | None = None,
    *,
    timeout: float = 120.0,
    max_concurrency: int = 5,
) -> PipelineResult:
    """Run multiple stages concurrently with bounded parallelism."""
    context = context or {}
    result = PipelineResult()
    t0 = time.monotonic()
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_one(name: str, fn: Stage) -> StageResult:
        async with semaphore:
            stage_t0 = time.monotonic()
            try:
                data = await asyncio.wait_for(fn(context), timeout=timeout)
                elapsed = int((time.monotonic() - stage_t0) * 1000)
                return StageResult(name=name, success=True, data=data, elapsed_ms=elapsed)
            except Exception as exc:
                elapsed = int((time.monotonic() - stage_t0) * 1000)
                return StageResult(name=name, success=False, error=str(exc), elapsed_ms=elapsed)

    stage_results = await asyncio.gather(*(_run_one(name, fn) for name, fn in stages))
    for sr in stage_results:
        result.stages.append(sr)
        if sr.success:
            result.completed += 1
            context[sr.name] = sr.data
        else:
            result.failed += 1

    result.total_elapsed_ms = int((time.monotonic() - t0) * 1000)
    return result
