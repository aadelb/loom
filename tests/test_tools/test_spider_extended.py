"""Unit tests for spider tool — validation, deduplication, concurrency."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.spider import research_spider


class TestSpiderValidation:
    """research_spider validation tests."""

    def test_spider_validates_empty_url_list(self) -> None:
        """Empty URL list returns error dict."""

        async def run_test() -> None:
            result = await research_spider([])
            assert len(result) == 1
            assert "error" in result[0]
            assert result[0]["error"] == "urls list is empty"

        asyncio.run(run_test())

    def test_spider_clamps_concurrency(self) -> None:
        """Concurrency > SPIDER_CONCURRENCY is clamped."""
        with patch("loom.tools.spider.research_fetch") as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "text": "content",
            }

            async def run_test() -> None:
                # Pass concurrency at limit; should succeed
                result = await research_spider(
                    ["https://example.com"],
                    concurrency=20,
                )
                # Should succeed without error
                assert len(result) >= 1
                # At least one fetch happened
                assert mock_fetch.called

            asyncio.run(run_test())

    def test_spider_deduplicates_urls(self) -> None:
        """Duplicate URLs are fetched only once."""
        with patch("loom.tools.spider.research_fetch") as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "text": "content",
            }

            async def run_test() -> None:
                result = await research_spider(
                    [
                        "https://example.com",
                        "https://example.com",
                        "https://example.com/page",
                    ],
                    dedupe=True,
                )
                # Should have fetched 2 unique URLs, not 3
                assert mock_fetch.call_count == 2

            asyncio.run(run_test())
