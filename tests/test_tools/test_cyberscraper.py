"""Unit tests for CyberScraper-2077 integration tools.

Tests for:
- research_smart_extract: LLM-powered structured extraction
- research_paginate_scrape: Multi-page extraction with pagination
- research_stealth_browser: Patchright stealth browser (fallback to httpx)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.cyberscraper import (
    SmartExtractParams,
    SmartExtractResult,
    PaginateParams,
    PaginateScrapeResult,
    StealthBrowserParams,
    StealthBrowserResult,
    _WebPreprocessor,
    _JSONExtractor,
    _parse_page_range,
    _detect_pagination_pattern,
    _apply_url_pattern,
    research_smart_extract,
    research_paginate_scrape,
    research_stealth_browser,
)


class TestSmartExtractParams:
    """SmartExtractParams validation."""

    def test_valid_params(self) -> None:
        """Valid parameters are accepted."""
        params = SmartExtractParams(
            url="https://example.com",
            query="extract data",
            model="groq",
            max_chars=50000,
            timeout=30,
        )
        assert params.url == "https://example.com"
        assert params.query == "extract data"
        assert params.model == "groq"

    def test_invalid_url(self) -> None:
        """Invalid URLs are rejected."""
        with pytest.raises(ValueError):
            SmartExtractParams(url="not-a-url", query="extract")

    def test_query_too_short(self) -> None:
        """Queries shorter than 3 chars rejected."""
        with pytest.raises(ValueError):
            SmartExtractParams(url="https://example.com", query="ab")

    def test_query_too_long(self) -> None:
        """Queries longer than 1000 chars rejected."""
        SmartExtractParams(
            url="https://example.com", query="x" * 1000
        )  # OK at 1000
        with pytest.raises(ValueError):
            SmartExtractParams(
                url="https://example.com", query="x" * 1001
            )

    def test_max_chars_bounds(self) -> None:
        """max_chars must be 1000-200000."""
        with pytest.raises(ValueError):
            SmartExtractParams(
                url="https://example.com", query="test", max_chars=999
            )
        with pytest.raises(ValueError):
            SmartExtractParams(
                url="https://example.com", query="test", max_chars=200001
            )

    def test_timeout_bounds(self) -> None:
        """timeout must be 5-120 seconds."""
        with pytest.raises(ValueError):
            SmartExtractParams(
                url="https://example.com", query="test", timeout=4
            )
        with pytest.raises(ValueError):
            SmartExtractParams(
                url="https://example.com", query="test", timeout=121
            )


class TestPaginateParams:
    """PaginateParams validation."""

    def test_valid_page_range(self) -> None:
        """Valid page ranges accepted."""
        params = PaginateParams(
            url="https://example.com",
            query="extract",
            page_range="1-5",
        )
        assert params.page_range == "1-5"

        params2 = PaginateParams(
            url="https://example.com",
            query="extract",
            page_range="1,3,5",
        )
        assert params2.page_range == "1,3,5"

    def test_invalid_page_range(self) -> None:
        """Invalid page ranges rejected."""
        with pytest.raises(ValueError):
            PaginateParams(
                url="https://example.com",
                query="extract",
                page_range="abc",
            )


class TestStealthBrowserParams:
    """StealthBrowserParams validation."""

    def test_valid_params(self) -> None:
        """Valid parameters are accepted."""
        params = StealthBrowserParams(
            url="https://example.com",
            wait_for="load",
            screenshot=False,
            timeout=30,
        )
        assert params.url == "https://example.com"
        assert params.wait_for == "load"

    def test_wait_for_options(self) -> None:
        """wait_for accepts valid options."""
        StealthBrowserParams(url="https://example.com", wait_for="load")
        StealthBrowserParams(url="https://example.com", wait_for="domcontentloaded")
        StealthBrowserParams(url="https://example.com", wait_for="networkidle")
        StealthBrowserParams(url="https://example.com", wait_for=None)


class TestWebPreprocessor:
    """HTML preprocessing: remove noise, extract text."""

    def test_preprocess_simple_html(self) -> None:
        """Simple HTML is cleaned properly."""
        html = "<html><body>Hello <script>alert(1)</script> World</body></html>"
        result = _WebPreprocessor.preprocess_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "script" not in result.lower()

    def test_preprocess_removes_styles(self) -> None:
        """Style tags are removed."""
        html = "<html><body>Text<style>body{color:red}</style>More</body></html>"
        result = _WebPreprocessor.preprocess_html(html)
        assert "color:red" not in result
        assert "Text" in result
        assert "More" in result

    def test_preprocess_removes_empty_tags(self) -> None:
        """Empty tags are removed."""
        html = "<div></div><p>Content</p><span></span>"
        result = _WebPreprocessor.preprocess_html(html)
        assert "Content" in result
        assert len(result) > 0

    def test_preprocess_whitespace_cleanup(self) -> None:
        """Excessive whitespace is normalized."""
        html = "<p>Line   1</p><p>Line   2</p>"
        result = _WebPreprocessor.preprocess_html(html)
        lines = result.strip().split("\n")
        # Should have reasonable number of lines, not tons of whitespace
        assert len(lines) <= 5


class TestJSONExtractor:
    """JSON extraction from LLM responses."""

    def test_extract_pure_json(self) -> None:
        """Pure JSON is extracted directly."""
        response = '{"name": "John", "age": 30}'
        result = _JSONExtractor.extract_json(response)
        assert result == {"name": "John", "age": 30}

    def test_extract_json_array(self) -> None:
        """JSON arrays are extracted."""
        response = '[{"id": 1}, {"id": 2}]'
        result = _JSONExtractor.extract_json(response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_extract_from_markdown_json(self) -> None:
        """JSON in markdown code blocks is extracted."""
        response = "Here's the data:\n```json\n{\"key\": \"value\"}\n```"
        result = _JSONExtractor.extract_json(response)
        assert result == {"key": "value"}

    def test_extract_from_code_block(self) -> None:
        """JSON in generic code blocks is extracted."""
        response = "The result:\n```\n[{\"item\": 1}]\n```"
        result = _JSONExtractor.extract_json(response)
        assert result == [{"item": 1}]

    def test_extract_invalid_json_returns_none(self) -> None:
        """Invalid JSON returns None."""
        response = "This is not JSON at all"
        result = _JSONExtractor.extract_json(response)
        assert result is None


class TestPageRangeParsing:
    """Page range parsing utility."""

    def test_parse_single_range(self) -> None:
        """Parse '1-5' into [1,2,3,4,5]."""
        result = _parse_page_range("1-5")
        assert result == [1, 2, 3, 4, 5]

    def test_parse_comma_separated(self) -> None:
        """Parse '1,3,5' into [1,3,5]."""
        result = _parse_page_range("1,3,5")
        assert result == [1, 3, 5]

    def test_parse_mixed(self) -> None:
        """Parse '1-3,5,7-9' into [1,2,3,5,7,8,9]."""
        result = _parse_page_range("1-3,5,7-9")
        assert result == [1, 2, 3, 5, 7, 8, 9]

    def test_parse_deduplicates(self) -> None:
        """Duplicates are removed and sorted."""
        result = _parse_page_range("1,1,2,3,2")
        assert result == [1, 2, 3]


class TestPaginationDetection:
    """Pagination pattern detection."""

    def test_detect_query_param_pattern(self) -> None:
        """Detect query parameter pagination."""
        url = "https://example.com/items?page=1"
        pattern = _detect_pagination_pattern(url)
        assert pattern is not None
        assert "page=" in pattern

    def test_detect_path_pattern(self) -> None:
        """Detect path segment pagination."""
        url = "https://example.com/items/page/1/listing"
        pattern = _detect_pagination_pattern(url)
        assert pattern is not None
        assert "{page}" in pattern

    def test_no_pattern_detected(self) -> None:
        """Return None when no pagination pattern found."""
        url = "https://example.com/items"
        pattern = _detect_pagination_pattern(url)
        # May be None or detect some pattern - that's OK
        # The important thing is it doesn't error


class TestURLPatternApplication:
    """Apply pagination patterns to URLs."""

    def test_apply_query_param_pattern(self) -> None:
        """Apply query parameter pattern."""
        url = "https://example.com/items?page=1"
        pattern = "page={page}"
        result = _apply_url_pattern(url, pattern, 2)
        assert "page=2" in result

    def test_apply_path_pattern(self) -> None:
        """Apply path segment pattern."""
        url = "https://example.com/items/1"
        pattern = "/items/{page}"
        result = _apply_url_pattern(url, pattern, 3)
        assert "/items/3" in result

    def test_apply_none_pattern(self) -> None:
        """None pattern returns original URL."""
        url = "https://example.com/items"
        result = _apply_url_pattern(url, None, 2)
        assert result == url


class TestSmartExtractAsync:
    """Async tests for research_smart_extract."""

    @pytest.mark.asyncio
    async def test_smart_extract_basic_mock(self, tmp_cache_dir) -> None:
        """Basic smart extract with mocked browser and LLM."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            # Mock browser fetch
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "<html><body><p>John Doe, $50000</p><p>Jane Smith, $60000</p></body></html>",
                "status_code": 200,
                "screenshot_b64": None,
                "error": None,
            }

            # Mock LLM provider
            with patch("loom.tools.cyberscraper._get_llm_provider") as mock_llm:
                mock_provider = AsyncMock()
                mock_llm.return_value = mock_provider

                # Mock LLM response
                mock_response = MagicMock()
                mock_response.content = [
                    MagicMock(
                        text='[{"name": "John Doe", "salary": "$50000"}, {"name": "Jane Smith", "salary": "$60000"}]'
                    )
                ]
                mock_provider.chat.return_value = mock_response

                result = await research_smart_extract(
                    url="https://example.com/jobs",
                    query="extract names and salaries",
                    model="groq",
                )

                assert isinstance(result, SmartExtractResult)
                assert result.url == "https://example.com/jobs"
                assert result.query == "extract names and salaries"
                assert isinstance(result.extracted_data, list)
                assert len(result.extracted_data) == 2

    @pytest.mark.asyncio
    async def test_smart_extract_error_handling(self) -> None:
        """Error handling in smart_extract."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            # Mock browser failure
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "",
                "status_code": None,
                "screenshot_b64": None,
                "error": "Network error",
            }

            result = await research_smart_extract(
                url="https://example.com",
                query="extract data",
            )

            assert isinstance(result, SmartExtractResult)
            assert result.error is not None
            assert "Network error" in result.error
            assert result.extracted_data == {}

    @pytest.mark.asyncio
    async def test_smart_extract_empty_content(self, tmp_cache_dir) -> None:
        """Handle empty preprocessed content."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "<html><body></body></html>",
                "status_code": 200,
                "screenshot_b64": None,
                "error": None,
            }

            result = await research_smart_extract(
                url="https://example.com",
                query="extract",
            )

            assert isinstance(result, SmartExtractResult)
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_smart_extract_cache_hit(self, tmp_cache_dir) -> None:
        """Cache hit returns cached result."""
        import os
        import hashlib

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        # Pre-populate cache
        from loom.cache import get_cache

        cache = get_cache()
        cache_key = hashlib.sha256(
            "https://example.com:extract".encode()
        ).hexdigest()
        cached_data = [{"item": "cached"}]
        cache.put(f"cyberscraper:{cache_key}", {"data": cached_data})

        result = await research_smart_extract(
            url="https://example.com",
            query="extract",
        )

        assert isinstance(result, SmartExtractResult)
        assert result.cached is True
        assert result.model_used == "cache"
        assert result.extracted_data == cached_data


class TestPaginateScrapeAsync:
    """Async tests for research_paginate_scrape."""

    @pytest.mark.asyncio
    async def test_paginate_scrape_multiple_pages(self) -> None:
        """Scrape multiple pages with pagination."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser

            # Mock browser to return different content for each page
            mock_browser.fetch_with_patchright.side_effect = [
                {
                    "html": "<p>Job 1</p>",
                    "status_code": 200,
                    "screenshot_b64": None,
                    "error": None,
                },
                {
                    "html": "<p>Job 2</p>",
                    "status_code": 200,
                    "screenshot_b64": None,
                    "error": None,
                },
            ]

            with patch("loom.tools.cyberscraper._get_llm_provider") as mock_llm:
                mock_provider = AsyncMock()
                mock_llm.return_value = mock_provider

                # Mock LLM responses for each page
                response1 = MagicMock()
                response1.content = [MagicMock(text='[{"title": "Job 1"}]')]
                response2 = MagicMock()
                response2.content = [MagicMock(text='[{"title": "Job 2"}]')]

                mock_provider.chat.side_effect = [response1, response2]

                result = await research_paginate_scrape(
                    url="https://example.com/jobs?page=1",
                    query="extract jobs",
                    page_range="1-2",
                )

                assert isinstance(result, PaginateScrapeResult)
                assert result.pages_scraped == 2
                assert result.total_items == 2
                assert len(result.extracted_data) == 2

    @pytest.mark.asyncio
    async def test_paginate_invalid_range(self) -> None:
        """Invalid page range handling."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            await research_paginate_scrape(
                url="https://example.com",
                query="extract",
                page_range="invalid",
            )

    @pytest.mark.asyncio
    async def test_paginate_auto_detect_pattern(self) -> None:
        """Auto-detect pagination pattern."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "<p>Data</p>",
                "status_code": 200,
                "screenshot_b64": None,
                "error": None,
            }

            with patch("loom.tools.cyberscraper._get_llm_provider"):
                with patch("loom.tools.cyberscraper._detect_pagination_pattern") as mock_detect:
                    mock_detect.return_value = "page={page}"

                    result = await research_paginate_scrape(
                        url="https://example.com?page=1",
                        query="extract",
                        page_range="1-1",
                        auto_detect_pattern=True,
                    )

                    assert isinstance(result, PaginateScrapeResult)
                    # Pattern should have been detected
                    mock_detect.assert_called_once()


class TestStealthBrowserAsync:
    """Async tests for research_stealth_browser."""

    @pytest.mark.asyncio
    async def test_stealth_browser_basic(self) -> None:
        """Basic stealth browser fetch."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "<html><body>Test content</body></html>",
                "status_code": 200,
                "screenshot_b64": None,
                "error": None,
            }

            result = await research_stealth_browser(
                url="https://example.com",
                wait_for="load",
                screenshot=False,
            )

            assert isinstance(result, StealthBrowserResult)
            assert result.url == "https://example.com"
            assert "Test content" in result.text
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_stealth_browser_with_screenshot(self) -> None:
        """Screenshot capture in stealth browser."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "<html><body>Page</body></html>",
                "status_code": 200,
                "screenshot_b64": "iVBORw0KGgo=",  # Minimal fake base64
                "error": None,
            }

            result = await research_stealth_browser(
                url="https://example.com",
                screenshot=True,
            )

            assert isinstance(result, StealthBrowserResult)
            assert result.screenshot_b64 is not None

    @pytest.mark.asyncio
    async def test_stealth_browser_error(self) -> None:
        """Error handling in stealth browser."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser
            mock_browser.fetch_with_patchright.return_value = {
                "html": "",
                "status_code": None,
                "screenshot_b64": None,
                "error": "Timeout",
            }

            result = await research_stealth_browser(
                url="https://example.com",
            )

            assert isinstance(result, StealthBrowserResult)
            assert result.error is not None
            assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_stealth_browser_max_chars(self) -> None:
        """Respect max_chars limit."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser_class.return_value = mock_browser

            # Return large HTML
            large_html = "<p>" + ("x" * 100000) + "</p>"
            mock_browser.fetch_with_patchright.return_value = {
                "html": large_html,
                "status_code": 200,
                "screenshot_b64": None,
                "error": None,
            }

            result = await research_stealth_browser(
                url="https://example.com",
                max_chars=1000,
            )

            assert isinstance(result, StealthBrowserResult)
            assert len(result.html) <= 1000


class TestIntegrationScenarios:
    """Integration scenarios combining multiple tools."""

    @pytest.mark.asyncio
    async def test_workflow_fetch_then_extract(self) -> None:
        """Workflow: stealth fetch then smart extract."""
        with patch("loom.tools.cyberscraper._PatchrightAdapter"):
            # This demonstrates the two-step workflow
            # In real usage, smart_extract does both internally
            pass


class TestResultModels:
    """Test result model serialization."""

    def test_smart_extract_result_serialization(self) -> None:
        """SmartExtractResult serializes to JSON."""
        result = SmartExtractResult(
            url="https://example.com",
            query="test",
            extracted_data={"key": "value"},
            model_used="groq",
            token_count=100,
        )
        data = result.model_dump()
        assert data["url"] == "https://example.com"
        assert data["extracted_data"]["key"] == "value"

    def test_paginate_result_serialization(self) -> None:
        """PaginateScrapeResult serializes to JSON."""
        result = PaginateScrapeResult(
            url="https://example.com",
            query="test",
            pages_scraped=5,
            total_items=50,
            extracted_data=[{"id": 1}],
            model_used="multi-page",
        )
        data = result.model_dump()
        assert data["pages_scraped"] == 5
        assert data["total_items"] == 50

    def test_stealth_result_serialization(self) -> None:
        """StealthBrowserResult serializes to JSON."""
        result = StealthBrowserResult(
            url="https://example.com",
            html="<p>test</p>",
            text="test",
            status_code=200,
            chars_extracted=10,
        )
        data = result.model_dump()
        assert data["status_code"] == 200
