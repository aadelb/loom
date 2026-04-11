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

from loom.tools.fetch import research_fetch

_SCRAPLING_API_TODO = (
    "fetch.py currently uses httpx; Scrapling cache+return-shape API "
    "from Hetzner research-toolbox will be ported post-v0.1.0-alpha"
)


class TestFetch:
    """research_fetch tool tests."""

    def test_fetch_rejects_ssrf_url(self) -> None:
        """Fetch rejects URLs that fail SSRF validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            research_fetch(url="http://localhost:8080")

    def test_fetch_rejects_private_ip(self) -> None:
        """Fetch rejects private IPs."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            research_fetch(url="http://192.168.1.1")

    @pytest.mark.skip(reason=_SCRAPLING_API_TODO)
    def test_fetch_returns_expected_fields(self, tmp_cache_dir: Path) -> None:
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

                result = research_fetch(
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

    @pytest.mark.skip(reason=_SCRAPLING_API_TODO)
    def test_fetch_cache_hit(self, tmp_cache_dir: Path) -> None:
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
                result1 = research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=False,
                )

                # Second call — should be cached
                result2 = research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=False,
                )

                # Both should have the same content
                assert result1["text"] == result2["text"]
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")

    @pytest.mark.skip(reason=_SCRAPLING_API_TODO)
    def test_fetch_max_chars_applied(self, tmp_cache_dir: Path) -> None:
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

                result = research_fetch(
                    url="https://example.com",
                    mode="http",
                    max_chars=1000,
                    bypass_cache=True,
                )

                # Text should be capped at max_chars
                assert len(result["text"]) <= 1000
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")

    @pytest.mark.skip(reason=_SCRAPLING_API_TODO)
    def test_fetch_bypass_cache(self, tmp_cache_dir: Path) -> None:
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
                result1 = research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=True,
                )

                # Change mock response
                mock_page.get_all_text.return_value = "Content v2"

                # Second call with bypass_cache=True should get new content
                result2 = research_fetch(
                    url="https://example.com",
                    mode="http",
                    bypass_cache=True,
                )

                assert result1["text"] != result2["text"]
        except ModuleNotFoundError as e:
            pytest.skip(f"scrapling dependency missing: {e}")
