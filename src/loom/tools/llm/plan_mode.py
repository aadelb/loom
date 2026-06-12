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
import hashlib
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
_VALID_ACTIONS = frozenset({"plan", "approve", "reject", "status", "list", "revise", "execute", "complete_step", "rollback"})


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


def _generate_plan_id(goal: str, salt: str = "") -> str:
    """Generate a stable plan_id from the goal.

    Uses SHA-256, which is stable across processes — unlike the builtin ``hash()``,
    which is salted per-process via PYTHONHASHSEED (so the old "deterministic" id was
    not actually stable between restarts, and its 10**8 space risked birthday
    collisions). ``salt`` lets the caller mint a NEW id for the same goal when an
    existing plan must not be overwritten (see ``_action_plan``).
    """
    digest = hashlib.sha256((goal + salt).encode("utf-8")).hexdigest()
    return f"plan_{digest[:12]}"


# Statuses a plan must never be silently overwritten in — re-planning the same goal
# must not invalidate an approval or clobber an in-flight/finished run.
_LOCKED_STATUSES = frozenset({"approved", "executing", "completed", "failed"})


def _mint_plan_id(goal: str) -> str:
    """Return a plan_id for ``goal`` that does not clobber a locked plan.

    Re-uses the stable id when free or when the existing plan is still re-plannable
    (pending_approval / rejected). If a plan with that id is in a LOCKED state
    (approved/executing/completed/failed), salts a fresh id so the locked plan is
    preserved. Bounded retry guards against the pathological all-collide case.
    """
    plan_id = _generate_plan_id(goal)
    for attempt in range(1, 50):
        existing = _load_plan(plan_id)
        if not existing or existing.get("status") not in _LOCKED_STATUSES:
            return plan_id
        plan_id = _generate_plan_id(goal, salt=f"#{attempt}")
    # Extremely unlikely fallback: append a uuid suffix so we never overwrite.
    return f"{_generate_plan_id(goal)}-{uuid.uuid4().hex[:6]}"


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
    step_n: int = 0,
    step_result: str = "",
    step_state: str = "",
) -> dict[str, Any]:
    """Multi-action approval-gated planning with execution tracking and versioning.

    Implements PocketPaw's planning mode with approval/rejection/execution workflow:
    - "plan": LLM decomposes goal into steps, Guardian assesses risk per-step, DAG dependencies, plan persisted pending approval
    - "approve": Mark plan approved + audit record
    - "reject": Mark plan rejected + audit record
    - "status": Retrieve one plan + its full audit trail
    - "list": List all plans with goals, risks, statuses
    - "revise": Load approved plan, accept reviewer feedback, generate improved version (version+1)
    - "execute": Mark approved plan as executing (status=executing, steps.state=pending)
    - "complete_step": Mark step done/failed with result; enforces DAG order (deps must be done first);
                       returns next_steps (step numbers now unblocked); auto-completes plan when all steps finish
    - "rollback": Revert an executing plan back to approved (clears step states), so it can be revised and re-executed

    Plans are persisted to ~/.loom/plans/<plan_id>.json (atomically written).
    Approval decisions logged to ~/.loom/plans/_audit.jsonl (append-only).

    Args:
        action: One of "plan", "approve", "reject", "status", "list", "revise", "execute", "complete_step", "rollback".
        goal: (for action="plan") The task to plan.
        plan_id: (for approve/reject/status/revise/execute/complete_step) Plan ID to act on.
        note: (for approve/reject/revise) Reviewer's decision or feedback note.
        context: (for action="plan") Optional surrounding context/constraints.
        max_steps: (for action="plan") Max steps to decompose (1-20).
        model: (for action="plan") LLM model ("auto" = config default).
        auto_approve_threshold: (for action="plan") Threat level for auto-approval (NONE|LOW|MEDIUM|HIGH|CRITICAL).
        step_n: (for action="complete_step") Step number to mark as done (1-100).
        step_result: (for action="complete_step") Result/output of the completed step.
        step_state: (for action="complete_step") State: 'done' or 'failed'.

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
    elif action == "revise":
        return await _action_revise(plan_id, note, model)
    elif action == "execute":
        return await _action_execute(plan_id)
    elif action == "complete_step":
        return await _action_complete_step(plan_id, step_n, step_state, step_result)
    elif action == "rollback":
        return await _action_rollback(plan_id, note)
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

    # Stable plan_id from the goal, but never one that would overwrite an already
    # approved/executing/completed/failed plan (re-planning must not invalidate an approval).
    plan_id = _mint_plan_id(goal)

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
4. Declare its dependencies (which prior steps it depends on, if any)

Respond ONLY with a JSON array of objects. Each object must have exactly these keys:
- "n": step number (1, 2, 3, ...)
- "action": what to do (short description)
- "tool": which tool/command (e.g., "research_fetch", "bash rm", "python script")
- "depends_on": list of step numbers this step depends on (e.g., [1], [1, 2], or [] for independent)

Example format:
[
  {{"n": 1, "action": "fetch data from API", "tool": "research_fetch", "depends_on": []}},
  {{"n": 2, "action": "parse JSON response", "tool": "python json.loads", "depends_on": [1]}},
  {{"n": 3, "action": "write to file", "tool": "bash tee", "depends_on": [2]}}
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
                        depends_on = step.get("depends_on", [])
                        if not isinstance(depends_on, list):
                            depends_on = []
                        steps_list.append(
                            {
                                "n": step.get("n", len(steps_list) + 1),
                                "action": str(step.get("action", ""))[:200],
                                "tool": str(step.get("tool", ""))[:100],
                                "depends_on": depends_on,
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
                "depends_on": [],
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

    # STEP 3: Compute approval gate (using per-step risk_level from Guardian)
    # Threat threshold as numeric value
    threshold_order = _order_threat_levels(auto_approve_threshold)

    # Determine overall risk (max risk across all steps)
    overall_risk = "NONE"
    if final_steps:
        max_risk_order = max(
            _order_threat_levels(step.get("risk_level", "NONE"))
            for step in final_steps
        )
        # Reverse map from order to threat level
        for threat, order in _THREAT_LEVEL_ORDER.items():
            if order == max_risk_order:
                overall_risk = threat
                break

    # Compute execution layers (topological sort by depends_on)
    execution_layers, has_cycle = _topological_sort(final_steps)

    # Determine requires_approval
    requires_approval = False
    for step in final_steps:
        risk_order = _order_threat_levels(step.get("risk_level", "NONE"))

        # Require approval if: risk exceeds threshold
        if risk_order > threshold_order:
            requires_approval = True
            break

    # Auto-approvable: all steps are at/below threshold
    auto_approvable = all(
        _order_threat_levels(step.get("risk_level", "NONE")) <= threshold_order
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
        "status": "pending_approval",  # Will change to approved/rejected/executing/completed
        "version": 1,  # For tracking revisions
        "revision_history": [],  # Stores old versions on revise
        "execution_layers": execution_layers,  # Steps that can run in parallel per layer
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

    # Build a focused progress view so callers don't have to parse the full plan blob.
    # Includes: per-step state summary, which steps are now runnable (deps satisfied),
    # which are blocked (deps not done), and what's failed.
    steps = plan.get("steps", [])
    step_states: dict[int, str] = {s.get("n", 0): s.get("state", "pending") for s in steps}
    done_set = {n for n, st in step_states.items() if st == "done"}

    progress_steps = []
    next_runnable: list[int] = []
    blocked: list[int] = []
    for s in steps:
        n = s.get("n", 0)
        st = s.get("state", "pending")
        deps = [d for d in s.get("depends_on", []) if isinstance(d, int)]
        deps_done = all(step_states.get(d) == "done" for d in deps)
        entry: dict[str, Any] = {
            "n": n,
            "action": s.get("action", "")[:80],
            "state": st,
            "risk_level": s.get("risk_level", "NONE"),
            "depends_on": deps,
            "deps_satisfied": deps_done,
        }
        if st == "pending" and deps_done:
            next_runnable.append(n)
        elif st == "pending" and not deps_done:
            blocked.append(n)
        progress_steps.append(entry)

    progress = {
        "status": plan.get("status"),
        "done": sum(1 for s in steps if s.get("state") == "done"),
        "failed": sum(1 for s in steps if s.get("state") == "failed"),
        "pending": sum(1 for s in steps if s.get("state") == "pending"),
        "total": len(steps),
        "next_runnable": next_runnable,
        "blocked_on_deps": blocked,
        "steps": progress_steps,
    }

    logger.info("plan_status_retrieved plan_id=%s status=%s", plan_id, plan.get("status"))

    return {
        "success": True,
        "action": "status",
        "plan_id": plan_id,
        "plan": plan,
        "progress": progress,
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
    """Risk-assess a single step via Guardian tool (regex mode = offline).

    Args:
        step: The step dict with n, action, tool.
        goal: The original goal (for Guardian context).
        context: Optional surrounding context.

    Returns:
        Step dict with risk_level, risk_categories added (not threat_level for backwards compat).
    """
    try:
        from loom.tools.security.guardian import research_guardian_check

        action = step.get("action", "")
        tool_name = step.get("tool", "")

        # Construct context for Guardian
        guardian_context = f"Goal: {goal}"
        if context:
            guardian_context += f"\nEnvironment: {context}"

        # Guardian in "auto" mode (LLM + regex fallback): plan steps are PROSE
        # descriptions ("delete old temp files with rm"), not literal shell commands,
        # so regex-only scores them NONE — a dangerous false-safe for a gating tool.
        # The LLM judge reads the intent; regex still backstops if the LLM is down.
        # All steps are assessed concurrently (asyncio.gather) so latency stays bounded.
        guardian_result = await research_guardian_check(
            action=action,
            context=guardian_context,
            tool_name=tool_name,
            mode="auto",
            fail_closed=True,
        )

        # Extract verdict from Guardian
        risk_level = guardian_result.get("threat_level", "HIGH")
        risk_categories = guardian_result.get("categories", [])
        reason = guardian_result.get("reason", "Guardian assessment")

        # Validate threat level
        if risk_level not in _VALID_THREAT_LEVELS:
            risk_level = "HIGH"

        result = dict(step)
        result["risk_level"] = risk_level
        result["risk_categories"] = risk_categories
        result["reason"] = reason
        result["depends_on"] = step.get("depends_on", [])  # Preserve depends_on if present

        logger.debug(
            "plan_step_assessed n=%s action_preview=%s risk=%s categories=%s",
            step.get("n"),
            action[:40],
            risk_level,
            risk_categories,
        )

        return result

    except Exception as e:
        # Guardian failed; return step with HIGH risk, fail-closed
        logger.error(
            "plan_step_guardian_error n=%s error=%s",
            step.get("n"),
            str(e)[:100],
        )
        result = dict(step)
        result["risk_level"] = "HIGH"
        result["risk_categories"] = ["unknown"]
        result["reason"] = f"Guardian check failed: {str(e)[:80]}"
        result["depends_on"] = step.get("depends_on", [])
        return result


def _topological_sort(steps: list[dict[str, Any]]) -> tuple[list[list[int]], bool]:
    """Topologically sort steps by depends_on; return execution layers + cycle flag.

    Args:
        steps: List of step dicts with 'n' and 'depends_on' keys.

    Returns:
        (execution_layers, has_cycle) where execution_layers is list of lists of step numbers
        that can run in parallel (each layer depends on prior layers), and has_cycle is True
        if a cycle was detected (fallback to sequential).
    """
    if not steps:
        return [], False

    # Build dependency graph and in-degree map
    in_degree: dict[int, int] = {}
    graph: dict[int, list[int]] = {}  # graph[n] = list of steps that depend on n

    # Initialize all steps
    for step in steps:
        n = step.get("n", 0)
        depends_on = step.get("depends_on", [])
        if not isinstance(depends_on, list):
            depends_on = []
        in_degree[n] = len(depends_on)
        if n not in graph:
            graph[n] = []

    # Build adjacency: if step A depends on B, then B -> A
    for step in steps:
        n = step.get("n", 0)
        depends_on = step.get("depends_on", [])
        if not isinstance(depends_on, list):
            depends_on = []
        for dep in depends_on:
            if dep not in graph:
                graph[dep] = []
            graph[dep].append(n)

    # Kahn's algorithm for topological sort (detect cycles)
    queue = [n for n in in_degree if in_degree[n] == 0]
    topo_order = []
    processed_count = 0

    while queue:
        queue.sort()  # Deterministic order
        layer = list(queue)
        topo_order.append(layer)
        processed_count += len(layer)

        next_queue = []
        for n in layer:
            for dependent in graph.get(n, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    next_queue.append(dependent)

        queue = next_queue

    # If not all steps processed, there's a cycle
    has_cycle = processed_count < len(steps)

    if has_cycle:
        logger.warning("plan_cycle_detected_fallback_sequential step_count=%d", len(steps))
        # Fallback to sequential (each step depends on previous)
        all_steps = [step.get("n", i + 1) for i, step in enumerate(steps)]
        return [[n] for n in all_steps], True

    return topo_order, False


async def _action_rollback(plan_id: str, note: str) -> dict[str, Any]:
    """Revert an executing plan back to approved so it can be revised or re-executed.

    Clears per-step state (back to 'pending') and removes execution timestamps.
    Only valid when status == 'executing' — safe to call after a failed step
    when you want to revise the plan rather than abandon it.
    """
    if not plan_id or not plan_id.strip():
        return {"success": False, "action": "rollback", "error": "plan_id is required"}

    plan = _load_plan(plan_id)
    if not plan:
        return {"success": False, "action": "rollback", "plan_id": plan_id,
                "error": f"Plan {plan_id} not found"}

    current_status = plan.get("status")
    if current_status not in ("executing", "failed"):
        return {
            "success": False,
            "action": "rollback",
            "plan_id": plan_id,
            "error": (
                f"Cannot rollback plan with status '{current_status}'; "
                "rollback is only valid for status 'executing' or 'failed'"
            ),
        }

    # Snapshot current state into revision_history before clearing
    snapshot = {
        "rolled_back_from_status": current_status,
        "rolled_back_at": datetime.utcnow().isoformat(),
        "note": note,
        "step_states": {str(s.get("n")): s.get("state", "pending") for s in plan.get("steps", [])},
    }
    plan.setdefault("rollback_history", []).append(snapshot)

    # Clear per-step execution state
    for step in plan.get("steps", []):
        step["state"] = "pending"
        step.pop("result", None)
        step.pop("completed_at", None)

    plan["status"] = "approved"
    plan["last_updated"] = datetime.utcnow().isoformat()
    plan.pop("execution_started_at", None)
    plan.pop("execution_completed_at", None)

    _save_plan(plan_id, plan)
    _write_audit_record("rollback", plan_id, note or f"rolled back from {current_status}")

    logger.info("plan_rolled_back plan_id=%s from_status=%s", plan_id, current_status)

    return {
        "success": True,
        "action": "rollback",
        "plan_id": plan_id,
        "plan": plan,
        "message": (
            f"Plan rolled back from '{current_status}' to 'approved'. "
            "All step states cleared. Use 'revise' to update steps, or 'execute' to re-run as-is."
        ),
    }


async def _action_revise(plan_id: str, note: str, model: str) -> dict[str, Any]:
    """Revise a plan: load plan, accept feedback, generate improved version.

    Only allowed if plan status is pending_approval or approved. Creates version+1,
    stores old steps in revision_history, resets status to pending_approval.
    """
    if not plan_id or not plan_id.strip():
        return {
            "success": False,
            "action": "revise",
            "error": "plan_id is required and must be non-empty",
        }

    plan = _load_plan(plan_id)
    if not plan:
        return {
            "success": False,
            "action": "revise",
            "plan_id": plan_id,
            "error": f"Plan {plan_id} not found",
        }

    if plan.get("status") not in ("pending_approval", "approved"):
        return {
            "success": False,
            "action": "revise",
            "plan_id": plan_id,
            "error": f"Cannot revise plan with status {plan.get('status')}; must be pending_approval or approved",
        }

    # Extract current plan info
    goal = plan.get("goal", "")
    old_steps = plan.get("steps", [])
    old_version = plan.get("version", 1)
    new_version = old_version + 1

    # Initialize revision_history if not present
    if "revision_history" not in plan:
        plan["revision_history"] = []

    # Store old version
    plan["revision_history"].append({
        "version": old_version,
        "steps": old_steps,
        "stored_at": datetime.utcnow().isoformat(),
    })

    # Call LLM to revise plan
    try:
        from loom.tools.llm.llm import _call_with_cascade

        # Build step summary for LLM
        step_summary = "\n".join(
            f"{i+1}. {step.get('action', '')} (risk: {step.get('risk_level', 'UNKNOWN')})"
            for i, step in enumerate(old_steps[:10])
        )

        revise_prompt = f"""You are a planning AI. The user has provided feedback on a draft plan.
Revise and improve the plan based on the feedback.

Original goal: {goal}

Current steps:
{step_summary}

Reviewer feedback: {note}

Generate an improved plan. Each step should include:
- "n": step number (1, 2, 3, ...)
- "action": what to do
- "tool": which tool/command
- "depends_on": list of step numbers this step depends on (e.g., [1] for sequential, [] for independent)

Respond ONLY with a JSON array of step objects. No markdown or extra text."""

        response = await _call_with_cascade(
            messages=[{"role": "user", "content": revise_prompt}],
            model=model,
            max_tokens=1500,
            temperature=0.2,
            timeout=30,
        )

        parsed_steps = None
        if response and response.text:
            parsed_steps = _parse_plan_json(response.text)

        if not parsed_steps or not isinstance(parsed_steps, list):
            return {
                "success": False,
                "action": "revise",
                "plan_id": plan_id,
                "error": "Failed to parse revised plan from LLM",
            }

        # Normalize steps and add depends_on
        revised_steps = []
        for step in parsed_steps:
            if isinstance(step, dict):
                revised_steps.append({
                    "n": step.get("n", len(revised_steps) + 1),
                    "action": str(step.get("action", ""))[:200],
                    "tool": str(step.get("tool", ""))[:100],
                    "depends_on": step.get("depends_on", []),
                })

    except Exception as e:
        logger.error("plan_revise_llm_error error=%s", str(e)[:100])
        return {
            "success": False,
            "action": "revise",
            "plan_id": plan_id,
            "error": f"Revision failed: {str(e)[:100]}",
        }

    # Risk-assess revised steps
    guardian_tasks = []
    for step in revised_steps:
        task = _assess_step_risk(step, goal, "")
        guardian_tasks.append(task)

    assessed_steps = await asyncio.gather(*guardian_tasks, return_exceptions=True)

    final_steps = []
    for i, result in enumerate(assessed_steps):
        if isinstance(result, dict):
            final_steps.append(result)
        elif isinstance(result, Exception):
            if i < len(revised_steps):
                step = revised_steps[i]
                final_steps.append({
                    "n": step.get("n", i + 1),
                    "action": step.get("action", ""),
                    "tool": step.get("tool", ""),
                    "risk_level": "HIGH",
                    "risk_categories": ["unknown"],
                    "reason": f"Guardian assessment failed: {str(result)[:80]}",
                    "depends_on": step.get("depends_on", []),
                })

    # Compute overall risk
    overall_risk = "NONE"
    if final_steps:
        max_risk_order = max(
            _order_threat_levels(step.get("risk_level", "NONE"))
            for step in final_steps
        )
        for threat, order in _THREAT_LEVEL_ORDER.items():
            if order == max_risk_order:
                overall_risk = threat
                break

    # Compute execution layers
    execution_layers, has_cycle = _topological_sort(final_steps)

    # Update plan
    plan["version"] = new_version
    plan["steps"] = final_steps
    plan["overall_risk"] = overall_risk
    plan["execution_layers"] = execution_layers
    plan["status"] = "pending_approval"  # Reset for re-approval
    plan["revision_note"] = note

    _save_plan(plan_id, plan)
    _write_audit_record("revised", plan_id, f"v{new_version}: {note}")

    logger.info(
        "plan_revised plan_id=%s version=%d old_version=%d step_count=%d",
        plan_id, new_version, old_version, len(final_steps),
    )

    return {
        "success": True,
        "action": "revise",
        "plan_id": plan_id,
        "plan": plan,
    }


async def _action_execute(plan_id: str) -> dict[str, Any]:
    """Mark an approved plan as executing: status=executing, steps.state=pending."""
    if not plan_id or not plan_id.strip():
        return {
            "success": False,
            "action": "execute",
            "error": "plan_id is required and must be non-empty",
        }

    plan = _load_plan(plan_id)
    if not plan:
        return {
            "success": False,
            "action": "execute",
            "plan_id": plan_id,
            "error": f"Plan {plan_id} not found",
        }

    if plan.get("status") != "approved":
        return {
            "success": False,
            "action": "execute",
            "plan_id": plan_id,
            "error": f"Cannot execute plan with status {plan.get('status')}; must be 'approved'",
        }

    # Initialize step states
    for step in plan.get("steps", []):
        step["state"] = "pending"
        step["result"] = ""

    plan["status"] = "executing"
    plan["execution_started_at"] = datetime.utcnow().isoformat()

    _save_plan(plan_id, plan)
    _write_audit_record("execution_started", plan_id, "")

    logger.info("plan_execute_started plan_id=%s step_count=%d", plan_id, len(plan.get("steps", [])))

    return {
        "success": True,
        "action": "execute",
        "plan_id": plan_id,
        "plan": plan,
    }


async def _action_complete_step(plan_id: str, step_n: int, step_state: str, step_result: str) -> dict[str, Any]:
    """Mark a step as done or failed; auto-complete plan if all steps done."""
    if not plan_id or not plan_id.strip():
        return {
            "success": False,
            "action": "complete_step",
            "error": "plan_id is required and must be non-empty",
        }

    if step_n <= 0 or step_n > 100:
        return {
            "success": False,
            "action": "complete_step",
            "error": "step_n must be between 1 and 100",
        }

    if step_state not in ("done", "failed"):
        return {
            "success": False,
            "action": "complete_step",
            "error": "step_state must be 'done' or 'failed'",
        }

    plan = _load_plan(plan_id)
    if not plan:
        return {
            "success": False,
            "action": "complete_step",
            "plan_id": plan_id,
            "error": f"Plan {plan_id} not found",
        }

    if plan.get("status") != "executing":
        return {
            "success": False,
            "action": "complete_step",
            "plan_id": plan_id,
            "error": f"Cannot complete step in plan with status {plan.get('status')}; must be 'executing'",
        }

    # Find the target step; enforce DAG order before accepting the update.
    steps = plan.get("steps", [])
    target_step = next((s for s in steps if s.get("n") == step_n), None)
    if target_step is None:
        return {
            "success": False,
            "action": "complete_step",
            "plan_id": plan_id,
            "error": f"Step {step_n} not found in plan",
        }

    # DAG enforcement: all depends_on steps must be "done" before this step can complete.
    # (A failed predecessor means this step may not run; caller should rollback+revise.)
    step_states: dict[int, str] = {s.get("n", 0): s.get("state", "pending") for s in steps}
    deps = [d for d in target_step.get("depends_on", []) if isinstance(d, int)]
    not_done_deps = [d for d in deps if step_states.get(d) != "done"]
    if not_done_deps and step_state == "done":
        return {
            "success": False,
            "action": "complete_step",
            "plan_id": plan_id,
            "error": (
                f"Step {step_n} depends on step(s) {not_done_deps} which are not yet 'done'. "
                "Complete prerequisite steps first, or use rollback+revise to reorder the plan."
            ),
        }

    # Apply the update
    target_step["state"] = step_state
    target_step["result"] = step_result
    target_step["completed_at"] = datetime.utcnow().isoformat()
    step_states[step_n] = step_state  # keep in sync for next_steps calc below

    # Auto-complete: all steps terminal → determine final plan status.
    # Bug fix: a plan where ALL steps failed must become "failed", not "completed".
    all_terminal = all(s.get("state") in ("done", "failed") for s in steps)
    if all_terminal:
        any_done = any(s.get("state") == "done" for s in steps)
        plan["status"] = "completed" if any_done else "failed"
        plan["execution_completed_at"] = datetime.utcnow().isoformat()

    # Compute which pending steps are now unblocked (all their deps are "done").
    done_set = {n for n, st in step_states.items() if st == "done"}
    next_steps: list[int] = [
        s["n"] for s in steps
        if s.get("state") == "pending"
        and all(d in done_set for d in s.get("depends_on", []) if isinstance(d, int))
    ]

    _save_plan(plan_id, plan)
    _write_audit_record("step_completed", plan_id, f"step {step_n} -> {step_state}")

    # Progress summary
    total_steps = len(steps)
    done_steps = sum(1 for s in steps if s.get("state") == "done")
    failed_steps = sum(1 for s in steps if s.get("state") == "failed")
    pending_steps = sum(1 for s in steps if s.get("state") == "pending")

    logger.info(
        "plan_step_completed plan_id=%s step_n=%d state=%s done=%d/%d failed=%d pending=%d next=%s",
        plan_id, step_n, step_state, done_steps, total_steps, failed_steps, pending_steps, next_steps,
    )

    return {
        "success": True,
        "action": "complete_step",
        "plan_id": plan_id,
        "plan": plan,
        "next_steps": next_steps,   # step numbers now runnable (deps satisfied)
        "progress": {
            "done": done_steps,
            "failed": failed_steps,
            "pending": pending_steps,
            "total": total_steps,
        },
    }
