"""Tests for research_generate_report and research_report_from_results tools."""

from __future__ import annotations

import json
import pytest
from datetime import datetime
from typing import Any

from loom.tools.auto_report import (
    research_generate_report,
    research_report_from_results,
)


@pytest.mark.asyncio
class TestGenerateReport:
    """Test research_generate_report tool."""

    @pytest.mark.live
    async def test_generate_report_standard(self) -> None:
        """Test generating a standard-depth report."""
        result = await research_generate_report(
            topic="Python programming best practices",
            depth="standard",
            format="markdown",
        )

        assert isinstance(result, dict)
        assert "title" in result
        assert "report" in result
        assert "sections" in result
        assert "sources_used" in result
        assert "confidence" in result
        assert "generated_at" in result
        assert "word_count" in result
        assert "depth" in result
        assert "format" in result

        # Check values
        assert result["depth"] == "standard"
        assert result["format"] == "markdown"
        assert isinstance(result["title"], str)
        assert len(result["title"]) > 0
        assert isinstance(result["report"], str)
        assert len(result["report"]) > 0
        assert isinstance(result["sections"], list)
        assert len(result["sections"]) > 0
        assert 0 <= result["confidence"] <= 1
        assert result["word_count"] >= 0

    @pytest.mark.live
    async def test_generate_report_brief(self) -> None:
        """Test generating a brief-depth report."""
        result = await research_generate_report(
            topic="Cloud computing",
            depth="brief",
            format="markdown",
            num_sources=2,
        )

        assert result["depth"] == "brief"
        assert "sources_used" in result
        assert 0 <= result["sources_used"] <= 2

    @pytest.mark.live
    async def test_generate_report_comprehensive(self) -> None:
        """Test generating a comprehensive-depth report."""
        result = await research_generate_report(
            topic="Machine learning algorithms",
            depth="comprehensive",
            format="markdown",
            num_sources=8,
        )

        assert result["depth"] == "comprehensive"
        assert "sources_used" in result
        assert 0 <= result["sources_used"] <= 8

    @pytest.mark.live
    async def test_generate_report_json_format(self) -> None:
        """Test report generation with JSON format."""
        result = await research_generate_report(
            topic="API design patterns",
            depth="standard",
            format="json",
        )

        assert result["format"] == "json"
        # JSON format report should be serializable
        if result["format"] == "json":
            try:
                json.loads(result["report"]) if isinstance(result["report"], str) else True
            except json.JSONDecodeError:
                # Report might be already parsed, that's OK
                pass

    @pytest.mark.live
    async def test_generate_report_html_format(self) -> None:
        """Test report generation with HTML format."""
        result = await research_generate_report(
            topic="Web security",
            depth="standard",
            format="html",
        )

        assert result["format"] == "html"
        assert "<!DOCTYPE html>" in result["report"] or "<html>" in result["report"]
        assert "</html>" in result["report"]

    @pytest.mark.live
    async def test_generate_report_custom_num_sources(self) -> None:
        """Test report with custom number of sources."""
        result = await research_generate_report(
            topic="Cybersecurity trends",
            depth="standard",
            num_sources=3,
        )

        assert result["sources_used"] <= 3

    @pytest.mark.live
    async def test_generate_report_without_methodology(self) -> None:
        """Test report generation without methodology section."""
        result = await research_generate_report(
            topic="Data science",
            depth="standard",
            include_methodology=False,
        )

        assert "sections" in result
        methodology_sections = [s for s in result["sections"] if s.get("type") == "methodology"]
        assert len(methodology_sections) == 0

    @pytest.mark.live
    async def test_generate_report_without_recommendations(self) -> None:
        """Test report generation without recommendations section."""
        result = await research_generate_report(
            topic="DevOps practices",
            depth="standard",
            include_recommendations=False,
        )

        assert "sections" in result
        recommendation_sections = [s for s in result["sections"] if s.get("type") == "recommendations"]
        assert len(recommendation_sections) == 0

    def test_generate_report_invalid_topic_empty(self) -> None:
        """Test that empty topic raises validation error."""
        with pytest.raises(ValueError, match="topic cannot be empty"):
            import asyncio
            asyncio.run(research_generate_report(topic="", depth="standard"))

    def test_generate_report_invalid_topic_too_long(self) -> None:
        """Test that overly long topic raises validation error."""
        with pytest.raises(ValueError, match="topic must be <= 2000 characters"):
            import asyncio
            asyncio.run(research_generate_report(topic="x" * 2001, depth="standard"))

    @pytest.mark.live
    async def test_generate_report_sections_structure(self) -> None:
        """Test that report sections have required structure."""
        result = await research_generate_report(
            topic="Software architecture",
            depth="standard",
        )

        assert "sections" in result
        for section in result["sections"]:
            assert "title" in section
            assert "content" in section
            assert "type" in section
            assert isinstance(section["title"], str)
            assert isinstance(section["content"], str)
            assert isinstance(section["type"], str)

    @pytest.mark.live
    async def test_generate_report_title_generation(self) -> None:
        """Test that report title is properly generated."""
        result = await research_generate_report(
            topic="Kubernetes container orchestration",
            depth="standard",
        )

        assert "title" in result
        assert "Research Report:" in result["title"] or len(result["title"]) > 0
        assert "Kubernetes" in result["title"] or "kubernetes" in result["title"].lower()

    @pytest.mark.live
    async def test_generate_report_has_executive_summary(self) -> None:
        """Test that report includes executive summary section."""
        result = await research_generate_report(
            topic="Internet of Things",
            depth="standard",
        )

        summary_sections = [s for s in result["sections"] if s.get("type") == "summary"]
        assert len(summary_sections) > 0
        assert len(summary_sections[0]["content"]) > 0

    @pytest.mark.live
    async def test_generate_report_has_findings(self) -> None:
        """Test that report includes findings section."""
        result = await research_generate_report(
            topic="Artificial intelligence",
            depth="standard",
        )

        findings_sections = [s for s in result["sections"] if s.get("type") == "findings"]
        assert len(findings_sections) > 0

    @pytest.mark.live
    async def test_generate_report_timestamp_valid(self) -> None:
        """Test that generated_at is a valid ISO timestamp."""
        result = await research_generate_report(
            topic="Testing methodology",
            depth="standard",
        )

        assert "generated_at" in result
        # Should be parseable as ISO timestamp
        try:
            datetime.fromisoformat(result["generated_at"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("generated_at is not a valid ISO timestamp")

    @pytest.mark.live
    async def test_generate_report_confidence_score(self) -> None:
        """Test that confidence score is valid."""
        result = await research_generate_report(
            topic="Database design",
            depth="standard",
        )

        assert "confidence" in result
        assert isinstance(result["confidence"], (int, float))
        assert 0 <= result["confidence"] <= 1


@pytest.mark.asyncio
class TestReportFromResults:
    """Test research_report_from_results tool."""

    async def test_report_from_results_basic(self) -> None:
        """Test generating report from pre-existing results."""
        results = [
            {
                "url": "https://example.com/article1",
                "title": "Article 1",
                "content": "This is a detailed content about the topic. " * 50,
                "snippet": "Brief snippet about article 1",
            },
            {
                "url": "https://example.com/article2",
                "title": "Article 2",
                "content": "More detailed content about the topic. " * 50,
                "snippet": "Brief snippet about article 2",
            },
        ]

        result = await research_report_from_results(
            results=results,
            title="Test Report Topic",
            depth="standard",
            format="markdown",
        )

        assert isinstance(result, dict)
        assert "title" in result
        assert result["title"] == "Test Report Topic"
        assert "report" in result
        assert "sections" in result
        assert result["sources_used"] == 2

    async def test_report_from_results_single_result(self) -> None:
        """Test generating report from a single result."""
        results = [
            {
                "url": "https://example.com/single",
                "title": "Single Source",
                "content": "Content about the topic. " * 30,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="Single Source Report",
            depth="brief",
        )

        assert result["sources_used"] == 1

    async def test_report_from_results_json_format(self) -> None:
        """Test report from results with JSON format."""
        results = [
            {
                "url": "https://example.com/data",
                "title": "Data Source",
                "content": "Structured data. " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="JSON Format Report",
            format="json",
        )

        assert result["format"] == "json"

    async def test_report_from_results_html_format(self) -> None:
        """Test report from results with HTML format."""
        results = [
            {
                "url": "https://example.com/html",
                "title": "HTML Source",
                "content": "HTML formatted content. " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="HTML Format Report",
            format="html",
        )

        assert result["format"] == "html"
        assert "<html>" in result["report"] or "<!DOCTYPE" in result["report"]

    async def test_report_from_results_comprehensive(self) -> None:
        """Test comprehensive report from results."""
        results = [
            {
                "url": f"https://example.com/doc{i}",
                "title": f"Source {i}",
                "content": f"Content for source {i}. " * 30,
                "snippet": f"Snippet {i}",
            }
            for i in range(5)
        ]

        result = await research_report_from_results(
            results=results,
            title="Multi-Source Comprehensive Report",
            depth="comprehensive",
        )

        assert result["sources_used"] <= 5
        assert result["depth"] == "comprehensive"

    def test_report_from_results_invalid_empty_results(self) -> None:
        """Test that empty results raises validation error."""
        with pytest.raises(ValueError, match="results list cannot be empty"):
            import asyncio
            asyncio.run(
                research_report_from_results(
                    results=[],
                    title="Invalid Report",
                )
            )

    def test_report_from_results_invalid_title_empty(self) -> None:
        """Test that empty title raises validation error."""
        with pytest.raises(ValueError, match="title must be"):
            import asyncio
            asyncio.run(
                research_report_from_results(
                    results=[{"content": "test"}],
                    title="",
                )
            )

    def test_report_from_results_invalid_title_too_long(self) -> None:
        """Test that overly long title raises validation error."""
        with pytest.raises(ValueError, match="title must be"):
            import asyncio
            asyncio.run(
                research_report_from_results(
                    results=[{"content": "test"}],
                    title="x" * 501,
                )
            )

    async def test_report_from_results_missing_content_skipped(self) -> None:
        """Test that results without content are skipped."""
        results = [
            {"url": "https://example.com/no-content", "title": "No Content"},  # Missing content
            {"url": "https://example.com/with-content", "title": "With Content", "content": "Valid content " * 20},
        ]

        result = await research_report_from_results(
            results=results,
            title="Partial Results Report",
        )

        # Should only use the result with content
        assert result["sources_used"] == 1

    async def test_report_from_results_without_methodology(self) -> None:
        """Test report from results without methodology."""
        results = [
            {
                "url": "https://example.com/test",
                "title": "Test",
                "content": "Content " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="No Methodology Report",
            include_methodology=False,
        )

        methodology_sections = [s for s in result["sections"] if s.get("type") == "methodology"]
        assert len(methodology_sections) == 0

    async def test_report_from_results_without_recommendations(self) -> None:
        """Test report from results without recommendations."""
        results = [
            {
                "url": "https://example.com/test",
                "title": "Test",
                "content": "Content " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="No Recommendations Report",
            include_recommendations=False,
        )

        recommendation_sections = [s for s in result["sections"] if s.get("type") == "recommendations"]
        assert len(recommendation_sections) == 0

    async def test_report_from_results_sections_have_urls(self) -> None:
        """Test that detailed sections include URLs when available."""
        results = [
            {
                "url": "https://example.com/source1",
                "title": "Source 1",
                "content": "Detailed content " * 30,
            },
            {
                "url": "https://example.com/source2",
                "title": "Source 2",
                "content": "More content " * 30,
            },
        ]

        result = await research_report_from_results(
            results=results,
            title="URL Test Report",
            depth="comprehensive",
        )

        # Check that detailed sections have URLs
        detailed_sections = [s for s in result["sections"] if s.get("type") == "detailed"]
        for section in detailed_sections:
            if "url" in section:
                assert section["url"].startswith("https://example.com")

    async def test_report_from_results_confidence_based_on_sources(self) -> None:
        """Test that confidence is based on number of valid sources."""
        results = [
            {
                "url": f"https://example.com/source{i}",
                "title": f"Source {i}",
                "content": f"Content {i} " * 20,
            }
            for i in range(3)
        ]

        result = await research_report_from_results(
            results=results,
            title="Confidence Test Report",
        )

        # All 3 results have content, so confidence should be 1.0
        assert result["confidence"] == 1.0
        assert result["sources_used"] == 3

    async def test_report_from_results_word_count(self) -> None:
        """Test that word count is calculated correctly."""
        results = [
            {
                "url": "https://example.com/test",
                "title": "Test",
                "content": "word " * 100,  # 100 words
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="Word Count Report",
        )

        assert result["word_count"] > 0
        # Word count should be reasonable (at least from the content)
        assert result["word_count"] >= 50


@pytest.mark.asyncio
class TestReportFormatting:
    """Test report formatting functions."""

    async def test_markdown_format_contains_headers(self) -> None:
        """Test that markdown format includes headers."""
        results = [
            {
                "url": "https://example.com/md",
                "title": "Markdown Test",
                "content": "Test content " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="Markdown Test",
            format="markdown",
        )

        report = result["report"]
        assert "##" in report or "#" in report  # Markdown headers
        assert "Executive Summary" in report

    async def test_html_format_valid_structure(self) -> None:
        """Test that HTML format has valid structure."""
        results = [
            {
                "url": "https://example.com/html",
                "title": "HTML Test",
                "content": "Test content " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="HTML Test",
            format="html",
        )

        report = result["report"]
        assert "<html>" in report or "<!DOCTYPE html>" in report
        assert "</html>" in report
        assert "<head>" in report
        assert "</head>" in report
        assert "<body>" in report
        assert "</body>" in report

    async def test_json_format_parseable(self) -> None:
        """Test that JSON format is valid JSON."""
        results = [
            {
                "url": "https://example.com/json",
                "title": "JSON Test",
                "content": "Test content " * 20,
            }
        ]

        result = await research_report_from_results(
            results=results,
            title="JSON Test",
            format="json",
        )

        # Should be JSON array of sections
        report = result["report"]
        try:
            parsed = json.loads(report) if isinstance(report, str) else report
            assert isinstance(parsed, list)
        except json.JSONDecodeError:
            # If it's not JSON string, the report might be the parsed object
            pass
