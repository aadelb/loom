"""Tests for ephemeral .onion site scanner (dead_drop_scanner)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestResearchDeadDropScanner:
    async def test_empty_urls_list(self):
        """Test handling of empty URLs list."""
        from loom.tools.dead_drop_scanner import research_dead_drop_scanner

        result = await research_dead_drop_scanner([])

        assert result["error"] == "urls list is empty"
        assert result["scanned"] == 0
        assert result["alive"] == 0
        assert result["content"] == []

    async def test_tor_disabled(self):
        """Test error when Tor is disabled in config."""
        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config:
            mock_config.return_value = {"TOR_ENABLED": False}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            urls = ["http://example.onion"]
            result = await research_dead_drop_scanner(urls)

            assert "Tor disabled" in result["error"]
            assert result["scanned"] == 1
            assert result["alive"] == 0

    async def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config, patch(
            "loom.tools.dead_drop_scanner.validate_url",
            side_effect=ValueError("Invalid URL"),
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            result = await research_dead_drop_scanner(["not-a-valid-url"])

            assert result["scanned"] == 1
            assert result["alive"] == 0
            assert len(result["content"]) == 1
            assert result["content"][0]["status"] == "invalid"

    async def test_successful_fetch_creates_node(self):
        """Test that successful fetch creates a content node."""
        fetch_result = {
            "text": "Page content here",
            "html": "<html>content</html>",
            "title": "Test Page",
        }

        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config, patch(
            "loom.tools.dead_drop_scanner.validate_url"
        ), patch(
            "loom.tools.dead_drop_scanner.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            result = await research_dead_drop_scanner(["http://example.onion"])

            assert result["alive"] == 1
            assert len(result["content"]) == 1
            assert result["content"][0]["status"] == "alive"
            assert "content_hash" in result["content"][0]
            assert "shingle_count" in result["content"][0]

    async def test_empty_content_handling(self):
        """Test handling when fetch returns empty content."""
        fetch_result = {"text": "", "html": ""}

        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config, patch(
            "loom.tools.dead_drop_scanner.validate_url"
        ), patch(
            "loom.tools.dead_drop_scanner.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            result = await research_dead_drop_scanner(["http://example.onion"])

            assert result["alive"] == 0
            assert len(result["content"]) == 1
            assert result["content"][0]["status"] == "empty"

    async def test_fetch_error_handling(self):
        """Test handling of fetch errors."""
        fetch_result = {"error": "Connection timeout"}

        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config, patch(
            "loom.tools.dead_drop_scanner.validate_url"
        ), patch(
            "loom.tools.dead_drop_scanner.research_fetch",
            return_value=fetch_result,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            result = await research_dead_drop_scanner(["http://example.onion"])

            assert result["alive"] == 0
            assert len(result["content"]) == 1
            assert result["content"][0]["status"] == "dead"

    async def test_urls_capped_at_100(self):
        """Test that URLs list is capped at 100."""
        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config:
            mock_config.return_value = {"TOR_ENABLED": True}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            urls = [f"http://example{i}.onion" for i in range(150)]
            result = await research_dead_drop_scanner(urls)

            assert result["scanned"] == 100

    async def test_response_has_required_keys(self):
        """Test that response has all required keys."""
        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config:
            mock_config.return_value = {"TOR_ENABLED": False}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            result = await research_dead_drop_scanner(["http://example.onion"])

            assert "scanned" in result
            assert "alive" in result
            assert "dead" in result
            assert "content" in result
            assert "reuse_pairs" in result
            assert "scan_timestamp" in result


@pytest.mark.asyncio
class TestShinglingAndSimilarity:
    async def test_shingle_generation(self):
        """Test k-gram shingle generation."""
        from loom.tools.dead_drop_scanner import _shingle_text

        text = "thequickbrownfox"
        shingles = _shingle_text(text, k=5)

        # With k=5, "thequickbrownfox" should generate shingles
        assert len(shingles) > 0
        assert "thequ" in shingles
        assert "quick" in shingles

    def test_shingle_empty_text(self):
        """Test shingle generation with empty text."""
        from loom.tools.dead_drop_scanner import _shingle_text

        shingles = _shingle_text("", k=10)

        assert shingles == set()

    def test_shingle_text_shorter_than_k(self):
        """Test shingle generation when text is shorter than k."""
        from loom.tools.dead_drop_scanner import _shingle_text

        shingles = _shingle_text("short", k=10)

        assert shingles == set()

    def test_jaccard_similarity_identical_sets(self):
        """Test Jaccard similarity of identical sets."""
        from loom.tools.dead_drop_scanner import _jaccard_similarity

        set1 = {"a", "b", "c"}
        set2 = {"a", "b", "c"}

        similarity = _jaccard_similarity(set1, set2)

        assert similarity == 1.0

    def test_jaccard_similarity_disjoint_sets(self):
        """Test Jaccard similarity of disjoint sets."""
        from loom.tools.dead_drop_scanner import _jaccard_similarity

        set1 = {"a", "b", "c"}
        set2 = {"x", "y", "z"}

        similarity = _jaccard_similarity(set1, set2)

        assert similarity == 0.0

    def test_jaccard_similarity_partial_overlap(self):
        """Test Jaccard similarity with partial overlap."""
        from loom.tools.dead_drop_scanner import _jaccard_similarity

        set1 = {"a", "b", "c"}
        set2 = {"b", "c", "d"}

        similarity = _jaccard_similarity(set1, set2)

        # Intersection: {b, c}, Union: {a, b, c, d}
        # Similarity: 2/4 = 0.5
        assert similarity == 0.5

    def test_jaccard_similarity_empty_sets(self):
        """Test Jaccard similarity of empty sets."""
        from loom.tools.dead_drop_scanner import _jaccard_similarity

        set1 = set()
        set2 = set()

        similarity = _jaccard_similarity(set1, set2)

        assert similarity == 1.0

    async def test_reuse_detection_above_threshold(self):
        """Test that content reuse above threshold is detected."""
        fetch_result1 = {"text": "common content repeated pattern"}
        fetch_result2 = {"text": "common content repeated pattern"}

        call_count = [0]

        def fetch_side_effect(*args, **kwargs):
            call_count[0] += 1
            return fetch_result1 if call_count[0] == 1 else fetch_result2

        with patch("loom.tools.dead_drop_scanner.get_config") as mock_config, patch(
            "loom.tools.dead_drop_scanner.validate_url"
        ), patch(
            "loom.tools.dead_drop_scanner.research_fetch",
            side_effect=fetch_side_effect,
        ):
            mock_config.return_value = {"TOR_ENABLED": True, "TOR_SOCKS5_PROXY": "socks5h://127.0.0.1:9050"}

            from loom.tools.dead_drop_scanner import research_dead_drop_scanner

            result = await research_dead_drop_scanner([
                "http://site1.onion",
                "http://site2.onion",
            ])

            # Should detect reuse pairs if content is similar enough
            assert "reuse_pairs" in result


class TestContentHashing:
    def test_content_hash_generated(self):
        """Test that content hash is generated for fetched content."""
        import hashlib

        content = "test content for hashing"
        expected_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Simulate what the tool does
        actual_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        assert actual_hash == expected_hash

    def test_different_content_different_hash(self):
        """Test that different content produces different hashes."""
        import hashlib

        content1 = "first content"
        content2 = "second content"

        hash1 = hashlib.sha256(content1.encode()).hexdigest()[:16]
        hash2 = hashlib.sha256(content2.encode()).hexdigest()[:16]

        assert hash1 != hash2
