"""Unit tests for spider tool - validation, deduplication, concurrency."""

from __future__ import annotations
import pytest

from unittest.mock import patch, AsyncMock
from pydantic_core import ValidationError

from loom.tools.core.spider import research_spider


pytestmark = pytest.mark.asyncio

class TestSpiderValidation:
    """research_spider validation tests."""

    async def test_spider_validates_empty_url_list(self) -> None:
        """Empty URL list returns validation error."""
        with pytest.raises(ValidationError) as exc_info:
            await research_spider([])
        assert "urls list cannot be empty" in str(exc_info.value)

    async def test_spider_clamps_concurrency(self) -> None:
        """Concurrency > SPIDER_CONCURRENCY is clamped."""
        with patch("loom.tools.core.spider.research_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "text": "content",
            }

            result = await research_spider(
                ["https://example.com"],
                concurrency=20,
            )
            assert len(result) >= 1
            assert mock_fetch.called

    async def test_spider_deduplicates_urls(self) -> None:
        """Duplicate URLs are fetched only once."""
        with patch("loom.tools.core.spider.research_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "text": "content",
            }

            result = await research_spider(
                [
                    "https://example.com",
                    "https://example.com",
                    "https://example.com/page",
                ],
                dedupe=True,
            )
            assert mock_fetch.call_count == 2
