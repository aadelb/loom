"""Brain Core — research_smart_call orchestrator tying all 5 layers together.

Flow: Perception → Memory → Reasoning → Action → Reflection
Provider: always NVIDIA NIM (free tier).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from loom.brain.action import execute_step
from loom.brain.memory import get_memory
from loom.brain.perception import parse_intent
from loom.brain.reasoning import plan_workflow, select_tools
from loom.brain.reflection import evaluate_result, reflect_with_llm
from loom.brain.types import QualityMode, SmartCallResult

logger = logging.getLogger("loom.brain.core")

# Known escalation chains — when tool A fails, try tool B
_ESCALATION_CHAINS: dict[str, str] = {
    "research_fetch": "research_camoufox",
    "research_camoufox": "research_botasaurus",
    "research_search": "research_multi_search",
    "research_nuclei_scan": "research_cve_lookup",
}


def _find_fallback_tool(
    failed_tool: str,
    all_matches: list[Any],
    already_tried: list[str],
) -> Any | None:
    """Find a fallback tool when the primary one fails.

    Priority: explicit escalation chain > next best match from candidates.
    """
    # Check explicit escalation
    escalation = _ESCALATION_CHAINS.get(failed_tool)
    if escalation and escalation not in already_tried:
        from loom.brain.types import ToolMatch
        return ToolMatch(tool_name=escalation, confidence=0.9, match_source="escalation")

    # Fall back to next untried candidate
    for match in all_matches:
        if match.tool_name not in already_tried and match.tool_name != failed_tool:
            return match

    return None


async def research_smart_call(
    query: str,
    quality_mode: str = "auto",
    max_iterations: int = 3,
    forced_tools: list[str] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Intelligent tool orchestration — the main Brain entry point.

    Takes a natural language query, selects the best tool(s), extracts
    parameters, executes them, and reflects on results. Iterates up to
    max_iterations times if results are incomplete.

    Args:
        query: Natural language research query
        quality_mode: "max", "auto", or "economy"
        max_iterations: Maximum reflection-retry loops (1-5)
        forced_tools: Override tool selection with specific tool names
        timeout: Total timeout in seconds

    Returns:
        Dict with: success, matched_tools, plan_steps, final_output,
        iterations, quality_mode, error, elapsed_ms
    """
    start = time.time()
    mode = QualityMode(quality_mode) if quality_mode in ("max", "auto", "economy") else QualityMode.AUTO
    max_iterations = max(1, min(max_iterations, 5))
    memory = get_memory()

    # --- Layer 1: Perception ---
    intent = parse_intent(query)
    logger.info(
        "brain_perceive query=%s domains=%s intent_type=%s",
        query[:60],
        intent["domains"],
        intent["intent_type"],
    )

    # --- Layer 2: Memory ---
    recent_context = memory.get_recent_context(n=3)

    # --- Layer 3: Reasoning (tool selection + planning) ---
    matched = select_tools(
        query=query,
        quality_mode=mode,
        max_tools=10 if mode == QualityMode.MAX else 5,
        forced_tools=forced_tools,
    )

    if not matched:
        elapsed_ms = int((time.time() - start) * 1000)
        return SmartCallResult(
            success=False,
            error="No matching tools found for query",
            quality_mode=mode,
            elapsed_ms=elapsed_ms,
        ).model_dump()

    plan = plan_workflow(query, matched, mode)
    matched_tool_names = [m.tool_name for m in matched]
    plan_step_names = [s.tool_name for s in plan.steps]

    logger.info(
        "brain_plan matched_tools=%s plan_steps=%s",
        matched_tool_names[:5],
        plan_step_names,
    )

    # --- Layer 4: Action (execute plan steps with context piping) ---
    final_output: Any = None
    iterations = 0
    step_outputs: list[dict[str, Any]] = []

    try:
        async with asyncio.timeout(timeout):
            for iteration in range(max_iterations):
                iterations = iteration + 1

                for step in plan.steps:
                    step_context = {
                        "recent": recent_context,
                        "previous_outputs": step_outputs,
                    }
                    # Context piping: inject previous step's output as context
                    if step_outputs and step.depends_on:
                        prev = step_outputs[-1]
                        if prev.get("success") and prev.get("result"):
                            step_context["piped_result"] = prev["result"]

                    step_result = await execute_step(
                        step=step,
                        query=query,
                        quality_mode=mode,
                        context=step_context,
                    )

                    step_outputs.append(step_result)

                    # Record in memory
                    memory.record_call(
                        tool_name=step.tool_name,
                        query=query,
                        params=step_result.get("params_used", {}),
                        success=step_result.get("success", False),
                        elapsed_ms=step_result.get("elapsed_ms", 0),
                        error=step_result.get("error"),
                    )

                    if step_result.get("success"):
                        final_output = step_result.get("result")
                    elif mode != QualityMode.ECONOMY:
                        # Error recovery: try next best tool from matched list
                        fallback = _find_fallback_tool(
                            step.tool_name, matched, [s.tool_name for s in plan.steps]
                        )
                        if fallback:
                            logger.info("brain_fallback from=%s to=%s", step.tool_name, fallback.tool_name)
                            from loom.brain.types import PlanStep as _PS
                            fallback_step = _PS(tool_name=fallback.tool_name, timeout=step.timeout)
                            fallback_result = await execute_step(
                                step=fallback_step, query=query, quality_mode=mode, context=step_context,
                            )
                            step_outputs.append(fallback_result)
                            memory.record_call(
                                tool_name=fallback.tool_name, query=query,
                                params=fallback_result.get("params_used", {}),
                                success=fallback_result.get("success", False),
                                elapsed_ms=fallback_result.get("elapsed_ms", 0),
                                error=fallback_result.get("error"),
                            )
                            if fallback_result.get("success"):
                                final_output = fallback_result.get("result")

                # --- Layer 5: Reflection ---
                if final_output is not None:
                    if mode == QualityMode.MAX and iterations < max_iterations:
                        reflection = await reflect_with_llm(
                            query=query,
                            tool_name=plan.steps[-1].tool_name if plan.steps else "",
                            result={"success": True, "result": final_output},
                        )
                    else:
                        reflection = evaluate_result(
                            query=query,
                            tool_name=plan.steps[-1].tool_name if plan.steps else "",
                            result={"success": True, "result": final_output},
                            quality_mode=mode,
                        )

                    if reflection.get("complete"):
                        break

                    if reflection.get("next_action") == "done":
                        break
                else:
                    break

    except TimeoutError:
        logger.warning("brain_timeout query=%s after %.1fs", query[:40], timeout)
        if final_output is None:
            elapsed_ms = int((time.time() - start) * 1000)
            return SmartCallResult(
                success=False,
                matched_tools=matched_tool_names,
                plan_steps=plan_step_names,
                error=f"timeout after {timeout}s",
                iterations=iterations,
                quality_mode=mode,
                elapsed_ms=elapsed_ms,
            ).model_dump()

    elapsed_ms = int((time.time() - start) * 1000)

    result = SmartCallResult(
        success=final_output is not None,
        matched_tools=matched_tool_names,
        plan_steps=plan_step_names,
        final_output=final_output,
        iterations=iterations,
        quality_mode=mode,
        elapsed_ms=elapsed_ms,
    )

    logger.info(
        "brain_complete success=%s tools=%s iterations=%d elapsed_ms=%d",
        result.success,
        plan_step_names,
        iterations,
        elapsed_ms,
    )

    return result.model_dump()
