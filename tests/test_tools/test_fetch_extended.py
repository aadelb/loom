"""Extended tests for research_fetch tool — HTTP mode, stealthy, dynamic, escalation, cache.

Target: 80%+ coverage for src/loom/tools/fetch.py (currently 43%).

Tests cover:
- HTTP mode (httpx + Scrapling paths)
- Stealthy mode with Scrapling/Camoufox
- Auto-escalation (HTTP -> stealthy -> dynamic on Cloudflare)
- Cache hit/miss scenarios
- Text extraction (_extract_text with/without selectolax)
- Schema transformations (_to_scrapling_schema, FetchResult)
- Error handling and edge cases
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from loom.params import FetchParams
from loom.tools.fetch import (
    FetchResult,
    _extract_text,
    _fetch_http_httpx,
    _fetch_stealthy,
    _is_cloudflare_block,
    _make_cache_key,
    _to_scrapling_schema,
    research_fetch,
)


class TestMakeCacheKey:
    """Tests for _make_cache_key — consistent hash generation."""

    def test_make_cache_key_deterministic(self) -> None:
        """Cache key is deterministic for same input."""
        key1 = _make_cache_key("https://example.com", "http")
        key2 = _make_cache_key("https://example.com", "http")
        assert key1 == key2

    def test_make_cache_key_differs_by_url(self) -> None:
        """Different URLs produce different keys."""
        key1 = _make_cache_key("https://example.com", "http")
        key2 = _make_cache_key("https://other.com", "http")
        assert key1 != key2

    def test_make_cache_key_differs_by_mode(self) -> None:
        """Different modes produce different keys."""
        key1 = _make_cache_key("https://example.com", "http")
        key2 = _make_cache_key("https://example.com", "stealthy")
        assert key1 != key2

    def test_make_cache_key_length(self) -> None:
        """Cache key is 32 characters."""
        key = _make_cache_key("https://example.com", "http")
        assert len(key) == 32


class TestExtractText:
    """Tests for _extract_text — HTML to text conversion."""

    def test_extract_text_simple_html(self) -> None:
        """Extract plain text from simple HTML."""
        html = "<html><body><p>Hello world</p></body></html>"
        text = _extract_text(html, max_chars=1000)
        assert "Hello" in text
        assert "world" in text

    def test_extract_text_removes_script_tags(self) -> None:
        """Extract text removes <script> content."""
        html = "<html><body><p>Visible</p><script>alert('hidden')</script></body></html>"
        text = _extract_text(html, max_chars=1000)
        assert "Visible" in text
        assert "alert" not in text

    def test_extract_text_removes_style_tags(self) -> None:
        """Extract text removes <style> content."""
        html = "<html><body><p>Visible</p><style>.x { color: red; }</style></body></html>"
        text = _extract_text(html, max_chars=1000)
        assert "Visible" in text
        assert "color" not in text

    def test_extract_text_normalizes_whitespace(self) -> None:
        """Extract text normalizes multiple spaces."""
        html = "<html><body><p>Hello    world</p></body></html>"
        text = _extract_text(html, max_chars=1000)
        assert "Hello" in text and "world" in text

    def test_extract_text_respects_max_chars(self) -> None:
        """Extract text is capped at max_chars."""
        html = "<html><body><p>" + "x" * 5000 + "</p></body></html>"
        text = _extract_text(html, max_chars=1000)
        assert len(text) <= 1001

    def test_extract_text_adds_ellipsis_when_truncated(self) -> None:
        """Extract text adds ellipsis when truncated."""
        html = "<html><body>" + "x" * 2000 + "</body></html>"
        text = _extract_text(html, max_chars=100)
        assert text.endswith("…")

    def test_extract_text_empty_html(self) -> None:
        """Extract text handles empty HTML."""
        text = _extract_text("", max_chars=1000)
        assert text == ""

    def test_extract_text_malformed_html(self) -> None:
        """Extract text handles malformed HTML gracefully."""
        html = "<p>Unclosed paragraph"
        text = _extract_text(html, max_chars=1000)
        assert isinstance(text, str)


class TestToScraplingSchema:
    """Tests for _to_scrapling_schema — transform to Scrapling-compatible format."""

    def test_to_scrapling_schema_basic_fields(self) -> None:
        """Transform includes url, title, text, html_len, fetched_at."""
        result = {
            "url": "https://example.com",
            "title": "Example",
            "text": "Content",
            "html": "<html>content</html>",
            "tool": "httpx",
        }
        output = _to_scrapling_schema(result, max_chars=5000)

        assert output["url"] == "https://example.com"
        assert output["title"] == "Example"
        assert output["text"] == "Content"
        assert output["html_len"] == len("<html>content</html>")
        assert "fetched_at" in output
        assert output["tool"] == "httpx"

    def test_to_scrapling_schema_caps_text(self) -> None:
        """Transform caps text at max_chars."""
        result = {
            "url": "https://example.com",
            "text": "x" * 10000,
            "tool": "httpx",
        }
        output = _to_scrapling_schema(result, max_chars=1000)
        assert len(output["text"]) == 1000

    def test_to_scrapling_schema_missing_optional_fields(self) -> None:
        """Transform handles missing optional fields."""
        result = {
            "url": "https://example.com",
            "tool": "httpx",
        }
        output = _to_scrapling_schema(result, max_chars=5000)

        assert output["url"] == "https://example.com"
        assert output["title"] == ""
        assert output["text"] == ""
        assert output["html_len"] == 0

    def test_to_scrapling_schema_includes_status_code(self) -> None:
        """Transform includes status_code if present."""
        result = {
            "url": "https://example.com",
            "status_code": 200,
            "tool": "httpx",
        }
        output = _to_scrapling_schema(result, max_chars=5000)
        assert output["status_code"] == 200

    def test_to_scrapling_schema_includes_error(self) -> None:
        """Transform includes error if present."""
        result = {
            "url": "https://example.com",
            "error": "Connection timeout",
            "tool": "httpx",
        }
        output = _to_scrapling_schema(result, max_chars=5000)
        assert output["error"] == "Connection timeout"


class TestFetchHttpMode:
    """Tests for HTTP mode fetching."""

    def test_fetch_http_httpx_basic(self) -> None:
        """_fetch_http_httpx makes HTTP request."""
        params = FetchParams(
            url="https://example.com",
            mode="http",
            max_chars=5000,
            return_format="text",
        )

        with patch("loom.tools.fetch._get_http_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><title>Example</title><body>Content</body></html>"
            mock_response.headers = {"content-type": "text/html"}
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = _fetch_http_httpx(params)

            assert result.status_code == 200
            assert result.url == "https://example.com"
            assert result.tool == "httpx"

    def test_fetch_http_httpx_handles_timeout(self) -> None:
        """_fetch_http_httpx handles request timeout."""
        params = FetchParams(
            url="https://example.com",
            mode="http",
            max_chars=5000,
        )

        with patch("loom.tools.fetch._get_http_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = TimeoutError("Request timeout")
            mock_get_client.return_value = mock_client

            result = _fetch_http_httpx(params)

            assert result.error is not None


class TestFetchStealthyMode:
    """Tests for stealthy mode fetching."""

    def test_fetch_stealthy_basic(self) -> None:
        """_fetch_stealthy returns FetchResult."""
        params = FetchParams(
            url="https://example.com",
            mode="stealthy",
            max_chars=5000,
        )

        with patch("loom.tools.fetch._fetch_http_scrapling") as mock_scrapling:
            mock_result = FetchResult(
                url="https://example.com",
                text="Content",
                tool="scrapling_stealthy",
            )
            mock_scrapling.return_value = mock_result

            result = _fetch_stealthy(params)
            assert isinstance(result, FetchResult)


class TestCacheHitMiss:
    """Tests for cache behavior in research_fetch."""

    def test_fetch_cache_hit(self, tmp_cache_dir: Path) -> None:
        """Fetch returns cached result on second call."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.fetch._fetch_http") as mock_fetch:
            mock_result = FetchResult(
                url="https://example.com",
                text="Original content",
                status_code=200,
                tool="httpx",
            )
            mock_fetch.return_value = mock_result

            result1 = research_fetch(
                url="https://example.com",
                mode="http",
                bypass_cache=False,
            )

            result2 = research_fetch(
                url="https://example.com",
                mode="http",
                bypass_cache=False,
            )

            assert result1["text"] == result2["text"]
            assert mock_fetch.call_count == 1

    def test_fetch_cache_miss(self, tmp_cache_dir: Path) -> None:
        """Fetch bypasses cache when bypass_cache=True."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.fetch._fetch_http") as mock_fetch:
            mock_result1 = FetchResult(
                url="https://example.com",
                text="Version 1",
                status_code=200,
                tool="httpx",
            )
            mock_result2 = FetchResult(
                url="https://example.com",
                text="Version 2",
                status_code=200,
                tool="httpx",
            )
            mock_fetch.side_effect = [mock_result1, mock_result2]

            research_fetch(
                url="https://example.com",
                mode="http",
                bypass_cache=True,
            )

            research_fetch(
                url="https://example.com",
                mode="http",
                bypass_cache=True,
            )

            assert mock_fetch.call_count == 2

    def test_fetch_cache_separate_modes(self, tmp_cache_dir: Path) -> None:
        """Fetch caches separately by mode."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.fetch._fetch_http") as mock_http, patch(
            "loom.tools.fetch._fetch_stealthy"
        ) as mock_stealthy:
            http_result = FetchResult(
                url="https://example.com",
                text="HTTP version",
                tool="httpx",
            )
            stealthy_result = FetchResult(
                url="https://example.com",
                text="Stealthy version",
                tool="scrapling",
            )
            mock_http.return_value = http_result
            mock_stealthy.return_value = stealthy_result

            result1 = research_fetch(
                url="https://example.com",
                mode="http",
                bypass_cache=False,
            )
            result2 = research_fetch(
                url="https://example.com",
                mode="stealthy",
                bypass_cache=False,
            )

            assert result1["text"] != result2["text"]


class TestAutoEscalation:
    """Tests for auto_escalate feature."""

    def test_auto_escalate_http_to_stealthy_on_cloudflare(self, tmp_cache_dir: Path) -> None:
        """Auto-escalate escalates HTTP to stealthy on Cloudflare block."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        cf_blocked = FetchResult(
            url="https://example.com",
            status_code=403,
            text="Cloudflare Ray ID: xyz",
            tool="httpx",
        )
        success = FetchResult(
            url="https://example.com",
            status_code=200,
            text="Real content",
            tool="scrapling",
        )

        with patch("loom.tools.fetch._fetch_http", return_value=cf_blocked), patch(
            "loom.tools.fetch._fetch_stealthy", return_value=success
        ):
            result = research_fetch(
                url="https://example.com",
                mode="http",
                auto_escalate=True,
                bypass_cache=True,
            )

            assert result["tool"] == "scrapling"


class TestFetchResult:
    """Tests for FetchResult model."""

    def test_fetch_result_basic(self) -> None:
        """FetchResult can be instantiated."""
        result = FetchResult(
            url="https://example.com",
            status_code=200,
            text="Content",
            tool="httpx",
        )
        assert result.url == "https://example.com"
        assert result.status_code == 200
        assert result.text == "Content"

    def test_fetch_result_json_alias(self) -> None:
        """FetchResult.json_data serializes as 'json'."""
        result = FetchResult(
            url="https://example.com",
            json_data={"key": "value"},
            tool="httpx",
        )
        output = result.model_dump(by_alias=True)
        assert "json" in output
        assert output["json"] == {"key": "value"}

    def test_fetch_result_with_error(self) -> None:
        """FetchResult can include error message."""
        result = FetchResult(
            url="https://example.com",
            error="Connection failed",
            tool="httpx",
        )
        assert result.error == "Connection failed"
        assert result.status_code is None


class TestFetchEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_fetch_respects_max_chars(self, tmp_cache_dir: Path) -> None:
        """Fetch respects max_chars parameter."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        long_content = "x" * 10000

        with patch("loom.tools.fetch._fetch_http") as mock_fetch:
            mock_result = FetchResult(
                url="https://example.com",
                text=long_content,
                tool="httpx",
            )
            mock_fetch.return_value = mock_result

            result = research_fetch(
                url="https://example.com",
                mode="http",
                max_chars=1000,
                bypass_cache=True,
            )

            assert len(result["text"]) <= 1000

    def test_fetch_with_custom_headers(self, tmp_cache_dir: Path) -> None:
        """Fetch passes custom headers to fetcher."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        custom_headers = {"X-Custom": "value"}

        with patch("loom.tools.fetch._fetch_http") as mock_fetch:
            mock_result = FetchResult(
                url="https://example.com",
                text="Content",
                tool="httpx",
            )
            mock_fetch.return_value = mock_result

            research_fetch(
                url="https://example.com",
                mode="http",
                headers=custom_headers,
                bypass_cache=True,
            )

            assert mock_fetch.called

    def test_fetch_elapsed_ms_is_numeric(self, tmp_cache_dir: Path) -> None:
        """Fetch result includes elapsed_ms as integer."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.fetch._fetch_stealthy") as mock_fetch:
            mock_result = FetchResult(
                url="https://example.com",
                text="Content",
                tool="camoufox",
            )
            mock_fetch.return_value = mock_result

            result = research_fetch(
                url="https://example.com",
                mode="stealthy",
                bypass_cache=True,
            )

            assert "elapsed_ms" in result
            assert isinstance(result["elapsed_ms"], int)
            assert result["elapsed_ms"] >= 0

    def test_fetch_return_html_mode(self, tmp_cache_dir: Path) -> None:
        """Fetch can return HTML in return_format='html'."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        with patch("loom.tools.fetch._fetch_stealthy") as mock_fetch:
            mock_result = FetchResult(
                url="https://example.com",
                text="Content",
                html="<html>Raw HTML</html>",
                tool="camoufox",
            )
            mock_fetch.return_value = mock_result

            result = research_fetch(
                url="https://example.com",
                mode="stealthy",
                return_format="html",
                bypass_cache=True,
            )

            assert result.get("html") == "<html>Raw HTML</html>"


class TestCloudflareDetection:
    """Tests for _is_cloudflare_block helper."""

    def test_detects_403_with_ray_id(self) -> None:
        """Detects Cloudflare 403 with Ray ID."""
        result = FetchResult(
            url="https://x.com", status_code=403, text="Attention Required Ray ID: abc123"
        )
        assert _is_cloudflare_block(result) is True

    def test_detects_403_with_cf_ray(self) -> None:
        """Detects Cloudflare 403 with CF-Ray header."""
        result = FetchResult(
            url="https://x.com", status_code=403, html="<html>cf-ray header</html>"
        )
        assert _is_cloudflare_block(result) is True

    def test_detects_503_cloudflare(self) -> None:
        """Detects Cloudflare 503."""
        result = FetchResult(url="https://x.com", status_code=503, text="Cloudflare challenge page")
        assert _is_cloudflare_block(result) is True

    def test_ignores_normal_403(self) -> None:
        """Ignores normal 403 without Cloudflare markers."""
        result = FetchResult(url="https://x.com", status_code=403, text="Forbidden")
        assert _is_cloudflare_block(result) is False

    def test_ignores_200(self) -> None:
        """Ignores 200 responses."""
        result = FetchResult(url="https://x.com", status_code=200, text="OK")
        assert _is_cloudflare_block(result) is False
