"""Unit tests for research_markdown tool — Crawl4AI async markdown extractor."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("loom.tools.markdown")

from loom.tools.markdown import research_markdown


# Create a mock crawl4ai module for testing
@pytest.fixture
def mock_crawl4ai():
    """Inject mock crawl4ai module into sys.modules."""
    # Remove real crawl4ai if it exists
    old_crawl4ai = sys.modules.pop("crawl4ai", None)

    mock_module = MagicMock()
    mock_module.AsyncWebCrawler = MagicMock()
    sys.modules["crawl4ai"] = mock_module
    yield mock_module

    # Cleanup
    if "crawl4ai" in sys.modules:
        del sys.modules["crawl4ai"]
    if old_crawl4ai is not None:
        sys.modules["crawl4ai"] = old_crawl4ai


class TestMarkdownReturnsExpectedShape:
    """Test research_markdown returns correct data structure."""

    @pytest.mark.asyncio
    async def test_markdown_returns_expected_shape(self, mock_crawl4ai) -> None:
        """research_markdown returns dict with url, title, markdown, tool, fetched_at."""
        # Mock Crawl4AI AsyncWebCrawler
        mock_result = MagicMock()
        mock_result.markdown = "# Title\n\nContent here"
        mock_result.metadata = {"title": "Page Title"}

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)

        mock_crawl4ai.AsyncWebCrawler.return_value = mock_crawler

        result = await research_markdown(url="https://example.com")

        assert "url" in result
        assert result["url"] == "https://example.com"
        assert "title" in result
        assert result["title"] == "Page Title"
        assert "markdown" in result
        assert result["markdown"] == "# Title\n\nContent here"
        assert "tool" in result
        assert result["tool"] == "crawl4ai"
        assert "fetched_at" in result


class TestMarkdownHandlesImportError:
    """Test research_markdown gracefully handles Crawl4AI import failures."""

    @pytest.mark.asyncio
    async def test_markdown_handles_import_error(self) -> None:
        """research_markdown returns error when Crawl4AI unavailable."""
        # Remove crawl4ai from sys.modules to simulate import not available
        if "crawl4ai" in sys.modules:
            del sys.modules["crawl4ai"]

        # Mock the import to raise ImportError for a unique URL
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "crawl4ai":
                raise ImportError("crawl4ai not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Use bypass_cache to ensure we don't get a cached result
            result = await research_markdown(
                url="https://example.com/import-error-test", bypass_cache=True
            )

        assert "error" in result
        assert "crawl4ai not available" in result["error"]
        assert result["url"] == "https://example.com/import-error-test"
        assert result["tool"] == "crawl4ai"


class TestMarkdownRespectsMaxChars:
    """Test research_markdown respects max character limit."""

    @pytest.mark.asyncio
    async def test_markdown_respects_max_chars(self, mock_crawl4ai) -> None:
        """research_markdown caps markdown output at 30000 chars."""
        # Create markdown larger than 30000 chars
        large_markdown = "x" * 35000

        mock_result = MagicMock()
        mock_result.markdown = large_markdown
        mock_result.metadata = {"title": "Page"}

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)

        mock_crawl4ai.AsyncWebCrawler.return_value = mock_crawler

        result = await research_markdown(url="https://example.com/large")

        # Should be capped at 30000
        assert len(result["markdown"]) <= 30000
        assert len(result["markdown"]) == 30000


class TestMarkdownValidatesUrlSsrf:
    """Test research_markdown rejects private IPs (SSRF protection)."""

    @pytest.mark.asyncio
    async def test_markdown_rejects_localhost(self) -> None:
        """research_markdown rejects localhost URLs."""
        with pytest.raises(Exception):  # Should raise UrlSafetyError
            await research_markdown(url="http://localhost:8080/page")

    @pytest.mark.asyncio
    async def test_markdown_rejects_private_ip(self) -> None:
        """research_markdown rejects private IP addresses."""
        with pytest.raises(Exception):  # Should raise UrlSafetyError
            await research_markdown(url="http://192.168.1.1/admin")

    @pytest.mark.asyncio
    async def test_markdown_rejects_loopback(self) -> None:
        """research_markdown rejects loopback IP."""
        with pytest.raises(Exception):  # Should raise UrlSafetyError
            await research_markdown(url="http://127.0.0.1/page")

    @pytest.mark.asyncio
    async def test_markdown_rejects_link_local(self) -> None:
        """research_markdown rejects link-local IPs."""
        with pytest.raises(Exception):  # Should raise UrlSafetyError
            await research_markdown(url="http://169.254.1.1/page")
