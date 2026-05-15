"""Tests for experts research tool."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clear_module_cache():
    """Ensure clean import state for each test."""
    sys.modules.pop("loom.tools.llm.experts", None)
    yield
    sys.modules.pop("loom.tools.llm.experts", None)


@pytest.mark.asyncio
class TestResearchFindExperts:
    async def test_basic_search(self):
        mock_github_result = {
            "results": [
                {"name": "user1/repo1", "stars": 100, "url": "https://github.com/user1/repo1"},
                {"name": "user2/repo2", "stars": 50, "url": "https://github.com/user2/repo2"},
            ]
        }

        mock_arxiv_result = {
            "results": [
                {
                    "title": "Paper 1",
                    "authors": ["user1", "user3"],
                    "url": "https://arxiv.org/1",
                    "published_date": "2024-01-01",
                }
            ]
        }

        with (
            patch("loom.tools.core.github.research_github", return_value=mock_github_result),
            patch("loom.providers.arxiv_search.search_arxiv", return_value=mock_arxiv_result),
        ):
            from loom.tools.llm.experts import research_find_experts

            result = await research_find_experts("machine learning", n=5)

        assert "query" in result
        assert "experts" in result
        assert "total_found" in result
        assert result["query"] == "machine learning"
        assert len(result["experts"]) == 3

        # user1 should have 2 sources (github, arxiv) and multiple mentions
        user1 = next(e for e in result["experts"] if e["name"] == "user1")
        assert len(user1["sources"]) == 2
        assert user1["mentions"] >= 2

    async def test_no_results_from_github(self):
        mock_arxiv_result = {
            "results": [
                {
                    "title": "Paper 1",
                    "authors": ["author1"],
                    "url": "https://arxiv.org/1",
                    "published_date": "2024-01-01",
                }
            ]
        }

        with (
            patch("loom.tools.core.github.research_github", return_value={"results": []}),
            patch("loom.providers.arxiv_search.search_arxiv", return_value=mock_arxiv_result),
        ):
            from loom.tools.llm.experts import research_find_experts

            result = await research_find_experts("topic", n=5)

        assert len(result["experts"]) == 1
        assert result["experts"][0]["name"] == "author1"
        assert result["experts"][0]["sources"] == ["arxiv"]

    async def test_no_results_from_arxiv(self):
        mock_github_result = {
            "results": [
                {"name": "user1/repo1", "stars": 100, "url": "https://github.com/user1/repo1"}
            ]
        }

        with (
            patch("loom.tools.core.github.research_github", return_value=mock_github_result),
            patch("loom.providers.arxiv_search.search_arxiv", return_value={"results": []}),
        ):
            from loom.tools.llm.experts import research_find_experts

            result = await research_find_experts("topic", n=5)

        assert len(result["experts"]) == 1
        assert result["experts"][0]["name"] == "user1"
        assert result["experts"][0]["sources"] == ["github"]
