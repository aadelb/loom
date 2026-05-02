"""Report Template Engine — customizable report formatting with 5+ templates.

Renders research data into structured reports with executive, technical,
threat intelligence, compliance, and presentation formats.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal

logger = logging.getLogger("loom.tools.report_templates")

# Template registry: minimal definitions
_TEMPLATES = {
    "executive": {"desc": "1-page summary", "sections": ["overview", "key_findings", "recommendations"]},
    "technical": {"desc": "Detailed analysis with code", "sections": ["abstract", "methodology", "findings", "code_examples", "conclusion"]},
    "threat_brief": {"desc": "MITRE ATT&CK aligned threat analysis", "sections": ["executive_summary", "threat_overview", "tactics_techniques", "iocs", "recommendations"]},
    "compliance": {"desc": "EU AI Act Article 15 format", "sections": ["executive_summary", "assessment_scope", "compliance_findings", "risk_assessment", "remediation_plan"]},
    "presentation": {"desc": "Slide bullet points", "sections": ["slide_deck"]},
}


async def research_report_template(
    template: str = "executive",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render research data into formatted report template.

    Templates: executive (1-page), technical (detailed+code), threat_brief (MITRE),
    compliance (EU AI Act), presentation (slides).

    Args:
        template: Template type
        data: Research data dict with section keys matching template

    Returns:
        {report: str (markdown), template: str, word_count: int, sections_count: int, format: str}
    """
    if template not in _TEMPLATES:
        return {"error": f"Unknown template: {template}", "available": list(_TEMPLATES.keys())}

    data = data or {}
    tpl = _TEMPLATES[template]
    report_parts = []
    sections_rendered = 0

    # Header
    title = data.get("title", f"{template.replace('_', ' ').title()} Report")
    report_parts.append(f"# {title}\n\n**Format:** {template}\n**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

    # Render sections
    for section_name in tpl["sections"]:
        content = data.get(section_name)
        if content:
            sec_type = data.get(f"{section_name}_type", "text")
            heading = section_name.replace("_", " ").title()

            # Format by type
            if sec_type == "code":
                formatted = f"## {heading}\n\n```\n{content}\n```\n\n"
            elif sec_type == "list":
                lines = content.split("\n") if isinstance(content, str) else content
                formatted = f"## {heading}\n\n" + "".join(f"- {line.strip()}\n" if line.strip() else "" for line in lines if line) + "\n"
            else:  # text or table
                formatted = f"## {heading}\n\n{content}\n\n"

            report_parts.append(formatted)
            sections_rendered += 1

    report = "".join(report_parts)
    word_count = len(report.split())

    return {
        "report": report,
        "template": template,
        "word_count": word_count,
        "sections_count": sections_rendered,
        "format": "markdown",
    }


async def research_report_custom(
    title: str,
    sections: list[dict[str, str]],
    style: str = "professional",
) -> dict[str, Any]:
    """Build custom report from sections.

    Args:
        title: Report title
        sections: List of {heading: str, content: str, type: text|list|table|code}
        style: professional|academic|brief

    Returns:
        {report: str, title: str, sections_rendered: int, style: str, word_count: int}
    """
    if style not in ("professional", "academic", "brief"):
        return {"error": f"Unknown style: {style}"}

    if not sections or not isinstance(sections, list):
        return {"error": "Sections must be a non-empty list"}

    # Validate & normalize sections
    valid = []
    for sec in sections:
        if not isinstance(sec, dict) or "heading" not in sec or "content" not in sec:
            continue
        sec_type = sec.get("type", "text")
        if sec_type not in ("text", "list", "table", "code"):
            sec_type = "text"
        valid.append({"heading": sec["heading"], "content": sec["content"], "type": sec_type})

    if not valid:
        return {"error": "No valid sections found"}

    if len(valid) > 50:
        return {"error": "Maximum 50 sections allowed"}

    report_parts = [f"# {title}\n\n**Style:** {style}\n**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"]

    for sec in valid:
        if sec["type"] == "code":
            report_parts.append(f"## {sec['heading']}\n\n```\n{sec['content']}\n```\n\n")
        elif sec["type"] == "list":
            report_parts.append(f"## {sec['heading']}\n\n")
            for line in (sec["content"].split("\n") if isinstance(sec["content"], str) else sec["content"]):
                if line.strip():
                    report_parts.append(f"- {line.strip()}\n")
            report_parts.append("\n")
        else:
            report_parts.append(f"## {sec['heading']}\n\n{sec['content']}\n\n")

    report = "".join(report_parts)
    word_count = len(report.split())

    return {
        "report": report,
        "title": title,
        "sections_rendered": len(valid),
        "style": style,
        "word_count": word_count,
    }
