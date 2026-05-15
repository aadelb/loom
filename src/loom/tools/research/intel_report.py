"""Intelligence Report Formatter — generate professional reports from raw research data."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors
import html

import logging
from datetime import UTC, datetime
from typing import Any

try:
    from loom.report_formatters import to_markdown, to_html, section, key_value_block
    _FORMATTERS_AVAILABLE = True
except ImportError:
    _FORMATTERS_AVAILABLE = False

logger = logging.getLogger("loom.tools.intel_report")


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text)


def _build_banner(title: str, classification: str, now: str, fmt: str) -> str:
    """Build classification banner in specified format."""
    if fmt == "markdown":
        return f"# {title}\n\n**Classification:** {classification}\n**Generated:** {now}\n"
    elif fmt == "html":
        return (f"<div class='classification-banner'>"
                f"<h1>{_escape_html(title)}</h1>"
                f"<p><strong>Classification:</strong> {classification}</p>"
                f"<p><strong>Generated:</strong> {now}</p></div>")
    return f"{'='*60}\n{title}\n{'='*60}\nClassification: {classification}\nGenerated: {now}\n"


def _build_findings(findings: list[dict], fmt: str) -> str:
    """Build key findings section."""
    if not _FORMATTERS_AVAILABLE:
        # Fallback to manual formatting
        if fmt == "markdown":
            s = "## Key Findings\n\n"
            for i, f in enumerate(findings, 1):
                s += f"### Finding {i}\n- **Source:** {f.get('source', 'Unknown')}\n- **Confidence:** {f.get('confidence', 'UNKNOWN')}\n- **Timestamp:** {f.get('timestamp', '')}\n- **Summary:** {f.get('content', '')[:200]}...\n\n"
            return s
        elif fmt == "html":
            s = "<h2>Key Findings</h2><ul>"
            for i, f in enumerate(findings, 1):
                src, conf = _escape_html(f.get('source', 'Unknown')), f.get('confidence', 'UNKNOWN')
                cont = _escape_html(f.get('content', '')[:200])
                s += f"<li><strong>Finding {i}</strong>: {src} ({conf}) - {cont}...</li>"
            return s + "</ul>"
        s = "\nKEY FINDINGS\n" + "-"*40 + "\n"
        for i, f in enumerate(findings, 1):
            s += f"\nFinding {i}:\n  Source: {f.get('source', 'Unknown')}\n  Confidence: {f.get('confidence', 'UNKNOWN')}\n  {f.get('content', '')[:200]}...\n"
        return s

    # Use shared formatters
    if fmt == "markdown":
        s = section("Key Findings", "")
        for i, f in enumerate(findings, 1):
            finding_detail = f"**Source:** {f.get('source', 'Unknown')}\n- **Confidence:** {f.get('confidence', 'UNKNOWN')}\n- **Timestamp:** {f.get('timestamp', '')}\n- **Summary:** {f.get('content', '')[:200]}..."
            s += f"\n### Finding {i}\n- {finding_detail}\n"
        return s
    elif fmt == "html":
        s = "<h2>Key Findings</h2><ul>"
        for i, f in enumerate(findings, 1):
            src, conf = _escape_html(f.get('source', 'Unknown')), f.get('confidence', 'UNKNOWN')
            cont = _escape_html(f.get('content', '')[:200])
            s += f"<li><strong>Finding {i}</strong>: {src} ({conf}) - {cont}...</li>"
        return s + "</ul>"
    s = "\nKEY FINDINGS\n" + "-"*40 + "\n"
    for i, f in enumerate(findings, 1):
        s += f"\nFinding {i}:\n  Source: {f.get('source', 'Unknown')}\n  Confidence: {f.get('confidence', 'UNKNOWN')}\n  {f.get('content', '')[:200]}...\n"
    return s


@handle_tool_errors("research_intel_report")
async def research_intel_report(
    title: str,
    findings: list[dict],
    classification: str = "CONFIDENTIAL",
    format: str = "markdown",
) -> dict[str, Any]:
    """Generate professional intelligence report from findings.

    Args:
        title: Report title
        findings: List with {source, content, confidence, timestamp}
        classification: Classification level
        format: Output format (markdown, html, text)

    Returns:
        {report, classification, findings_count, generated_at, word_count}
    """
    try:
        classification = classification if classification in ("UNCLASSIFIED", "CONFIDENTIAL", "SECRET", "TOP_SECRET") else "CONFIDENTIAL"
        format = format if format in ("markdown", "html", "text") else "markdown"
        now = datetime.now(UTC).isoformat()
        sources = set(f.get("source", "") for f in findings)
        high_conf = sum(1 for f in findings if f.get("confidence", "").upper() == "HIGH")

        sections = [_build_banner(title, classification, now, format)]

        # Executive Summary
        if format == "markdown":
            sections.append(f"## Executive Summary\n\nTotal findings: **{len(findings)}**\nHigh confidence: **{high_conf}**\n\n")
        elif format == "html":
            sections.append(f"<h2>Executive Summary</h2><p>Total findings: <strong>{len(findings)}</strong></p>")
        else:
            sections.append(f"\nEXECUTIVE SUMMARY\n{'-'*40}\nTotal findings: {len(findings)}\n")

        sections.append(_build_findings(findings, format))

        # Source Assessment
        if format == "markdown":
            sections.append(f"## Source Assessment\n\nSources: {len(sources)}\n- {', '.join(sources)}\n\n")
        elif format == "html":
            sections.append(f"<h2>Source Assessment</h2><p>Sources: {len(sources)}\n{', '.join(sources)}</p>")
        else:
            sections.append(f"\nSOURCE ASSESSMENT\n{'-'*40}\nTotal sources: {len(sources)}\n")

        # Methodology & Recommendations
        if format == "markdown":
            sections.append("## Methodology\n\n- Systematic research\n- Confidence assessment\n- Timestamp validation\n")
            sections.append("## Recommendations\n\n1. Prioritize high-confidence findings\n2. Validate against secondary sources\n3. Monitor for updates\n")
        elif format == "html":
            sections.append("<h2>Methodology</h2><ul><li>Systematic research</li><li>Confidence assessment</li></ul>")
            sections.append("<h2>Recommendations</h2><ol><li>Prioritize findings</li><li>Validate sources</li><li>Monitor updates</li></ol>")
        else:
            sections.append(f"\nMETHODOLOGY\n{'-'*40}\n- Systematic research\n- Confidence assessment\n")
            sections.append(f"\nRECOMMENDATIONS\n{'-'*40}\n1. Prioritize high-confidence\n2. Validate against sources\n3. Monitor for updates\n")

        report = f"<html><head><title>{_escape_html(title)}</title></head><body>{''.join(sections)}</body></html>" if format == "html" else "\n".join(sections)

        return {
            "report": report,
            "classification": classification,
            "findings_count": len(findings),
            "generated_at": now,
            "word_count": _count_words(report),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_intel_report"}


@handle_tool_errors("research_brief_generate")
async def research_brief_generate(
    topic: str,
    points: list[str],
    audience: str = "executive",
) -> dict[str, Any]:
    """Generate short intelligence brief (1 page).

    Args:
        topic: Brief topic
        points: Key points to cover
        audience: Target audience (executive, technical, policy)

    Returns:
        {brief, topic, audience, points_covered, word_count}
    """
    try:
        audience = audience if audience in ("executive", "technical", "policy") else "executive"
        max_points = 3 if audience == "executive" else (5 if audience == "technical" else 4)
        points = points[:max_points]
        now = datetime.now(UTC).isoformat()

        brief = f"INTELLIGENCE BRIEF\n{topic}\nGenerated: {now}\nAudience: {audience.upper()}\n\n{'='*60}\n\n"

        if audience == "executive":
            brief += "KEY POINTS:\n\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(points, 1))
            brief += f"\n\n{'='*60}\nRECOMMENDED ACTION: Review and escalate as needed.\n"
        elif audience == "technical":
            brief += "TECHNICAL ANALYSIS:\n\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(points, 1))
            brief += f"\n\n{'='*60}\nIMPLEMENTATION NOTES: Detailed assessment provided above.\n"
        else:  # policy
            brief += "POLICY IMPLICATIONS:\n\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(points, 1))
            brief += f"\n\n{'='*60}\nPOLICY RESPONSE: Review implications and update policies.\n"

        return {
            "brief": brief,
            "topic": topic,
            "audience": audience,
            "points_covered": len(points),
            "word_count": _count_words(brief),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_brief_generate"}
