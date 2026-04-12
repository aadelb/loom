"""Comprehensive CLI smoke tests for Loom — all subcommands and functional scenarios.

Tests:
  - Help output for all 14 subcommands (verify exit_code=0)
  - Functional tests with mocked MCP tool calls
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

pytest.importorskip("loom.cli")

from loom.cli import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Typer CliRunner for CLI testing."""
    return CliRunner()


class TestHelpOutput:
    """Help output tests for all subcommands."""

    def test_serve_help(self, cli_runner: CliRunner) -> None:
        """loom serve --help shows help."""
        result = cli_runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "serve" in result.stdout.lower()

    def test_fetch_help(self, cli_runner: CliRunner) -> None:
        """loom fetch --help shows help."""
        result = cli_runner.invoke(app, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "fetch" in result.stdout.lower()

    def test_spider_help(self, cli_runner: CliRunner) -> None:
        """loom spider --help shows help."""
        result = cli_runner.invoke(app, ["spider", "--help"])
        assert result.exit_code == 0
        assert "spider" in result.stdout.lower()

    def test_markdown_help(self, cli_runner: CliRunner) -> None:
        """loom markdown --help shows help."""
        result = cli_runner.invoke(app, ["markdown", "--help"])
        assert result.exit_code == 0
        assert "markdown" in result.stdout.lower()

    def test_search_help(self, cli_runner: CliRunner) -> None:
        """loom search --help shows help."""
        result = cli_runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.stdout.lower()

    def test_deep_help(self, cli_runner: CliRunner) -> None:
        """loom deep --help shows help."""
        result = cli_runner.invoke(app, ["deep", "--help"])
        assert result.exit_code == 0
        assert "deep" in result.stdout.lower()

    def test_github_help(self, cli_runner: CliRunner) -> None:
        """loom github --help shows help."""
        result = cli_runner.invoke(app, ["github", "--help"])
        assert result.exit_code == 0
        assert "github" in result.stdout.lower()

    def test_camoufox_help(self, cli_runner: CliRunner) -> None:
        """loom camoufox --help shows help."""
        result = cli_runner.invoke(app, ["camoufox", "--help"])
        assert result.exit_code == 0
        assert "camoufox" in result.stdout.lower()

    def test_botasaurus_help(self, cli_runner: CliRunner) -> None:
        """loom botasaurus --help shows help."""
        result = cli_runner.invoke(app, ["botasaurus", "--help"])
        assert result.exit_code == 0
        assert "botasaurus" in result.stdout.lower()

    def test_session_help(self, cli_runner: CliRunner) -> None:
        """loom session --help shows help."""
        result = cli_runner.invoke(app, ["session", "--help"])
        assert result.exit_code == 0
        assert "session" in result.stdout.lower()

    def test_config_help(self, cli_runner: CliRunner) -> None:
        """loom config --help shows help."""
        result = cli_runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.stdout.lower()

    def test_cache_help(self, cli_runner: CliRunner) -> None:
        """loom cache --help shows help."""
        result = cli_runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0
        assert "cache" in result.stdout.lower()

    def test_llm_help(self, cli_runner: CliRunner) -> None:
        """loom llm --help shows help."""
        result = cli_runner.invoke(app, ["llm", "--help"])
        assert result.exit_code == 0
        assert "llm" in result.stdout.lower()

    def test_journey_test_help(self, cli_runner: CliRunner) -> None:
        """loom journey-test --help shows help."""
        result = cli_runner.invoke(app, ["journey-test", "--help"])
        assert result.exit_code == 0
        assert "journey" in result.stdout.lower()

    def test_install_browsers_help(self, cli_runner: CliRunner) -> None:
        """loom install-browsers --help shows help."""
        result = cli_runner.invoke(app, ["install-browsers", "--help"])
        assert result.exit_code == 0
        assert "install" in result.stdout.lower() or "browser" in result.stdout.lower()


class TestFunctional:
    """Functional tests with mocked MCP calls."""

    def test_config_list_invokes_mcp(self, cli_runner: CliRunner) -> None:
        """loom config list invokes research_config_get MCP tool."""
        with patch("loom.cli._call_mcp_tool") as mock_call:
            mock_call.return_value = AsyncMock(return_value={"config": "data"})()

            result = cli_runner.invoke(app, ["config", "list"])

            # May fail if server unavailable, but should call the tool
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][1] == "research_config_get"

    def test_cache_stats_invokes_mcp(self, cli_runner: CliRunner) -> None:
        """loom cache stats invokes research_cache_stats MCP tool."""
        with patch("loom.cli._call_mcp_tool") as mock_call:
            mock_call.return_value = AsyncMock(return_value={"stats": "data"})()

            result = cli_runner.invoke(app, ["cache", "stats"])

            # May fail if server unavailable, but should call the tool
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][1] == "research_cache_stats"
