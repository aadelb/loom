"""Report formatting utilities for tool output.

Generates markdown tables, bullet lists, and structured reports
from tool result dictionaries.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

logger = logging.getLogger("loom.report_formatters")


def markdown_table(
    rows: list[dict[str, Any]],
    *,
    columns: list[str] | None = None,
    max_cell_width: int = 60,
) -> str:
    """Generate a markdown table from a list of dicts.

    Args:
        rows: List of dictionaries (each dict is one row)
        columns: Column names to include (default: all keys from first row)
        max_cell_width: Max characters per cell before truncation

    Returns:
        Markdown-formatted table string
    """
    if not rows:
        return "_No data_"

    if columns is None:
        columns = list(rows[0].keys())

    def _cell(value: Any) -> str:
        text = str(value).replace("|", "\\|").replace("\n", " ")
        if len(text) > max_cell_width:
            text = text[: max_cell_width - 3] + "..."
        return text

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body_lines: list[str] = []
    for row in rows:
        cells = [_cell(row.get(col, "")) for col in columns]
        body_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, separator, *body_lines])


def bullet_list(items: list[str | dict[str, Any]], *, indent: int = 0) -> str:
    """Format items as a markdown bullet list.

    Args:
        items: List of strings or dicts (dicts become key: value pairs)
        indent: Number of indentation levels (2 spaces per level)

    Returns:
        Markdown-formatted bullet list string
    """
    prefix = "  " * indent + "- "
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            key = next(iter(item), "")
            lines.append(f"{prefix}**{key}**: {item[key]}")
        else:
            lines.append(f"{prefix}{item}")
    return "\n".join(lines)


def section(title: str, content: str, *, level: int = 2) -> str:
    """Format a markdown section with header.

    Args:
        title: Section title
        content: Section content
        level: Heading level (1-6)

    Returns:
        Markdown-formatted section string
    """
    header = "#" * level + " " + title
    return f"{header}\n\n{content}"


def key_value_block(data: dict[str, Any], *, separator: str = ": ") -> str:
    """Format a dict as aligned key-value pairs.

    Args:
        data: Dictionary to format
        separator: String separating keys and values

    Returns:
        Markdown-formatted key-value block string
    """
    if not data:
        return "_No data_"
    max_key_len = max(len(str(k)) for k in data)
    lines: list[str] = []
    for key, value in data.items():
        lines.append(f"**{str(key).ljust(max_key_len)}**{separator}{value}")
    return "\n".join(lines)


def summary_box(
    title: str,
    stats: dict[str, Any],
    *,
    border: str = "─",
) -> str:
    """Format a summary statistics box.

    Args:
        title: Box title
        stats: Dictionary of statistics to display
        border: Border character (unused, kept for API compatibility)

    Returns:
        Markdown-formatted summary box string
    """
    lines = [f"## {title}", ""]
    for key, value in stats.items():
        lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)


def format_findings(
    findings: list[dict[str, Any]],
    *,
    severity_key: str = "severity",
    title_key: str = "title",
    description_key: str = "description",
) -> str:
    """Format a list of findings/vulnerabilities as a report.

    Sorts findings by severity (critical > high > medium > low > info).

    Args:
        findings: List of finding dicts
        severity_key: Dict key for severity field
        title_key: Dict key for title field
        description_key: Dict key for description field

    Returns:
        Markdown-formatted findings report string
    """
    if not findings:
        return "_No findings_"

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_findings = sorted(
        findings,
        key=lambda f: severity_order.get(
            str(f.get(severity_key, "info")).lower(), 5
        ),
    )

    lines: list[str] = []
    for i, finding in enumerate(sorted_findings, 1):
        severity = str(finding.get(severity_key, "INFO")).upper()
        title = finding.get(title_key, f"Finding {i}")
        desc = finding.get(description_key, "")
        lines.append(f"### {i}. [{severity}] {title}")
        if desc:
            lines.append(f"\n{desc}\n")

    return "\n".join(lines)


def to_markdown(sections: list[dict[str, Any]]) -> str:
    """Convert sections to Markdown format.

    Args:
        sections: List of section dicts with keys: title, content, url (optional)

    Returns:
        Markdown-formatted output string
    """
    lines = []
    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        url = section.get("url", "")

        lines.append(f"## {title}\n")
        lines.append(content)
        if url:
            lines.append(f"\n**Source**: {url}")
        lines.append("\n")

    return "\n".join(lines)


def to_html(sections: list[dict[str, Any]]) -> str:
    """Convert sections to HTML format.

    Args:
        sections: List of section dicts with keys: title, content, url (optional)

    Returns:
        HTML-formatted output string
    """
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width">',
        "<style>",
        "body { font-family: sans-serif; line-height: 1.6; max-width: 900px; margin: 20px; }",
        "h2 { color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }",
        "a { color: #0066cc; }",
        ".source { font-size: 0.9em; color: #666; margin-top: 10px; }",
        "</style>",
        "</head>",
        "<body>",
    ]

    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        url = section.get("url", "")

        html_parts.append(f"<h2>{_escape_html(title)}</h2>")
        html_parts.append(f"<p>{_escape_html(content)}</p>")
        if url:
            html_parts.append(
                f'<p class="source"><strong>Source</strong>: '
                f'<a href="{_escape_html(url)}">{_escape_html(url[:80])}</a></p>'
            )

    html_parts.extend(["</body>", "</html>"])
    return "\n".join(html_parts)


def to_json(sections: list[dict[str, Any]]) -> str:
    """Convert sections to JSON format.

    Args:
        sections: List of section dicts

    Returns:
        JSON-formatted output string
    """
    return json.dumps(sections, indent=2)


def format_report(
    sections: list[dict[str, Any]],
    format: Literal["markdown", "json", "html"] = "markdown",
) -> str:
    """Format report sections into requested output format.

    Args:
        sections: List of section dicts
        format: Output format (markdown, json, or html)

    Returns:
        Formatted output string
    """
    if format == "json":
        return to_json(sections)
    elif format == "html":
        return to_html(sections)
    else:  # markdown (default)
        return to_markdown(sections)


def _escape_html(text: str) -> str:
    """Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
