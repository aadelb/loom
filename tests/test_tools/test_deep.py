"""Unit tests for research_deep tool — search + markdown chaining."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("loom.tools.deep")

from loom.tools.deep import research_deep


@pytest.mark.asyncio
async def test_deep_returns_expected_shape() -> None:
    """research_deep returns dict with query, results list with url/title/markdown."""
    mock_search = MagicMock(
        return_value={
            "results": [
                {"url": "https://example.com/1", "title": "Example 1"},
                {"url": "https://example.com/2", "title": "Example 2"},
            ],
            "provider": "test_provider",
        }
    )

    mock_markdown = AsyncMock(
        side_effect=[
            {"url": "https://example.com/1", "markdown": "# Example 1\nContent 1"},
            {"url": "https://example.com/2", "markdown": "# Example 2\nContent 2"},
        ]
    )

    with patch("loom.tools.search.research_search", mock_search):
        with patch("loom.tools.markdown.research_markdown", mock_markdown):
            result = await research_deep(query="test query")

    assert result["query"] == "test query"
    assert "pages" in result
    assert len(result["pages"]) == 2
    assert result["pages"][0]["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_deep_handles_search_failure() -> None:
    """research_deep returns error when search fails."""
    mock_search = MagicMock(side_effect=ValueError("Search API error"))

    with patch("loom.tools.search.research_search", mock_search):
        result = await research_deep(query="test query")

    assert "error" in result
    assert result["pages"] == []
    assert result["hit_count"] == 0


@pytest.mark.asyncio
async def test_deep_handles_markdown_failure() -> None:
    """research_deep returns partial results when markdown fetch fails."""
    mock_search = MagicMock(
        return_value={
            "results": [
                {"url": "https://example.com/1", "title": "Example 1"},
                {"url": "https://example.com/2", "title": "Example 2"},
            ],
            "provider": "test_provider",
        }
    )

    # First markdown succeeds, second fails
    mock_markdown = AsyncMock(
        side_effect=[
            {"url": "https://example.com/1", "markdown": "# Content 1"},
            ValueError("Markdown extraction failed"),
        ]
    )

    with patch("loom.tools.search.research_search", mock_search):
        with patch("loom.tools.markdown.research_markdown", mock_markdown):
            result = await research_deep(query="test query")

    # Should return partial results
    assert len(result["pages"]) == 1
    assert result["pages"][0]["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_deep_respects_depth_parameter() -> None:
    """research_deep with depth=2 limits URL fetches."""
    search_results = [
        {"url": f"https://example.com/{i}", "title": f"Result {i}"}
        for i in range(10)
    ]

    mock_search = MagicMock(
        return_value={
            "results": search_results,
            "provider": "test_provider",
        }
    )

    mock_markdown = AsyncMock(
        return_value={"url": "https://example.com", "markdown": "Content"}
    )

    with patch("loom.tools.search.research_search", mock_search):
        with patch("loom.tools.markdown.research_markdown", mock_markdown):
            result = await research_deep(query="test", depth=2)

    # With depth=2, should limit to depth*3 = 6 URLs
    assert mock_markdown.call_count <= 6
    assert result["hit_count"] <= 6


@pytest.mark.asyncio
async def test_deep_validates_query_empty() -> None:
    """research_deep handles empty query gracefully."""
    mock_search = MagicMock(
        return_value={"results": [], "provider": None}
    )

    with patch("loom.tools.search.research_search", mock_search):
        result = await research_deep(query="")

    assert result["pages"] == [] or "error" in result
