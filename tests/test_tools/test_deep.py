"""Unit tests for research_deep tool — updated for v2 pipeline return shape."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("loom.tools.deep")

from loom.tools.deep import research_deep

_MOCK_CONFIG: dict = {
    "RESEARCH_SEARCH_PROVIDERS": ["exa"],
    "RESEARCH_EXPAND_QUERIES": False,
    "RESEARCH_EXTRACT": False,
    "RESEARCH_SYNTHESIZE": False,
    "RESEARCH_GITHUB_ENRICHMENT": False,
    "RESEARCH_MAX_COST_USD": 0.50,
    "SPIDER_CONCURRENCY": 5,
    "FETCH_AUTO_ESCALATE": True,
}


def _mock_fetch(url, **kwargs):
    return {"url": url, "text": "content", "tool": "httpx"}


@pytest.mark.asyncio
async def test_deep_returns_expected_shape() -> None:
    """research_deep returns dict with new v2 shape."""
    mock_search = MagicMock(
        return_value={
            "results": [
                {"url": "https://example.com/1", "title": "Example 1", "score": 0.9},
                {"url": "https://example.com/2", "title": "Example 2", "score": 0.8},
            ],
            "provider": "exa",
        }
    )

    mock_markdown = AsyncMock(
        side_effect=[
            {"url": "https://example.com/1", "title": "Example 1", "markdown": "M" * 200},
            {"url": "https://example.com/2", "title": "Example 2", "markdown": "M" * 200},
        ]
    )

    with (
        patch("loom.config.get_config", return_value=_MOCK_CONFIG),
        patch("loom.tools.deep.research_search", mock_search),
        patch("loom.tools.deep.research_markdown", mock_markdown),
        patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch),
    ):
        result = await research_deep(query="test query", expand_queries=False)

    assert result["query"] == "test query"
    assert "top_pages" in result
    assert "pages_fetched" in result
    assert "providers_used" in result
    assert "elapsed_ms" in result


@pytest.mark.asyncio
async def test_deep_handles_search_failure() -> None:
    """research_deep returns error when search fails."""
    mock_search = MagicMock(side_effect=ValueError("Search API error"))

    with (
        patch("loom.config.get_config", return_value=_MOCK_CONFIG),
        patch("loom.tools.deep.research_search", mock_search),
    ):
        result = await research_deep(query="test query", expand_queries=False)

    assert result["top_pages"] == []
    assert result["pages_fetched"] == 0


@pytest.mark.asyncio
async def test_deep_handles_markdown_failure() -> None:
    """research_deep returns partial results when markdown fetch fails."""
    mock_search = MagicMock(
        return_value={
            "results": [
                {"url": "https://example.com/1", "title": "Example 1", "score": 0.9},
                {"url": "https://example.com/2", "title": "Example 2", "score": 0.8},
            ],
            "provider": "exa",
        }
    )

    mock_markdown = AsyncMock(
        side_effect=[
            {"url": "https://example.com/1", "title": "Ex 1", "markdown": "M" * 200},
            ValueError("Markdown extraction failed"),
        ]
    )

    with (
        patch("loom.config.get_config", return_value=_MOCK_CONFIG),
        patch("loom.tools.deep.research_search", mock_search),
        patch("loom.tools.deep.research_markdown", mock_markdown),
        patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch),
    ):
        result = await research_deep(query="test query", expand_queries=False)

    assert len(result["top_pages"]) >= 1


@pytest.mark.asyncio
async def test_deep_respects_depth_parameter() -> None:
    """research_deep with depth=1 limits results."""
    search_results = [
        {"url": f"https://example.com/{i}", "title": f"Result {i}", "score": 0.5} for i in range(20)
    ]

    mock_search = MagicMock(return_value={"results": search_results, "provider": "exa"})

    mock_markdown = AsyncMock(
        return_value={"url": "https://example.com", "title": "T", "markdown": "M" * 200}
    )

    with (
        patch("loom.config.get_config", return_value=_MOCK_CONFIG),
        patch("loom.tools.deep.research_search", mock_search),
        patch("loom.tools.deep.research_markdown", mock_markdown),
        patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch),
    ):
        result = await research_deep(query="test", depth=1, expand_queries=False)

    assert result["pages_fetched"] <= 3


@pytest.mark.asyncio
async def test_deep_empty_query() -> None:
    """research_deep handles empty query gracefully."""
    mock_search = MagicMock(return_value={"results": [], "provider": "exa"})

    with (
        patch("loom.config.get_config", return_value=_MOCK_CONFIG),
        patch("loom.tools.deep.research_search", mock_search),
    ):
        result = await research_deep(query="", expand_queries=False)

    assert result["top_pages"] == [] or "error" in result
