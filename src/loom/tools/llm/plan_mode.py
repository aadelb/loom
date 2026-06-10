"""Plan mode: Approval-gated execution planning with per-step risk assessment.

Mirrors PocketPaw's planning mode: an LLM breaks down a goal into concrete steps,
each step is risk-assessed via the Guardian tool, and human approval is required
if any step exceeds a configurable threat threshold.

Provides:
  - research_plan_mode: Multi-action planning with approval workflow:
    - "plan": Decompose goal → risk-assess steps → return pending plan
    - "approve": Mark plan approved with note → audit record
    - "reject": Mark plan rejected with note → audit record
    - "status": Get one plan + its audit trail
    - "list": List all plans with truncated summaries
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from loom.error_responses import handle_tool_errors
from loom.llm_parsers import extract_json

logger = logging.getLogger("loom.tools.llm.plan_mode")

# Plans storage directory
_PLANS_DIR = Path.home() / ".loom" / "plans"
_AUDIT_LOG = _PLANS_DIR / "_audit.jsonl"

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

# Valid actions
_VALID_ACTIONS = frozenset({"plan", "approve", "reject", "status", "list"})


def _ensure_plans_dir() -> None:
    """Ensure ~/.loom/plans directory exists."""
    _PLANS_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: str) -> None:
    """Atomic file write: write to temp, then rename."""
    tmp_path = path.parent / f".{path.name}.{uuid.uuid4().hex[:8]}.tmp"
    try:
        tmp_path.write_text(data, encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _write_audit_record(decision: str, plan_id: str, note: str) -> None:
    """Append an audit record to the audit log (append-only JSONL)."""
    _ensure_plans_dir()
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "plan_id": plan_id,
        "decision": decision,  # "approved" | "rejected"
        "note": note,
    }
    try:
        with open(_AUDIT_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.error("audit_write_error plan_id=%s error=%s", plan_id, str(e)[:100])


def _generate_plan_id(goal: str) -> str:
    """Generate a deterministic plan_id from the goal."""
    # Use hash of goal for determinism (not time/random)
    hash_val = abs(hash(goal)) % (10**8)
    return f"plan_{hash_val:08d}"


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


def _load_plan(plan_id: str) -> dict[str, Any] | None:
    """Load a plan by ID from disk."""
    plan_path = _PLANS_DIR / f"{plan_id}.json"
    if not plan_path.exists():
        return None
    try:
        data = plan_path.read_text(encoding="utf-8")
        return json.loads(data)
    except Exception as e:
        logger.error("plan_load_error plan_id=%s error=%s", plan_id, str(e)[:100])
        return None


def _save_plan(plan_id: str, plan_data: dict[str, Any]) -> None:
    """Atomically save a plan to disk."""
    _ensure_plans_dir()
    plan_path = _PLANS_DIR / f"{plan_id}.json"
    plan_data["last_updated"] = datetime.utcnow().isoformat()
    _atomic_write(plan_path, json.dumps(plan_data, indent=2))


def _get_plan_audit_trail(plan_id: str) -> list[dict[str, Any]]:
    """Load audit records for a specific plan from the audit log."""
    trail: list[dict[str, Any]] = []
    if not _AUDIT_LOG.exists():
        return trail
    try:
        with open(_AUDIT_LOG, "r") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get("plan_id") == plan_id:
                        trail.append(record)
    except Exception as e:
        logger.error("audit_read_error plan_id=%s error=%s", plan_id, str(e)[:100])
    return trail


@handle_tool_errors("research_plan_mode")
async def research_plan_mode(
    action: str,
    goal: str = "",
    plan_id: str = "",
    note: str = "",
    context: str = "",
    max_steps: int = 8,
    model: str = "auto",
    auto_approve_threshold: str = "LOW",
) -> dict[str, Any]:
    """Multi-action approval-gated planning with persistent audit trail.

    Implements PocketPaw's planning mode with approval/rejection workflow:
    - "plan": LLM decomposes goal into steps, Guardian assesses risk, plan persisted pending approval
    - "approve": Mark plan approved + audit record + store reviewer note
    - "reject": Mark plan rejected + audit record + store reviewer note
    - "status": Retrieve one plan + its full audit trail
    - "list": List all plans with goals, risks, statuses

    Plans are persisted to ~/.loom/plans/<plan_id>.json (atomically written).
    Approval decisions logged to ~/.loom/plans/_audit.jsonl (append-only).

    Args:
        action: One of "plan", "approve", "reject", "status", "list".
        goal: (for action="plan") The task to plan.
        plan_id: (for approve/reject/status) Plan ID to act on.
        note: (for approve/reject) Reviewer's decision note.
        context: (for action="plan") Optional surrounding context/constraints.
        max_steps: (for action="plan") Max steps to decompose (1-20).
        model: (for action="plan") LLM model ("auto" = config default).
        auto_approve_threshold: (for action="plan") Threat level for auto-approval (NONE|LOW|MEDIUM|HIGH|CRITICAL).

    Returns:
        {
            "success": bool,
            "action": str (the action performed),
            "plan_id": str (for plan/approve/reject/status),
            "plan": {...} (full plan object for plan/approve/reject/status),
            "audit_trail": [...] (for status/approve/reject),
            "plans": [...] (for list),
            "error": str (if action failed),
        }

    Example:
        >>> # Step 1: Create a plan
        >>> result = await research_plan_mode(
        ...     action="plan",
        ...     goal="fetch customer data and send email notifications",
        ...     auto_approve_threshold="MEDIUM"
        ... )
        >>> plan_id = result["plan_id"]
        >>>
        >>> # Step 2: Reviewer checks the plan
        >>> status = await research_plan_mode(
        ...     action="status",
        ...     plan_id=plan_id
        ... )
        >>> print(status["plan"]["overall_risk"])  # HIGH → requires approval
        >>>
        >>> # Step 3: Approve with note
        >>> approval = await research_plan_mode(
        ...     action="approve",
        ...     plan_id=plan_id,
        ...     note="Risk accepted; HIGH-risk steps are within tolerance"
        ... )
        >>> print(approval["plan"]["status"])  # approved
        >>> print(approval["audit_trail"])  # includes the approval record
    """
    # Validate action
    if action not in _VALID_ACTIONS:
        return {
            "success": False,
            "action": action,
            "error": f"Invalid action {action!r}; must be one of {sorted(_VALID_ACTIONS)}",
        }

    # Route to appropriate sub-handler
    if action == "plan":
        return await _action_plan(goal, context, max_steps, model, auto_approve_threshold)
    elif action == "approve":
        return await _action_approve(plan_id, note)
    elif action == "reject":
        return await _action_reject(plan_id, note)
    elif action == "status":
        return await _action_status(plan_id)
    elif action == "list":
        return await _action_list()
    else:
        # Unreachable (action validated above)
        return {"success": False, "action": action, "error": "Unknown action"}


async def _action_plan(
    goal: str,
    context: str,
    max_steps: int,
    model: str,
    auto_approve_threshold: str,
) -> dict[str, Any]:
    """Create a new plan: decompose goal, assess risk, persist with status=pending_approval."""
    if not goal or not goal.strip():
        return {
            "success": False,
            "action": "plan",
            "error": "goal is required and must be non-empty",
        }

    # Validate auto_approve_threshold
    if auto_approve_threshold not in _VALID_AUTO_APPROVE:
        return {
            "success": False,
            "action": "plan",
            "error": f"Invalid auto_approve_threshold {auto_approve_threshold!r}; must be one of {sorted(_VALID_AUTO_APPROVE)}",
        }

    # Cap max_steps
    max_steps = max(1, min(int(max_steps), 20))

    logger.info(
        "plan_action_start goal_preview=%s max_steps=%d threshold=%s",
        goal[:60],
        max_steps,
        auto_approve_threshold,
    )

    # Generate deterministic plan_id
    plan_id = _generate_plan_id(goal)

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
                    logger.warning("plan_decompose_empty response_preview=%s", response.text[:200])
            else:
                decompose_error = "LLM response was not a JSON array or lacked 'steps' key"
                logger.warning(
                    "plan_decompose_invalid response_type=%s response_preview=%s",
                    type(parsed),
                    response.text[:200] if response.text else "",
                )
        else:
            decompose_error = "LLM returned empty response"

    except Exception as e:
        decompose_error = f"Decomposition failed: {str(e)[:100]}"
        logger.error("plan_decompose_error error=%s", decompose_error)

    # FALLBACK: If decomposition failed, create a single-step placeholder
    if not steps_list:
        logger.info(
            "plan_fallback_single_step goal_preview=%s decompose_error=%s",
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

    # STEP 4: Persist plan
    plan_data = {
        "plan_id": plan_id,
        "goal": goal,
        "steps": final_steps,
        "step_count": len(final_steps),
        "overall_risk": overall_risk,
        "requires_approval": requires_approval,
        "auto_approvable": auto_approvable,
        "summary": summary,
        "status": "pending_approval",  # Will change to approved/rejected
        "created_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
    }

    if decompose_error:
        plan_data["decompose_error"] = decompose_error

    _save_plan(plan_id, plan_data)

    logger.info(
        "plan_created plan_id=%s goal_preview=%s step_count=%d overall_risk=%s requires_approval=%s",
        plan_id,
        goal[:60],
        len(final_steps),
        overall_risk,
        requires_approval,
    )

    return {
        "success": True,
        "action": "plan",
        "plan_id": plan_id,
        "plan": plan_data,
    }


async def _action_approve(plan_id: str, note: str) -> dict[str, Any]:
    """Approve a plan and record the decision."""
    if not plan_id or not plan_id.strip():
        return {
            "success": False,
            "action": "approve",
            "error": "plan_id is required and must be non-empty",
        }

    plan = _load_plan(plan_id)
    if not plan:
        return {
            "success": False,
            "action": "approve",
            "plan_id": plan_id,
            "error": f"Plan {plan_id} not found",
        }

    # Update plan status
    plan["status"] = "approved"
    plan["approval_note"] = note
    _save_plan(plan_id, plan)

    # Write audit record
    _write_audit_record("approved", plan_id, note)

    # Fetch updated audit trail
    audit_trail = _get_plan_audit_trail(plan_id)

    logger.info("plan_approved plan_id=%s note_preview=%s", plan_id, note[:50])

    return {
        "success": True,
        "action": "approve",
        "plan_id": plan_id,
        "plan": plan,
        "audit_trail": audit_trail,
    }


async def _action_reject(plan_id: str, note: str) -> dict[str, Any]:
    """Reject a plan and record the decision."""
    if not plan_id or not plan_id.strip():
        return {
            "success": False,
            "action": "reject",
            "error": "plan_id is required and must be non-empty",
        }

    plan = _load_plan(plan_id)
    if not plan:
        return {
            "success": False,
            "action": "reject",
            "plan_id": plan_id,
            "error": f"Plan {plan_id} not found",
        }

    # Update plan status
    plan["status"] = "rejected"
    plan["rejection_note"] = note
    _save_plan(plan_id, plan)

    # Write audit record
    _write_audit_record("rejected", plan_id, note)

    # Fetch updated audit trail
    audit_trail = _get_plan_audit_trail(plan_id)

    logger.info("plan_rejected plan_id=%s note_preview=%s", plan_id, note[:50])

    return {
        "success": True,
        "action": "reject",
        "plan_id": plan_id,
        "plan": plan,
        "audit_trail": audit_trail,
    }


async def _action_status(plan_id: str) -> dict[str, Any]:
    """Retrieve a plan and its audit trail."""
    if not plan_id or not plan_id.strip():
        return {
            "success": False,
            "action": "status",
            "error": "plan_id is required and must be non-empty",
        }

    plan = _load_plan(plan_id)
    if not plan:
        return {
            "success": False,
            "action": "status",
            "plan_id": plan_id,
            "error": f"Plan {plan_id} not found",
        }

    audit_trail = _get_plan_audit_trail(plan_id)

    logger.info("plan_status_retrieved plan_id=%s status=%s", plan_id, plan.get("status"))

    return {
        "success": True,
        "action": "status",
        "plan_id": plan_id,
        "plan": plan,
        "audit_trail": audit_trail,
    }


async def _action_list() -> dict[str, Any]:
    """List all plans with truncated goals and status summaries."""
    _ensure_plans_dir()
    plans_list: list[dict[str, Any]] = []

    try:
        for plan_file in sorted(_PLANS_DIR.glob("plan_*.json")):
            try:
                plan = json.loads(plan_file.read_text(encoding="utf-8"))
                plans_list.append(
                    {
                        "plan_id": plan.get("plan_id", "unknown"),
                        "goal": plan.get("goal", "")[:100],  # Truncate
                        "overall_risk": plan.get("overall_risk", "UNKNOWN"),
                        "status": plan.get("status", "unknown"),
                        "step_count": plan.get("step_count", 0),
                        "created_at": plan.get("created_at", ""),
                    }
                )
            except Exception as e:
                logger.warning("plan_list_skip file=%s error=%s", plan_file.name, str(e)[:50])

    except Exception as e:
        logger.error("plan_list_error error=%s", str(e)[:100])

    logger.info("plan_list_retrieved count=%d", len(plans_list))

    return {
        "success": True,
        "action": "list",
        "plans": plans_list,
        "count": len(plans_list),
    }


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
