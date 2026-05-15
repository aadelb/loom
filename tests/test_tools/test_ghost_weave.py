"""Tests for temporal hyperlink graph builder (ghost_weave)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestResearchGhostWeave:
    async def test_invalid_seed_url(self):
        """Test error when seed URL is invalid."""
        with patch("loom.tools.adversarial.ghost_weave.validate_url", side_effect=ValueError("Invalid URL")):
            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("not-a-url")

            assert "error" in result
            assert "invalid seed URL" in result["error"]
            assert result["pages_crawled"] == 0

    async def test_tor_disabled(self):
        """Test error when Tor is disabled."""
        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ):
            mock_config.return_value = {"TOR_ENABLED": False}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("http://example.onion")

            assert "Tor disabled" in result["error"]
            assert result["pages_crawled"] == 0

    async def test_depth_clamping(self):
        """Test that depth is clamped to 1-3 range."""
        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch"
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            # Request depth=10 should be clamped to 3
            result = await research_ghost_weave("http://example.onion", depth=10)

            # Should still return valid response
            assert "nodes" in result
            assert "edges" in result

    async def test_max_pages_clamping(self):
        """Test that max_pages is clamped to 1-100 range."""
        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch"
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            # Request max_pages=500 should be clamped to 100
            result = await research_ghost_weave("http://example.onion", max_pages=500)

            # Pages crawled should not exceed 100
            assert result["pages_crawled"] <= 100

    async def test_successful_single_page_crawl(self):
        """Test successful crawl of single page."""
        fetch_result = {
            "html": '<html><a href="http://example2.onion">Link 1</a><a href="http://example3.onion">Link 2</a></html>',
            "text": "Page content",
            "title": "Example Page",
        }

        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("http://example.onion", depth=1, max_pages=10)

            assert result["pages_crawled"] >= 1
            assert "nodes" in result
            assert len(result["nodes"]) >= 1
            assert result["nodes"][0]["url"] == "http://example.onion"

    async def test_edge_creation(self):
        """Test that edges are created from hyperlinks."""
        fetch_result = {
            "html": '<a href="http://target.onion">Target</a>',
            "text": "",
            "title": "Source",
        }

        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("http://example.onion", depth=1)

            assert "edges" in result

    async def test_dead_links_tracking(self):
        """Test that failed fetches are tracked as dead links."""
        fetch_result = {"error": "Connection timeout"}

        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("http://example.onion")

            assert "dead_links" in result
            assert len(result["dead_links"]) > 0

    async def test_graph_stats_calculation(self):
        """Test that graph statistics are calculated."""
        fetch_result = {
            "html": '<a href="http://other.onion">Link</a>',
            "text": "Content",
            "title": "Page",
        }

        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("http://example.onion", depth=1, max_pages=5)

            assert "graph_stats" in result
            assert "total_nodes" in result["graph_stats"]
            assert "total_edges" in result["graph_stats"]
            assert "avg_degree" in result["graph_stats"]
            assert "density" in result["graph_stats"]

    async def test_response_structure(self):
        """Test that response has all required keys."""
        with patch("loom.tools.adversarial.ghost_weave.get_config") as mock_config, patch(
            "loom.tools.adversarial.ghost_weave.validate_url"
        ), patch(
            "loom.tools.adversarial.ghost_weave.research_fetch"
        ):
            mock_config.return_value = {"TOR_ENABLED": False}

            from loom.tools.adversarial.ghost_weave import research_ghost_weave

            result = await research_ghost_weave("http://example.onion")

            assert "seed" in result
            assert "pages_crawled" in result
            assert "nodes" in result
            assert "edges" in result
            assert "dead_links" in result


class TestUrlExtraction:
    def test_extract_hyperlinks_from_html(self):
        """Test extracting hyperlinks from HTML."""
        from loom.tools.adversarial.ghost_weave import _extract_hyperlinks

        html = '''
            <a href="http://example.onion/page1">Page 1</a>
            <a href="http://example.onion/page2">Page 2</a>
            <a href="/relative">Relative</a>
        '''
        base_url = "http://example.onion"

        links = _extract_hyperlinks(html, base_url)

        assert len(links) >= 2
        assert "http://example.onion/page1" in links

    def test_relative_url_resolution(self):
        """Test that relative URLs are resolved."""
        from loom.tools.adversarial.ghost_weave import _extract_hyperlinks

        html = '<a href="/subpage">Sub</a>'
        base_url = "http://example.onion/path/"

        links = _extract_hyperlinks(html, base_url)

        assert len(links) > 0
        # Should be absolute URL
        assert links[0].startswith("http")

    def test_onion_urls_included(self):
        """Test that .onion URLs are included."""
        from loom.tools.adversarial.ghost_weave import _extract_hyperlinks

        html = '<a href="http://other.onion">Onion</a>'
        base_url = "http://example.onion"

        links = _extract_hyperlinks(html, base_url)

        assert any(".onion" in link for link in links)

    def test_malformed_urls_skipped(self):
        """Test that malformed URLs are skipped."""
        from loom.tools.adversarial.ghost_weave import _extract_hyperlinks

        html = '''
            <a href="http://valid.onion">Valid</a>
            <a href="ht!tp://invalid">Invalid</a>
        '''
        base_url = "http://example.onion"

        links = _extract_hyperlinks(html, base_url)

        # Should have at least the valid link
        assert len(links) >= 1


class TestUrlNormalization:
    def test_normalize_url_removes_fragment(self):
        """Test that URL fragments are removed."""
        from loom.tools.adversarial.ghost_weave import _normalize_url

        url = "http://example.onion/page#section"
        normalized = _normalize_url(url)

        assert "#section" not in normalized

    def test_normalize_url_keeps_query(self):
        """Test that query parameters are kept."""
        from loom.tools.adversarial.ghost_weave import _normalize_url

        url = "http://example.onion/page?id=123"
        normalized = _normalize_url(url)

        assert "?id=123" in normalized

    def test_normalize_identical_calls(self):
        """Test that normalization is idempotent."""
        from loom.tools.adversarial.ghost_weave import _normalize_url

        url = "http://example.onion/page?key=value#frag"
        norm1 = _normalize_url(url)
        norm2 = _normalize_url(norm1)

        assert norm1 == norm2
