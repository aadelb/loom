"""research_transcribe — Audio/video transcription using OpenAI Whisper."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.transcribe")

# Max audio duration in seconds (30 minutes)
MAX_AUDIO_DURATION_SECS = 1800


async def research_transcribe(
    url: str,
    language: str | None = None,
    model_size: str = "base",
) -> dict[str, Any]:
    """Transcribe audio/video from YouTube or direct URL using OpenAI Whisper.

    Supports YouTube videos and direct audio/video file URLs. Falls back
    to smaller model if GPU memory insufficient. Returns transcript text
    and detected language.

    Args:
        url: YouTube video URL or direct audio/video file URL
        language: optional ISO 639-1 language code (e.g. 'en', 'ar', 'es')
        model_size: whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            - tiny: fastest, lowest quality (39M params)
            - base: balanced (74M params)
            - small: better quality (244M params)
            - medium: high quality (769M params)
            - large: best quality (1.5B params)

    Returns:
        Dict with keys:
        - transcript: transcribed text
        - language: detected language (ISO 639-1)
        - duration_seconds: audio duration
        - url: original input URL
        - model_size: model used
        - error: error message if transcription failed
    """
    try:
        import whisper
    except ImportError:
        return {
            "error": "whisper not installed. Install with: pip install openai-whisper",
            "url": url,
        }

    # Validate model size
    valid_sizes = ("tiny", "base", "small", "medium", "large")
    if model_size not in valid_sizes:
        return {
            "error": f"Invalid model_size: {model_size}. Must be one of {valid_sizes}",
            "url": url,
        }

    # Validate URL
    from loom.validators import validate_url

    try:
        url = validate_url(url)
    except ValueError as e:
        return {"error": str(e), "url": url}

    logger.info(
        "transcribe_start url=%s model=%s language=%s",
        url[:80],
        model_size,
        language,
    )

    # Download audio to temp file
    audio_path = None
    try:
        audio_path = await _download_audio(url)
        if not audio_path:
            return {"error": "Failed to download audio", "url": url}

        # Check file size (max 500MB for safety; 30 min at 256kbps ≈ 450MB)
        file_size = os.path.getsize(audio_path)
        max_size_mb = 500
        if file_size > max_size_mb * 1024 * 1024:
            return {
                "error": f"Audio file too large: {file_size / (1024**2):.1f}MB (max {max_size_mb}MB)",
                "url": url,
            }

        # Run whisper in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _transcribe_audio,
            audio_path,
            model_size,
            language,
        )

        if isinstance(result, dict) and "error" in result:
            return {**result, "url": url}

        return {
            "transcript": result.get("transcript"),
            "language": result.get("language", "unknown"),
            "duration_seconds": result.get("duration_seconds", 0),
            "url": url,
            "model_size": model_size,
        }

    except TimeoutError:
        return {"error": "Transcription timed out (max 30 min audio)", "url": url}
    except Exception as e:
        logger.error("transcribe_failed url=%s error=%s", url[:80], type(e).__name__)
        return {"error": f"Transcription failed: {type(e).__name__}", "url": url}
    finally:
        # Clean up temp file
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except OSError:
                pass


async def _download_audio(url: str) -> str | None:
    """Download audio to temp file.

    For YouTube URLs, uses yt-dlp. For direct URLs, uses httpx.

    Args:
        url: YouTube or direct audio/video URL

    Returns:
        Path to temp file with audio, or None on failure.
    """
    # YouTube URL detection
    is_youtube = any(
        domain in url for domain in ("youtube.com", "youtu.be", "youtube.co")
    )

    if is_youtube:
        return await _download_youtube_audio(url)
    else:
        return await _download_file_audio(url)


async def _download_youtube_audio(url: str) -> str | None:
    """Download audio from YouTube using yt-dlp.

    Args:
        url: YouTube video URL

    Returns:
        Path to temp file, or None on failure.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt_dlp not installed, cannot transcribe YouTube URLs")
        return None

    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, "loom_audio_%(id)s.%(ext)s")

    try:
        loop = asyncio.get_event_loop()

        def _yt_dlp_download() -> str | None:
            """Run yt-dlp in sync context."""
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": temp_file,
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Return actual output file path
                return ydl.prepare_filename(info).replace(".webm", ".wav").replace(
                    ".m4a", ".wav"
                )

        result = await loop.run_in_executor(None, _yt_dlp_download)
        return result

    except Exception as e:
        logger.error(
            "youtube_download_failed url=%s error=%s",
            url[:80],
            type(e).__name__,
        )
        return None


async def _download_file_audio(url: str) -> str | None:
    """Download audio from direct URL using httpx.

    Args:
        url: Direct audio/video file URL

    Returns:
        Path to temp file, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if not any(
                t in content_type
                for t in ("audio/", "video/", "application/octet-stream")
            ):
                logger.warning(
                    "unexpected_content_type url=%s type=%s", url[:80], content_type
                )

            # Check file size (max 500MB)
            file_size = len(response.content)
            if file_size > 500 * 1024 * 1024:
                return None

            # Write to temp file
            suffix = _get_file_extension(content_type)
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, dir=tempfile.gettempdir()
            ) as f:
                f.write(response.content)
                return f.name

    except Exception as e:
        logger.error(
            "file_download_failed url=%s error=%s",
            url[:80],
            type(e).__name__,
        )
        return None


def _transcribe_audio(
    audio_path: str, model_size: str, language: str | None
) -> dict[str, Any]:
    """Transcribe audio file using Whisper (blocking).

    Args:
        audio_path: path to audio file
        model_size: whisper model size
        language: optional language code

    Returns:
        Dict with transcript, language, and duration.
    """
    try:
        import whisper

        # Load model
        model = whisper.load_model(model_size)

        # Transcribe
        result = model.transcribe(audio_path, language=language)

        # Extract duration from audio file metadata
        duration_secs = 0
        try:
            import librosa

            duration_secs = int(librosa.get_duration(filename=audio_path))
        except (ImportError, Exception):
            # librosa not installed or failed, skip duration
            pass

        # Check max duration
        if duration_secs > MAX_AUDIO_DURATION_SECS:
            return {
                "error": f"Audio too long: {duration_secs}s (max {MAX_AUDIO_DURATION_SECS}s)"
            }

        return {
            "transcript": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "duration_seconds": duration_secs,
        }

    except Exception as e:
        logger.error("whisper_transcribe_failed error=%s", type(e).__name__)
        return {"error": f"Whisper transcription failed: {type(e).__name__}"}


def _get_file_extension(content_type: str) -> str:
    """Map content type to file extension.

    Args:
        content_type: HTTP content-type header value

    Returns:
        File extension with leading dot.
    """
    content_type = content_type.lower()

    # Audio types
    if "mp3" in content_type or "mpeg" in content_type:
        return ".mp3"
    elif "wav" in content_type:
        return ".wav"
    elif "flac" in content_type:
        return ".flac"
    elif "aac" in content_type or "m4a" in content_type:
        return ".m4a"
    elif "ogg" in content_type:
        return ".ogg"
    # Video types
    elif "mp4" in content_type:
        return ".mp4"
    elif "webm" in content_type:
        return ".webm"
    elif "mpeg" in content_type or "mpg" in content_type:
        return ".mpg"
    elif "quicktime" in content_type or "mov" in content_type:
        return ".mov"
    else:
        return ".audio"
