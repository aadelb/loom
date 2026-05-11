"""Report Template Engine — customizable report formatting with 5+ templates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal

logger = logging.getLogger("loom.tools.report_templates")

_TEMPLATES = {
    "executive": {"sections": ["overview", "key_findings", "recommendations"]},
    "technical": {"sections": ["abstract", "methodology", "findings", "code_examples", "conclusion"]},
    "threat_brief": {"sections": ["executive_summary", "threat_overview", "tactics_techniques", "iocs", "recommendations"]},
    "compliance": {"sections": ["assessment_scope", "compliance_findings", "risk_assessment", "remediation_plan"]},
    "presentation": {"sections": ["slide_deck"]},
}


async def research_report_template(
    template: str = "executive",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render research data into formatted report template.

    Templates: executive, technical, threat_brief, compliance, presentation.
    """
    try:
        if template not in _TEMPLATES:
            return {"error": f"Unknown template: {template}", "available": list(_TEMPLATES.keys())}

        data = data or {}
        report_parts = []
        sections_rendered = 0
        title = data.get("title", f"{template.replace('_', ' ').title()} Report")
        report_parts.append(f"# {title}\n\n**Format:** {template}\n**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

        for section_name in _TEMPLATES[template]["sections"]:
            content = data.get(section_name)
            if not content:
                continue
            sec_type = data.get(f"{section_name}_type", "text")
            heading = section_name.replace("_", " ").title()
            if sec_type == "code":
                report_parts.append(f"## {heading}\n\n```\n{content}\n```\n\n")
            elif sec_type == "list":
                report_parts.append(f"## {heading}\n\n" + "".join(f"- {l.strip()}\n" for l in (content.split("\n") if isinstance(content, str) else content) if l.strip()) + "\n")
            else:
                report_parts.append(f"## {heading}\n\n{content}\n\n")
            sections_rendered += 1

        report = "".join(report_parts)
        return {"report": report, "template": template, "word_count": len(report.split()), "sections_count": sections_rendered, "format": "markdown"}
    except Exception as exc:
        logger.error("report_template_error: %s", exc)
        return {"error": str(exc), "tool": "research_report_template"}


async def research_report_custom(
    title: str,
    sections: list[dict[str, str]],
    style: str = "professional",
) -> dict[str, Any]:
    """Build custom report from sections: heading, content, type (text|list|table|code)."""
    try:
        if style not in ("professional", "academic", "brief"):
            return {"error": f"Unknown style: {style}"}
        if not sections or not isinstance(sections, list):
            return {"error": "Sections must be a non-empty list"}

        valid = []
        for sec in sections:
            if not isinstance(sec, dict) or "heading" not in sec or "content" not in sec:
                continue
            sec_type = sec.get("type", "text")
            if sec_type not in ("text", "list", "table", "code"):
                sec_type = "text"
            valid.append({"heading": sec["heading"], "content": sec["content"], "type": sec_type})

        if not valid or len(valid) > 50:
            return {"error": "Invalid: need 1-50 sections"}

        report_parts = [f"# {title}\n\n**Style:** {style}\n**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"]
        for sec in valid:
            if sec["type"] == "code":
                report_parts.append(f"## {sec['heading']}\n\n```\n{sec['content']}\n```\n\n")
            elif sec["type"] == "list":
                report_parts.append(f"## {sec['heading']}\n\n" + "".join(f"- {l.strip()}\n" for l in (sec["content"].split("\n") if isinstance(sec["content"], str) else sec["content"]) if l.strip()) + "\n")
            else:
                report_parts.append(f"## {sec['heading']}\n\n{sec['content']}\n\n")

        report = "".join(report_parts)
        return {"report": report, "title": title, "sections_rendered": len(valid), "style": style, "word_count": len(report.split())}
    except Exception as exc:
        logger.error("report_custom_error: %s", exc)
        return {"error": str(exc), "tool": "research_report_custom"}
