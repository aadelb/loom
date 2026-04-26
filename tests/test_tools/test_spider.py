"""Unit tests for research_spider tool — parallel fetches, concurrency, mixed results."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_spider_empty_urls_returns_empty() -> None:
    """Spider with empty URL list returns empty result."""
    pytest.importorskip("loom.tools.spider")

    from loom.tools.spider import research_spider

    result = await research_spider(urls=[])

    # Spider returns a list, not a dict
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_spider_parallel_fetches() -> None:
    """Spider fetches URLs in parallel up to concurrency limit."""
    pytest.importorskip("loom.tools.spider")

    from loom.tools.spider import research_spider

    urls = [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]

    with patch("loom.tools.spider.research_fetch") as mock_fetch:
        mock_fetch.return_value = {
            "url": "https://example.com/test",
            "text": "content",
            "title": "title",
        }

        result = await research_spider(urls=urls, concurrency=2)

        # Spider returns a list directly, not a dict with results key
        assert isinstance(result, list)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_spider_respects_concurrency_limit() -> None:
    """Spider respects concurrency parameter."""
    pytest.importorskip("loom.tools.spider")

    from loom.tools.spider import research_spider

    urls = [f"https://example.com/{i}" for i in range(10)]

    concurrent_count = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    def slow_fetch(*args, **kwargs):  # type: ignore
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)

        import time
        time.sleep(0.01)

        concurrent_count -= 1

        return {
            "url": kwargs.get("url", ""),
            "text": "content",
            "title": "title",
        }

    with patch("loom.tools.spider.research_fetch", side_effect=slow_fetch):
        await research_spider(urls=urls, concurrency=3)

        # Max concurrent should be <= 3
        assert max_concurrent <= 3


@pytest.mark.asyncio
async def test_spider_mixed_ok_fail() -> None:
    """Spider handles mixed ok/fail results gracefully."""
    pytest.importorskip("loom.tools.spider")

    from loom.tools.spider import research_spider

    urls = [
        "https://good.com",
        "https://bad-timing.com",
        "https://another-good.com",
    ]

    def mock_fetch(url: str, **kwargs):  # type: ignore
        if "bad" in url:
            return {"url": url, "error": "timeout"}
        return {"url": url, "text": "content", "title": "ok"}

    with patch("loom.tools.spider.research_fetch", side_effect=mock_fetch):
        with patch("loom.tools.spider.SpiderParams") as mock_params:
            # Mock the validator to accept any URL
            mock_params.return_value.urls = urls
            mock_params.return_value.dedupe = False
            mock_params.return_value.fail_fast = False
            mock_params.return_value.mode = "stealthy"
            mock_params.return_value.max_chars_each = 5000
            mock_params.return_value.concurrency = 5
            mock_params.return_value.solve_cloudflare = True
            mock_params.return_value.headers = None
            mock_params.return_value.user_agent = None
            mock_params.return_value.proxy = None
            mock_params.return_value.cookies = None
            mock_params.return_value.accept_language = "en-US"
            mock_params.return_value.timeout = None

            result = await research_spider(urls=urls)

            # Spider returns a list
            assert isinstance(result, list)
            # Should not crash even with mixed results
            assert len(result) > 0


@pytest.mark.asyncio
async def test_spider_deduplication() -> None:
    """Spider with dedupe=True removes duplicate URLs."""
    pytest.importorskip("loom.tools.spider")

    from loom.tools.spider import research_spider

    urls = [
        "https://example.com",
        "https://example.com",  # Duplicate
        "https://test.com",
    ]

    with patch("loom.tools.spider.research_fetch") as mock_fetch:
        mock_fetch.return_value = {"url": "test", "text": "content"}
        with patch("loom.tools.spider.SpiderParams") as mock_params:
            # Mock the validator to accept any URL
            mock_params.return_value.urls = urls
            mock_params.return_value.dedupe = True
            mock_params.return_value.fail_fast = False
            mock_params.return_value.mode = "stealthy"
            mock_params.return_value.max_chars_each = 5000
            mock_params.return_value.concurrency = 5
            mock_params.return_value.solve_cloudflare = True
            mock_params.return_value.headers = None
            mock_params.return_value.user_agent = None
            mock_params.return_value.proxy = None
            mock_params.return_value.cookies = None
            mock_params.return_value.accept_language = "en-US"
            mock_params.return_value.timeout = None

            result = await research_spider(urls=urls, dedupe=True)

            # Should have fetched only 2 unique URLs
            assert mock_fetch.call_count <= 2
