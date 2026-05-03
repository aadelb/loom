"""Unit tests for the 'loom tools' CLI command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

pytest.importorskip("loom.cli")

from loom.cli import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Typer CliRunner for CLI testing."""
    return CliRunner()


def _create_mock_tool(
    name: str,
    description: str = "Test tool",
    parameters: dict | None = None,
) -> MagicMock:
    """Helper to create a mock MCP tool object."""
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.title = name.replace("_", " ").title()

    if parameters:
        tool.inputSchema = {"properties": parameters}
    else:
        tool.inputSchema = {"properties": {}}

    return tool


class TestToolsCommand:
    """Tests for the 'loom tools' subcommand."""

    def test_tools_command_help(self, cli_runner: CliRunner) -> None:
        """loom tools --help prints help text."""
        result = cli_runner.invoke(app, ["tools", "--help"])

        assert result.exit_code == 0
        assert "List all available MCP tools" in result.stdout

    def test_tools_command_exists(self, cli_runner: CliRunner) -> None:
        """loom tools command is registered."""
        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools"])

            # Should execute without crashing
            assert result.exit_code == 0
            mock_create_app.assert_called_once()

    def test_tools_lists_tools(self, cli_runner: CliRunner) -> None:
        """loom tools displays all tools in a table."""
        tool1 = _create_mock_tool("research_fetch", "Fetch a URL")
        tool2 = _create_mock_tool("research_search", "Search across providers")

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[tool1, tool2])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools"])

            assert result.exit_code == 0
            assert "research_fetch" in result.stdout
            assert "research_search" in result.stdout
            assert "Loom MCP Tools" in result.stdout

    def test_tools_json_output(self, cli_runner: CliRunner) -> None:
        """loom tools --json outputs valid JSON."""
        tool1 = _create_mock_tool("research_fetch", "Fetch a URL")
        tool2 = _create_mock_tool("research_search", "Search across providers")

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[tool1, tool2])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools", "--json"])

            assert result.exit_code == 0
            # Verify valid JSON output
            data = json.loads(result.stdout)
            assert "tools" in data
            assert "count" in data
            assert data["count"] == 2
            assert len(data["tools"]) == 2
            assert data["tools"][0]["name"] == "research_fetch"
            assert data["tools"][1]["name"] == "research_search"

    def test_tools_category_filter(self, cli_runner: CliRunner) -> None:
        """loom tools --category filters tools by prefix."""
        llm_tool1 = _create_mock_tool("research_llm_summarize", "Summarize text")
        llm_tool2 = _create_mock_tool("research_llm_extract", "Extract structured data")
        fetch_tool = _create_mock_tool("research_fetch", "Fetch a URL")

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[llm_tool1, llm_tool2, fetch_tool])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools", "--category", "llm"])

            assert result.exit_code == 0
            assert "research_llm_summarize" in result.stdout
            assert "research_llm_extract" in result.stdout
            assert "research_fetch" not in result.stdout
            assert "(category: llm)" in result.stdout

    def test_tools_category_with_json(self, cli_runner: CliRunner) -> None:
        """loom tools --category --json filters and returns JSON."""
        llm_tool = _create_mock_tool("research_llm_summarize", "Summarize text")
        fetch_tool = _create_mock_tool("research_fetch", "Fetch a URL")

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[llm_tool, fetch_tool])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools", "--category", "llm", "--json"])

            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert data["count"] == 1
            assert data["tools"][0]["name"] == "research_llm_summarize"

    def test_tools_verbose_shows_parameters(self, cli_runner: CliRunner) -> None:
        """loom tools --verbose shows parameter information."""
        tool = _create_mock_tool(
            "research_fetch",
            "Fetch a URL",
            parameters={"url": {"type": "string"}, "mode": {"type": "string"}},
        )

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[tool])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools", "--verbose"])

            assert result.exit_code == 0
            assert "Parameters" in result.stdout
            # Parameters should be listed in the output
            assert "url" in result.stdout or "mode" in result.stdout

    def test_tools_verbose_json_includes_parameters(self, cli_runner: CliRunner) -> None:
        """loom tools --verbose --json includes parameter schema."""
        tool = _create_mock_tool(
            "research_fetch",
            "Fetch a URL",
            parameters={"url": {"type": "string"}, "mode": {"type": "string"}},
        )

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[tool])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools", "--verbose", "--json"])

            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert data["tools"][0]["name"] == "research_fetch"
            assert "parameters" in data["tools"][0]
            assert "url" in data["tools"][0]["parameters"]
            assert "mode" in data["tools"][0]["parameters"]

    def test_tools_category_nonexistent(self, cli_runner: CliRunner) -> None:
        """loom tools --category with nonexistent category prints message."""
        tool = _create_mock_tool("research_fetch", "Fetch a URL")

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[tool])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools", "--category", "nonexistent"])

            assert result.exit_code == 0
            assert "No tools found in category" in result.stderr

    def test_tools_shows_category_summary(self, cli_runner: CliRunner) -> None:
        """loom tools displays category summary when no filter."""
        fetch_tool = _create_mock_tool("research_fetch", "Fetch")
        spider_tool = _create_mock_tool("research_spider", "Spider")
        llm_tool = _create_mock_tool("research_llm_summarize", "Summarize")

        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[fetch_tool, spider_tool, llm_tool])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools"])

            assert result.exit_code == 0
            assert "Categories:" in result.stdout
            assert "fetch" in result.stdout or "Total:" in result.stdout

    def test_tools_empty_list(self, cli_runner: CliRunner) -> None:
        """loom tools handles empty tool list gracefully."""
        with patch("loom.server.create_app") as mock_create_app:
            mock_app = MagicMock()
            mock_app.list_tools = AsyncMock(return_value=[])
            mock_create_app.return_value = mock_app

            result = cli_runner.invoke(app, ["tools"])

            assert result.exit_code == 0
            # Should still display table, just with 0 tools
            assert "Total: 0 tools" in result.stdout
