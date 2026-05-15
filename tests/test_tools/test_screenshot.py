"""Unit tests for research_screenshot — Playwright screenshot capture."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.core.screenshot import research_screenshot


class TestScreenshot:
    """research_screenshot captures webpage screenshots using Playwright."""

    @pytest.mark.asyncio
    async def test_screenshot_invalid_url(self) -> None:
        """Tool rejects invalid URLs."""
        result = await research_screenshot(url="not-a-url")

        assert "error" in result
        assert result["url"] == "not-a-url"

    @pytest.mark.asyncio
    async def test_screenshot_url_too_long(self) -> None:
        """Tool rejects URLs exceeding character limit."""
        long_url = "https://example.com/" + "x" * 3000
        result = await research_screenshot(url=long_url)

        assert "error" in result
        assert "exceeds" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_screenshot_invalid_selector(self) -> None:
        """Tool rejects invalid CSS selectors."""
        result = await research_screenshot(url="https://example.com", selector="")

        assert "error" in result
        assert "selector must be a non-empty string" in result["error"]

    @pytest.mark.asyncio
    async def test_screenshot_selector_too_long(self) -> None:
        """Tool rejects selectors exceeding 256 characters."""
        long_selector = "." + "x" * 300
        result = await research_screenshot(
            url="https://example.com", selector=long_selector
        )

        assert "error" in result
        assert "exceeds 256" in result["error"]

    @pytest.mark.asyncio
    async def test_screenshot_playwright_not_available(self) -> None:
        """Tool handles Playwright unavailable gracefully."""
        with patch("loom.tools.core.screenshot._HAS_PLAYWRIGHT", False):
            result = await research_screenshot(url="https://example.com")

            assert "error" in result
            assert "not installed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_screenshot_viewport_capture(self) -> None:
        """Tool captures viewport screenshot with correct dimensions."""
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(
            return_value=b"\x89PNG\r\n\x1a\n" + b"fake_png_data" * 100
        )
        mock_page.evaluate = AsyncMock(
            return_value={"width": 1920, "height": 1080}
        )

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(
                url="https://example.com", full_page=False
            )

            assert "screenshot_base64" in result
            assert result["width"] == 1920
            assert result["height"] == 1080
            assert result["full_page"] is False

    @pytest.mark.asyncio
    async def test_screenshot_full_page_capture(self) -> None:
        """Tool captures full-page screenshot."""
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(
            return_value=b"\x89PNG\r\n\x1a\n" + b"fullpage_data" * 200
        )
        mock_page.evaluate = AsyncMock(
            return_value={"width": 1920, "height": 5000}
        )

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(
                url="https://example.com", full_page=True
            )

            assert result["full_page"] is True
            assert result["height"] == 5000
            mock_page.screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_screenshot_element_selector(self) -> None:
        """Tool captures screenshot of specific element."""
        mock_element = AsyncMock()
        mock_element.screenshot = AsyncMock(return_value=b"\x89PNG" + b"elem_data" * 50)
        mock_element.bounding_box = AsyncMock(
            return_value={"width": 400, "height": 300, "x": 0, "y": 0}
        )

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(
                url="https://example.com", selector=".header"
            )

            assert result["selector"] == ".header"
            assert result["width"] == 400
            assert result["height"] == 300

    @pytest.mark.asyncio
    async def test_screenshot_selector_not_found(self) -> None:
        """Tool handles missing selector gracefully."""
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(
                url="https://example.com", selector=".nonexistent"
            )

            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_screenshot_page_navigation_timeout(self) -> None:
        """Tool handles page navigation timeout."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout"))

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(url="https://example.com")

            assert "error" in result
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_screenshot_base64_encoding(self) -> None:
        """Tool properly base64-encodes PNG data."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"test_image_data" * 50

        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=png_data)

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(url="https://example.com")

            assert "screenshot_base64" in result
            # Verify it's valid base64
            decoded = base64.b64decode(result["screenshot_base64"])
            assert decoded[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_screenshot_browser_cleanup(self) -> None:
        """Tool properly closes browser after capture."""
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"\x89PNG" + b"data" * 50)

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        with patch("loom.tools.core.screenshot.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            result = await research_screenshot(url="https://example.com")

            assert "error" not in result
            mock_page.close.assert_called_once()
