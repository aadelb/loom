"""Sandboxed code detonation — static analysis without execution."""

from __future__ import annotations
import ast, logging, re
from typing import Any

logger = logging.getLogger(__name__)

_CRITICAL = [
    (r"\beval\s*\(", "eval() — execution"), (r"\bexec\s*\(", "exec() — execution"),
    (r"\b__import__\s*\(", "__import__()"), (r"os\.system\s*\(", "os.system()"),
    (r"subprocess\.(run|Popen)", "subprocess"), (r"socket\.socket", "socket"),
    (r"requests\.get\s*\(", "requests"), (r"urllib\.request\.", "urllib"),
]
_HIGH = [
    (r"import\s+(os|sys|subprocess|socket|requests)", "High-risk imports"),
    (r"open\s*\(.*['\"]w", "File write"), (r"rmdir\s*\(|remove\s*\(|unlink\s*\(", "File delete"),
]
_MEDIUM = [(r"open\s*\(", "File I/O"), (r"pickle\.", "pickle"), (r"input\s*\(", "User input")]
_EXFIL = [
    (r"requests\.post\s*\(", "HTTP POST"), (r"socket\.send", "Socket send"),
    (r"sudo\s|os\.chmod.*0o777|os\.setuid", "Priv escalation"),
    (r"cron|crontab|launchd|\.plist|\.service", "Persistence"),
]

async def research_sandbox_analyze(code: str, language: str = "python", timeout_seconds: int = 10, allow_network: bool = False) -> dict[str, Any]:
    """Static analysis of code for dangerous patterns (no execution).
    Returns: {syntax_valid, dangerous_patterns, exfiltration_vectors, risk_score, classification, safe_to_execute}"""
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
                    findings.append({
                        "line": ln, "code": line.strip()[:60], "description": desc,
                        "severity": severity, "pattern": pattern[:40]
                    })

    risk = min(10, (sum(f["severity"] for f in findings) / max(1, len(findings)))) if findings else 0
    classify = ["safe", "suspicious", "dangerous", "critical"][min(3, int(risk / 3.5))]

    return {
        "language": language, "syntax_valid": syntax_err is None, "syntax_error": syntax_err,
        "dangerous_patterns": findings, "exfiltration_vectors": [f for f in findings if f["severity"] >= 8],
        "risk_score": round(risk, 1), "classification": classify, "safe_to_execute": classify == "safe",
        "analysis_notes": f"Static analysis: {len(findings)} threats found"
    }

async def research_sandbox_report(code: str, context: str = "") -> dict[str, Any]:
    """Generate security assessment report."""
    result = await research_sandbox_analyze(code)
    if "error" in result:
        return {**result, "context": context}

    patterns = result["dangerous_patterns"]
    injection = [p["description"] for p in patterns if any(x in p["pattern"] for x in ["eval", "exec", "__import__"])]
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
        "risk_score": result["risk_score"], "classification": result["classification"],
        "safe_to_execute": result["safe_to_execute"], "syntax_valid": result["syntax_valid"],
        "dangerous_patterns": patterns, "injection_vectors": injection,
        "exfiltration_risks": exfil, "privilege_escalation_risks": priv_esc,
        "persistence_mechanisms": persistence, "recommendations": recs, "context": context,
        "summary": f"Risk {result['risk_score']}/10 ({result['classification']}). {len(patterns)} threats. Safe: {result['safe_to_execute']}"
    }
