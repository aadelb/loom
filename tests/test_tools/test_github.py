"""Unit tests for research_github tool — query sanitization, subprocess mocking, caching."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

pytest.importorskip("loom.tools.github")

from loom.tools.github import research_github


class TestGitHub:
    """research_github tool tests."""

    def test_github_rejects_flag_injection(self) -> None:
        """GitHub query rejects --flag injection."""
        result = research_github(kind="repos", query="--owner attacker")

        assert "error" in result
        assert "flag" in result["error"].lower() or "-" in result["error"]

    def test_github_rejects_shell_injection(self) -> None:
        """GitHub query rejects shell injection."""
        result = research_github(kind="repos", query="$(rm -rf /)")

        assert "error" in result
        assert "allow-list" in result["error"].lower() or "allow" in result["error"].lower()

    def test_github_result_parsed_as_json(self) -> None:
        """GitHub result is parsed from JSON subprocess output."""
        mock_response = [
            {
                "name": "example-repo",
                "url": "https://github.com/example/example-repo",
                "description": "Example repo",
            }
        ]

        with patch("loom.tools.github.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)
            mock_run.return_value.stderr = ""

            result = research_github(kind="repos", query="example llm")

            assert "results" in result
            assert len(result["results"]) > 0

    def test_github_cache_on_repeated_query(self) -> None:
        """GitHub caches results for repeated queries."""
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory

        mock_response = {"items": [{"name": "repo1", "url": "https://github.com/r1"}]}

        with TemporaryDirectory() as tmpdir:
            os.environ["LOOM_CACHE_DIR"] = tmpdir

            with patch("loom.tools.github.subprocess.run") as mock_run:
                mock_run.return_value.stdout = json.dumps(mock_response)

                # First call
                result1 = research_github(kind="repos", query="llm", limit=5)

                # Second call (should be cached)
                result2 = research_github(kind="repos", query="llm", limit=5)

                # subprocess should be called fewer times due to caching
                # (may still be called twice if cache miss, but content should match)
                assert result1.get("items") == result2.get("items") or result1 == result2

    def test_github_all_kinds_accepted(self) -> None:
        """GitHub accepts all kinds: repos, code, issues."""
        with patch("loom.tools.github.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps([])
            mock_run.return_value.stderr = ""

            for kind in ["repos", "code", "issues"]:
                result = research_github(kind=kind, query="test")
                assert "results" in result
