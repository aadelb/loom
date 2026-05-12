"""Tests for report_formatters module.

Tests markdown_table, bullet_list, format_findings, and other formatting functions.
"""

from __future__ import annotations

import pytest

from loom.report_formatters import (
    bullet_list,
    format_findings,
    format_report,
    key_value_block,
    markdown_table,
    section,
    summary_box,
    to_html,
    to_json,
    to_markdown,
)


class TestMarkdownTable:
    """Test markdown_table function."""

    def test_markdown_table_basic(self) -> None:
        """Test basic markdown table generation."""
        rows = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        result = markdown_table(rows)
        assert "|" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "age" in result

    def test_markdown_table_column_selection(self) -> None:
        """Test table with specific columns."""
        rows = [
            {"name": "Alice", "age": 30, "city": "NY"},
            {"name": "Bob", "age": 25, "city": "LA"},
        ]
        result = markdown_table(rows, columns=["name", "city"])
        assert "Alice" in result
        assert "NY" in result
        assert "age" not in result

    def test_markdown_table_max_cell_width(self) -> None:
        """Test cell width truncation."""
        rows = [{"text": "a" * 100}]
        result = markdown_table(rows, max_cell_width=10)
        assert "..." in result
        assert len(result.split("|")[1]) <= 20  # Cell + padding

    def test_markdown_table_escapes_pipes(self) -> None:
        """Test that pipes are escaped in cells."""
        rows = [{"text": "a | b"}]
        result = markdown_table(rows)
        assert "\\|" in result

    def test_markdown_table_handles_newlines(self) -> None:
        """Test that newlines are converted to spaces."""
        rows = [{"text": "line1\nline2"}]
        result = markdown_table(rows)
        assert "\n" not in result.split("|")[1]  # Newline converted to space

    def test_markdown_table_empty_rows(self) -> None:
        """Test markdown_table with empty rows."""
        result = markdown_table([])
        assert "_No data_" in result

    def test_markdown_table_header_and_separator(self) -> None:
        """Test that table has header and separator rows."""
        rows = [{"id": 1, "name": "test"}]
        result = markdown_table(rows)
        lines = result.split("\n")
        assert len(lines) >= 3  # header, separator, at least one row


class TestBulletList:
    """Test bullet_list function."""

    def test_bullet_list_strings(self) -> None:
        """Test bullet list with string items."""
        items = ["item one", "item two", "item three"]
        result = bullet_list(items)
        assert "- item one" in result
        assert "- item two" in result
        assert "- item three" in result

    def test_bullet_list_dicts(self) -> None:
        """Test bullet list with dict items."""
        items = [{"key1": "value1"}, {"key2": "value2"}]
        result = bullet_list(items)
        assert "**key1**: value1" in result
        assert "**key2**: value2" in result

    def test_bullet_list_indentation(self) -> None:
        """Test bullet list with indentation."""
        items = ["item"]
        result = bullet_list(items, indent=1)
        assert "  - item" in result

    def test_bullet_list_multiple_indents(self) -> None:
        """Test bullet list with multiple indentation levels."""
        items = ["item"]
        result = bullet_list(items, indent=3)
        assert "      - item" in result

    def test_bullet_list_mixed_types(self) -> None:
        """Test bullet list with mixed string and dict items."""
        items = ["string item", {"key": "value"}]
        result = bullet_list(items)
        assert "- string item" in result
        assert "**key**: value" in result

    def test_bullet_list_empty(self) -> None:
        """Test bullet list with empty items."""
        result = bullet_list([])
        assert result == ""


class TestSection:
    """Test section function."""

    def test_section_heading_level_2(self) -> None:
        """Test section with default level 2."""
        result = section("Title", "Content here")
        assert "## Title" in result
        assert "Content here" in result

    def test_section_custom_level(self) -> None:
        """Test section with custom heading level."""
        result = section("Title", "Content", level=1)
        assert "# Title" in result

    def test_section_preserves_content(self) -> None:
        """Test that content is preserved exactly."""
        content = "Line 1\nLine 2\nLine 3"
        result = section("Title", content)
        assert content in result


class TestKeyValueBlock:
    """Test key_value_block function."""

    def test_key_value_block_basic(self) -> None:
        """Test basic key-value block."""
        data = {"name": "Alice", "age": 30}
        result = key_value_block(data)
        assert "**name**: Alice" in result
        assert "**age**: 30" in result

    def test_key_value_block_alignment(self) -> None:
        """Test key alignment."""
        data = {"short": "a", "very_long_key": "b"}
        result = key_value_block(data)
        # Keys should be padded to align
        assert "**" in result

    def test_key_value_block_custom_separator(self) -> None:
        """Test custom separator."""
        data = {"key": "value"}
        result = key_value_block(data, separator=" = ")
        assert "**key** = value" in result

    def test_key_value_block_empty(self) -> None:
        """Test empty key-value block."""
        result = key_value_block({})
        assert "_No data_" in result


class TestSummaryBox:
    """Test summary_box function."""

    def test_summary_box_basic(self) -> None:
        """Test basic summary box."""
        result = summary_box("Summary", {"count": 5, "status": "ok"})
        assert "## Summary" in result
        assert "count**: 5" in result
        assert "status**: ok" in result

    def test_summary_box_format(self) -> None:
        """Test summary box is properly formatted."""
        result = summary_box("Test", {"key": "value"})
        lines = result.split("\n")
        assert len(lines) >= 2


class TestFormatFindings:
    """Test format_findings function."""

    def test_format_findings_sorts_by_severity(self) -> None:
        """Test findings are sorted by severity."""
        findings = [
            {"severity": "info", "title": "Info Finding"},
            {"severity": "critical", "title": "Critical Finding"},
            {"severity": "medium", "title": "Medium Finding"},
        ]
        result = format_findings(findings)
        # Critical should appear before medium, medium before info
        critical_pos = result.find("Critical")
        medium_pos = result.find("Medium")
        info_pos = result.find("Info")
        assert critical_pos < medium_pos < info_pos

    def test_format_findings_custom_keys(self) -> None:
        """Test format_findings with custom keys."""
        findings = [
            {"level": "high", "issue": "Bad Thing", "details": "Description"}
        ]
        result = format_findings(
            findings,
            severity_key="level",
            title_key="issue",
            description_key="details",
        )
        assert "Bad Thing" in result
        assert "Description" in result

    def test_format_findings_empty(self) -> None:
        """Test format_findings with empty list."""
        result = format_findings([])
        assert "_No findings_" in result

    def test_format_findings_default_severity(self) -> None:
        """Test missing severity defaults to info."""
        findings = [{"title": "No Severity"}]
        result = format_findings(findings)
        assert "[INFO]" in result or "INFO" in result


class TestConversionFunctions:
    """Test to_markdown, to_html, to_json functions."""

    def test_to_markdown_basic(self) -> None:
        """Test markdown conversion."""
        sections = [
            {"title": "Section 1", "content": "Content 1"},
            {"title": "Section 2", "content": "Content 2"},
        ]
        result = to_markdown(sections)
        assert "## Section 1" in result
        assert "Content 1" in result

    def test_to_markdown_with_url(self) -> None:
        """Test markdown includes source URL."""
        sections = [
            {"title": "Title", "content": "Content", "url": "https://example.com"}
        ]
        result = to_markdown(sections)
        assert "Source" in result
        assert "https://example.com" in result

    def test_to_html_basic(self) -> None:
        """Test HTML conversion."""
        sections = [{"title": "Title", "content": "Content"}]
        result = to_html(sections)
        assert "<!DOCTYPE html>" in result
        assert "<h2>" in result
        assert "Title" in result

    def test_to_html_escapes_html(self) -> None:
        """Test HTML escaping."""
        sections = [{"title": "<script>alert('xss')</script>", "content": ""}]
        result = to_html(sections)
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_to_html_with_url(self) -> None:
        """Test HTML includes source URL."""
        sections = [
            {"title": "Title", "content": "Content", "url": "https://example.com"}
        ]
        result = to_html(sections)
        assert '<a href=' in result
        assert "https://example.com" in result

    def test_to_json_basic(self) -> None:
        """Test JSON conversion."""
        sections = [{"title": "Title", "content": "Content"}]
        result = to_json(sections)
        assert '"title"' in result
        assert '"content"' in result


class TestFormatReport:
    """Test format_report function."""

    def test_format_report_markdown(self) -> None:
        """Test format_report in markdown mode."""
        sections = [{"title": "Test", "content": "Data"}]
        result = format_report(sections, format="markdown")
        assert "## Test" in result

    def test_format_report_json(self) -> None:
        """Test format_report in JSON mode."""
        sections = [{"title": "Test", "content": "Data"}]
        result = format_report(sections, format="json")
        assert '"title"' in result

    def test_format_report_html(self) -> None:
        """Test format_report in HTML mode."""
        sections = [{"title": "Test", "content": "Data"}]
        result = format_report(sections, format="html")
        assert "<!DOCTYPE html>" in result

    def test_format_report_default_markdown(self) -> None:
        """Test format_report defaults to markdown."""
        sections = [{"title": "Test", "content": "Data"}]
        result = format_report(sections)
        assert "## Test" in result
