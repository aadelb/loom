"""Tests for research_transcribe tool."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


class TestResearchTranscribe:
    """Tests for research_transcribe() function."""

    @pytest.mark.asyncio
    async def test_missing_whisper(self):
        """Test error when whisper is not installed."""
        with patch.dict("sys.modules", {"whisper": None}):
            from loom.tools.transcribe import research_transcribe

            result = await research_transcribe("https://example.com/audio.mp3")

            assert "error" in result
            assert "whisper not installed" in result["error"]
            assert result["url"] == "https://example.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_invalid_model_size(self):
        """Test error for invalid model_size."""
        import sys
        with patch.dict(sys.modules, {"whisper": MagicMock()}):
            from loom.tools.transcribe import research_transcribe

            result = await research_transcribe(
                "https://example.com/audio.mp3", model_size="invalid"
            )

            assert "error" in result
            assert "Invalid model_size" in result["error"]
            assert "invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test error for invalid URL."""
        import sys
        with patch.dict(sys.modules, {"whisper": MagicMock()}):
            from loom.tools.transcribe import research_transcribe

            result = await research_transcribe("not a valid url")

            assert "error" in result
            assert result["url"] == "not a valid url"

    @pytest.mark.asyncio
    async def test_download_audio_failure(self):
        """Test error when audio download fails."""
        import sys
        with (
            patch.dict(sys.modules, {"whisper": MagicMock()}),
            patch("loom.tools.transcribe._download_audio", new_callable=AsyncMock) as mock_download,
        ):
            mock_download.return_value = None

            from loom.tools.transcribe import research_transcribe

            result = await research_transcribe("https://example.com/audio.mp3")

            assert "error" in result
            assert "Failed to download audio" in result["error"]

    @pytest.mark.asyncio
    async def test_file_size_exceeds_limit(self):
        """Test error when audio file exceeds size limit."""
        import sys
        with (
            patch.dict(sys.modules, {"whisper": MagicMock()}),
            patch("loom.tools.transcribe._download_audio", new_callable=AsyncMock) as mock_download,
            patch("os.path.getsize") as mock_getsize,
        ):
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_path = tmp.name

            try:
                mock_download.return_value = temp_path
                # Set file size to 600MB (exceeds 500MB limit)
                mock_getsize.return_value = 600 * 1024 * 1024

                from loom.tools.transcribe import research_transcribe

                result = await research_transcribe("https://example.com/audio.mp3")

                assert "error" in result
                assert "too large" in result["error"].lower()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_transcription_success(self):
        """Test successful transcription."""
        import sys
        with (
            patch.dict(sys.modules, {"whisper": MagicMock()}),
            patch(
                "loom.tools.transcribe._download_audio", new_callable=AsyncMock
            ) as mock_download,
            patch("os.path.getsize") as mock_getsize,
            patch(
                "loom.tools.transcribe._transcribe_audio", new_callable=AsyncMock
            ) as mock_transcribe,
            patch("os.path.exists") as mock_exists,
            patch("os.unlink") as mock_unlink,
        ):
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_path = tmp.name

            try:
                mock_download.return_value = temp_path
                mock_getsize.return_value = 10 * 1024 * 1024
                mock_transcribe.return_value = {
                    "transcript": "Hello world",
                    "language": "en",
                    "duration_seconds": 5,
                }
                mock_exists.return_value = True

                # Need to patch run_in_executor to return the mocked result
                with patch(
                    "loom.tools.transcribe.asyncio.get_event_loop"
                ) as mock_get_loop:
                    mock_loop = AsyncMock()
                    mock_loop.run_in_executor = AsyncMock(
                        return_value={
                            "transcript": "Hello world",
                            "language": "en",
                            "duration_seconds": 5,
                        }
                    )
                    mock_get_loop.return_value = mock_loop

                    from loom.tools.transcribe import research_transcribe

                    result = await research_transcribe(
                        "https://example.com/audio.mp3", model_size="base"
                    )

                assert "error" not in result
                assert result["transcript"] == "Hello world"
                assert result["language"] == "en"
                assert result["duration_seconds"] == 5
                assert result["model_size"] == "base"
            finally:
                # Clean up temp file only if it still exists (mocking may have deleted)
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except (OSError, FileNotFoundError):
                    pass

    @pytest.mark.asyncio
    async def test_transcription_with_language(self):
        """Test transcription with specified language."""
        import sys
        with (
            patch.dict(sys.modules, {"whisper": MagicMock()}),
            patch(
                "loom.tools.transcribe._download_audio", new_callable=AsyncMock
            ) as mock_download,
            patch("os.path.getsize") as mock_getsize,
            patch("os.path.exists") as mock_exists,
        ):
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_path = tmp.name

            try:
                mock_download.return_value = temp_path
                mock_getsize.return_value = 5 * 1024 * 1024
                mock_exists.return_value = True

                with patch(
                    "loom.tools.transcribe.asyncio.get_event_loop"
                ) as mock_get_loop:
                    mock_loop = AsyncMock()
                    mock_loop.run_in_executor = AsyncMock(
                        return_value={
                            "transcript": "Merhaba dünya",
                            "language": "tr",
                            "duration_seconds": 3,
                        }
                    )
                    mock_get_loop.return_value = mock_loop

                    from loom.tools.transcribe import research_transcribe

                    result = await research_transcribe(
                        "https://example.com/audio.mp3",
                        language="tr",
                        model_size="small",
                    )

                assert result["language"] == "tr"
                assert result["model_size"] == "small"
            finally:
                # Clean up temp file only if it still exists (mocking may have deleted)
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except (OSError, FileNotFoundError):
                    pass

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self):
        """Test temp file is cleaned up on exception."""
        import sys
        with (
            patch.dict(sys.modules, {"whisper": MagicMock()}),
            patch(
                "loom.tools.transcribe._download_audio", new_callable=AsyncMock
            ) as mock_download,
            patch("os.path.getsize") as mock_getsize,
            patch("os.path.exists") as mock_exists,
            patch("os.unlink") as mock_unlink,
        ):
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_path = tmp.name

            mock_download.return_value = temp_path
            mock_getsize.return_value = 5 * 1024 * 1024
            mock_exists.return_value = True

            with patch(
                "loom.tools.transcribe.asyncio.get_event_loop"
            ) as mock_get_loop:
                mock_loop = AsyncMock()
                mock_loop.run_in_executor = AsyncMock(
                    side_effect=Exception("Transcription error")
                )
                mock_get_loop.return_value = mock_loop

                from loom.tools.transcribe import research_transcribe

                result = await research_transcribe("https://example.com/audio.mp3")

            assert "error" in result
            # Verify cleanup was attempted
            assert mock_unlink.called or not mock_exists.return_value


class TestDownloadAudio:
    """Tests for _download_audio() function."""

    @pytest.mark.asyncio
    async def test_youtube_url_detection(self):
        """Test YouTube URL detection."""
        from loom.tools.transcribe import _download_audio

        with patch("loom.tools.transcribe._download_youtube_audio", new_callable=AsyncMock) as mock_yt:
            mock_yt.return_value = "/tmp/audio.wav"

            result = await _download_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            assert mock_yt.called

    @pytest.mark.asyncio
    async def test_youtu_be_url_detection(self):
        """Test youtu.be short URL detection."""
        from loom.tools.transcribe import _download_audio

        with patch("loom.tools.transcribe._download_youtube_audio", new_callable=AsyncMock) as mock_yt:
            mock_yt.return_value = "/tmp/audio.wav"

            result = await _download_audio("https://youtu.be/dQw4w9WgXcQ")
            assert mock_yt.called

    @pytest.mark.asyncio
    async def test_direct_audio_url(self):
        """Test direct audio URL handling."""
        from loom.tools.transcribe import _download_audio

        with patch("loom.tools.transcribe._download_file_audio", new_callable=AsyncMock) as mock_file:
            mock_file.return_value = "/tmp/audio.wav"

            result = await _download_audio("https://example.com/audio.mp3")
            assert mock_file.called


class TestDownloadYoutubeAudio:
    """Tests for _download_youtube_audio() function."""

    @pytest.mark.asyncio
    async def test_yt_dlp_not_installed(self):
        """Test handling when yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            from loom.tools.transcribe import _download_youtube_audio

            result = await _download_youtube_audio("https://www.youtube.com/watch?v=test")
            assert result is None

    @pytest.mark.asyncio
    async def test_yt_dlp_download_success(self):
        """Test successful yt-dlp download."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"id": "test"}
        mock_ydl.prepare_filename.return_value = "/tmp/audio.wav"
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}):
            from loom.tools.transcribe import _download_youtube_audio

            result = await _download_youtube_audio("https://www.youtube.com/watch?v=test")
            assert result == "/tmp/audio.wav"

    @pytest.mark.asyncio
    async def test_yt_dlp_download_failure(self):
        """Test yt-dlp download failure."""
        import sys
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Download failed")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with patch.dict(sys.modules, {"yt_dlp": mock_yt_dlp}):
            from loom.tools.transcribe import _download_youtube_audio

            result = await _download_youtube_audio("https://www.youtube.com/watch?v=test")
            assert result is None


class TestDownloadFileAudio:
    """Tests for _download_file_audio() function."""

    @pytest.mark.asyncio
    async def test_successful_download(self):
        """Test successful file download."""
        from loom.tools.transcribe import _download_file_audio

        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "audio/mpeg"
            mock_response.content = b"audio data"
            mock_response.raise_for_status = MagicMock()

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = await _download_file_audio("https://example.com/audio.mp3")
            assert result is not None
            assert result.endswith(".mp3")

            # Cleanup
            if result and os.path.exists(result):
                os.unlink(result)

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        """Test handling of files exceeding size limit."""
        from loom.tools.transcribe import _download_file_audio

        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "audio/mpeg"
            # 600MB of content
            mock_response.content = b"x" * (600 * 1024 * 1024)
            mock_response.raise_for_status = MagicMock()

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = await _download_file_audio("https://example.com/audio.mp3")
            assert result is None

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test handling of HTTP errors."""
        from loom.tools.transcribe import _download_file_audio

        with patch("httpx.Client") as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = Exception("HTTP 404")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = await _download_file_audio("https://example.com/audio.mp3")
            assert result is None


class TestTranscribeAudio:
    """Tests for _transcribe_audio() function."""

    def test_invalid_audio_path(self):
        """Test handling of invalid audio path."""
        import sys
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = FileNotFoundError("File not found")
        mock_whisper.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper}):
            from loom.tools.transcribe import _transcribe_audio

            result = _transcribe_audio("/nonexistent/audio.mp3", "base", None)
            assert "error" in result

    def test_audio_too_long(self):
        """Test handling of audio exceeding max duration."""
        import sys
        from loom.tools.transcribe import MAX_AUDIO_DURATION_SECS

        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test", "language": "en"}
        mock_whisper.load_model.return_value = mock_model

        mock_librosa = MagicMock()
        # Set duration to exceed limit (2 hours)
        mock_librosa.get_duration.return_value = MAX_AUDIO_DURATION_SECS + 3600

        with (
            patch.dict(sys.modules, {"whisper": mock_whisper, "librosa": mock_librosa}),
        ):
            from loom.tools.transcribe import _transcribe_audio

            result = _transcribe_audio("/tmp/audio.wav", "base", None)
            assert "error" in result
            assert "too long" in result["error"].lower()


class TestGetFileExtension:
    """Tests for _get_file_extension() function."""

    def test_mp3_extension(self):
        """Test MP3 content type."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("audio/mpeg") == ".mp3"
        assert _get_file_extension("audio/mp3") == ".mp3"

    def test_wav_extension(self):
        """Test WAV content type."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("audio/wav") == ".wav"

    def test_flac_extension(self):
        """Test FLAC content type."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("audio/flac") == ".flac"

    def test_mp4_extension(self):
        """Test MP4 content type."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("video/mp4") == ".mp4"

    def test_webm_extension(self):
        """Test WebM content type."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("video/webm") == ".webm"

    def test_unknown_extension(self):
        """Test unknown content type."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("application/octet-stream") == ".audio"
        assert _get_file_extension("unknown/type") == ".audio"

    def test_case_insensitive(self):
        """Test case-insensitive content type handling."""
        from loom.tools.transcribe import _get_file_extension

        assert _get_file_extension("AUDIO/MPEG") == ".mp3"
        assert _get_file_extension("Audio/Mp3") == ".mp3"
