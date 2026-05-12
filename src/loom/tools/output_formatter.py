"""output_formatter — Structured output formatting and actionable extraction tools."""

from __future__ import annotations

import json
import re
from typing import Any, Literal
from loom.error_responses import handle_tool_errors

logger_name = "loom.tools.output_formatter"


@handle_tool_errors("research_format_report")
def research_format_report(
    raw_text: str,
    format: Literal["json", "markdown", "executive_brief", "technical_spec"] = "json",
) -> dict[str, Any]:
    """Format raw LLM output into structured report.

    Args:
        raw_text: Raw unstructured text output
        format: Output format (json, markdown, executive_brief, technical_spec)

    Returns:
        Dict with keys: formatted (formatted text/object), format, sections_extracted (list),
        word_count (int)
    """
    try:
        sections = {}
        sections_extracted = []

        # Extract common sections using regex patterns
        patterns = {
            "executive_summary": r"(?:executive\s+summary|overview|summary)[\s:]*(.+?)(?=\n(?:methodology|methodology steps|approach|tools|timeline|cost|risk|$))",
            "methodology": r"(?:methodology|approach|method)(?:\s+steps)?[\s:]*(.+?)(?=\n(?:tools|timeline|cost|risk|sources|$))",
            "tools_required": r"(?:tools|tools\s+required)[\s:]*(.+?)(?=\n(?:timeline|cost|risk|sources|$))",
            "timeline": r"(?:timeline|timeframe|schedule)[\s:]*(.+?)(?=\n(?:cost|risk|sources|$))",
            "cost_breakdown": r"(?:cost|costs|budget|pricing)[\s:]*(.+?)(?=\n(?:risk|sources|$))",
            "risk_assessment": r"(?:risk|risks|limitations|challenges)[\s:]*(.+?)(?=\n(?:sources|$))",
            "sources": r"(?:sources|references|citations)[\s:]*(.+?)$",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if content:
                    sections[key] = content
                    sections_extracted.append(key)

        # If no structured sections found, treat entire text as content
        if not sections_extracted:
            sections["content"] = raw_text
            sections_extracted.append("content")

        # Format output based on requested format
        word_count = len(raw_text.split())

        if format == "json":
            # Extract numbered steps if present
            steps = _extract_numbered_items(sections.get("methodology", ""))
            tools = _extract_list_items(sections.get("tools_required", ""))
            costs = _extract_monetary_values(sections.get("cost_breakdown", ""))
            risks = _extract_list_items(sections.get("risk_assessment", ""))
            sources = _extract_list_items(sections.get("sources", ""))

            formatted = {
                "executive_summary": sections.get("executive_summary", ""),
                "methodology_steps": steps,
                "tools_required": tools,
                "timeline": sections.get("timeline", ""),
                "cost_breakdown": costs,
                "risk_assessment": risks,
                "sources": sources,
            }
        elif format == "markdown":
            formatted = _to_markdown(sections)
        elif format == "executive_brief":
            formatted = _to_executive_brief(sections)
        else:  # technical_spec
            formatted = _to_technical_spec(sections)

        return {
            "formatted": formatted,
            "format": format,
            "sections_extracted": sections_extracted,
            "word_count": word_count,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_format_report"}


@handle_tool_errors("research_extract_actionables")
def research_extract_actionables(text: str) -> dict[str, Any]:
    """Extract actionable items from any text.

    Args:
        text: Input text (LLM output, document, etc.)

    Returns:
        Dict with keys: actions[], tools_needed[], timeline_items[], costs[], risks[]
    """
    try:
        result = {
            "actions": _extract_action_items(text),
            "tools_needed": _extract_tools(text),
            "timeline_items": _extract_timeline_items(text),
            "costs": _extract_monetary_values(text),
            "risks": _extract_risk_items(text),
        }

        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_extract_actionables"}


# Helper functions


def _extract_numbered_items(text: str) -> list[str]:
    """Extract numbered steps (1., 1), 1:, etc.)."""
    if not text:
        return []

    # Match patterns like "1.", "1)", "1:"
    pattern = r"^\s*\d+[.):\s]+(.+?)$"
    matches = re.findall(pattern, text, re.MULTILINE)
    return [m.strip() for m in matches if m.strip()]


def _extract_list_items(text: str) -> list[str]:
    """Extract bullet points and list items (-, *, •, etc.)."""
    if not text:
        return []

    # Match various list markers
    pattern = r"^\s*[-*•·]\s+(.+?)$"
    matches = re.findall(pattern, text, re.MULTILINE)
    return [m.strip() for m in matches if m.strip()]


def _extract_monetary_values(text: str) -> list[dict[str, Any]]:
    """Extract cost items with amounts and descriptions."""
    if not text:
        return []

    # Match patterns like "$1000", "$10.50k", "€500", "£200"
    pattern = r"([$€£¥₹])\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*([a-zA-Z]*)\s*(?:-|:)?\s*(.+?)(?=\n|$)"
    matches = re.findall(pattern, text, re.MULTILINE)

    costs = []
    for currency, amount, unit, description in matches:
        try:
            numeric = float(amount.replace(",", ""))
            costs.append({
                "currency": currency,
                "amount": numeric,
                "unit": unit.strip() or "USD",
                "description": description.strip(),
            })
        except ValueError:
            continue

    return costs


def _extract_action_items(text: str) -> list[str]:
    """Extract action verbs and TODO items."""
    actions = []

    # Extract TODO items
    todo_pattern = r"(?:TODO|FIXME|ACTION|MUST|SHOULD)[\s:]*(.+?)(?=\n|$)"
    todos = re.findall(todo_pattern, text, re.IGNORECASE | re.MULTILINE)
    actions.extend([t.strip() for t in todos if t.strip()])

    # Extract numbered/bulleted items as potential actions
    numbered = _extract_numbered_items(text)
    bulleted = _extract_list_items(text)
    actions.extend(numbered)
    actions.extend(bulleted)

    return list(dict.fromkeys(actions))  # Remove duplicates preserving order


def _extract_tools(text: str) -> list[str]:
    """Extract tool names and technologies mentioned."""
    tools = []

    # Common tool patterns
    tool_pattern = r"(?:tool|framework|library|service|platform|api)[\s:]*(.+?)(?=\n|$)"
    matches = re.findall(tool_pattern, text, re.IGNORECASE | re.MULTILINE)
    for match in matches:
        items = [t.strip() for t in re.split(r"[,;]", match) if t.strip()]
        tools.extend(items)

    # Extract capitalized terms that look like tools (2+ words or with special chars)
    capitalized_pattern = r"\b([A-Z][a-zA-Z0-9\-_]+(?:\s+[A-Z][a-zA-Z0-9\-_]+)*)\b"
    candidates = re.findall(capitalized_pattern, text)

    # Filter for likely tool names (not common words)
    common_words = {"The", "This", "That", "These", "Those", "And", "Or", "Not", "But"}
    tools.extend([c for c in candidates if c not in common_words and len(c) > 3])

    return list(dict.fromkeys(tools))  # Remove duplicates


def _extract_timeline_items(text: str) -> list[dict[str, str]]:
    """Extract timeline items with dates/durations."""
    timeline = []

    # Match date patterns: YYYY-MM-DD, MM/DD/YYYY, "2 weeks", "Q1 2025", etc.
    date_pattern = r"(?:date|deadline|start|end|by|until)[\s:]*([^,\n]+?)(?=,|\n|$)"
    matches = re.findall(date_pattern, text, re.IGNORECASE | re.MULTILINE)

    for match in matches:
        if match.strip():
            timeline.append({"time": match.strip(), "description": ""})

    # Match duration patterns
    duration_pattern = r"(\d+\s*(?:days?|weeks?|months?|years?|hours?|minutes?))"
    durations = re.findall(duration_pattern, text, re.IGNORECASE)

    for duration in durations:
        if duration.strip():
            timeline.append({"time": duration.strip(), "description": ""})

    return timeline


def _extract_risk_items(text: str) -> list[str]:
    """Extract risk and limitation items."""
    risks = []

    # Extract risk patterns
    risk_pattern = r"(?:risk|limitation|challenge|concern|issue|threat|danger)[\s:]*(.+?)(?=\n|$)"
    matches = re.findall(risk_pattern, text, re.IGNORECASE | re.MULTILINE)
    risks.extend([m.strip() for m in matches if m.strip()])

    # Extract bulleted risks if under risk section
    risk_section = re.search(
        r"(?:risk|limitation|challenge)(?:\s+assessment)?[\s:]*(.+?)(?=\n\n|\nReferences|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if risk_section:
        risk_text = risk_section.group(1)
        bulleted = _extract_list_items(risk_text)
        risks.extend(bulleted)

    return list(dict.fromkeys(risks))  # Remove duplicates


def _to_markdown(sections: dict[str, str]) -> str:
    """Convert sections dict to markdown format."""
    md_parts = []

    for section, content in sections.items():
        section_title = section.replace("_", " ").title()
        md_parts.append(f"## {section_title}\n")
        md_parts.append(f"{content}\n")

    return "\n".join(md_parts)


def _to_executive_brief(sections: dict[str, str]) -> str:
    """Convert to executive brief format (condensed)."""
    brief_parts = []

    if "executive_summary" in sections:
        brief_parts.append(f"**Summary:** {sections['executive_summary'][:200]}...\n")

    if "tools_required" in sections:
        tools = _extract_list_items(sections["tools_required"])
        if tools:
            brief_parts.append(f"**Tools Required:** {', '.join(tools[:5])}\n")

    if "timeline" in sections:
        brief_parts.append(f"**Timeline:** {sections['timeline']}\n")

    if "cost_breakdown" in sections:
        costs = _extract_monetary_values(sections["cost_breakdown"])
        if costs:
            # Group by currency — only sum if all same currency
            currencies = {c["currency"] for c in costs}
            if len(currencies) == 1:
                total = sum(c["amount"] for c in costs)
                brief_parts.append(f"**Total Cost:** {costs[0]['currency']}{total:,.2f}\n")
            else:
                # Mixed currencies — list individually
                cost_str = ", ".join([f"{c['currency']}{c['amount']:,.2f}" for c in costs])
                brief_parts.append(f"**Costs:** {cost_str}\n")

    if "risk_assessment" in sections:
        risks = _extract_list_items(sections["risk_assessment"])
        if risks:
            brief_parts.append(f"**Key Risks:** {', '.join(risks[:3])}\n")

    return "".join(brief_parts)


def _to_technical_spec(sections: dict[str, str]) -> dict[str, Any]:
    """Convert to technical specification object."""
    spec = {}

    for section, content in sections.items():
        if section == "methodology":
            spec[section] = _extract_numbered_items(content) or [content]
        elif section in ("tools_required", "sources", "risk_assessment"):
            spec[section] = _extract_list_items(content) or [content]
        elif section == "cost_breakdown":
            spec[section] = _extract_monetary_values(content) or [{"description": content}]
        else:
            spec[section] = content

    return spec
