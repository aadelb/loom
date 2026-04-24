"""Tests for enrichment tools (language detection, Wayback Machine)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestDetectLanguage:
    def test_english_detection(self):
        mock_lang = MagicMock()
        mock_lang.prob = 0.99
        mock_lang.__str__ = lambda self: "en:0.99"

        with (
            patch("langdetect.detect", return_value="en"),
            patch("langdetect.detect_langs", return_value=[mock_lang]),
        ):
            from loom.tools.enrich import research_detect_language

            result = research_detect_language("This is a test sentence in English.")

        assert result["language"] == "en"
        assert result["confidence"] == 0.99

    def test_short_text(self):
        from loom.tools.enrich import research_detect_language

        result = research_detect_language("hi")
        assert result["language"] == "unknown"
        assert "too short" in result.get("error", "")

    def test_empty_text(self):
        from loom.tools.enrich import research_detect_language

        result = research_detect_language("")
        assert result["language"] == "unknown"

    def test_langdetect_not_installed(self):
        with patch.dict("sys.modules", {"langdetect": None}):
            # Need to reimport to trigger the ImportError
            import importlib

            import loom.tools.enrich

            importlib.reload(loom.tools.enrich)
            result = loom.tools.enrich.research_detect_language("This is English text for testing.")
            assert "not installed" in result.get("error", "")


class TestWayback:
    def test_snapshot_found(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype", "digest"],
            ["20240101120000", "https://example.com", "200", "text/html", "abc123"],
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.enrich import research_wayback

            result = research_wayback("https://example.com")

        assert len(result["snapshots"]) == 1
        assert "archive_url" in result["snapshots"][0]
        assert "20240101120000" in result["snapshots"][0]["archive_url"]

    def test_no_snapshots(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            ["timestamp", "original", "statuscode", "mimetype", "digest"],
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.enrich import research_wayback

            result = research_wayback("https://dead-link.com")

        assert result["snapshots"] == []
        assert "no snapshots" in result.get("error", "")
