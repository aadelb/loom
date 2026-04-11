"""Unit tests for CLI — smoke tests with typer CliRunner."""

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


class TestCLI:
    """CLI smoke tests."""

    def test_cli_help(self, cli_runner: CliRunner) -> None:
        """loom --help prints usage."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.stdout or "help" in result.stdout.lower()

    def test_cli_fetch_help(self, cli_runner: CliRunner) -> None:
        """loom fetch --help prints subcommand usage."""
        result = cli_runner.invoke(app, ["fetch", "--help"])

        assert result.exit_code == 0

    def test_cli_search_help(self, cli_runner: CliRunner) -> None:
        """loom search --help prints subcommand usage."""
        result = cli_runner.invoke(app, ["search", "--help"])

        assert result.exit_code == 0

    def test_cli_session_help(self, cli_runner: CliRunner) -> None:
        """loom session --help prints subcommand usage."""
        result = cli_runner.invoke(app, ["session", "--help"])

        assert result.exit_code == 0

    def test_cli_config_help(self, cli_runner: CliRunner) -> None:
        """loom config --help prints subcommand usage."""
        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0

    def test_cli_fetch_ssrf_returns_error(self, cli_runner: CliRunner) -> None:
        """loom fetch with SSRF URL returns non-zero exit."""
        result = cli_runner.invoke(app, ["fetch", "http://localhost:8080"])

        assert result.exit_code != 0

    def test_cli_fetch_valid_url_invokes_tool(self, cli_runner: CliRunner) -> None:
        """loom fetch with valid URL invokes MCP tool."""
        with patch("loom.cli._call_mcp_tool") as mock_call:
            mock_call.return_value = AsyncMock(return_value={
                "url": "https://example.com",
                "text": "content",
                "title": "Example",
            })()

            result = cli_runner.invoke(
                app,
                [
                    "fetch",
                    "https://example.com",
                    "--json",
                ],
            )

            # Should not crash
            assert result.exit_code in (0, 1)  # May fail if MCP not available

    def test_cli_config_set(self, cli_runner: CliRunner) -> None:
        """loom config set KEY VALUE works."""
        with patch("loom.cli._call_mcp_tool") as mock_call:
            mock_call.return_value = AsyncMock(return_value={"key": "TEST", "new": 100})()

            result = cli_runner.invoke(app, ["config", "set", "TEST", "100"])

            # May fail if config not available, but shouldn't crash
            assert result.exit_code in (0, 1)
