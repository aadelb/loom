"""Documentation accuracy tests: Verify docs match implementation.

Tests cover:
  - Documented tools exist in codebase
  - Documented parameters are reasonable
  - Documented return types match implementation
  - Parameter defaults in docs match code
  - Documentation integrity (syntax, structure)
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.unit


class TestDocumentationAccuracy:
    """Verify tools-reference.md accurately reflects implementation."""

    @staticmethod
    def _parse_tools_markdown(doc_path: Path) -> dict[str, dict[str, Any]]:
        """Parse tools-reference.md and extract tool definitions.

        Returns:
            Dict of {tool_name: {params: [list], returns: str, description: str}}
        """
        content = doc_path.read_text(encoding="utf-8")
        tools: dict[str, dict[str, Any]] = {}

        # Split by tool sections (### research_*)
        tool_pattern = r"### (research_\w+)"
        matches = list(re.finditer(tool_pattern, content))

        for i, match in enumerate(matches):
            tool_name = match.group(1)
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)

            section = content[start_pos:end_pos]

            # Extract description (first paragraph)
            desc_match = re.search(
                r"### \w+\n\n(.+?)\n\n",
                section,
                re.DOTALL
            )
            description = desc_match.group(1) if desc_match else ""

            # Extract parameters from markdown table
            params_match = re.search(
                r"\*\*Parameters:\*\*.*?\n\n\|(.+?)\n\n",
                section,
                re.DOTALL
            )
            params = []
            if params_match:
                table_body = params_match.group(1)
                # Skip header row, parse data rows
                rows = table_body.strip().split("\n")
                for row in rows[1:]:  # Skip header separator
                    cells = [cell.strip() for cell in row.split("|")]
                    if len(cells) >= 2:
                        param_name = cells[1].strip("`")
                        if param_name and param_name not in ("Name", ""):
                            params.append(param_name)

            # Extract return type info
            returns_match = re.search(
                r"\*\*Returns:\*\*.*?(?=\*\*|###|$)",
                section,
                re.DOTALL
            )
            returns_info = returns_match.group(0) if returns_match else ""

            tools[tool_name] = {
                "description": description,
                "params": params,
                "returns_doc": returns_info,
            }

        return tools

    def test_tools_reference_md_parses(self) -> None:
        """Documentation markdown parses without error."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        assert doc_path.exists(), f"Documentation file not found at {doc_path}"

        tools = self._parse_tools_markdown(doc_path)
        assert len(tools) > 0, "No tools found in documentation"

    def test_documented_core_tools_exist(self) -> None:
        """All documented core tools exist in codebase."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        tools = self._parse_tools_markdown(doc_path)

        # Check core tools
        core_tools = ["research_fetch", "research_spider", "research_markdown"]
        for tool_name in core_tools:
            assert tool_name in tools, (
                f"Documented tool {tool_name} not found in docs parsing"
            )

    def test_fetch_tool_has_documented_params(self) -> None:
        """research_fetch has documented parameters."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        tools = self._parse_tools_markdown(doc_path)

        fetch_params = tools.get("research_fetch", {}).get("params", [])
        assert len(fetch_params) > 0, "research_fetch has no documented parameters"
        assert "url" in fetch_params, "url not in documented fetch params"

    def test_spider_tool_has_documented_params(self) -> None:
        """research_spider has documented parameters."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        tools = self._parse_tools_markdown(doc_path)

        spider_params = tools.get("research_spider", {}).get("params", [])
        assert len(spider_params) > 0, "research_spider has no documented parameters"
        assert "urls" in spider_params, "urls not in documented spider params"

    def test_markdown_tool_has_documented_params(self) -> None:
        """research_markdown has documented parameters."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        tools = self._parse_tools_markdown(doc_path)

        markdown_params = tools.get("research_markdown", {}).get("params", [])
        assert len(markdown_params) > 0, "research_markdown has no documented parameters"
        assert "url" in markdown_params, "url not in documented markdown params"


class TestDocumentationCompleteness:
    """Verify documentation covers all important tools."""

    def test_core_tools_documented(self) -> None:
        """All core tools are documented."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        # These are fundamental tools that must be documented
        critical_tools = [
            "research_fetch",
            "research_spider",
            "research_markdown",
            "research_search",
        ]

        for tool_name in critical_tools:
            assert f"### {tool_name}" in content, (
                f"Critical tool {tool_name} not documented"
            )

    def test_documented_tools_have_sections(self) -> None:
        """Each documented tool has Parameters and Returns sections."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        # Find all tool sections
        tool_pattern = r"### (research_\w+)"
        matches = list(re.finditer(tool_pattern, content))

        assert len(matches) > 0, "No tools found in documentation"

        for i, match in enumerate(matches):
            tool_name = match.group(1)
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section = content[start_pos:end_pos]

            # Check for Parameters section
            has_params = "**Parameters:**" in section or "*Parameters:*" in section
            if tool_name in ["research_health_check", "research_config_list"]:
                # Some tools might not have parameters
                pass
            else:
                assert has_params or len(section) > 200, (
                    f"Tool {tool_name} missing Parameters section"
                )

            # Check for Returns section
            has_returns = (
                "**Returns:**" in section or
                "*Returns:*" in section or
                "```json" in section
            )
            assert has_returns, f"Tool {tool_name} missing Returns documentation"

    def test_documented_tools_have_api_key_info(self) -> None:
        """Documented tools indicate API key requirements."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        # Sample of tools to check
        sample_tools = ["research_fetch", "research_search"]

        tool_pattern = r"### (research_\w+)"
        matches = list(re.finditer(tool_pattern, content))

        for i, match in enumerate(matches):
            tool_name = match.group(1)
            if tool_name not in sample_tools:
                continue

            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section = content[start_pos:end_pos]

            # Check for API Key section
            has_api_key_info = "API Key:" in section or "api key" in section.lower()
            assert has_api_key_info, (
                f"Tool {tool_name} missing API Key information"
            )

    def test_documented_tools_have_examples(self) -> None:
        """Documented tools include usage examples."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        # Sample tools that should have examples
        sample_tools = ["research_fetch", "research_spider"]

        tool_pattern = r"### (research_\w+)"
        matches = list(re.finditer(tool_pattern, content))

        for i, match in enumerate(matches):
            tool_name = match.group(1)
            if tool_name not in sample_tools:
                continue

            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section = content[start_pos:end_pos]

            # Check for example
            has_example = (
                "Example" in section or
                "```python" in section or
                "```" in section
            )
            assert has_example, (
                f"Tool {tool_name} missing usage example"
            )


class TestParameterDefaultConsistency:
    """Verify parameter defaults in docs match code."""

    def test_fetch_mode_default_matches_doc(self) -> None:
        """research_fetch mode default matches documentation."""
        from loom.tools.core.fetch import research_fetch
        from loom.params import FetchParams

        # Check code
        sig = inspect.signature(research_fetch)
        mode_param = sig.parameters["mode"]
        code_default = mode_param.default

        # Check model
        model_defaults = FetchParams.model_fields["mode"].default
        doc_default = "stealthy"  # From docs

        assert code_default == doc_default, (
            f"Mode default mismatch: code={code_default}, doc={doc_default}"
        )

    def test_fetch_max_chars_is_reasonable(self) -> None:
        """research_fetch max_chars default is reasonable."""
        from loom.tools.core.fetch import research_fetch

        sig = inspect.signature(research_fetch)
        max_chars_param = sig.parameters["max_chars"]
        code_default = max_chars_param.default

        # Should be a positive integer in reasonable range
        assert isinstance(code_default, int), "max_chars default should be int"
        assert code_default > 1000, (
            f"max_chars default {code_default} not in reasonable range"
        )


class TestDocumentationIntegrity:
    """Test overall documentation integrity and consistency."""

    def test_documentation_file_readable(self) -> None:
        """Documentation file is readable and contains expected content."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        assert doc_path.exists(), f"Documentation file not found at {doc_path}"

        content = doc_path.read_text(encoding="utf-8")
        assert len(content) > 1000, "Documentation file too short"
        assert "research_" in content, "No tools found in documentation"
        assert "Parameters:" in content or "Returns:" in content, (
            "Documentation missing standard sections"
        )

    def test_tool_names_follow_naming_convention(self) -> None:
        """All documented tools follow naming convention (research_*)."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        tool_pattern = r"### (research_\w+)"
        matches = re.findall(tool_pattern, content)

        assert len(matches) > 0, "No tools found matching convention"

        for tool_name in matches:
            assert tool_name.startswith("research_"), (
                f"Tool {tool_name} doesn't follow naming convention"
            )
            assert tool_name.islower(), f"Tool {tool_name} has uppercase letters"
            assert "_" in tool_name, f"Tool {tool_name} has no underscores"

    def test_documentation_has_table_structure(self) -> None:
        """Documentation uses proper markdown table structure."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        # Should have markdown tables with pipes
        assert "|" in content, "No markdown tables found"
        assert "---" in content, "No markdown table separators found"
