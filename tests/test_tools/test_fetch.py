"""Unit tests for research_fetch tool — URL validation, caching, scrapling.

NOTE: The 4 cache/scrapling-shape tests below are written against the
Hetzner research-toolbox design (Scrapling-based fetcher with on-disk
content-hash cache and {title, html_len, fetched_at} return shape).
The current Loom fetch.py is an httpx-based implementation with a
different return shape and no cache layer. The 4 tests are marked as
skipped with a TODO until fetch.py is reunified with the Hetzner design
(tracked for post-alpha). SSRF validation tests (non-skipped) still run
against the current implementation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loom.tools.fetch import FetchResult, _is_cloudflare_block, research_fetch

_SCRAPLING_API_TODO = (
    "fetch.py currently uses httpx; Scrapling cache+return-shape API "
    "from Hetzner research-toolbox will be ported post-v0.1.0-alpha"
)



pytestmark = pytest.mark.asyncio
class TestFetch:
    """research_fetch tool tests."""

    async def test_fetch_rejects_ssrf_url(self) -> None:
        """Fetch rejects URLs that fail SSRF validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await research_fetch(url="http://localhost:8080")

    async def test_fetch_rejects_private_ip(self) -> None:
        """Fetch rejects private IPs."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await research_fetch(url="http://192.168.1.1")

    async def test_fetch_returns_expected_fields(self, tmp_cache_dir: Path) -> None:
        """Fetch result has expected fields (url, title, text, html_len, fetched_at)."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            # Mock Scrapling since we don't want real network calls
            # Patch at the location where scrapling is imported in the fetch module
            with patch("scrapling.fetchers.Fetcher") as mock_fetcher:
                mock_page = MagicMock()
                mock_page.css.return_value.get.return_value = "Page Title"
                mock_page.get_all_text.return_value = "Page content here"
                mock_page.html_content = "<html>content</html>"

                mock_fetcher.get.return_value = mock_page

                result = await research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=True,
                )

                assert "url" in result
                assert "title" in result
                assert "text" in result
                assert "html_len" in result
                assert "fetched_at" in result
                assert "tool" in result
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")

    async def test_fetch_cache_hit(self, tmp_cache_dir: Path) -> None:
        """Fetch returns cached result on second call (same params)."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            with patch("scrapling.fetchers.Fetcher") as mock_fetcher:
                mock_page = MagicMock()
                mock_page.css.return_value.get.return_value = "Title"
                mock_page.get_all_text.return_value = "Content"
                mock_page.html_content = "<html></html>"

                mock_fetcher.get.return_value = mock_page

                # First call
                result1 = await research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=False,
                )

                # Second call — should be cached
                result2 = await research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=False,
                )

                # Both should have the same content
                assert result1["text"] == result2["text"]
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")

    async def test_fetch_max_chars_applied(self, tmp_cache_dir: Path) -> None:
        """Fetch respects max_chars parameter."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            with patch("scrapling.fetchers.Fetcher") as mock_fetcher:
                mock_page = MagicMock()
                mock_page.css.return_value.get.return_value = "Title"
                # Very long content
                long_content = "x" * 100000
                mock_page.get_all_text.return_value = long_content
                mock_page.html_content = "<html>" + long_content + "</html>"

                mock_fetcher.get.return_value = mock_page

                result = await research_fetch(
                    url="https://example.com",
                    mode="http",
                    max_chars=1000,
                    bypass_cache=True,
                )

                # Text should be capped at max_chars
                assert len(result["text"]) <= 1000
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")

    async def test_fetch_bypass_cache(self, tmp_cache_dir: Path) -> None:
        """Fetch with bypass_cache=True ignores cache."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        try:
            with patch("scrapling.fetchers.Fetcher") as mock_fetcher:
                mock_page = MagicMock()
                mock_page.css.return_value.get.return_value = "Title"
                mock_page.get_all_text.return_value = "Content v1"
                mock_page.html_content = "<html></html>"

                mock_fetcher.get.return_value = mock_page

                # First call
                result1 = await research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=True,
                )

                # Change mock response
                mock_page.get_all_text.return_value = "Content v2"

                # Second call with bypass_cache=True should get new content
                result2 = await research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=True,
                )

                assert result1["text"] != result2["text"]
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")


class TestCloudflareDetection:
    """Tests for _is_cloudflare_block helper."""

    async def test_detects_403_with_ray_id(self):
        result = FetchResult(
            url="https://x.com", status_code=403, text="Attention Required Ray ID: abc123"
        )
        assert _is_cloudflare_block(result) is True

    async def test_detects_403_with_cf_ray(self):
        result = FetchResult(
            url="https://x.com", status_code=403, html="<html>cf-ray header</html>"
        )
        assert _is_cloudflare_block(result) is True

    async def test_detects_503_cloudflare(self):
        result = FetchResult(url="https://x.com", status_code=503, text="Cloudflare challenge page")
        assert _is_cloudflare_block(result) is True

    async def test_ignores_normal_403(self):
        result = FetchResult(url="https://x.com", status_code=403, text="Forbidden")
        assert _is_cloudflare_block(result) is False

    async def test_ignores_200(self):
        result = FetchResult(url="https://x.com", status_code=200, text="OK")
        assert _is_cloudflare_block(result) is False

    async def test_ignores_404(self):
        result = FetchResult(url="https://x.com", status_code=404, text="Not found cloudflare")
        assert _is_cloudflare_block(result) is False


class TestFetchAutoEscalation:
    """Tests for auto_escalate parameter."""

    async def test_auto_escalate_off_returns_as_is(self, tmp_cache_dir):
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        cf_result = FetchResult(
            url="https://example.com", status_code=403, text="Cloudflare Ray ID: x", tool="httpx"
        )
        with patch("loom.tools.fetch._fetch_http", return_value=cf_result):
            result = await research_fetch(
                url="https://example.com", mode="http", auto_escalate=False, bypass_cache=True
            )
        assert result.get("status_code") == 403

    async def test_auto_escalate_on_tries_stealthy(self, tmp_cache_dir):
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        cf_result = FetchResult(
            url="https://example.com", status_code=403, text="Cloudflare Ray ID: x", tool="httpx"
        )
        ok_result = FetchResult(
            url="https://example.com", status_code=200, text="Real content", tool="camoufox"
        )

        with (
            patch("loom.tools.fetch._fetch_http", return_value=cf_result),
            patch("loom.tools.fetch._fetch_stealthy", return_value=ok_result),
        ):
            result = await research_fetch(
                url="https://example.com", mode="http", auto_escalate=True, bypass_cache=True
            )

        assert result.get("tool") == "camoufox"
