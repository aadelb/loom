"""Tests for enrichment tools (language detection, Wayback Machine)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDetectLanguage:
    def test_english_detection(self):
        mock_lang = MagicMock()
        mock_lang.prob = 0.99
        mock_lang.__str__ = lambda self: "en:0.99"

        mock_langdetect = MagicMock()
        mock_langdetect.detect = MagicMock(return_value="en")
        mock_langdetect.detect_langs = MagicMock(return_value=[mock_lang])

        with patch.dict("sys.modules", {"langdetect": mock_langdetect}):
            from loom.tools.core.enrich import research_detect_language

            result = research_detect_language("This is a test sentence in English.")

        assert result["language"] == "en"
        assert result["confidence"] == 0.99

    def test_short_text(self):
        from loom.tools.core.enrich import research_detect_language

        result = research_detect_language("hi")
        assert result["language"] == "unknown"
        assert "too short" in result.get("error", "")

    def test_empty_text(self):
        from loom.tools.core.enrich import research_detect_language

        result = research_detect_language("")
        assert result["language"] == "unknown"

    def test_langdetect_not_installed(self):
        with patch.dict("sys.modules", {"langdetect": None}):
            # Need to reimport to trigger the ImportError
            import importlib

            import loom.tools.core.enrich

            importlib.reload(loom.tools.enrich)
            result = loom.tools.enrich.research_detect_language("This is English text for testing.")
            assert "not installed" in result.get("error", "")

    def test_langdetect_no_features_exception(self):
        """Test graceful handling of LangDetectException (no detectable features)."""
        mock_langdetect = MagicMock()

        class FakeLangDetectException(Exception):
            pass

        mock_langdetect.LangDetectException = FakeLangDetectException
        mock_langdetect.detect.side_effect = FakeLangDetectException("No features in text")
        mock_langdetect.detect_langs = MagicMock(return_value=[])

        with patch.dict("sys.modules", {"langdetect": mock_langdetect}):
            from loom.tools.core.enrich import research_detect_language

            result = research_detect_language("12345 !@#$% 67890")

        assert result["language"] == "unknown"
        assert "insufficient text for detection" in result.get("error", "")


class TestWayback:
    @pytest.mark.asyncio
    async def test_snapshot_found(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype", "digest"],
            ["20240101120000", "https://example.com", "200", "text/html", "abc123"],
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.core.enrich import research_wayback

            result = await research_wayback("https://example.com")

        assert len(result["snapshots"]) == 1
        assert "archive_url" in result["snapshots"][0]
        assert "20240101120000" in result["snapshots"][0]["archive_url"]

    @pytest.mark.asyncio
    async def test_no_snapshots(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype", "digest"],
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.core.enrich import research_wayback

            result = await research_wayback("https://dead-link.com")

        assert result["snapshots"] == []
        assert "no snapshots" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_malformed_rows_skipped(self):
        """Test that malformed rows are gracefully skipped."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype", "digest"],
            ["20240101120000", "https://example.com", "200", "text/html", "abc123"],
            ["20240102"],  # Incomplete row (too few fields)
            ["20240103120000", "https://example.com", "200", "text/html"],  # Complete row
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.core.enrich import research_wayback

            result = await research_wayback("https://example.com")

        # Should have 2 valid snapshots (malformed row skipped)
        assert len(result["snapshots"]) == 2
        assert result["snapshots"][0]["timestamp"] == "20240101120000"
        assert result["snapshots"][1]["timestamp"] == "20240103120000"

    @pytest.mark.asyncio
    async def test_invalid_response_type(self):
        """Test that non-list responses are handled gracefully."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "unexpected format"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            from loom.tools.core.enrich import research_wayback

            result = await research_wayback("https://example.com")

        assert result["snapshots"] == []
        assert "no snapshots" in result.get("error", "")
