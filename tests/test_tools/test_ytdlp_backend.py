"""Tests for yt-dlp backend tools (research_video_download, research_video_info, research_audio_extract)."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestResearchVideoDownload:
    """Tests for research_video_download() function."""

    @pytest.mark.asyncio
    async def test_missing_yt_dlp(self):
        """Test error when yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.backends.ytdlp_backend import research_video_download

            result = await research_video_download("https://www.youtube.com/watch?v=test")

            assert "error" in result
            assert "yt-dlp not installed" in result["error"]
            assert result["url"] == "https://www.youtube.com/watch?v=test"

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test error for invalid URL."""
        import sys
        with patch.dict(sys.modules, {"yt_dlp": MagicMock()}):
            from loom.tools.backends.ytdlp_backend import research_video_download

            result = await research_video_download("not a valid url")

            assert "error" in result
            assert result["url"] == "not a valid url"

    @pytest.mark.asyncio
    async def test_invalid_format_causes_error(self):
        """Test that invalid format eventually causes an error."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        
        # yt-dlp will fail with invalid format
        mock_ydl.extract_info.side_effect = Exception("Invalid format")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl
        
        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={"error": "yt-dlp error: Exception: Invalid format"}
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_download
            
            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
                format="@#$%",
            )
            
            assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_max_duration(self):
        """Test error for invalid max_duration."""
        import sys
        with patch.dict(sys.modules, {"yt_dlp": MagicMock()}):
            from loom.tools.backends.ytdlp_backend import research_video_download

            # Test too high
            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
                max_duration=700,
            )
            assert "error" in result
            assert "max_duration" in result["error"]

            # Test too low
            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
                max_duration=0,
            )
            assert "error" in result
            assert "max_duration" in result["error"]

    @pytest.mark.asyncio
    async def test_download_success(self):
        """Test successful video download."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        # Mock the info returned
        info = {
            "title": "Test Video",
            "duration": 300,
            "format": "best",
            "thumbnail": "https://example.com/thumb.jpg",
            "description": "Test description",
            "uploader": "Test Channel",
            "upload_date": "20240101",
            "view_count": 1000,
            "like_count": 50,
            "formats": [{"format_id": "22"}, {"format_id": "18"}],
        }

        mock_ydl.extract_info.return_value = info
        mock_ydl.prepare_filename.return_value = "/tmp/test_video.mp4"
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=100 * 1024 * 1024),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={
                    "title": "Test Video",
                    "duration": 300,
                    "format": "best",
                    "file_path": "/tmp/test_video.mp4",
                    "file_size": 100 * 1024 * 1024,
                    "thumbnail": "https://example.com/thumb.jpg",
                    "description": "Test description",
                    "uploader": "Test Channel",
                    "upload_date": "20240101",
                    "view_count": 1000,
                    "like_count": 50,
                }
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_download

            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
                format="best",
            )

            assert "error" not in result
            assert result["title"] == "Test Video"
            assert result["duration"] == 300
            assert result["uploader"] == "Test Channel"

    @pytest.mark.asyncio
    async def test_audio_only_download(self):
        """Test audio-only extraction."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        info = {
            "title": "Test Audio",
            "duration": 180,
            "format": "audio",
            "uploader": "Test Channel",
            "upload_date": "20240101",
        }

        mock_ydl.extract_info.return_value = info
        mock_ydl.prepare_filename.return_value = "/tmp/test_audio.m4a"
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=50 * 1024 * 1024),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={
                    "title": "Test Audio",
                    "duration": 180,
                    "format": "audio",
                    "file_path": "/tmp/test_audio.m4a",
                    "file_size": 50 * 1024 * 1024,
                    "thumbnail": None,
                    "description": None,
                    "uploader": "Test Channel",
                    "upload_date": "20240101",
                    "view_count": None,
                    "like_count": None,
                }
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_download

            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
                audio_only=True,
            )

            assert "error" not in result
            assert result["title"] == "Test Audio"

    @pytest.mark.asyncio
    async def test_video_exceeds_max_duration(self):
        """Test error when video exceeds max_duration."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        info = {"title": "Long Video", "duration": 700}
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={"error": "Video duration (700s) exceeds max (600s)"}
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_download

            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
                max_duration=600,
            )

            assert "error" in result
            assert "exceeds max" in result["error"]

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        """Test error when downloaded file exceeds size limit."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        info = {"title": "Large Video", "duration": 300}
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            # File size exceeds 500MB
            error_msg = "File too large: 600.0MB (max 500MB)"
            mock_loop.run_in_executor = AsyncMock(
                return_value={"error": error_msg}
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_download

            result = await research_video_download(
                "https://www.youtube.com/watch?v=test",
            )

            assert "error" in result
            assert "too large" in result["error"].lower()


class TestResearchVideoInfo:
    """Tests for research_video_info() function."""

    @pytest.mark.asyncio
    async def test_missing_yt_dlp(self):
        """Test error when yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.backends.ytdlp_backend import research_video_info

            result = await research_video_info("https://www.youtube.com/watch?v=test")

            assert "error" in result
            assert "yt-dlp not installed" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test error for invalid URL."""
        import sys
        with patch.dict(sys.modules, {"yt_dlp": MagicMock()}):
            from loom.tools.backends.ytdlp_backend import research_video_info

            result = await research_video_info("not a valid url")

            assert "error" in result

    @pytest.mark.asyncio
    async def test_info_extraction_success(self):
        """Test successful metadata extraction."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        info = {
            "title": "Test Video",
            "duration": 300,
            "description": "Test description",
            "uploader": "Test Channel",
            "upload_date": "20240101",
            "view_count": 1000,
            "like_count": 50,
            "formats": [{"format_id": "22"}, {"format_id": "18"}],
        }

        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={
                    "title": "Test Video",
                    "duration": 300,
                    "description": "Test description",
                    "uploader": "Test Channel",
                    "upload_date": "20240101",
                    "view_count": 1000,
                    "like_count": 50,
                    "formats_available": ["22", "18"],
                }
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_info

            result = await research_video_info("https://www.youtube.com/watch?v=test")

            assert "error" not in result
            assert result["title"] == "Test Video"
            assert result["duration"] == 300
            assert result["formats_available"] == ["22", "18"]

    @pytest.mark.asyncio
    async def test_info_extraction_failure(self):
        """Test metadata extraction failure."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={"error": "yt-dlp error: Exception: Network error"}
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_video_info

            result = await research_video_info("https://www.youtube.com/watch?v=test")

            assert "error" in result


class TestResearchAudioExtract:
    """Tests for research_audio_extract() function."""

    @pytest.mark.asyncio
    async def test_missing_yt_dlp(self):
        """Test error when yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.backends.ytdlp_backend import research_audio_extract

            result = await research_audio_extract("https://www.youtube.com/watch?v=test")

            assert "error" in result
            assert "yt-dlp not installed" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test error for invalid URL."""
        import sys
        with patch.dict(sys.modules, {"yt_dlp": MagicMock()}):
            from loom.tools.backends.ytdlp_backend import research_audio_extract

            result = await research_audio_extract("not a valid url")

            assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_format(self):
        """Test error for unsupported audio format."""
        import sys
        with patch.dict(sys.modules, {"yt_dlp": MagicMock()}):
            from loom.tools.backends.ytdlp_backend import research_audio_extract

            result = await research_audio_extract(
                "https://www.youtube.com/watch?v=test",
                format="aac",
            )

            assert "error" in result
            assert "Unsupported format" in result["error"]

    @pytest.mark.asyncio
    async def test_audio_extract_success_mp3(self):
        """Test successful audio extraction in MP3 format."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        info = {
            "title": "Test Audio",
            "duration": 180,
            "formats": [{"format_id": "251"}],
        }

        mock_ydl.extract_info.return_value = info
        mock_ydl.prepare_filename.return_value = "/tmp/test_audio.mp3"
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=30 * 1024 * 1024),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={
                    "title": "Test Audio",
                    "duration": 180,
                    "file_path": "/tmp/test_audio.mp3",
                    "file_size": 30 * 1024 * 1024,
                }
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_audio_extract

            result = await research_audio_extract(
                "https://www.youtube.com/watch?v=test",
                format="mp3",
            )

            assert "error" not in result
            assert result["title"] == "Test Audio"
            assert result["format"] == "mp3"
            assert result["file_path"] == "/tmp/test_audio.mp3"

    @pytest.mark.asyncio
    async def test_audio_extract_success_wav(self):
        """Test successful audio extraction in WAV format."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        info = {
            "title": "Test WAV",
            "duration": 120,
            "formats": [{"format_id": "251"}],
        }

        mock_ydl.extract_info.return_value = info
        mock_ydl.prepare_filename.return_value = "/tmp/test_audio.wav"
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=50 * 1024 * 1024),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={
                    "title": "Test WAV",
                    "duration": 120,
                    "file_path": "/tmp/test_audio.wav",
                    "file_size": 50 * 1024 * 1024,
                }
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_audio_extract

            result = await research_audio_extract(
                "https://www.youtube.com/watch?v=test",
                format="wav",
            )

            assert "error" not in result
            assert result["format"] == "wav"

    @pytest.mark.asyncio
    async def test_audio_extract_failure(self):
        """Test audio extraction failure."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        mock_ydl.extract_info.side_effect = Exception("Download failed")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with (
            patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}),
            patch("loom.tools.ytdlp_backend.asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                return_value={"error": "yt-dlp error: Exception: Download failed"}
            )
            mock_get_loop.return_value = mock_loop

            from loom.tools.backends.ytdlp_backend import research_audio_extract

            result = await research_audio_extract("https://www.youtube.com/watch?v=test")

            assert "error" in result


class TestDownloadMedia:
    """Tests for _download_media() blocking function."""

    def test_missing_yt_dlp_in_executor(self):
        """Test error when yt-dlp is not installed in executor."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.backends.ytdlp_backend import _download_media

            result = _download_media(
                "https://www.youtube.com/watch?v=test",
                "best",
                False,
                600,
            )

            assert "error" in result
            assert "yt-dlp not installed" in result["error"]

    def test_download_failure(self):
        """Test download failure handling."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}):
            from loom.tools.backends.ytdlp_backend import _download_media

            result = _download_media(
                "https://www.youtube.com/watch?v=test",
                "best",
                False,
                600,
            )

            assert "error" in result
            assert "yt-dlp error" in result["error"]


class TestExtractInfo:
    """Tests for _extract_info() blocking function."""

    def test_missing_yt_dlp_in_executor(self):
        """Test error when yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.backends.ytdlp_backend import _extract_info

            result = _extract_info("https://www.youtube.com/watch?v=test")

            assert "error" in result
            assert "yt-dlp not installed" in result["error"]

    def test_info_extraction_failure(self):
        """Test info extraction failure."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        mock_ydl.extract_info.side_effect = Exception("Video unavailable")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}):
            from loom.tools.backends.ytdlp_backend import _extract_info

            result = _extract_info("https://www.youtube.com/watch?v=test")

            assert "error" in result
            assert "yt-dlp error" in result["error"]


class TestExtractAudio:
    """Tests for _extract_audio() blocking function."""

    def test_missing_yt_dlp_in_executor(self):
        """Test error when yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.backends.ytdlp_backend import _extract_audio

            result = _extract_audio(
                "https://www.youtube.com/watch?v=test",
                "mp3",
            )

            assert "error" in result
            assert "yt-dlp not installed" in result["error"]

    def test_audio_extraction_failure(self):
        """Test audio extraction failure."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()

        mock_ydl.extract_info.side_effect = Exception("Extraction failed")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}):
            from loom.tools.backends.ytdlp_backend import _extract_audio

            result = _extract_audio(
                "https://www.youtube.com/watch?v=test",
                "mp3",
            )

            assert "error" in result
            assert "yt-dlp error" in result["error"]
