"""Unit tests for stealth tools — camoufox and botasaurus."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from loom.tools.stealth import research_botasaurus, research_camoufox


class TestCamoufox:
    """research_camoufox tool tests."""

    def test_camoufox_import_error_graceful(self) -> None:
        """ImportError on camoufox import returns error dict."""
        with patch("loom.tools.stealth._fetch_camoufox") as mock_fetch:
            # Simulate ImportError
            mock_fetch.return_value = MagicMock(
                url="https://example.com",
                error="Camoufox not installed: pip install camoufox",
                model_dump=lambda exclude_none=True: {
                    "url": "https://example.com",
                    "error": "Camoufox not installed: pip install camoufox",
                },
            )

            async def run_test() -> None:
                result = await research_camoufox("https://example.com")
                assert result["error"] == "Camoufox not installed: pip install camoufox"
                assert result["url"] == "https://example.com"

            asyncio.run(run_test())

    def test_camoufox_returns_expected_fields(self) -> None:
        """Camoufox result includes url, title, text, tool keys."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "url": "https://example.com",
            "title": "Example Page",
            "text": "Example content",
            "html": "<html>example</html>",
        }

        with patch("loom.tools.stealth._fetch_camoufox", return_value=mock_result):

            async def run_test() -> None:
                result = await research_camoufox("https://example.com")
                assert result["url"] == "https://example.com"
                assert result["title"] == "Example Page"
                assert result["text"] == "Example content"
                assert result["tool"] == "camoufox"

            asyncio.run(run_test())


class TestBotasaurus:
    """research_botasaurus tool tests."""

    def test_botasaurus_delegates_to_fetch(self) -> None:
        """botasaurus delegates to research_fetch with mode='dynamic'."""
        with patch("loom.tools.fetch.research_fetch") as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "text": "Content",
                "title": "Example",
            }

            async def run_test() -> None:
                result = await research_botasaurus("https://example.com")
                mock_fetch.assert_called_once()
                call_kwargs = mock_fetch.call_args.kwargs
                assert call_kwargs["mode"] == "dynamic"

            asyncio.run(run_test())

    def test_botasaurus_returns_tool_field(self) -> None:
        """botasaurus result has tool='botasaurus'."""
        with patch("loom.tools.fetch.research_fetch") as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "text": "Content",
            }

            async def run_test() -> None:
                result = await research_botasaurus("https://example.com")
                assert result["tool"] == "botasaurus"

            asyncio.run(run_test())
