"""Compliance reporting and audit trail tools."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.compliance_report")
DEFAULT_AUDIT_DIR = Path.home() / ".loom" / "audit"

FRAMEWORKS = {
    "eu_ai_act": {"name": "EU AI Act (Article 15)", "desc": "Transparency + Logging for high-risk AI systems"},
    "nist_ai_rmf": {"name": "NIST AI Risk Management Framework", "desc": "Governance + Risk management"},
    "owasp_agentic": {"name": "OWASP Agentic AI Security", "desc": "Agent security + Tool sandboxing"},
}


def research_compliance_report(period_days: int = 30, framework: str = "eu_ai_act") -> dict[str, Any]:
    """Generate compliance report for specified framework."""
    try:
        if framework not in FRAMEWORKS:
            raise ValueError(f"Unknown framework: {framework}")
        fw = FRAMEWORKS[framework]
        entries = _read_audit_entries(DEFAULT_AUDIT_DIR, datetime.now(UTC) - timedelta(days=period_days))
        findings = _classify_findings(entries)
        findings_count = sum(len(v) for v in findings.values())
        recs = _generate_recommendations(findings)
        report = f"COMPLIANCE: {fw['name']}\n{fw['desc']}\nEntries: {len(entries)} | Findings: {findings_count}\n"
        report += f"Risk: {_calc_risk(findings).upper()}\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(recs))
        return {
            "framework": fw["name"],
            "period_days": period_days,
            "total_tests_run": len(entries),
            "findings_count": findings_count,
            "risk_level": _calc_risk(findings),
            "recommendations": recs,
            "report_text": report,
            "audit_entries_analyzed": len(entries),
            "last_updated": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_compliance_report"}


def research_audit_trail(tool_name: str = "", limit: int = 100) -> dict[str, Any]:
    """Retrieve audit trail entries, filtered by tool name."""
    try:
        all_entries = _read_audit_entries(DEFAULT_AUDIT_DIR, datetime.now(UTC) - timedelta(days=90))
        filtered = [e for e in all_entries if not tool_name or e.get("tool_name") == tool_name]
        sorted_entries = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        return {
            "entries": sorted_entries,
            "total": len(sorted_entries),
            "filtered_by": tool_name or "none",
            "audit_dir": str(DEFAULT_AUDIT_DIR),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_audit_trail"}


def _read_audit_entries(audit_dir: Path, cutoff: datetime) -> list[dict[str, Any]]:
    """Read audit entries from JSONL files."""
    entries = []
    if not audit_dir.exists():
        return entries
    for log_file in sorted(audit_dir.glob("*.jsonl")):
        try:
            file_dt = datetime.fromisoformat(log_file.stem)
            # Ensure both datetimes have timezone awareness for comparison
            if file_dt.tzinfo is None:
                file_dt = file_dt.replace(tzinfo=UTC)
            if file_dt < cutoff:
                continue
        except ValueError:
            continue
        try:
            with open(log_file) as f:
                for line in f:
                    if line := line.strip():
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
    return entries


def _classify_findings(entries: list[dict[str, Any]]) -> dict[str, list]:
    """Classify audit entries into compliance findings."""
    findings = {"missing_checksum": [], "redacted": [], "errors": [], "slow": []}
    for entry in entries:
        if not entry.get("checksum"):
            findings["missing_checksum"].append(entry)
        if any(v == "***REDACTED***" for v in entry.get("params_summary", {}).values()):
            findings["redacted"].append(entry)
        if entry.get("status") not in ("success", "cached"):
            findings["errors"].append(entry)
        if entry.get("duration_ms", 0) > 5000:
            findings["slow"].append(entry)
    return findings


def _calc_risk(findings: dict[str, list]) -> str:
    """Calculate risk level."""
    if findings.get("missing_checksum"):
        return "critical"
    if len(findings.get("errors", [])) > 5:
        return "high"
    return "medium" if len(findings.get("slow", [])) > 10 else "low"


def _generate_recommendations(findings: dict[str, list]) -> list[str]:
    """Generate remediation recommendations."""
    recs = []
    if findings.get("missing_checksum"):
        recs.append("Enable checksum generation in audit logging")
    if findings.get("errors"):
        recs.append("Investigate and fix execution errors")
    if findings.get("slow"):
        recs.append("Optimize slow-running tools")
    if findings.get("redacted"):
        recs.append("Review redacted sensitive fields")
    return recs if recs else ["System in compliance - continue audits"]


def tool_compliance_report(period_days: int = 30, framework: str = "eu_ai_act") -> list[TextContent]:
    """MCP wrapper for research_compliance_report."""
    return [TextContent(type="text", text=json.dumps(research_compliance_report(period_days, framework), indent=2))]


def tool_audit_trail(tool_name: str = "", limit: int = 100) -> list[TextContent]:
    """MCP wrapper for research_audit_trail."""
    return [TextContent(type="text", text=json.dumps(research_audit_trail(tool_name, limit), indent=2))]
