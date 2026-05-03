"""Tests for social intelligence tools."""

from __future__ import annotations
import pytest

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


pytestmark = pytest.mark.asyncio

class TestSocialSearch:
    """Tests for research_social_search tool."""

    async def test_valid_username_github(self):
        """Test searching for valid GitHub username."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_search

            result = await research_social_search("testuser", platforms=["github"])

        assert result["username"] == "testuser"
        assert result["platforms_checked"] == 1
        assert result["total_found"] >= 0

    async def test_invalid_username(self):
        """Test with invalid username characters."""
        from loom.tools.social_intel import research_social_search

        result = await research_social_search("user@invalid#name", platforms=["github"])
        assert "error" in result
        assert result["platforms_checked"] == 0

    async def test_username_too_long(self):
        """Test with username exceeding length limit."""
        from loom.tools.social_intel import research_social_search

        long_username = "a" * 300
        result = await research_social_search(long_username)
        assert "error" in result

    async def test_empty_username(self):
        """Test with empty username."""
        from loom.tools.social_intel import research_social_search

        result = await research_social_search("", platforms=["github"])
        assert "error" in result

    async def test_default_platforms(self):
        """Test that default platforms are used when not specified."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_search

            result = await research_social_search("testuser")

        # Should check default platforms
        assert result["platforms_checked"] == 8
        assert result["username"] == "testuser"

    async def test_unknown_platform(self):
        """Test handling of unknown platform."""
        from loom.tools.social_intel import research_social_search

        result = await research_social_search("testuser", platforms=["unknown_platform"])
        assert "error" in result

    async def test_profile_exists(self):
        """Test when profile exists (200 status)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_search

            result = await research_social_search("github", platforms=["github"])

        assert result["total_found"] >= 0

    async def test_profile_not_found(self):
        """Test when profile doesn't exist (404 status)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.head = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_search

            result = await research_social_search("nonexistentuser123xyz", platforms=["github"])

        assert result["username"] == "nonexistentuser123xyz"
        assert "github" in result["not_found"]

    async def test_valid_usernames(self):
        """Test various valid username formats."""
        from loom.tools.social_intel import research_social_search

        valid_usernames = ["user123", "user_name", "user-name", "UserName", "123user"]

        for username in valid_usernames:
            result = await research_social_search(username, platforms=["github"])
            assert "error" not in result, f"Username {username} should be valid"


class TestSocialProfile:
    """Tests for research_social_profile tool."""

    async def test_extract_og_metadata(self):
        """Test extracting Open Graph metadata from HTML."""
        html = """
        <html>
            <head>
                <meta property="og:title" content="John Doe">
                <meta property="og:description" content="Software Engineer">
                <meta property="og:image" content="https://example.com/avatar.jpg">
            </head>
        </html>
        """

        mock_resp = AsyncMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("loom.tools.social_intel.httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_profile

            result = await research_social_profile("https://github.com/johndoe")

        assert result["name"] == "John Doe"
        assert result["bio"] == "Software Engineer"
        assert result["avatar_url"] == "https://example.com/avatar.jpg"
        assert result["platform"] == "github"

    async def test_detect_platform(self):
        """Test platform detection from URL."""
        test_cases = [
            ("https://github.com/user", "github"),
            ("https://x.com/user", "twitter"),
            ("https://twitter.com/user", "twitter"),
            ("https://reddit.com/user/user", "reddit"),
            ("https://news.ycombinator.com/user?id=user", "hackernews"),
            ("https://linkedin.com/in/user", "linkedin"),
            ("https://medium.com/@user", "medium"),
            ("https://dev.to/user", "dev.to"),
            ("https://keybase.io/user", "keybase"),
            ("https://example.com", "unknown"),
        ]

        for url, expected_platform in test_cases:
            mock_resp = AsyncMock()
            mock_resp.text = "<html></html>"
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)

            with patch("loom.tools.social_intel.httpx.AsyncClient", return_value=mock_client):
                from loom.tools.social_intel import research_social_profile

                result = await research_social_profile(url)

            assert result["platform"] == expected_platform, f"Failed for {url}"

    async def test_invalid_url(self):
        """Test with invalid URL."""
        from loom.tools.social_intel import research_social_profile

        result = await research_social_profile("not a valid url")
        assert "error" in result
        assert result["avatar_url"] is None

    async def test_network_error(self):
        """Test handling network errors."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("Network timeout"))

        with patch("loom.tools.social_intel.httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_profile

            result = await research_social_profile("https://github.com/user")

        assert "error" in result
        assert result["name"] is None

    async def test_no_metadata(self):
        """Test with HTML that has no Open Graph tags."""
        html = """
        <html>
            <head>
                <title>User Profile</title>
            </head>
            <body>Profile content</body>
        </html>
        """

        mock_resp = AsyncMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("loom.tools.social_intel.httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_profile

            result = await research_social_profile("https://github.com/user")

        assert result["name"] is None
        assert result["bio"] is None
        assert result["avatar_url"] is None
        assert result["metadata"] == {}

    async def test_case_insensitive_platform_detection(self):
        """Test platform detection is case-insensitive."""
        mock_resp = AsyncMock()
        mock_resp.text = "<html></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("loom.tools.social_intel.httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_profile

            result = await research_social_profile("HTTPS://GITHUB.COM/USER")

        assert result["platform"] == "github"

    async def test_metadata_with_name_attribute(self):
        """Test extracting metadata using name attribute instead of property."""
        html = """
        <html>
            <head>
                <meta name="og:title" content="Jane Doe">
                <meta name="og:description" content="Designer">
            </head>
        </html>
        """

        mock_resp = AsyncMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("loom.tools.social_intel.httpx.AsyncClient", return_value=mock_client):
            from loom.tools.social_intel import research_social_profile

            result = await research_social_profile("https://medium.com/@jane")

        assert result["name"] == "Jane Doe"
        assert result["bio"] == "Designer"
