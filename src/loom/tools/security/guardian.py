"""Guardian AI defensive-safety evaluator.

Mirrors PocketPaw's Guardian pattern: a secondary LLM that evaluates
proposed actions (commands, tool-calls, payloads) for safety BEFORE execution.

Provides:
  - research_guardian_check: Assess threat level of proposed action

Key features:
  - 5-tier threat classification: NONE, LOW, MEDIUM, HIGH, CRITICAL
  - Threat categories: destructive, exfil, injection, obfuscation, fork_bomb
  - Fail-closed posture: on uncertainty, lean toward blocking
  - Heuristic fallback: regex patterns for destructive/exfil ops when LLM unavailable
  - Mode support: "auto" (LLM + fallback), "regex" (offline only), "llm" (LLM only)
  - Score (0-10) and recommendation (allow/review/block)
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

# ============================================================================
# Threat Taxonomy: 5 Levels + 5 Categories
# ============================================================================
# THREAT LEVELS (0-5 scale):
#   - NONE (0): Safe, no security concern
#   - LOW (2): Minor risk, acceptable in most contexts (logging, benign tools)
#   - MEDIUM (5): Moderate risk, requires authorization (external API calls, file I/O)
#   - HIGH (7): Dangerous, should be reviewed carefully (creds exfil, destructive ops)
#   - CRITICAL (10): Extremely dangerous, should be blocked (fork bombs, rm -rf /)
#
# THREAT CATEGORIES (classify which risk applies):
#   - destructive: File/system destruction (rm -rf, mkfs, DROP TABLE, format)
#   - exfil: Credential exfiltration (API keys, SSH keys, env vars)
#   - injection: Command/shell injection (pipe to sh/bash, eval, code exec)
#   - obfuscation: Obfuscated execution (base64 pipe, binary encoding)
#   - fork_bomb: Resource exhaustion (fork bombs, kernel panic)

_THREAT_LEVEL_SCORES = {
    "NONE": 0,
    "LOW": 2,
    "MEDIUM": 5,
    "HIGH": 7,
    "CRITICAL": 10,
}

_CATEGORY_DESCRIPTIONS = {
    "destructive": "File/system destruction (rm -rf, mkfs, DROP TABLE, format)",
    "exfil": "Credential exfiltration (API keys, SSH keys, env vars)",
    "injection": "Command/shell injection (pipe to sh/bash, eval)",
    "obfuscation": "Obfuscated execution (base64, encoding, binary)",
    "fork_bomb": "Resource exhaustion (fork bombs, kernel panic)",
}

# Dangerous patterns for heuristic fallback (regex, compiled once)
_DANGEROUS_PATTERNS = [
    # Destructive file/system operations
    (r"rm\s+-.*rf\s+/", "destructive", "destructive_rm_rf_root"),
    (r"rm\s+-rf\s*\*", "destructive", "destructive_rm_rf_wildcard"),
    (r"mkfs\.", "destructive", "destructive_mkfs"),
    (r"dd\s+if=|dd\s+of=", "destructive", "destructive_dd"),
    (r"format\s+[A-Z]:", "destructive", "destructive_format_windows"),
    (r"DROP\s+TABLE", "destructive", "destructive_sql_drop"),
    (r"TRUNCATE\s+TABLE", "destructive", "destructive_sql_truncate"),
    # Shell injection / command chaining with shell invocation
    (r"\|\s*sh\b", "injection", "shell_injection_pipe_sh"),
    (r"\|\s*bash\b", "injection", "shell_injection_pipe_bash"),
    (r"\|\s*/bin/", "injection", "shell_injection_pipe_bin"),
    (r"&&\s*sh\b", "injection", "shell_injection_and_sh"),
    (r";\s*python", "injection", "shell_injection_python"),
    (r";\s*perl", "injection", "shell_injection_perl"),
    (r"eval\s*\(", "injection", "code_injection_eval"),
    (r"exec\s*\(", "injection", "code_injection_exec"),
    # Base64 decode piped to shell
    (r"base64\s+-d\s*\|", "obfuscation", "obfuscation_base64_pipe"),
    (r"base64\s+-D\s*\|", "obfuscation", "obfuscation_base64_pipe_macos"),
    # Secret exfiltration (API keys, credentials)
    (r"curl.*-H\s+['\"]Authorization", "exfil", "exfil_auth_header"),
    (r"curl.*-H\s+['\"]X-API-Key", "exfil", "exfil_api_key_header"),
    (r"ssh\s+-i\s+/root/.ssh", "exfil", "exfil_ssh_root_key"),
    (r"ssh\s+-i\s+/home/.*/.ssh", "exfil", "exfil_ssh_user_key"),
    (r"AWS_ACCESS_KEY_ID=", "exfil", "exfil_aws_key_env"),
    (r"STRIPE_API_KEY=", "exfil", "exfil_stripe_key_env"),
    (r"sk-[A-Za-z0-9]{40,}", "exfil", "exfil_openai_key"),
    (r"AKIA[0-9A-Z]{16}", "exfil", "exfil_aws_key"),
    # Fork bombs
    (r":\(\)\s*\{.*:\|:&", "fork_bomb", "fork_bomb"),
    # Kernel panic / system halt
    (r"echo\s+['\"]1['\"].*kd\.", "fork_bomb", "kernel_panic"),
    (r"halt\s+-f", "fork_bomb", "force_halt"),
    (r"poweroff\s+-f", "fork_bomb", "force_poweroff"),
]
_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), category, name)
    for pattern, category, name in _DANGEROUS_PATTERNS
]


def _classify_categories(action: str) -> list[str]:
    """Classify which threat categories apply to an action.

    Returns list of category names (destructive, exfil, injection, obfuscation, fork_bomb).
    """
    categories_found = set()
    for compiled_pattern, category, _ in _COMPILED_PATTERNS:
        if compiled_pattern.search(action):
            categories_found.add(category)
    return sorted(list(categories_found))


def _local_safety_check(
    action: str,
) -> tuple[Literal["CRITICAL", "HIGH", "NONE"], list[str], str]:
    """Heuristic deny-by-default check.

    Returns (threat_level, categories, reason) for any action matching a dangerous pattern.
    Used when LLM backend unavailable or in regex mode.

    Threat level mapping:
      - Destructive or injection: CRITICAL
      - Exfil or obfuscation or fork_bomb: HIGH
      - No match: NONE
    """
    categories = _classify_categories(action)

    if not categories:
        return "NONE", [], "Allowed by local safety check (no dangerous pattern matched)"

    # Map categories to threat level
    if "destructive" in categories or "injection" in categories:
        threat = "CRITICAL"
    else:
        threat = "HIGH"

    reason = f"Heuristic match: {', '.join(categories)}"
    logger.warning(
        "local_safety_check matched categories=%s action_preview=%s",
        categories,
        truncate(action, 100),
    )
    return threat, categories, reason


def _threat_to_recommendation(
    threat_level: str, fail_closed: bool
) -> Literal["allow", "review", "block"]:
    """Convert threat level to recommendation.

    Maps:
      - NONE -> "allow"
      - LOW -> "review" (fail_closed) or "allow"
      - MEDIUM -> "review"
      - HIGH -> "block" (fail_closed) or "review"
      - CRITICAL -> "block"
    """
    if threat_level == "NONE":
        return "allow"
    elif threat_level == "LOW":
        return "review" if fail_closed else "allow"
    elif threat_level == "MEDIUM":
        return "review"
    elif threat_level == "HIGH":
        return "block" if fail_closed else "review"
    else:  # CRITICAL
        return "block"


@handle_tool_errors("research_guardian_check")
async def research_guardian_check(
    action: str = "",
    content: str = "",
    context: str = "",
    mode: str = "auto",
    tool_name: str = "",
    judge_model: str = "auto",
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Evaluate threat level of a proposed action.

    Mirrors PocketPaw Guardian AI: a secondary LLM safety evaluator for
    commands, tool-calls, or payloads. Returns a threat classification
    (NONE/LOW/MEDIUM/HIGH/CRITICAL) with threat categories and a recommendation.

    **Fail-Closed Logic:**
    When `fail_closed=True` and the LLM is uncertain or errors, this tool
    biases toward blocking high-risk actions.

    **Heuristic Fallback:**
    If the LLM judge is unavailable (or mode="regex"), regex patterns check
    for destructive shell commands, secret exfiltration, and injection attacks.
    This ensures a verdict even offline.

    **Modes:**
    - "auto": LLM first, heuristic fallback if LLM fails
    - "regex": Offline heuristic check only (fast, no network)
    - "llm": LLM only (raises if unavailable)

    Args:
        action: The proposed command/tool-call/payload to assess (alias: content).
        context: Optional surrounding context or user intent (helps LLM judge).
        mode: "auto" | "regex" | "llm" (default "auto").
        tool_name: Optional name of the tool being called (e.g. "research_fetch").
        judge_model: LLM model for safety judgment ("auto" selects default).
        fail_closed: On uncertainty/error, bias toward blocking HIGH/CRITICAL
                    actions (default True).

    Returns:
        {
            "action": str (truncated preview, max 100 chars),
            "tool_name": str,
            "threat_level": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
            "score": int (0-10 scale),
            "categories": list[str] (e.g. ["exfil", "injection"]),
            "recommendation": "allow" | "review" | "block",
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
        >>> result["recommendation"]
        "block"
    """
    # `content` is an accepted alias for `action` — coalesce so callers can use either.
    action = action or content
    # Cap action length to prevent context-overflow attacks
    action = action[: _MAX_ACTION_LENGTH]
    action_preview = truncate(action, 100)

    # Offline regex-only mode: skip LLM entirely
    if mode == "regex":
        heuristic_threat, categories, heuristic_reason = _local_safety_check(action)
        score = _THREAT_LEVEL_SCORES.get(heuristic_threat, 0)
        recommendation = _threat_to_recommendation(heuristic_threat, fail_closed)
        logger.info(
            "guardian_regex_check action_preview=%s threat=%s score=%d",
            action_preview,
            heuristic_threat,
            score,
        )
        return {
            "action": action_preview,
            "tool_name": tool_name,
            "threat_level": heuristic_threat,
            "score": score,
            "categories": categories,
            "recommendation": recommendation,
            "reason": heuristic_reason,
            "method": "heuristic",
            "judge_model": "offline",
        }

    # Attempt LLM-based safety judgment (mode="auto" or "llm")
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

Identify threat categories that apply (any of):
- destructive: File/system destruction
- exfil: Credential exfiltration
- injection: Command/shell injection
- obfuscation: Obfuscated execution
- fork_bomb: Resource exhaustion

Respond with a JSON object ONLY (no markdown, no explanation outside the JSON):
{{
  "threat_level": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "categories": ["destructive", "exfil", ...],
  "reason": "One-line justification"
}}

If you cannot classify, default to CRITICAL with empty categories."""

        llm_response = await _call_with_cascade(
            messages=[{"role": "user", "content": llm_prompt}],
            model=judge_model,
            max_tokens=300,
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
            categories = parsed.get("categories", [])
            reason = parsed.get("reason", "LLM judgment")

            # Validate threat level (fail-closed)
            if threat_level not in _VALID_THREAT_LEVELS:
                threat_level = "CRITICAL"
                reason = f"Invalid LLM threat level {parsed.get('threat_level')!r}; defaulting to CRITICAL"

            score = _THREAT_LEVEL_SCORES.get(threat_level, 10)
            recommendation = _threat_to_recommendation(threat_level, fail_closed)

            logger.info(
                "guardian_llm_check action_preview=%s threat=%s score=%d categories=%s",
                action_preview,
                threat_level,
                score,
                categories,
            )
            return {
                "action": action_preview,
                "tool_name": tool_name,
                "threat_level": threat_level,
                "score": score,
                "categories": categories,
                "recommendation": recommendation,
                "reason": reason,
                "method": "llm",
                "judge_model": judge_model,
            }
        else:
            llm_error = "Empty LLM response"

    except Exception as e:
        llm_error = str(e)
        if mode == "llm":
            # LLM-only mode: re-raise
            logger.error("guardian_llm_check failed in llm-only mode: %s", llm_error)
            raise
        logger.warning(
            "guardian_llm_check failed, falling back to heuristic: %s", llm_error
        )

    # Heuristic fallback (mode="auto" with LLM error)
    heuristic_threat, categories, heuristic_reason = _local_safety_check(action)
    score = _THREAT_LEVEL_SCORES.get(heuristic_threat, 0)
    recommendation = _threat_to_recommendation(heuristic_threat, fail_closed)

    # Fail-closed: if LLM errored and heuristic found nothing, block with LOW
    if llm_error and heuristic_threat == "NONE" and fail_closed:
        heuristic_threat = "LOW"
        score = _THREAT_LEVEL_SCORES["LOW"]
        recommendation = "review"
        heuristic_reason = (
            "LLM unavailable and heuristic inconclusive; fail-closed: recommend review"
        )

    logger.info(
        "guardian_heuristic_check action_preview=%s threat=%s score=%d categories=%s llm_error=%s",
        action_preview,
        heuristic_threat,
        score,
        categories,
        "yes" if llm_error else "no",
    )

    return {
        "action": action_preview,
        "tool_name": tool_name,
        "threat_level": heuristic_threat,
        "score": score,
        "categories": categories,
        "recommendation": recommendation,
        "reason": heuristic_reason,
        "method": "heuristic",
        "judge_model": "fallback",
    }
