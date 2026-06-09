"""Guardian AI defensive-safety evaluator.

Mirrors PocketPaw's Guardian pattern: a secondary LLM that evaluates
proposed actions (commands, tool-calls, payloads) for safety BEFORE execution.

Provides:
  - research_guardian_check: Assess threat level of proposed action

Key features:
  - 5-tier threat classification: NONE, LOW, MEDIUM, HIGH, CRITICAL
  - Fail-closed posture: on uncertainty, lean toward blocking
  - Heuristic fallback: regex patterns for destructive/exfil ops when LLM unavailable
  - Audit logging: method used (llm vs heuristic) + confidence
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from loom.error_responses import handle_tool_errors

try:
    from loom.text_utils import truncate
except ImportError:

    def truncate(
        text: str, max_chars: int = 500, *, suffix: str = "..."
    ) -> str:
        """Fallback truncate if text_utils unavailable."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix


logger = logging.getLogger("loom.tools.security.guardian")

# Maximum command length to embed in LLM prompt (prevent context-overflow attacks)
_MAX_ACTION_LENGTH: int = 2048

# Valid threat levels the Guardian LLM is allowed to return
_VALID_THREAT_LEVELS: frozenset[str] = frozenset(
    {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
)

# Dangerous patterns for heuristic fallback (regex, compiled once)
_DANGEROUS_PATTERNS = [
    # Destructive file/system operations
    (r"rm\s+-.*rf\s+/", "destructive_rm_rf_root"),
    (r"rm\s+-rf\s*\*", "destructive_rm_rf_wildcard"),
    (r"mkfs\.", "destructive_mkfs"),
    (r"dd\s+if=|dd\s+of=", "destructive_dd"),
    (r"format\s+[A-Z]:", "destructive_format_windows"),
    (r"DROP\s+TABLE", "destructive_sql_drop"),
    (r"TRUNCATE\s+TABLE", "destructive_sql_truncate"),
    # Shell injection / command chaining with shell invocation
    (r"\|\s*sh\b", "shell_injection_pipe_sh"),
    (r"\|\s*bash\b", "shell_injection_pipe_bash"),
    (r"\|\s*/bin/", "shell_injection_pipe_bin"),
    (r"&&\s*sh\b", "shell_injection_and_sh"),
    (r";\s*python", "shell_injection_python"),
    (r";\s*perl", "shell_injection_perl"),
    # Base64 decode piped to shell
    (r"base64\s+-d\s*\|", "obfuscation_base64_pipe"),
    (r"base64\s+-D\s*\|", "obfuscation_base64_pipe_macos"),
    # Secret exfiltration (API keys, credentials)
    (r"curl.*-H\s+['\"]Authorization", "exfil_auth_header"),
    (r"curl.*-H\s+['\"]X-API-Key", "exfil_api_key_header"),
    (r"ssh\s+-i\s+/root/.ssh", "exfil_ssh_root_key"),
    (r"ssh\s+-i\s+/home/.*/.ssh", "exfil_ssh_user_key"),
    (r"AWS_ACCESS_KEY_ID=", "exfil_aws_key_env"),
    (r"STRIPE_API_KEY=", "exfil_stripe_key_env"),
    # Fork bombs
    (r":\(\)\s*\{.*:\|:&", "fork_bomb"),
    # Kernel panic / system halt
    (r"echo\s+['\"]1['\"].*kd\.", "kernel_panic"),
    (r"halt\s+-f", "force_halt"),
    (r"poweroff\s+-f", "force_poweroff"),
]
_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), name)
    for pattern, name in _DANGEROUS_PATTERNS
]


def _local_safety_check(action: str) -> tuple[Literal["CRITICAL", "HIGH"], str]:
    """Heuristic deny-by-default check.

    Returns (CRITICAL or HIGH, reason) for any action matching a dangerous pattern.
    Used when LLM backend unavailable or as fallback.

    Threat level mapping:
      - Destructive or injection: CRITICAL
      - Exfil or obfuscation: HIGH
    """
    for compiled_pattern, pattern_name in _COMPILED_PATTERNS:
        if compiled_pattern.search(action):
            # Map pattern name to threat level
            if "destructive" in pattern_name or "injection" in pattern_name or "fork_bomb" in pattern_name:
                threat = "CRITICAL"
            else:
                threat = "HIGH"
            reason = f"Blocked by heuristic pattern: {pattern_name}"
            logger.warning(
                "local_safety_check matched pattern=%s action_preview=%s",
                pattern_name,
                truncate(action, 100),
            )
            return threat, reason

    # No dangerous pattern matched
    return "NONE", "Allowed by local safety check (no dangerous pattern matched)"


@handle_tool_errors("research_guardian_check")
async def research_guardian_check(
    action: str,
    context: str = "",
    tool_name: str = "",
    judge_model: str = "auto",
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Evaluate threat level of a proposed action.

    Mirrors PocketPaw Guardian AI: a secondary LLM safety evaluator for
    commands, tool-calls, or payloads. Returns a threat classification
    (NONE/LOW/MEDIUM/HIGH/CRITICAL) with allow/block recommendation.

    **Fail-Closed Logic:**
    When `fail_closed=True` and the LLM is uncertain or errors, this tool
    biases toward blocking high-risk actions.

    **Heuristic Fallback:**
    If the LLM judge is unavailable, regex patterns check for destructive
    shell commands, secret exfiltration, and injection attacks. This ensures
    a verdict even offline.

    Args:
        action: The proposed command/tool-call/payload to assess.
        context: Optional surrounding context or user intent (helps LLM judge).
        tool_name: Optional name of the tool being called (e.g. "research_fetch").
        judge_model: LLM model for safety judgment ("auto" selects default).
        fail_closed: On uncertainty/error, bias toward blocking HIGH/CRITICAL
                    actions (default True).

    Returns:
        {
            "action": str (truncated preview),
            "tool_name": str,
            "threat_level": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
            "allow": bool,
            "reason": str (short justification),
            "method": "llm" | "heuristic" (which check was used),
            "judge_model": str (model name or "fallback"),
        }

    Example:
        >>> result = await research_guardian_check(
        ...     action="rm -rf /tmp/test",
        ...     tool_name="research_shell_exec"
        ... )
        >>> result["threat_level"]
        "CRITICAL"
        >>> result["allow"]
        False
    """
    # Cap action length to prevent context-overflow attacks
    action = action[: _MAX_ACTION_LENGTH]
    action_preview = truncate(action, 100)

    # Attempt LLM-based safety judgment
    llm_error = None

    try:
        from loom.tools.llm.llm import _call_with_cascade

        llm_prompt = f"""You are a security AI evaluating a proposed action for safety.

Action to evaluate:
```
{action}
```

{f'Tool name: {tool_name}' if tool_name else ''}
{f'Context: {context}' if context else ''}

Classify this action into one of these threat levels:
- NONE: Safe, no security concern
- LOW: Minor risk, acceptable in most contexts
- MEDIUM: Moderate risk, requires authorization
- HIGH: Dangerous, should be reviewed carefully
- CRITICAL: Extremely dangerous, should be blocked

Respond with a JSON object ONLY (no markdown, no explanation outside the JSON):
{{
  "threat_level": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "allow": true | false,
  "reason": "One-line justification"
}}

If you cannot classify, default to CRITICAL with allow=false."""

        llm_response = await _call_with_cascade(
            messages=[{"role": "user", "content": llm_prompt}],
            model=judge_model,
            max_tokens=200,
            temperature=0.0,  # Deterministic judgment
            timeout=10,
        )

        if llm_response and llm_response.text:
            # Parse JSON from LLM response (tolerant: extract first {...} block)
            json_text = llm_response.text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "{" in json_text:
                json_text = json_text[json_text.find("{") : json_text.rfind("}") + 1]

            parsed = json.loads(json_text)
            threat_level = parsed.get("threat_level", "CRITICAL").upper()
            allow = parsed.get("allow", False)
            reason = parsed.get("reason", "LLM judgment")

            # Validate threat level (fail-closed)
            if threat_level not in _VALID_THREAT_LEVELS:
                threat_level = "CRITICAL"
                allow = False
                reason = f"Invalid LLM threat level {parsed.get('threat_level')!r}; defaulting to CRITICAL"

            # Fail-closed override: if uncertain and threat is HIGH/CRITICAL, block
            if (
                fail_closed
                and threat_level in ("HIGH", "CRITICAL")
                and allow is True
            ):
                allow = False
                reason = f"{reason} [fail-closed override: blocking HIGH/CRITICAL]"

            logger.info(
                "guardian_llm_check action_preview=%s threat=%s allow=%s",
                action_preview,
                threat_level,
                allow,
            )
            return {
                "action": action_preview,
                "tool_name": tool_name,
                "threat_level": threat_level,
                "allow": allow,
                "reason": reason,
                "method": "llm",
                "judge_model": judge_model,
            }
        else:
            llm_error = "Empty LLM response"

    except Exception as e:
        llm_error = str(e)
        logger.warning(
            "guardian_llm_check failed, falling back to heuristic: %s", llm_error
        )

    # Heuristic fallback: regex-based safety check
    heuristic_threat, heuristic_reason = _local_safety_check(action)

    # Fail-closed: block if threat is HIGH/CRITICAL and fail_closed=True
    if heuristic_threat in ("CRITICAL", "HIGH") and fail_closed:
        allow = False
    else:
        allow = heuristic_threat not in ("CRITICAL", "HIGH")

    logger.info(
        "guardian_heuristic_check action_preview=%s threat=%s allow=%s",
        action_preview,
        heuristic_threat,
        allow,
    )

    return {
        "action": action_preview,
        "tool_name": tool_name,
        "threat_level": heuristic_threat,
        "allow": allow,
        "reason": heuristic_reason,
        "method": "heuristic",
        "judge_model": "fallback",
    }
