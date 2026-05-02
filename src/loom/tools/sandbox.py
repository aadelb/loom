"""Sandboxed code detonation system — safe static analysis without execution."""

from __future__ import annotations

import ast
import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.sandbox")

# Dangerous pattern definitions
_CRITICAL = [
    (r"\beval\s*\(", "eval() — code execution"),
    (r"\bexec\s*\(", "exec() — code execution"),
    (r"\b__import__\s*\(", "__import__() — dynamic imports"),
    (r"os\.system\s*\(", "os.system() — shell execution"),
    (r"subprocess\.(run|Popen)", "subprocess — process spawning"),
    (r"socket\.socket", "socket — network access"),
    (r"requests\.get\s*\(", "requests — HTTP"),
    (r"urllib\.request\.", "urllib — fetch"),
    (r"paramiko\.", "paramiko — SSH"),
]

_HIGH = [
    (r"import\s+(os|sys|subprocess|socket|requests)", "High-risk imports"),
    (r"from\s+(os|sys|subprocess|socket)\s+import", "High-risk imports"),
    (r"open\s*\(.*['\"]w", "File write"),
    (r"rmdir\s*\(|remove\s*\(|unlink\s*\(", "File deletion"),
]

_MEDIUM = [
    (r"open\s*\(", "File I/O"),
    (r"pickle\.", "pickle — deserialization"),
    (r"yaml\.load", "yaml.load() — deserialization"),
    (r"input\s*\(", "User input"),
]

_EXFIL = [
    (r"requests\.post\s*\(", "HTTP POST — data exfil"),
    (r"socket\.send", "Socket send — exfil"),
    (r"ftplib\.|paramiko\..*SFTP", "File transfer"),
    (r"sudo\s|os\.chmod.*0o777|os\.setuid", "Privilege escalation"),
    (r"cron|crontab|launchd|\.plist|\.service", "Persistence"),
]


def _analyze_syntax(code: str) -> tuple[bool, str]:
    """Validate syntax. Return (valid, error_msg)."""
    try:
        ast.parse(code)
        return (True, "")
    except SyntaxError as e:
        return (False, f"Syntax error line {e.lineno}: {e.msg}")


def _scan_patterns(code: str, patterns: list, severity: str) -> list[dict]:
    """Scan code for patterns. Return findings."""
    findings = []
    lines = code.split("\n")
    risk_map = {"critical": 9, "high": 7, "medium": 4, "low": 1}

    for pattern, desc in patterns:
        for line_num, line in enumerate(lines, 1):
            if re.search(pattern, line):
                findings.append({
                    "pattern": pattern,
                    "description": desc,
                    "line": line_num,
                    "code": line.strip()[:80],
                    "severity": severity,
                    "risk_score": risk_map.get(severity, 1),
                })
    return findings


def _calc_risk(findings: list[dict]) -> float:
    """Calculate risk score (0-10)."""
    if not findings:
        return 0.0
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    avg_risk = sum(f.get("risk_score", 1) for f in findings) / len(findings)
    return min(10.0, avg_risk + (critical_count * 1.2))


def _classify(score: float, findings: list) -> str:
    """Classify safety level."""
    if not findings:
        return "safe"
    return ["safe", "suspicious", "dangerous", "critical"][min(3, int(score / 3.5))]


async def research_sandbox_analyze(
    code: str,
    language: str = "python",
    timeout_seconds: int = 10,
    allow_network: bool = False,
) -> dict[str, Any]:
    """Safely analyze code via static analysis (no execution).

    Args:
        code: Source code to analyze
        language: "python" (only language supported)
        timeout_seconds: Unused — no execution occurs
        allow_network: Penalize network patterns if False

    Returns:
        {risk_score, classification, dangerous_patterns, exfiltration_vectors,
         safe_to_execute, syntax_valid, syntax_error, analysis_notes}
    """
    if language != "python":
        return {"error": f"Language '{language}' unsupported. Use 'python'."}

    is_valid, syntax_err = _analyze_syntax(code)

    # Scan all threat levels
    critical = _scan_patterns(code, _CRITICAL, "critical")
    high = _scan_patterns(code, _HIGH, "high")
    medium = _scan_patterns(code, _MEDIUM, "medium")
    exfil = _scan_patterns(code, _EXFIL, "high")

    all_findings = critical + high + medium + exfil

    # Penalize network if disabled
    if not allow_network:
        network_patterns = [
            f for f in all_findings
            if any(x in f["pattern"] for x in ["socket", "requests", "urllib", "paramiko"])
        ]
        exfil.extend(network_patterns)

    risk_score = round(_calc_risk(all_findings), 1)
    classification = _classify(risk_score, all_findings)

    return {
        "language": language,
        "syntax_valid": is_valid,
        "syntax_error": syntax_err if not is_valid else None,
        "dangerous_patterns": critical + high + medium,
        "exfiltration_vectors": exfil,
        "risk_score": risk_score,
        "classification": classification,
        "safe_to_execute": classification == "safe",
        "analysis_notes": f"Static analysis only (no execution). {len(critical+high+medium)} "
                         f"dangerous patterns, {len(exfil)} exfil vectors.",
    }


async def research_sandbox_report(
    code: str,
    context: str = "",
) -> dict[str, Any]:
    """Generate security assessment report.

    Args:
        code: Source code
        context: Execution context/purpose

    Returns:
        {risk_score, classification, dangerous_patterns, injection_vectors,
         exfiltration_risks, privilege_escalation_risks, persistence_mechanisms,
         recommendations, safe_to_execute, summary}
    """
    result = await research_sandbox_analyze(code, "python")
    if "error" in result:
        return {**result, "context": context}

    dangerous = result["dangerous_patterns"]
    exfil = result["exfiltration_vectors"]

    # Extract risk vectors
    injection = [f["description"] for f in dangerous if any(x in f["pattern"] for x in ["eval", "exec", "__import__"])]
    exfil_risks = [f["description"] for f in exfil if "exfil" in f["description"].lower()]
    priv_esc = [f["description"] for f in exfil if any(x in f["description"] for x in ["sudo", "chmod", "setuid"])]
    persistence = [f["description"] for f in exfil if any(x in f["description"] for x in ["cron", "launchd", "plist"])]

    # Generate recommendations
    recommendations = []
    if result["risk_score"] >= 8:
        recommendations.append("CRITICAL: Do not execute. Extreme security risks.")
    if injection:
        recommendations.append("Remove eval/exec patterns. Use safer alternatives.")
    if exfil_risks:
        recommendations.append("Audit network operations. Implement isolation/monitoring.")
    if priv_esc:
        recommendations.append("Remove unnecessary privilege escalation calls.")
    if persistence:
        recommendations.append("Remove persistence mechanisms unless intended.")
    if not result["syntax_valid"]:
        recommendations.append(f"Fix syntax: {result['syntax_error']}")
    if not recommendations:
        recommendations.append("Code appears safe. Standard review recommended.")

    summary = (
        f"Risk: {result['risk_score']}/10 ({result['classification'].upper()}). "
        f"{len(dangerous)} dangerous patterns. "
        f"{len(exfil_risks)} exfil risks. "
        f"Safe: {result['safe_to_execute']}."
    )

    return {
        "risk_score": result["risk_score"],
        "classification": result["classification"],
        "safe_to_execute": result["safe_to_execute"],
        "syntax_valid": result["syntax_valid"],
        "dangerous_patterns": dangerous,
        "injection_vectors": injection,
        "exfiltration_risks": exfil_risks,
        "privilege_escalation_risks": priv_esc,
        "persistence_mechanisms": persistence,
        "recommendations": recommendations,
        "context": context,
        "summary": summary,
    }
