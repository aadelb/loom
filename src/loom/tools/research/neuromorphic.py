"""research_neuromorphic_schedule — Spike-timing based tool activation scheduling.

Generates execution schedules using neuromorphic patterns inspired by neural networks.
Does NOT execute tools — returns a schedule dict for async invocation.
"""

from __future__ import annotations

import logging
import math

from pydantic import BaseModel, Field
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.neuromorphic")


class NeuromorphicScheduleParams(BaseModel):
    """Parameters for neuromorphic scheduling."""

    tools: list[str] = Field(min_length=1, max_length=50)
    timing_pattern: str = "burst"
    interval_ms: int = Field(default=100, ge=10, le=5000)

    model_config = {"extra": "forbid", "strict": True}


class ToolExecution(BaseModel):
    """Single tool execution in the schedule."""

    tool: str
    fire_at_ms: int
    wave_number: int


class NeuromorphicSchedule(BaseModel):
    """Complete neuromorphic execution schedule."""

    tools_count: int
    pattern: str
    schedule: list[ToolExecution]
    waves: int
    total_duration_ms: int
    parallelism_score: float
    interference_risk: str
    recommendation: str


def _calculate_burst_schedule(
    tools: list[str], interval_ms: int
) -> tuple[list[ToolExecution], int, int, float, str]:
    """Burst: Fire all tools simultaneously (wave 1 at t=0)."""
    schedule = [ToolExecution(tool=t, fire_at_ms=0, wave_number=1) for t in tools]
    waves = 1
    duration = interval_ms
    parallelism = 1.0  # Maximum parallelism
    risk = "high"  # Maximum contention
    return schedule, waves, duration, parallelism, risk


def _calculate_gamma_schedule(
    tools: list[str], interval_ms: int
) -> tuple[list[ToolExecution], int, int, float, str]:
    """Gamma (40Hz): Fire every 25ms in groups of 3 (mimics 40Hz oscillation)."""
    schedule = []
    group_size = 3
    gamma_interval = 25  # 40Hz ~ 25ms per cycle

    for idx, tool in enumerate(tools):
        wave = (idx // group_size) + 1
        position_in_wave = idx % group_size
        fire_at = (wave - 1) * gamma_interval + position_in_wave * 5
        schedule.append(ToolExecution(tool=tool, fire_at_ms=fire_at, wave_number=wave))

    waves = (len(tools) + group_size - 1) // group_size
    duration = waves * gamma_interval + interval_ms
    parallelism = min(group_size / len(tools), 1.0)
    risk = "medium"
    return schedule, waves, duration, parallelism, risk


def _calculate_theta_schedule(
    tools: list[str], interval_ms: int
) -> tuple[list[ToolExecution], int, int, float, str]:
    """Theta (8Hz): Sequential with 125ms gaps (8Hz = 125ms period)."""
    schedule = []
    theta_interval = 125  # 8Hz ~ 125ms per cycle

    for idx, tool in enumerate(tools):
        wave = idx + 1
        fire_at = idx * theta_interval
        schedule.append(ToolExecution(tool=tool, fire_at_ms=fire_at, wave_number=wave))

    waves = len(tools)
    duration = (len(tools) - 1) * theta_interval + interval_ms
    parallelism = 1.0 / len(tools)  # Minimal parallelism
    risk = "low"
    return schedule, waves, duration, parallelism, risk


def _calculate_spike_train_schedule(
    tools: list[str], interval_ms: int
) -> tuple[list[ToolExecution], int, int, float, str]:
    """Spike train: Irregular intervals mimicking biological spike patterns."""
    schedule = []
    # Poisson-like intervals: vary between 50% and 200% of base interval
    import random

    random.seed(hash(tuple(tools)) % 2**31)  # Deterministic pseudo-randomness
    current_time = 0
    for idx, tool in enumerate(tools):
        wave = (idx // 4) + 1  # Group into waves of 4
        jitter = random.uniform(0.5, 2.0)
        current_time += int(interval_ms * jitter / 2)
        schedule.append(ToolExecution(tool=tool, fire_at_ms=current_time, wave_number=wave))

    waves = (len(tools) + 3) // 4
    duration = current_time + interval_ms
    parallelism = min(4.0 / len(tools), 1.0)
    risk = "medium"
    return schedule, waves, duration, parallelism, risk


def _calculate_resonance_schedule(
    tools: list[str], interval_ms: int
) -> tuple[list[ToolExecution], int, int, float, str]:
    """Resonance: Start slow, accelerate to match model's response rhythm."""
    schedule = []
    # Exponential acceleration: start at 3x interval, converge to interval/2
    current_time = 0
    acceleration_factor = 1.0

    for idx, tool in enumerate(tools):
        wave = max(1, (idx // 5) + 1)  # Group into waves of 5
        # Exponential decay towards fast firing
        interval_decay = interval_ms * (1.0 + math.exp(-idx / 3.0))
        current_time += int(interval_decay * acceleration_factor)
        acceleration_factor *= 0.9  # Gradually reduce interval
        schedule.append(ToolExecution(tool=tool, fire_at_ms=current_time, wave_number=wave))

    waves = (len(tools) + 4) // 5
    duration = current_time + interval_ms
    parallelism = min((5.0 / len(tools)) * 0.2, 1.0)  # Scaled down to 0-1 range
    risk = "medium-low"
    return schedule, waves, duration, parallelism, risk


@handle_tool_errors("research_neuromorphic_schedule")
async def research_neuromorphic_schedule(
    tools: list[str] | str,
    timing_pattern: str = "burst",
    interval_ms: int = 100,
) -> NeuromorphicSchedule:
    """Schedule tool executions using neuromorphic spike-timing patterns.

    Does NOT execute tools. Returns a schedule dict for the caller to invoke.

    Args:
        tools: List of tool names to schedule (max 50).
        timing_pattern: One of burst, gamma, theta, spike_train, resonance.
        interval_ms: Base interval in milliseconds (10-5000).

    Returns:
        NeuromorphicSchedule with execution plan, parallelism score, and risk assessment.
    """
    try:
        # Coerce string to list before validation
        if isinstance(tools, str):
            tools = [tools]

        # Validate
        params = NeuromorphicScheduleParams(
            tools=tools, timing_pattern=timing_pattern, interval_ms=interval_ms
        )

        # Route to pattern calculator
        if params.timing_pattern == "burst":
            schedule, waves, duration, parallelism, risk = _calculate_burst_schedule(
                params.tools, params.interval_ms
            )
        elif params.timing_pattern == "gamma":
            schedule, waves, duration, parallelism, risk = _calculate_gamma_schedule(
                params.tools, params.interval_ms
            )
        elif params.timing_pattern == "theta":
            schedule, waves, duration, parallelism, risk = _calculate_theta_schedule(
                params.tools, params.interval_ms
            )
        elif params.timing_pattern == "spike_train":
            schedule, waves, duration, parallelism, risk = _calculate_spike_train_schedule(
                params.tools, params.interval_ms
            )
        else:  # resonance
            schedule, waves, duration, parallelism, risk = _calculate_resonance_schedule(
                params.tools, params.interval_ms
            )

        # Score parallelism (0-1 scale, 1 = perfect)
        parallelism_score = min(parallelism, 1.0)

        # Generate recommendation based on pattern characteristics
        if risk == "high":
            recommendation = f"Burst pattern: max parallelism, high rate-limit risk. Suitable for non-critical batch tasks."
        elif risk == "low":
            recommendation = f"Theta pattern: minimal contention, safe for rate-limited APIs. Slower overall (~{duration}ms)."
        else:
            recommendation = f"{params.timing_pattern.title()} pattern: balanced parallelism and safety. Total duration {duration}ms."

        result = NeuromorphicSchedule(
            tools_count=len(params.tools),
            pattern=params.timing_pattern,
            schedule=schedule,
            waves=waves,
            total_duration_ms=duration,
            parallelism_score=parallelism_score,
            interference_risk=risk,
            recommendation=recommendation,
        )

        logger.info(
            "neuromorphic_schedule_generated",
            extra={
                "pattern": params.timing_pattern,
                "tools_count": len(params.tools),
                "waves": waves,
                "duration_ms": duration,
                "parallelism_score": parallelism_score,
            },
        )

        return result
    except Exception as exc:
        logger.error("research_neuromorphic_schedule failed: %s", exc)
        raise
