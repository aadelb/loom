"""Sandboxed code detonation — static analysis without execution."""

from __future__ import annotations

import ast
import logging
import re
from typing import Any

from loom.billing import requires_tier

logger = logging.getLogger(__name__)

_CRITICAL = [
    (r"\beval\s*\(", "eval() — execution"),
    (r"\bexec\s*\(", "exec() — execution"),
    (r"\b__import__\s*\(", "__import__()"),
    (r"os\.system\s*\(", "os.system()"),
    (r"subprocess\.(run|Popen)", "subprocess"),
    (r"socket\.socket", "socket"),
    (r"requests\.get\s*\(", "requests"),
    (r"urllib\.request\.", "urllib"),
]
_HIGH = [
    (r"import\s+(os|sys|subprocess|socket|requests)", "High-risk imports"),
    (r"open\s*\(.*['\"]w", "File write"),
    (r"rmdir\s*\(|remove\s*\(|unlink\s*\(", "File delete"),
]
_MEDIUM = [
    (r"open\s*\(", "File I/O"),
    (r"pickle\.", "pickle"),
    (r"input\s*\(", "User input"),
]
_EXFIL = [
    (r"requests\.post\s*\(", "HTTP POST"),
    (r"socket\.send", "Socket send"),
    (r"sudo\s|os\.chmod.*0o777|os\.setuid", "Priv escalation"),
    (r"cron|crontab|launchd|\.plist|\.service", "Persistence"),
]


async def research_sandbox_analyze(
    code: str, language: str = "python", timeout_seconds: int = 10, allow_network: bool = False
) -> dict[str, Any]:
    """Static analysis of code for dangerous patterns (no execution).

    Returns: {syntax_valid, dangerous_patterns, exfiltration_vectors, risk_score, classification, safe_to_execute}
    """
    try:
        if language != "python":
            return {"error": f"Language '{language}' unsupported"}

        try:
            ast.parse(code)
            syntax_err = None
        except SyntaxError as e:
            syntax_err = f"Line {e.lineno}: {e.msg}"

        lines = code.split("\n")
        findings = []

        for patterns, severity in [(_CRITICAL, 9), (_HIGH, 7), (_MEDIUM, 4), (_EXFIL, 8)]:
            for pattern, desc in patterns:
                for ln, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        findings.append(
                            {
                                "line": ln,
                                "code": line.strip()[:60],
                                "description": desc,
                                "severity": severity,
                                "pattern": pattern[:40],
                            }
                        )

        risk = (
            min(10, (sum(f["severity"] for f in findings) / max(1, len(findings))))
            if findings
            else 0
        )
        classify = ["safe", "suspicious", "dangerous", "critical"][
            min(3, int(risk / 3.5))
        ]

        return {
            "language": language,
            "syntax_valid": syntax_err is None,
            "syntax_error": syntax_err,
            "dangerous_patterns": findings,
            "exfiltration_vectors": [f for f in findings if f["severity"] >= 8],
            "risk_score": round(risk, 1),
            "classification": classify,
            "safe_to_execute": classify == "safe",
            "analysis_notes": f"Static analysis: {len(findings)} threats found",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_sandbox_analyze"}


async def research_sandbox_report(code: str, context: str = "") -> dict[str, Any]:
    """Generate security assessment report."""
    try:
        result = await research_sandbox_analyze(code)
        if "error" in result:
            return {**result, "context": context}

        patterns = result["dangerous_patterns"]
        injection = [
            p["description"]
            for p in patterns
            if any(x in p["pattern"] for x in ["eval", "exec", "__import__"])
        ]
        exfil = [p["description"] for p in patterns if p["severity"] >= 8]
        priv_esc = [p["description"] for p in exfil if "Priv" in p]
        persistence = [p["description"] for p in exfil if "Persistence" in p]

        recs = []
        if result["risk_score"] >= 8:
            recs.append("CRITICAL: Do not execute.")
        if injection:
            recs.append("Remove eval/exec patterns.")
        if exfil:
            recs.append("Audit network operations.")
        if priv_esc:
            recs.append("Remove privilege escalation.")
        if persistence:
            recs.append("Remove persistence unless intended.")
        if not result["syntax_valid"]:
            recs.append(f"Fix: {result['syntax_error']}")
        if not recs:
            recs.append("Code appears safe.")

        return {
            "risk_score": result["risk_score"],
            "classification": result["classification"],
            "safe_to_execute": result["safe_to_execute"],
            "syntax_valid": result["syntax_valid"],
            "dangerous_patterns": patterns,
            "injection_vectors": injection,
            "exfiltration_risks": exfil,
            "privilege_escalation_risks": priv_esc,
            "persistence_mechanisms": persistence,
            "recommendations": recs,
            "context": context,
            "summary": f"Risk {result['risk_score']}/10 ({result['classification']}). {len(patterns)} threats. Safe: {result['safe_to_execute']}",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_sandbox_report"}


@requires_tier("enterprise")
async def research_sandbox_execute(
    code: str, sandbox_type: str = "nix", timeout_seconds: int = 30
) -> dict[str, Any]:
    """Execute code in isolated sandbox (Docker/Nix).

    WARNING: This tool actually executes code and is restricted to Enterprise tier only.
    Only call after research_sandbox_report confirms safety.

    Requires: Enterprise tier or higher

    Args:
        code: Python code to execute (MUST be pre-validated)
        sandbox_type: "nix" for Nix flake, "docker" for Docker container
        timeout_seconds: execution timeout (1-300, default 30)

    Returns:
        Dict with:
        - stdout: execution output
        - stderr: error output if any
        - return_code: process exit code
        - duration_ms: execution time in milliseconds
        - sandbox_type: the sandbox that was used
        - error: error message if execution failed
    """
    try:
        if not isinstance(timeout_seconds, int) or timeout_seconds < 1 or timeout_seconds > 300:
            return {"error": "timeout_seconds must be between 1 and 300"}

        if sandbox_type not in ["nix", "docker"]:
            return {"error": "sandbox_type must be 'nix' or 'docker'"}

        # Placeholder: would integrate with nix/docker execution here
        return {
            "stdout": "Sandbox execution not yet implemented",
            "stderr": "",
            "return_code": 0,
            "duration_ms": 0,
            "sandbox_type": sandbox_type,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_sandbox_execute"}


@requires_tier("enterprise")
async def research_sandbox_monitor(
    code: str, event_types: list[str] | None = None
) -> dict[str, Any]:
    """Monitor code execution for system calls and side effects.

    Requires: Enterprise tier or higher

    Args:
        code: Code to monitor
        event_types: Event types to track (syscalls, file_io, network, etc.)

    Returns:
        Dict with system call trace and side effects
    """
    try:
        if event_types is None:
            event_types = ["syscalls", "file_io", "network"]

        # Placeholder: would integrate with strace/ebpf monitoring here
        return {
            "code_hash": "sha256_hash_here",
            "event_types": event_types,
            "syscalls_logged": [],
            "file_io_logged": [],
            "network_logged": [],
            "total_events": 0,
            "message": "Monitoring not yet implemented",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_sandbox_monitor"}
