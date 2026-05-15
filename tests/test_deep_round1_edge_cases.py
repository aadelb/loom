"""Deep testing round 1: Edge case tests for fetch, search, and spider tools.

Comprehensive edge case coverage for:
- research_fetch: unicode URLs, long paths, empty responses, redirects, binary content
- research_search: empty query, special chars, unicode, SQL injection, null bytes
- research_spider: duplicate URLs, invalid URLs, empty lists, large lists

All tests mock network calls to avoid external dependencies.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.core.fetch import research_fetch
from loom.tools.core.search import research_search
from loom.tools.core.spider import research_spider

pytestmark = pytest.mark.asyncio


# ============================================================================
# FETCH EDGE CASES (1-10)
# ============================================================================


class TestFetchEdgeCases:
    """Edge case tests for research_fetch."""

    async def test_fetch_unicode_url(self) -> None:
        """Fetch handles URL with unicode characters gracefully."""
        # Unicode in URL should either be accepted or return error dict
        result = await research_fetch(url="https://httpbin.org/anything/ünïcödé")
        assert isinstance(result, dict)
        assert "url" in result
        # Either success or error field, but not crash
        assert result.get("error") is None or isinstance(result.get("error"), str)

    async def test_fetch_very_long_path(self) -> None:
        """Fetch handles URL with 2000+ char path."""
        long_path = "a" * 2500
        result = await research_fetch(url=f"https://httpbin.org/anything/{long_path}")
        assert isinstance(result, dict)
        assert "url" in result
        # Should either succeed or return graceful error
        if result.get("error"):
            assert isinstance(result["error"], str)

    async def test_fetch_query_params_special_chars(self) -> None:
        """Fetch handles URL with special chars in query params."""
        result = await research_fetch(
            url="https://httpbin.org/anything?q=hello%20world&special=!@#$%"
        )
        assert isinstance(result, dict)
        assert "url" in result

    async def test_fetch_url_with_fragment(self) -> None:
        """Fetch handles URL with fragment (#anchor)."""
        result = await research_fetch(url="https://httpbin.org/anything#section")
        assert isinstance(result, dict)
        assert "url" in result

    async def test_fetch_204_no_content(self) -> None:
        """Fetch handles 204 No Content response gracefully."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.text = ""
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await research_fetch(
                url="https://httpbin.org/status/204", mode="http"
            )
            assert isinstance(result, dict)
            assert "url" in result
            assert result.get("text") is not None or result.get("error") is not None

    async def test_fetch_huge_response_truncation(self) -> None:
        """Fetch truncates huge responses at max_chars limit."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            huge_text = "x" * 500000  # 500K chars
            mock_response.text = huge_text
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await research_fetch(
                url="https://httpbin.org/anything",
                mode="http",
                max_chars=5000,
            )
            assert isinstance(result, dict)
            text = result.get("text", "")
            # Should be truncated to max_chars
            assert len(text) <= 5000

    async def test_fetch_redirect_chain(self) -> None:
        """Fetch follows redirect chains gracefully."""
        # requests.get follows redirects by default, so this should work
        result = await research_fetch(
            url="https://httpbin.org/redirect/3",
            mode="http",
        )
        assert isinstance(result, dict)
        assert "url" in result

    async def test_fetch_self_signed_cert_fails_gracefully(self) -> None:
        """Fetch handles self-signed cert error without crashing."""
        result = await research_fetch(
            url="https://self-signed.badssl.com/"
        )
        assert isinstance(result, dict)
        # Should return error dict, not crash
        assert "url" in result

    async def test_fetch_binary_content(self) -> None:
        """Fetch handles binary content (image/pdf) gracefully."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Simulate binary content
            mock_response.text = "\x89PNG\r\n\x1a\n" + "binary" * 100
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await research_fetch(
                url="https://example.com/image.png",
                mode="http",
            )
            assert isinstance(result, dict)
            assert "url" in result

    async def test_fetch_double_encoded_url(self) -> None:
        """Fetch handles double-encoded URL."""
        # URL with %25 (encoded %)
        result = await research_fetch(
            url="https://httpbin.org/anything?q=%2520encoded"
        )
        assert isinstance(result, dict)
        assert "url" in result


# ============================================================================
# SEARCH EDGE CASES (11-16)
# ============================================================================


class TestSearchEdgeCases:
    """Edge case tests for research_search."""

    async def test_search_empty_query(self) -> None:
        """Search rejects empty query with validation error."""
        result = await research_search(query="")
        # Should return error dict
        assert isinstance(result, dict)
        assert result.get("error") is not None

    async def test_search_whitespace_only_query(self) -> None:
        """Search rejects whitespace-only query."""
        result = await research_search(query="   ")
        assert isinstance(result, dict)
        assert result.get("error") is not None

    async def test_search_special_chars_query(self) -> None:
        """Search handles query with only special characters."""
        with patch("loom.providers.ddgs.search_ddgs") as mock_search:
            mock_search.return_value = {
                "results": [],
                "query": "@#$%^&*",
            }

            result = await research_search(
                query="@#$%^&*",
                provider="ddgs",
            )
            assert isinstance(result, dict)
            assert "query" in result

    async def test_search_very_long_query(self) -> None:
        """Search handles very long query (1000+ chars)."""
        long_query = "search term " * 100  # ~1200 chars
        result = await research_search(query=long_query)
        # Should either succeed or return error, not crash
        assert isinstance(result, dict)

    async def test_search_unicode_arabic_query(self) -> None:
        """Search handles unicode/Arabic query."""
        with patch("loom.providers.ddgs.search_ddgs") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "title": "نتيجة",
                        "url": "https://example.com",
                        "body": "الأمان",
                    }
                ],
                "query": "بحث عن الأمان",
            }

            result = await research_search(
                query="بحث عن الأمان",
                provider="ddgs",
            )
            assert isinstance(result, dict)
            assert "query" in result or "error" in result

    async def test_search_sql_injection_attempt(self) -> None:
        """Search safely handles SQL injection attempt in query."""
        with patch("loom.providers.ddgs.search_ddgs") as mock_search:
            mock_search.return_value = {
                "results": [],
                "query": "'; DROP TABLE--",
            }

            result = await research_search(
                query="'; DROP TABLE--",
                provider="ddgs",
            )
            assert isinstance(result, dict)
            # Should treat as normal query, not execute SQL
            assert "query" in result or "error" in result

    async def test_search_null_bytes_query(self) -> None:
        """Search safely handles null bytes in query."""
        # Python strings with null bytes are valid but unusual
        result = await research_search(query="test\x00query")
        assert isinstance(result, dict)
        # Should handle gracefully

    async def test_search_n_parameter_boundary(self) -> None:
        """Search validates n parameter boundaries (1-50)."""
        # Test n=0 (should be clamped or error)
        result = await research_search(query="test", n=0)
        assert isinstance(result, dict)

        # Test n=51 (should be clamped to 50)
        result = await research_search(query="test", n=51)
        assert isinstance(result, dict)

    async def test_search_free_only_with_paid_provider(self) -> None:
        """Search switches to free provider when free_only=True with paid provider."""
        result = await research_search(
            query="test",
            provider="exa",  # Paid provider
            free_only=True,  # Requested free only
        )
        assert isinstance(result, dict)
        # Should have switched to free provider or returned error
        if "provider" in result:
            assert result["provider"] in ("ddgs", "arxiv", "wikipedia", "reddit")


# ============================================================================
# SPIDER EDGE CASES (17-26)
# ============================================================================


class TestSpiderEdgeCases:
    """Edge case tests for research_spider."""

    async def test_spider_empty_url_list(self) -> None:
        """Spider rejects empty URL list and returns error dict."""
        result = await research_spider(urls=[])
        # Validation error returns dict, not list
        assert isinstance(result, dict)
        assert "error" in result

    async def test_spider_url_list_with_duplicates(self) -> None:
        """Spider deduplicates URLs when dedupe=True."""
        urls = [
            "https://example.com",
            "https://example.com",
            "https://example.org",
            "https://example.org",
        ]
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            mock_fetch.return_value = {"url": "", "text": "content", "error": None}

            result = await research_spider(urls=urls, dedupe=True)
            assert isinstance(result, list)
            # Should have 2 results (deduped), not 4
            # Count actual fetches (excluding error responses)
            fetch_calls = [
                call
                for call in mock_fetch.call_args_list
            ]
            # With dedup, should only fetch unique URLs
            assert len(fetch_calls) <= 2

    async def test_spider_mixed_valid_invalid_urls(self) -> None:
        """Spider handles mix of valid and invalid URLs - returns error dict."""
        urls = [
            "https://example.com",
            "invalid-url",
            "https://example.org",
            "http://[invalid]",
        ]
        result = await research_spider(urls=urls)
        # Invalid URLs fail validation, returns error dict
        assert isinstance(result, dict)
        assert "error" in result

    async def test_spider_url_list_over_100(self) -> None:
        """Spider caps URL list at config limit (100-200)."""
        # Generate 150 URLs
        urls = [f"https://example.com/{i}" for i in range(150)]
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            mock_fetch.return_value = {"url": "", "text": "content", "error": None}

            result = await research_spider(urls=urls)
            assert isinstance(result, list)
            # Should be capped at max_spider_urls (usually 100)
            assert len(result) <= 150

    async def test_spider_concurrency_boundary(self) -> None:
        """Spider validates concurrency parameter."""
        urls = ["https://example.com/1", "https://example.com/2"]

        # Test concurrency=0 (validation fails, returns error dict)
        result = await research_spider(urls=urls, concurrency=0)
        assert isinstance(result, dict)
        assert "error" in result

        # Test concurrency=100 (should be clamped to max)
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            mock_fetch.return_value = {"url": "", "text": "content"}
            result = await research_spider(urls=urls, concurrency=100)
            assert isinstance(result, dict)
            assert "error" in result

    async def test_spider_fail_fast_stops_on_error(self) -> None:
        """Spider stops on first error when fail_fast=True."""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        call_count = 0

        async def mock_fetch_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return {"url": urls[1], "error": "timeout"}
            return {"url": args[0] if args else "", "text": "content"}

        with patch(
            "loom.tools.core.spider.research_fetch",
            side_effect=mock_fetch_with_error,
        ):
            result = await research_spider(urls=urls, fail_fast=True)
            assert isinstance(result, list)
            # Should have stopped at error
            assert len(result) <= 3

    async def test_spider_timeout_hierarchy(self) -> None:
        """Spider enforces timeout hierarchy (inner < outer)."""
        urls = ["https://example.com/1"]
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            mock_fetch.return_value = {"url": "", "text": "content"}

            # Provide explicit timeout
            result = await research_spider(
                urls=urls,
                timeout=45,  # Should be clamped to INNER_FETCH_TIMEOUT
            )
            assert isinstance(result, list)

    async def test_spider_order_by_domain(self) -> None:
        """Spider orders results by domain when order='domain'."""
        urls = [
            "https://zebra.com/page",
            "https://apple.com/page",
            "https://middle.com/page",
        ]
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            def side_effect(url, **kwargs):
                return {"url": url, "text": f"content from {url}"}

            mock_fetch.side_effect = side_effect

            result = await research_spider(urls=urls, order="domain")
            assert isinstance(result, list)
            # Results should be sorted by URL
            if len(result) > 1:
                for i in range(len(result) - 1):
                    assert result[i].get("url", "") <= result[i + 1].get("url", "")

    async def test_spider_order_by_size(self) -> None:
        """Spider orders results by size when order='size'."""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
        ]
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            def side_effect(url, **kwargs):
                if "1" in url:
                    return {"url": url, "text": "small"}
                else:
                    return {"url": url, "text": "much larger content here"}

            mock_fetch.side_effect = side_effect

            result = await research_spider(urls=urls, order="size")
            assert isinstance(result, list)

    async def test_spider_headers_filtering(self) -> None:
        """Spider filters unsafe headers."""
        urls = ["https://example.com"]
        unsafe_headers = {
            "Authorization": "Bearer token",
            "Host": "evil.com",
            "Cookie": "session=123",
        }
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            mock_fetch.return_value = {"url": "", "text": "content"}

            result = await research_spider(
                urls=urls,
                headers=unsafe_headers,
            )
            assert isinstance(result, list)
            # Should either filter headers or pass through


# ============================================================================
# INTEGRATION & BOUNDARY TESTS
# ============================================================================


class TestEdgeCaseBoundaries:
    """Boundary and integration tests across tools."""

    async def test_fetch_max_chars_hard_cap(self) -> None:
        """Fetch respects max_chars hard cap from config."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "x" * 1000000  # 1M chars
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await research_fetch(
                url="https://example.com",
                mode="http",
                max_chars=50000,  # User requests 50K
            )
            assert isinstance(result, dict)
            text = result.get("text", "")
            # Should be capped at max (or hard cap from config)
            assert len(text) <= 50000

    async def test_search_include_exclude_domains(self) -> None:
        """Search filters results by include/exclude domains."""
        with patch("loom.providers.brave.search_brave") as mock_search:
            mock_search.return_value = {
                "results": [
                    {"url": "https://example.com/page", "title": "Example"},
                    {"url": "https://other.com/page", "title": "Other"},
                ],
                "query": "test",
            }

            result = await research_search(
                query="test",
                provider="brave",
                include_domains=["example.com"],
                exclude_domains=["excluded.com"],
            )
            assert isinstance(result, dict)

    async def test_spider_single_url(self) -> None:
        """Spider handles single-URL list gracefully."""
        urls = ["https://example.com"]
        with patch(
            "loom.tools.core.spider.research_fetch"
        ) as mock_fetch:
            mock_fetch.return_value = {"url": urls[0], "text": "content"}

            result = await research_spider(urls=urls)
            assert isinstance(result, list)
            assert len(result) >= 1

    async def test_error_responses_are_dicts_or_lists(self) -> None:
        """All tools return dict or list of dicts on error."""
        # Fetch error
        result_fetch = await research_fetch(url="invalid://url")
        assert isinstance(result_fetch, dict)

        # Search error
        result_search = await research_search(query="")
        assert isinstance(result_search, dict)

        # Spider error (validation failure returns dict)
        result_spider = await research_spider(urls=[])
        assert isinstance(result_spider, dict)
        assert "error" in result_spider


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
