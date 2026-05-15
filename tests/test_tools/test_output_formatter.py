"""Tests for output_formatter tools."""

import pytest

from loom.tools.infrastructure.output_formatter import (
    research_extract_actionables,
    research_format_report,
)


class TestFormatReport:
    """Tests for research_format_report."""

    def test_format_report_json_extraction(self):
        """Test JSON format with structured sections."""
        text = """
        Executive Summary:
        This is a comprehensive overview of the project.

        Methodology:
        1. Gather requirements
        2. Design architecture
        3. Implement solution

        Tools Required:
        - Python 3.11+
        - FastAPI
        - PostgreSQL

        Timeline:
        Q1 2025

        Cost Breakdown:
        $5000 for development
        $1000 for infrastructure

        Risk Assessment:
        - Resource constraints
        - Timeline pressure
        """

        result = research_format_report(text, format="json")

        assert result["format"] == "json"
        assert result["word_count"] > 0
        assert "sections_extracted" in result
        assert isinstance(result["formatted"], dict)

        formatted = result["formatted"]
        assert "executive_summary" in formatted
        assert "methodology_steps" in formatted
        assert "tools_required" in formatted
        assert "cost_breakdown" in formatted

    def test_format_report_markdown(self):
        """Test markdown format output."""
        text = """
        Executive Summary: Project overview
        Tools Required: Python, Git
        """

        result = research_format_report(text, format="markdown")

        assert result["format"] == "markdown"
        assert isinstance(result["formatted"], str)
        assert "Executive" in result["formatted"] or "Tools" in result["formatted"]

    def test_format_report_executive_brief(self):
        """Test executive brief format."""
        text = """
        Executive Summary: This is a comprehensive overview.
        Timeline: 3 months
        Cost Breakdown: $10000 total
        Risk Assessment: High complexity, resource constraints
        """

        result = research_format_report(text, format="executive_brief")

        assert result["format"] == "executive_brief"
        assert isinstance(result["formatted"], str)
        # Brief should be shorter than full text
        assert len(result["formatted"]) < len(text)

    def test_format_report_technical_spec(self):
        """Test technical specification format."""
        text = """
        Executive Summary: Technical details
        Methodology:
        1. Analyze requirements
        2. Design system
        Tools Required:
        - FastAPI
        - PostgreSQL
        - Redis
        """

        result = research_format_report(text, format="technical_spec")

        assert result["format"] == "technical_spec"
        assert isinstance(result["formatted"], dict)

    def test_format_report_no_sections(self):
        """Test handling of unstructured text."""
        text = "This is just plain text without any structured sections."

        result = research_format_report(text, format="json")

        assert result["format"] == "json"
        assert result["word_count"] == 11
        assert "content" in result["sections_extracted"]

    def test_format_report_cost_extraction(self):
        """Test monetary value extraction."""
        text = """
        Cost Breakdown:
        $5000 for development
        €2500 for infrastructure
        £1000 for testing
        """

        result = research_format_report(text, format="json")
        costs = result["formatted"]["cost_breakdown"]

        assert len(costs) > 0
        assert any(c["currency"] == "$" for c in costs)
        assert any(c["currency"] == "€" for c in costs)
        assert any(c["currency"] == "£" for c in costs)

    def test_format_report_default_format(self):
        """Test default format is JSON."""
        text = "Executive Summary: Test"

        result = research_format_report(text)

        assert result["format"] == "json"


class TestExtractActionables:
    """Tests for research_extract_actionables."""

    def test_extract_actions_numbered_list(self):
        """Test extraction of numbered action items."""
        text = """
        Action Items:
        1. Review requirements
        2. Create design document
        3. Set up development environment
        4. Begin implementation
        """

        result = research_extract_actionables(text)

        assert len(result["actions"]) > 0
        assert any("requirements" in action.lower() for action in result["actions"])

    def test_extract_actions_todo_keywords(self):
        """Test extraction of TODO/FIXME keywords."""
        text = """
        TODO: Fix authentication module
        FIXME: Update documentation
        ACTION: Schedule team meeting
        SHOULD: Optimize database queries
        """

        result = research_extract_actionables(text)

        assert len(result["actions"]) > 0

    def test_extract_tools_mentioned(self):
        """Test extraction of tool names."""
        text = """
        Tools Needed:
        - Python 3.11
        - FastAPI Framework
        - PostgreSQL Database

        We will use Docker, Kubernetes, and Redis.
        """

        result = research_extract_actionables(text)

        assert len(result["tools_needed"]) > 0
        assert any("Python" in tool or "FastAPI" in tool for tool in result["tools_needed"])

    def test_extract_timeline_items(self):
        """Test extraction of timeline items."""
        text = """
        Timeline:
        Start Date: 2025-01-15
        Deadline: 2025-06-30

        Phase 1: 2 weeks
        Phase 2: 3 months
        Phase 3: 4 weeks
        """

        result = research_extract_actionables(text)

        assert len(result["timeline_items"]) > 0

    def test_extract_costs(self):
        """Test extraction of cost items."""
        text = """
        Budget Breakdown:
        $5000 - Development team
        $2500 - Infrastructure costs
        €1000 - Licensing fees

        Total investment: $8500
        """

        result = research_extract_actionables(text)

        assert len(result["costs"]) > 0
        costs_with_currency = [c for c in result["costs"] if "currency" in c]
        assert len(costs_with_currency) > 0

    def test_extract_risks(self):
        """Test extraction of risk items."""
        text = """
        Risk Assessment:
        - Resource constraints may impact timeline
        - Technical complexity could cause delays
        - Budget limitations might reduce scope

        Challenges:
        Integration with legacy systems
        Training requirements for team
        """

        result = research_extract_actionables(text)

        assert len(result["risks"]) > 0
        assert any("resource" in risk.lower() for risk in result["risks"])

    def test_extract_actionables_comprehensive(self):
        """Test comprehensive extraction from mixed content."""
        text = """
        PROJECT PLAN

        Actions:
        1. Create project board
        2. Assign team members
        3. Set up CI/CD

        TODO: Configure monitoring

        Tools: Python, Docker, Jenkins

        Timeline: Q1 2025 - Q2 2025

        Costs:
        $10000 - Infrastructure
        €5000 - Training

        Risks:
        - Unknown dependencies
        - Integration issues
        """

        result = research_extract_actionables(text)

        assert len(result["actions"]) > 0
        assert len(result["tools_needed"]) > 0
        assert len(result["timeline_items"]) > 0
        assert len(result["costs"]) > 0
        assert len(result["risks"]) > 0

    def test_extract_actionables_empty_text(self):
        """Test handling of empty or minimal text."""
        text = "Just some plain text."

        result = research_extract_actionables(text)

        assert isinstance(result["actions"], list)
        assert isinstance(result["tools_needed"], list)
        assert isinstance(result["timeline_items"], list)
        assert isinstance(result["costs"], list)
        assert isinstance(result["risks"], list)

    def test_extract_actionables_response_structure(self):
        """Test response structure matches specification."""
        text = "Sample content"

        result = research_extract_actionables(text)

        required_keys = {"actions", "tools_needed", "timeline_items", "costs", "risks"}
        assert required_keys.issubset(result.keys())

        assert isinstance(result["actions"], list)
        assert isinstance(result["tools_needed"], list)
        assert isinstance(result["timeline_items"], list)
        assert isinstance(result["costs"], list)
        assert isinstance(result["risks"], list)


class TestFormatReportIntegration:
    """Integration tests combining both tools."""

    def test_format_then_extract_actionables(self):
        """Test formatting followed by actionable extraction."""
        raw_text = """
        Executive Summary: Platform redesign project

        Methodology:
        1. Conduct user research
        2. Create wireframes
        3. Build prototypes
        4. Launch MVP

        Tools Required:
        - Figma for design
        - React for frontend
        - Node.js for backend

        Timeline: 6 months

        Cost Breakdown:
        $50000 - Development
        $10000 - Design

        Risk Assessment:
        - Budget overruns
        - Scope creep
        """

        # First format the report
        formatted = research_format_report(raw_text, format="json")
        assert formatted["format"] == "json"

        # Then extract actionables from original text
        actionables = research_extract_actionables(raw_text)
        assert len(actionables["actions"]) > 0
        assert len(actionables["costs"]) > 0

    def test_multiple_formats_same_content(self):
        """Test that multiple formats can be applied to same content."""
        text = """
        Executive Summary: Comprehensive overview
        Timeline: 3 months
        Cost Breakdown: $15000 total
        """

        json_result = research_format_report(text, format="json")
        md_result = research_format_report(text, format="markdown")
        brief_result = research_format_report(text, format="executive_brief")

        assert json_result["format"] == "json"
        assert md_result["format"] == "markdown"
        assert brief_result["format"] == "executive_brief"

        # All should extract same word count
        assert json_result["word_count"] == md_result["word_count"]
        assert md_result["word_count"] == brief_result["word_count"]
