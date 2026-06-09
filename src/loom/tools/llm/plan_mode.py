"""Plan mode: Approval-gated execution planning with per-step risk assessment.

Mirrors PocketPaw's planning mode: an LLM breaks down a goal into concrete steps,
each step is risk-assessed via the Guardian tool, and human approval is required
if any step exceeds a configurable threat threshold.

Provides:
  - research_plan_mode: Decompose goal → risk-assess steps → approval gate
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

from loom.error_responses import handle_tool_errors
from loom.llm_parsers import extract_json

logger = logging.getLogger("loom.tools.llm.plan_mode")

# Threat level ordering (ascending severity)
_THREAT_LEVEL_ORDER: dict[str, int] = {
    "NONE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

_VALID_THREAT_LEVELS = frozenset(_THREAT_LEVEL_ORDER.keys())

# Auto-approve threshold order: steps AT or BELOW this level need no human approval
_VALID_AUTO_APPROVE = frozenset({"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"})


def _parse_plan_json(text: str) -> list[dict[str, Any]] | None:
    """Tolerant JSON parsing for step plan.

    Tries extract_json first, then falls back to manual boundary extraction.
    Returns list of step dicts or None.
    """
    # Try the standard JSON extractor
    parsed = extract_json(text)
    if parsed is not None:
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "steps" in parsed:
            steps = parsed.get("steps")
            if isinstance(steps, list):
                return steps

    # Fallback: look for JSON array manually
    text_clean = text.strip()
    if text_clean.startswith("[") and text_clean.endswith("]"):
        try:
            return json.loads(text_clean)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _order_threat_levels(threat: str) -> int:
    """Map threat level to numeric order (0=NONE, 4=CRITICAL)."""
    return _THREAT_LEVEL_ORDER.get(threat, 4)  # Default to CRITICAL if unknown


@handle_tool_errors("research_plan_mode")
async def research_plan_mode(
    goal: str,
    context: str = "",
    max_steps: int = 8,
    model: str = "auto",
    auto_approve_threshold: str = "LOW",
) -> dict[str, Any]:
    """Decompose a goal into steps, risk-assess each, and gate on approval.

    Plans a multi-step goal with built-in safety checks. Breaks the goal into
    concrete steps, evaluates the threat level of each step using the Guardian
    tool, and determines whether human approval is required before execution.

    This tool does NOT execute any steps; it only produces a plan and gates
    it based on configurable threat thresholds.

    **Threat Level Ordering:**
    NONE < LOW < MEDIUM < HIGH < CRITICAL

    A step requires approval if its threat_level exceeds auto_approve_threshold
    (via numeric ordering) OR if the Guardian explicitly returns allow=False.

    **Auto-Approval Threshold:**
    - NONE: All steps auto-approved (threshold = 0)
    - LOW: NONE, LOW auto-approved; MEDIUM+ need approval (threshold = 1)
    - MEDIUM: NONE, LOW, MEDIUM auto-approved (threshold = 2)
    - HIGH: NONE, LOW, MEDIUM, HIGH auto-approved (threshold = 3)
    - CRITICAL: No auto-approval, all need human decision (threshold = 4)

    Args:
        goal: The user's goal or task to accomplish (e.g., "fetch user data and export to CSV").
        context: Optional surrounding context, constraints, or environment info.
        max_steps: Maximum steps to decompose into (1-20; capped to prevent token overflow).
        model: LLM model for decomposition ("auto" uses config default).
        auto_approve_threshold: Threat level at/below which steps are auto-approved.
                              Must be one of: NONE, LOW, MEDIUM, HIGH, CRITICAL.

    Returns:
        {
            "goal": str (the original goal),
            "steps": [
                {
                    "n": int (step number),
                    "action": str (what to do),
                    "tool": str (which tool/command),
                    "threat_level": str (NONE|LOW|MEDIUM|HIGH|CRITICAL),
                    "allow": bool (Guardian verdict),
                    "reason": str (Guardian justification),
                }
            ],
            "step_count": int,
            "overall_risk": str (max threat level across all steps),
            "requires_approval": bool (True if any step exceeds threshold or allow=False),
            "auto_approvable": bool (True if all steps are auto-approvable),
            "summary": str (human-readable one-liner on approval status),
            "error": str (optional, if decomposition failed),
        }

    Example:
        >>> result = await research_plan_mode(
        ...     goal="fetch customer data and send email notifications",
        ...     auto_approve_threshold="MEDIUM"
        ... )
        >>> result["requires_approval"]
        True  # if any step is HIGH or CRITICAL
        >>> result["overall_risk"]
        "HIGH"
    """
    # Validate auto_approve_threshold
    if auto_approve_threshold not in _VALID_AUTO_APPROVE:
        return {
            "error": f"Invalid auto_approve_threshold {auto_approve_threshold!r}; must be one of {sorted(_VALID_AUTO_APPROVE)}",
            "goal": goal,
            "step_count": 0,
            "steps": [],
            "requires_approval": True,
            "auto_approvable": False,
        }

    # Cap max_steps
    max_steps = max(1, min(int(max_steps), 20))

    logger.info(
        "plan_mode_start goal_preview=%s max_steps=%d threshold=%s",
        goal[:60],
        max_steps,
        auto_approve_threshold,
    )

    # STEP 1: Decompose goal into steps via LLM
    steps_list: list[dict[str, Any]] | None = None
    decompose_error: str | None = None

    try:
        from loom.tools.llm.llm import _call_with_cascade

        decompose_prompt = f"""You are a planning AI. Decompose the following goal into a numbered list of concrete, actionable steps.

Goal: {goal}

{f'Context: {context}' if context else ''}

Generate {max_steps} or fewer steps. Each step should:
1. Be a single, concrete action
2. Specify which tool or command would execute it
3. Be ordered logically

Respond ONLY with a JSON array of objects. Each object must have exactly these keys:
- "n": step number (1, 2, 3, ...)
- "action": what to do (short description)
- "tool": which tool/command (e.g., "research_fetch", "bash rm", "python script")

Example format:
[
  {{"n": 1, "action": "fetch data from API", "tool": "research_fetch"}},
  {{"n": 2, "action": "parse JSON response", "tool": "python json.loads"}},
  {{"n": 3, "action": "write to file", "tool": "bash tee"}}
]

Do NOT include any text outside the JSON array. Do NOT include markdown fences."""

        response = await _call_with_cascade(
            messages=[{"role": "user", "content": decompose_prompt}],
            model=model,
            max_tokens=1500,
            temperature=0.2,  # Deterministic planning
            timeout=30,
        )

        if response and response.text:
            parsed = _parse_plan_json(response.text)
            if parsed and isinstance(parsed, list):
                # Validate step structure
                steps_list = []
                for step in parsed[: max_steps]:
                    if isinstance(step, dict):
                        steps_list.append(
                            {
                                "n": step.get("n", len(steps_list) + 1),
                                "action": str(step.get("action", ""))[:200],
                                "tool": str(step.get("tool", ""))[:100],
                            }
                        )

                if not steps_list:
                    decompose_error = "LLM returned empty step list"
                    logger.warning("plan_mode_decompose_empty response_preview=%s", response.text[:200])
            else:
                decompose_error = "LLM response was not a JSON array or lacked 'steps' key"
                logger.warning(
                    "plan_mode_decompose_invalid response_type=%s response_preview=%s",
                    type(parsed),
                    response.text[:200] if response.text else "",
                )
        else:
            decompose_error = "LLM returned empty response"

    except Exception as e:
        decompose_error = f"Decomposition failed: {str(e)[:100]}"
        logger.error("plan_mode_decompose_error error=%s", decompose_error)

    # FALLBACK: If decomposition failed, create a single-step placeholder
    if not steps_list:
        logger.info(
            "plan_mode_fallback_single_step goal_preview=%s decompose_error=%s",
            goal[:60],
            decompose_error,
        )
        steps_list = [
            {
                "n": 1,
                "action": goal[:200],
                "tool": "unknown",
            }
        ]
        if not decompose_error:
            decompose_error = "Failed to decompose; created single-step fallback"

    # STEP 2: Risk-assess each step via Guardian (concurrent)
    guardian_tasks = []
    for step in steps_list:
        task = _assess_step_risk(
            step=step,
            goal=goal,
            context=context,
        )
        guardian_tasks.append(task)

    assessed_steps = await asyncio.gather(*guardian_tasks, return_exceptions=True)

    # Flatten assessed steps (handle exceptions gracefully)
    final_steps: list[dict[str, Any]] = []
    for i, result in enumerate(assessed_steps):
        if isinstance(result, dict):
            final_steps.append(result)
        elif isinstance(result, Exception):
            # Guardian call failed; mark as HIGH fail-closed
            if i < len(steps_list):
                step = steps_list[i]
                final_steps.append(
                    {
                        "n": step.get("n", i + 1),
                        "action": step.get("action", ""),
                        "tool": step.get("tool", ""),
                        "threat_level": "HIGH",
                        "allow": False,
                        "reason": f"Guardian evaluation failed; fail-closed: {str(result)[:80]}",
                    }
                )

    # STEP 3: Compute approval gate
    # Threat threshold as numeric value
    threshold_order = _order_threat_levels(auto_approve_threshold)

    # Determine overall risk (max threat across all steps)
    overall_risk = "NONE"
    if final_steps:
        max_threat_order = max(
            _order_threat_levels(step.get("threat_level", "NONE"))
            for step in final_steps
        )
        # Reverse map from order to threat level
        for threat, order in _THREAT_LEVEL_ORDER.items():
            if order == max_threat_order:
                overall_risk = threat
                break

    # Determine requires_approval
    requires_approval = False
    for step in final_steps:
        threat_order = _order_threat_levels(step.get("threat_level", "NONE"))
        allow = step.get("allow", False)

        # Require approval if: threat exceeds threshold OR allow is False
        if threat_order > threshold_order or not allow:
            requires_approval = True
            break

    # Auto-approvable: all steps are at/below threshold AND all allow=True
    auto_approvable = all(
        _order_threat_levels(step.get("threat_level", "NONE")) <= threshold_order
        and step.get("allow", False)
        for step in final_steps
    )

    # Human-readable summary
    if requires_approval:
        if auto_approvable:
            summary = f"Plan requires review: {overall_risk}-risk step(s) present"
        else:
            summary = f"Plan BLOCKED: {overall_risk}-threat step(s) need approval"
    else:
        summary = "Plan auto-approved: all steps below threat threshold"

    result = {
        "goal": goal,
        "steps": final_steps,
        "step_count": len(final_steps),
        "overall_risk": overall_risk,
        "requires_approval": requires_approval,
        "auto_approvable": auto_approvable,
        "summary": summary,
    }

    if decompose_error:
        result["error"] = decompose_error

    logger.info(
        "plan_mode_complete goal_preview=%s step_count=%d overall_risk=%s requires_approval=%s",
        goal[:60],
        len(final_steps),
        overall_risk,
        requires_approval,
    )

    return result


async def _assess_step_risk(
    step: dict[str, Any],
    goal: str,
    context: str,
) -> dict[str, Any]:
    """Risk-assess a single step via Guardian tool.

    Args:
        step: The step dict with n, action, tool.
        goal: The original goal (for Guardian context).
        context: Optional surrounding context.

    Returns:
        Step dict with threat_level, allow, reason added.
    """
    try:
        from loom.tools.security.guardian import research_guardian_check

        action = step.get("action", "")
        tool_name = step.get("tool", "")

        # Construct context for Guardian
        guardian_context = f"Goal: {goal}"
        if context:
            guardian_context += f"\nEnvironment: {context}"

        # Call Guardian
        guardian_result = await research_guardian_check(
            action=action,
            context=guardian_context,
            tool_name=tool_name,
            judge_model="auto",
            fail_closed=True,
        )

        # Extract verdict from Guardian
        threat_level = guardian_result.get("threat_level", "HIGH")
        allow = guardian_result.get("allow", False)
        reason = guardian_result.get("reason", "Guardian assessment")

        # Validate threat level
        if threat_level not in _VALID_THREAT_LEVELS:
            threat_level = "HIGH"

        result = dict(step)
        result["threat_level"] = threat_level
        result["allow"] = allow
        result["reason"] = reason

        logger.debug(
            "plan_step_assessed n=%s action_preview=%s threat=%s allow=%s",
            step.get("n"),
            action[:40],
            threat_level,
            allow,
        )

        return result

    except Exception as e:
        # Guardian failed; return step with HIGH threat, fail-closed
        logger.error(
            "plan_step_guardian_error n=%s error=%s",
            step.get("n"),
            str(e)[:100],
        )
        result = dict(step)
        result["threat_level"] = "HIGH"
        result["allow"] = False
        result["reason"] = f"Guardian check failed: {str(e)[:80]}"
        return result
