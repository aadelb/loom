"""Tests for trafilatura extraction fallback."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_traf_module():
    sys.modules.pop("loom.providers.trafilatura_extract", None)
    yield
    sys.modules.pop("loom.providers.trafilatura_extract", None)


class TestTrafilaturaExtract:
    def test_sdk_not_installed(self):
        with patch.dict("sys.modules", {"trafilatura": None}):
            from loom.providers.trafilatura_extract import extract_with_trafilatura

            result = extract_with_trafilatura(url="https://example.com")
            assert "not installed" in result["error"]

    def test_extract_from_url(self):
        mock_traf = MagicMock()
        mock_traf.fetch_url.return_value = "<html><body>Hello world</body></html>"
        mock_traf.extract.return_value = "Hello world"
        mock_metadata = MagicMock()
        mock_metadata.title = "Test Page"
        mock_traf.extract_metadata.return_value = mock_metadata

        with patch.dict("sys.modules", {"trafilatura": mock_traf}):
            from loom.providers.trafilatura_extract import extract_with_trafilatura

            result = extract_with_trafilatura(url="https://example.com")

        assert result["text"] == "Hello world"
        assert result["title"] == "Test Page"
        assert result["tool"] == "trafilatura"

    def test_extract_from_html(self):
        mock_traf = MagicMock()
        mock_traf.extract.return_value = "Extracted text"
        mock_traf.extract_metadata.return_value = None

        with patch.dict("sys.modules", {"trafilatura": mock_traf}):
            from loom.providers.trafilatura_extract import extract_with_trafilatura

            result = extract_with_trafilatura(html="<html><body>content</body></html>")

        assert result["text"] == "Extracted text"
        mock_traf.fetch_url.assert_not_called()

    def test_no_content(self):
        mock_traf = MagicMock()
        mock_traf.fetch_url.return_value = None

        with patch.dict("sys.modules", {"trafilatura": mock_traf}):
            from loom.providers.trafilatura_extract import extract_with_trafilatura

            result = extract_with_trafilatura(url="https://example.com")

        assert "no HTML" in result["error"]

    def test_extract_error(self):
        mock_traf = MagicMock()
        mock_traf.fetch_url.side_effect = RuntimeError("network error")

        with patch.dict("sys.modules", {"trafilatura": mock_traf}):
            from loom.providers.trafilatura_extract import extract_with_trafilatura

            result = extract_with_trafilatura(url="https://example.com")

        assert "network error" in result["error"]
