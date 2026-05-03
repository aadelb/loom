"""Tests for YouTube transcript provider."""

from __future__ import annotations

import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_module_cache():
    """Ensure clean import state for each test."""
    sys.modules.pop("loom.providers.youtube_transcripts", None)
    yield
    sys.modules.pop("loom.providers.youtube_transcripts", None)



pytestmark = pytest.mark.asyncio
class TestFetchYoutubeTranscript:
    async def test_basic_transcript(self):
        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0
        mock_subprocess_run.stdout = json.dumps(
            {
                "title": "Test Video",
                "duration": 120,
                "subtitles": {"en": [{"ext": "json3", "url": "https://example.com/sub.json3"}]},
            }
        )

        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {
            "events": [{"segs": [{"utf8": "Hello "}]}, {"segs": [{"utf8": "World"}]}]
        }
        mock_resp.raise_for_status = MagicMock()

        with (
            patch("subprocess.run", return_value=mock_subprocess_run),
            patch("httpx.get", return_value=mock_resp),
        ):
            from loom.providers.youtube_transcripts import fetch_youtube_transcript

            result = fetch_youtube_transcript("https://youtube.com/watch?v=123")

        assert "transcript" in result
        assert "url" in result
        assert "title" in result
        assert "duration" in result
        assert "error" not in result
        assert result["title"] == "Test Video"
        assert "Hello" in result["transcript"] and "World" in result["transcript"]
        assert result["tool"] == "yt-dlp"

    async def test_no_subtitles(self):
        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0
        mock_subprocess_run.stdout = json.dumps(
            {
                "title": "No Subs Video",
                "duration": 60,
                "description": "This is a description.",
            }
        )

        with patch("subprocess.run", return_value=mock_subprocess_run):
            from loom.providers.youtube_transcripts import fetch_youtube_transcript

            result = fetch_youtube_transcript("https://youtube.com/watch?v=123")

        assert result["transcript"] == "This is a description."
        assert result["note"] == "no subtitles available, using description"
        assert "error" not in result

    async def test_ytdlp_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("command not found")):
            from loom.providers.youtube_transcripts import fetch_youtube_transcript

            result = fetch_youtube_transcript("https://youtube.com/watch?v=123")

        assert result["transcript"] == ""
        assert "not installed" in result["error"]

    async def test_timeout(self):
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="yt_dlp", timeout=30)
        ):
            from loom.providers.youtube_transcripts import fetch_youtube_transcript

            result = fetch_youtube_transcript("https://youtube.com/watch?v=123")

        assert result["transcript"] == ""
        assert "timed out" in result["error"]
