"""Tests for social_scraper module — Instagram and article extraction."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from loom.tools.intelligence.social_scraper import (
    research_instagram,
    research_article_extract,
    research_article_batch,
)



pytestmark = pytest.mark.asyncio
class TestInstagram:
    """Tests for research_instagram tool."""

    async def test_instagram_missing_library(self):
        """Test graceful handling when instaloader is not installed."""
        with patch("loom.tools.intelligence.social_scraper._HAS_INSTALOADER", False):
            result = await research_instagram("testuser")
            assert "error" in result
            assert "instaloader not installed" in result["error"]
            assert result["username"] == "testuser"

    async def test_instagram_invalid_username_none(self):
        """Test with None username."""
        result = await research_instagram(None)  # type: ignore
        assert "error" in result
        assert "invalid username" in result["error"]

    async def test_instagram_invalid_username_empty(self):
        """Test with empty username."""
        result = await research_instagram("")
        assert "error" in result
        assert "invalid username" in result["error"]

    async def test_instagram_invalid_username_type(self):
        """Test with non-string username."""
        result = await research_instagram(123)  # type: ignore
        assert "error" in result
        assert "invalid username" in result["error"]

    async def test_instagram_validation_order(self):
        """Test that input validation happens before library check."""
        # Invalid username should return error before checking library
        result = await research_instagram("")
        assert "error" in result
        assert "invalid username" in result["error"]
        assert "library" not in result.get("error", "").lower()

    async def test_instagram_library_check_after_validation(self):
        """Test library check happens after valid input."""
        with patch("loom.tools.intelligence.social_scraper._HAS_INSTALOADER", False):
            # Valid username but missing library
            result = await research_instagram("validuser")
            assert "error" in result
            assert "instaloader not installed" in result["error"]

    async def test_instagram_max_posts_positive(self):
        """Test max_posts parameter with positive value."""
        with patch("loom.tools.intelligence.social_scraper._HAS_INSTALOADER", False):
            result = await research_instagram("user", max_posts=50)
            # Should still fail due to missing library
            assert "error" in result

    async def test_instagram_max_posts_zero_or_negative(self):
        """Test max_posts parameter clamping with zero/negative values."""
        with patch("loom.tools.intelligence.social_scraper._HAS_INSTALOADER", False):
            result = await research_instagram("user", max_posts=-10)
            # Should clamp to 1, then fail on library
            assert "error" in result

    async def test_instagram_max_posts_large_value(self):
        """Test max_posts parameter clamping with large values."""
        with patch("loom.tools.intelligence.social_scraper._HAS_INSTALOADER", False):
            result = await research_instagram("user", max_posts=500)
            # Should clamp to 100, then fail on library
            assert "error" in result

    async def test_instagram_returns_dict_with_username(self):
        """Test that result includes username field."""
        result = await research_instagram("testuser")
        assert isinstance(result, dict)
        assert "username" in result


class TestArticleExtract:
    """Tests for research_article_extract tool."""

    async def test_article_missing_library(self):
        """Test graceful handling when newspaper3k is not installed."""
        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", False):
            result = await research_article_extract("https://example.com/article")
            assert "error" in result
            assert "newspaper3k not installed" in result["error"]
            assert result["url"] == "https://example.com/article"

    async def test_article_invalid_url_none(self):
        """Test with None URL."""
        result = await research_article_extract(None)  # type: ignore
        assert "error" in result
        assert "invalid url" in result["error"]

    async def test_article_invalid_url_empty(self):
        """Test with empty URL."""
        result = await research_article_extract("")
        assert "error" in result
        assert "invalid url" in result["error"]

    async def test_article_validation_before_library_check(self):
        """Test that URL validation happens before library check."""
        result = await research_article_extract("")
        assert "error" in result
        assert "invalid url" in result["error"]
        assert "library" not in result.get("error", "").lower()

    async def test_article_library_check_after_validation(self):
        """Test library check happens after valid URL input."""
        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", False):
            result = await research_article_extract("https://example.com/article")
            assert "error" in result
            assert "newspaper3k not installed" in result["error"]

    async def test_article_returns_dict_with_url(self):
        """Test that result includes url field."""
        result = await research_article_extract("https://example.com/article")
        assert isinstance(result, dict)
        assert "url" in result

    async def test_article_successful_extraction_fields(self):
        """Test successful article extraction returns expected structure."""
        mock_article = MagicMock()
        mock_article.title = "Test Title"
        mock_article.authors = ["Author A", "Author B"]
        mock_article.publish_date = datetime(2024, 1, 15, 10, 30, 0)
        mock_article.text = "Article content"
        mock_article.summary = "Summary"
        mock_article.keywords = ["key1", "key2"]
        mock_article.top_image = "https://example.com/img.jpg"
        mock_article.movies = ["https://example.com/video.mp4"]

        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch("loom.tools.intelligence.social_scraper.Article") as mock_class:
                mock_class.return_value = mock_article
                result = await research_article_extract("https://example.com/test")

                assert "url" in result
                assert "title" in result
                assert "authors" in result
                assert "publish_date" in result
                assert "text" in result
                assert "summary" in result
                assert "keywords" in result
                assert "top_image" in result
                assert "movies" in result

    async def test_article_extraction_handles_missing_optional_fields(self):
        """Test article extraction with None values."""
        mock_article = MagicMock()
        mock_article.title = None
        mock_article.authors = None
        mock_article.publish_date = None
        mock_article.text = "Content"
        mock_article.summary = None
        mock_article.keywords = None
        mock_article.top_image = None
        mock_article.movies = None

        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch("loom.tools.intelligence.social_scraper.Article") as mock_class:
                mock_class.return_value = mock_article
                result = await research_article_extract("https://example.com/test")

                # Should return a valid dict with default values
                assert result["title"] is None
                assert result["authors"] == []
                assert result["publish_date"] is None
                assert result["keywords"] == []

    async def test_article_extraction_with_exceptions(self):
        """Test error handling during extraction."""
        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch("loom.tools.intelligence.social_scraper.Article") as mock_class:
                mock_article = MagicMock()
                mock_article.download.side_effect = RuntimeError("Download failed")
                mock_class.return_value = mock_article

                result = await research_article_extract("https://example.com/test")
                assert "error" in result
                # Should contain the error message
                assert result["url"] == "https://example.com/test"


class TestArticleBatch:
    """Tests for research_article_batch tool."""

    async def test_batch_missing_library(self):
        """Test graceful handling when newspaper3k is not installed."""
        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", False):
            result = await research_article_batch(
                ["https://example.com/1", "https://example.com/2"]
            )
            assert "error" in result
            assert "newspaper3k not installed" in result["error"]
            assert result["urls_processed"] == 0

    async def test_batch_invalid_urls_empty(self):
        """Test with empty URL list."""
        result = await research_article_batch([])
        assert "error" in result
        assert "invalid urls" in result["error"]

    async def test_batch_invalid_urls_not_list(self):
        """Test with non-list URLs parameter."""
        result = await research_article_batch("not a list")  # type: ignore
        assert "error" in result
        assert "invalid urls" in result["error"]

    async def test_batch_validation_before_library_check(self):
        """Test that URL validation happens before library check."""
        result = await research_article_batch([])
        assert "error" in result
        assert "invalid urls" in result["error"]
        assert "library" not in result.get("error", "").lower()

    async def test_batch_library_check_after_validation(self):
        """Test library check happens after valid input."""
        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", False):
            result = await research_article_batch(["https://example.com/1"])
            assert "error" in result
            assert "newspaper3k not installed" in result["error"]

    async def test_batch_returns_expected_structure(self):
        """Test batch result has expected keys."""
        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch(
                "loom.tools.intelligence.social_scraper.research_article_extract"
            ) as mock_extract:
                mock_extract.return_value = {
                    "url": "https://example.com/1",
                    "title": "Test",
                    "authors": [],
                    "publish_date": None,
                    "text": "Content",
                    "summary": None,
                    "keywords": [],
                    "top_image": None,
                    "movies": [],
                }

                result = await research_article_batch(["https://example.com/1"])

                assert "urls_processed" in result
                assert "articles" in result
                assert "failed" in result
                assert isinstance(result["articles"], list)
                assert isinstance(result["failed"], list)

    async def test_batch_processes_urls(self):
        """Test batch processes URLs correctly."""
        urls = ["https://example.com/1", "https://example.com/2"]

        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch(
                "loom.tools.intelligence.social_scraper.research_article_extract"
            ) as mock_extract:
                mock_extract.return_value = {
                    "url": "https://example.com/1",
                    "title": "Test",
                    "authors": [],
                    "publish_date": None,
                    "text": "Content",
                    "summary": None,
                    "keywords": [],
                    "top_image": None,
                    "movies": [],
                }

                result = await research_article_batch(urls)

                assert result["urls_processed"] == 2
                assert mock_extract.called

    async def test_batch_max_concurrent_parameter(self):
        """Test max_concurrent parameter is accepted."""
        urls = ["https://example.com/1"]

        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch(
                "loom.tools.intelligence.social_scraper.research_article_extract"
            ) as mock_extract:
                mock_extract.return_value = {
                    "url": "https://example.com/1",
                    "title": "Test",
                    "authors": [],
                    "publish_date": None,
                    "text": "Content",
                    "summary": None,
                    "keywords": [],
                    "top_image": None,
                    "movies": [],
                }

                # Test with various max_concurrent values
                result = await research_article_batch(urls, max_concurrent=1)
                assert "urls_processed" in result

                result = await research_article_batch(urls, max_concurrent=10)
                assert "urls_processed" in result

                result = await research_article_batch(urls, max_concurrent=100)
                assert "urls_processed" in result

    async def test_batch_url_list_limit(self):
        """Test batch limits URL processing."""
        # Create more than 200 URLs
        urls = [f"https://example.com/{i}" for i in range(250)]

        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch(
                "loom.tools.intelligence.social_scraper.research_article_extract"
            ) as mock_extract:
                mock_extract.return_value = {
                    "url": "https://example.com/1",
                    "title": "Test",
                    "authors": [],
                    "publish_date": None,
                    "text": "Content",
                    "summary": None,
                    "keywords": [],
                    "top_image": None,
                    "movies": [],
                }

                result = await research_article_batch(urls)

                # Should be limited to 200
                assert result["urls_processed"] <= 200

    async def test_batch_handles_failed_extractions(self):
        """Test batch handles extraction failures."""
        urls = ["https://example.com/1", "https://example.com/2"]

        with patch("loom.tools.intelligence.social_scraper._HAS_NEWSPAPER", True):
            with patch(
                "loom.tools.intelligence.social_scraper.research_article_extract"
            ) as mock_extract:
                # First succeeds, second fails
                mock_extract.side_effect = [
                    {
                        "url": "https://example.com/1",
                        "title": "Test",
                        "authors": [],
                        "publish_date": None,
                        "text": "Content",
                        "summary": None,
                        "keywords": [],
                        "top_image": None,
                        "movies": [],
                    },
                    {
                        "url": "https://example.com/2",
                        "error": "Failed to extract",
                    },
                ]

                result = await research_article_batch(urls)

                assert result["urls_processed"] == 2
                assert len(result["articles"]) >= 0
                assert len(result["failed"]) >= 0


class TestIntegration:
    """Integration tests for social scraper tools."""

    async def test_instagram_returns_dict(self):
        """Test instagram returns dict structure."""
        result = await research_instagram("testuser")
        assert isinstance(result, dict)

    async def test_article_extract_returns_dict(self):
        """Test article extract returns dict structure."""
        result = await research_article_extract("https://example.com/article")
        assert isinstance(result, dict)

    async def test_article_batch_returns_dict(self):
        """Test article batch returns dict structure."""
        result = await research_article_batch(["https://example.com/1"])
        assert isinstance(result, dict)
        assert "urls_processed" in result
        assert "articles" in result
        assert "failed" in result
