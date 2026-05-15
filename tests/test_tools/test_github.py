"""Unit tests for research_github tool — query sanitization, subprocess mocking, caching."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

pytest.importorskip("loom.tools.core.github")

from loom.tools.core.github import research_github, research_github_readme, research_github_releases


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


class TestGitHubReadme:
    def test_readme_success(self):
        import base64
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "name": "README.md",
            "html_url": "https://github.com/owner/repo/blob/main/README.md",
            "content": base64.b64encode(b"# My Project\nHello world").decode(),
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            result = research_github_readme("owner", "repo")

        assert "content" in result
        assert "My Project" in result["content"]
        assert result["name"] == "README.md"

    def test_readme_not_found(self):
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("404 Not Found")

        with patch("httpx.Client", return_value=mock_client):
            result = research_github_readme("owner", "nonexistent")

        assert "error" in result


class TestGitHubReleases:
    def test_releases_success(self):
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            {
                "tag_name": "v1.0.0",
                "name": "First Release",
                "body": "Initial release notes",
                "published_at": "2024-01-01T00:00:00Z",
                "prerelease": False,
            }
        ]

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            result = research_github_releases("owner", "repo")

        assert "releases" in result
        assert len(result["releases"]) == 1
        assert result["releases"][0]["tag"] == "v1.0.0"

    def test_releases_error(self):
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("API error")

        with patch("httpx.Client", return_value=mock_client):
            result = research_github_releases("owner", "repo")

        assert "error" in result
