"""Tests for auto-documentation generator tools."""

from __future__ import annotations

import pytest

from loom.tools.infrastructure.auto_docs import research_generate_docs, research_docs_coverage


@pytest.mark.asyncio
class TestAutoDocsGenerator:
    """Test auto-documentation generation."""

    async def test_generate_docs_markdown(self) -> None:
        """Test generating markdown documentation."""
        result = await research_generate_docs(output_format="markdown", include_params=True)

        assert result["format"] == "markdown"
        assert result["total_tools"] > 0
        assert "documentation" in result
        assert isinstance(result["documentation"], str)
        assert "Loom Tools Reference" in result["documentation"]
        assert "# " in result["documentation"]  # Markdown headers

    async def test_generate_docs_json(self) -> None:
        """Test generating JSON documentation."""
        result = await research_generate_docs(output_format="json", include_params=True)

        assert result["format"] == "json"
        assert result["total_tools"] > 0
        assert "tools" in result
        assert isinstance(result["tools"], dict)
        assert "grouped_by_file" in result

    async def test_generate_docs_no_params(self) -> None:
        """Test generating documentation without parameters."""
        result = await research_generate_docs(output_format="markdown", include_params=False)

        assert result["format"] == "markdown"
        assert "documentation" in result
        # Should still have documentation, just without params list
        assert len(result["documentation"]) > 0

    async def test_docs_coverage(self) -> None:
        """Test documentation coverage report."""
        result = await research_docs_coverage()

        assert result["total_tools"] > 0
        assert result["documented"] >= 0
        assert result["documented"] <= result["total_tools"]
        assert "undocumented" in result
        assert isinstance(result["undocumented"], list)
        assert "coverage_pct" in result
        assert 0 <= result["coverage_pct"] <= 100
        assert "files_with_no_docs" in result
        assert isinstance(result["files_with_no_docs"], list)

    async def test_coverage_consistency(self) -> None:
        """Test that coverage numbers are internally consistent."""
        result = await research_docs_coverage()

        # Verify math
        expected_coverage = (result["documented"] / result["total_tools"] * 100) if result["total_tools"] > 0 else 0
        assert abs(result["coverage_pct"] - round(expected_coverage, 1)) < 0.2

        # Verify undocumented count
        assert len(result["undocumented"]) == result["total_tools"] - result["documented"]

    async def test_generated_docs_has_tools(self) -> None:
        """Test that generated documentation includes actual tools."""
        result = await research_generate_docs(output_format="markdown")

        # Should have markdown table structure
        assert "|" in result["documentation"]
        assert "Tool" in result["documentation"]
        assert "Description" in result["documentation"]

    async def test_json_tools_structure(self) -> None:
        """Test JSON output tool structure."""
        result = await research_generate_docs(output_format="json")

        # Pick a tool and verify structure
        if result["tools"]:
            tool_name = next(iter(result["tools"]))
            tool = result["tools"][tool_name]

            assert "name" in tool
            assert "docstring" in tool
            assert "parameters" in tool
            assert "return_type" in tool
            assert "file" in tool
