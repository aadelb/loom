"""research_video_download, research_video_info, research_audio_extract — yt-dlp media backend.

Uses yt-dlp (159K stars) for downloading/extracting metadata from YouTube, TikTok,
Twitter, Instagram, and 1000+ other platforms. Supports video, audio, and metadata
extraction with format selection and duration limits.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any, Literal

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.ytdlp_backend")

# Max duration in seconds (10 minutes)
MAX_DURATION_SECS = 600

# Max video file size (500MB for safety)
MAX_FILE_SIZE = 500 * 1024 * 1024

# Supported audio formats for extraction
AUDIO_FORMATS = ("mp3", "wav", "m4a", "opus", "vorbis", "flac", "alac")

@handle_tool_errors("research_video_download")

async def research_video_download(
    url: str,
    format: str = "best",
    audio_only: bool = False,
    max_duration: int = 600,
) -> dict[str, Any]:
    """Download video or audio from YouTube, TikTok, Twitter, Instagram, etc.

    Uses yt-dlp to download media from 1000+ supported platforms. Supports
    video download with format selection, audio extraction, and duration limits.

    Args:
        url: Media URL (YouTube, TikTok, Twitter, Instagram, etc.)
        format: Video format ('best', 'worst', or format spec like '22+251').
            - 'best': best available quality (h.264 video + AAC audio)
            - 'worst': lowest quality (fast download)
            - '22': specific format ID from yt-dlp --list-formats
        audio_only: if True, extract audio only (no video)
        max_duration: skip videos longer than this (seconds, max 600=10 min)

    Returns:
        Dict with keys:
        - url: original input URL
        - title: media title
        - duration: duration in seconds
        - format: format used/downloaded
        - file_path: local path to downloaded file
        - file_size: size in bytes
        - thumbnail: thumbnail URL
        - description: media description
        - uploader: uploader/creator name
        - upload_date: ISO 8601 date string
        - view_count: view count (if available)
        - like_count: like count (if available)
        - error: error message if download failed
    """
    try:
        import yt_dlp
    except ImportError:
        return {
            "error": "yt-dlp not installed. Install with: pip install yt-dlp",
            "url": url,
        }

    # Validate URL
    from loom.validators import validate_url

    try:
        url = validate_url(url)
    except ValueError as e:
        return {"error": str(e), "url": url}

    # Validate max_duration
    if max_duration < 1 or max_duration > MAX_DURATION_SECS:
        return {
            "error": f"max_duration must be 1-{MAX_DURATION_SECS} seconds",
            "url": url,
        }

    # Normalize audio_only
    audio_only = bool(audio_only)

    # Validate format parameter
    if format not in ("best", "worst") and not re.match(r"^[a-zA-Z0-9+\[\]/\-_.]+$", format):
        return {
            "error": f"Invalid format: {format}. Use 'best', 'worst', or yt-dlp format spec (e.g., '22+251')",
            "url": url,
        }

    logger.info(
        "video_download_start url=%s format=%s audio_only=%s max_duration=%d",
        url[:80],
        format,
        audio_only,
        max_duration,
    )

    try:
        # Run yt-dlp in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _download_media,
            url,
            format,
            audio_only,
            max_duration,
        )

        if isinstance(result, dict) and "error" in result:
            return {**result, "url": url}

        return {
            "url": url,
            "title": result.get("title"),
            "duration": result.get("duration"),
            "format": result.get("format"),
            "file_path": result.get("file_path"),
            "file_size": result.get("file_size"),
            "thumbnail": result.get("thumbnail"),
            "description": result.get("description"),
            "uploader": result.get("uploader"),
            "upload_date": result.get("upload_date"),
            "view_count": result.get("view_count"),
            "like_count": result.get("like_count"),
        }

    except Exception as e:
        logger.error("video_download_failed url=%s error=%s", url[:80], type(e).__name__)
        return {
            "error": f"Download failed: {type(e).__name__}",
            "url": url,
        }

@handle_tool_errors("research_video_info")

async def research_video_info(url: str) -> dict[str, Any]:
    """Extract metadata from video URL without downloading.

    Queries video/media metadata from supported platforms using yt-dlp's
    extract_info API without actually downloading the file.

    Args:
        url: Media URL (YouTube, TikTok, Twitter, Instagram, etc.)

    Returns:
        Dict with keys:
        - url: original input URL
        - title: media title
        - duration: duration in seconds
        - description: media description
        - uploader: uploader/creator name
        - upload_date: ISO 8601 date string
        - view_count: view count (if available)
        - like_count: like count (if available)
        - formats_available: list of available format IDs
        - error: error message if extraction failed
    """
    try:
        import yt_dlp
    except ImportError:
        return {
            "error": "yt-dlp not installed. Install with: pip install yt-dlp",
            "url": url,
        }

    # Validate URL
    from loom.validators import validate_url

    try:
        url = validate_url(url)
    except ValueError as e:
        return {"error": str(e), "url": url}

    logger.info("video_info_start url=%s", url[:80])

    try:
        # Run yt-dlp in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _extract_info,
            url,
        )

        if isinstance(result, dict) and "error" in result:
            return {**result, "url": url}

        return {
            "url": url,
            "title": result.get("title"),
            "duration": result.get("duration"),
            "description": result.get("description"),
            "uploader": result.get("uploader"),
            "upload_date": result.get("upload_date"),
            "view_count": result.get("view_count"),
            "like_count": result.get("like_count"),
            "formats_available": result.get("formats_available", []),
        }

    except Exception as e:
        logger.error("video_info_failed url=%s error=%s", url[:80], type(e).__name__)
        return {
            "error": f"Metadata extraction failed: {type(e).__name__}",
            "url": url,
        }

@handle_tool_errors("research_audio_extract")

async def research_audio_extract(
    url: str,
    format: str = "mp3",
) -> dict[str, Any]:
    """Extract audio from video URL.

    Downloads only the audio track from a video URL. Supports format
    conversion (mp3, wav, m4a, opus, vorbis, flac, alac).

    Args:
        url: Video URL (YouTube, TikTok, Twitter, Instagram, etc.)
        format: output audio format ('mp3', 'wav', 'm4a', 'opus', 'vorbis',
                'flac', 'alac'). Defaults to 'mp3'.

    Returns:
        Dict with keys:
        - url: original input URL
        - title: media title
        - duration: duration in seconds
        - format: audio format extracted
        - file_path: local path to audio file
        - file_size: size in bytes
        - error: error message if extraction failed
    """
    try:
        import yt_dlp
    except ImportError:
        return {
            "error": "yt-dlp not installed. Install with: pip install yt-dlp",
            "url": url,
        }

    # Validate URL
    from loom.validators import validate_url

    try:
        url = validate_url(url)
    except ValueError as e:
        return {"error": str(e), "url": url}

    # Validate format
    format = format.lower().strip()
    if format not in AUDIO_FORMATS:
        return {
            "error": f"Unsupported format: {format}. Supported: {', '.join(AUDIO_FORMATS)}",
            "url": url,
        }

    logger.info("audio_extract_start url=%s format=%s", url[:80], format)

    try:
        # Run yt-dlp in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _extract_audio,
            url,
            format,
        )

        if isinstance(result, dict) and "error" in result:
            return {**result, "url": url}

        return {
            "url": url,
            "title": result.get("title"),
            "duration": result.get("duration"),
            "format": format,
            "file_path": result.get("file_path"),
            "file_size": result.get("file_size"),
        }

    except Exception as e:
        logger.error("audio_extract_failed url=%s error=%s", url[:80], type(e).__name__)
        return {
            "error": f"Audio extraction failed: {type(e).__name__}",
            "url": url,
        }


def _download_media(
    url: str,
    format: str,
    audio_only: bool,
    max_duration: int,
) -> dict[str, Any]:
    """Download media using yt-dlp (blocking).

    Args:
        url: Media URL
        format: Format specifier
        audio_only: Extract audio only
        max_duration: Skip if duration exceeds this

    Returns:
        Dict with download result or error.
    """
    try:
        import yt_dlp
    except ImportError:
        return {"error": "yt-dlp not installed"}

    # Prepare output template
    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    # Build ydl options
    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    # Set format based on audio_only
    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "libmp3lame",
                "preferredquality": "192",
            }
        ]
    else:
        # Map format parameter to yt-dlp format string
        if format == "best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        elif format == "worst":
            ydl_opts["format"] = "worstvideo+worstaudio/worst"
        else:
            # Treat as format ID string (e.g., "22+251")
            ydl_opts["format"] = format

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to check duration
            logger.info("ytdlp_extracting_info url=%s", url[:80])
            info = ydl.extract_info(url, download=False)

            if not info:
                return {"error": "Failed to extract video information"}

            # Check duration
            duration = info.get("duration", 0)
            if duration and duration > max_duration:
                return {
                    "error": f"Video duration ({duration}s) exceeds max ({max_duration}s)",
                }

            # Download the media
            logger.info("ytdlp_downloading url=%s duration=%d", url[:80], duration or 0)
            info = ydl.extract_info(url, download=True)

            if not info:
                return {"error": "Download failed"}

            # Get the output file path
            file_path = ydl.prepare_filename(info)

            if not os.path.exists(file_path):
                return {"error": f"Downloaded file not found: {file_path}"}

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
                return {
                    "error": f"File too large: {file_size / (1024**2):.1f}MB (max {MAX_FILE_SIZE / (1024**2):.0f}MB)",
                }

            # Build response
            return {
                "title": info.get("title"),
                "duration": duration,
                "format": info.get("format"),
                "file_path": file_path,
                "file_size": file_size,
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
            }

    except Exception as e:
        logger.error("ytdlp_download_error url=%s error=%s", url[:80], type(e).__name__)
        return {"error": f"yt-dlp error: {type(e).__name__}: {str(e)[:100]}"}


def _extract_info(url: str) -> dict[str, Any]:
    """Extract metadata without downloading (blocking).

    Args:
        url: Media URL

    Returns:
        Dict with metadata or error.
    """
    try:
        import yt_dlp
    except ImportError:
        return {"error": "yt-dlp not installed"}

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("ytdlp_extracting_metadata url=%s", url[:80])
            info = ydl.extract_info(url, download=False)

            if not info:
                return {"error": "Failed to extract metadata"}

            # Get available format IDs
            formats_available = []
            if "formats" in info:
                formats_available = [fmt.get("format_id") for fmt in info["formats"]]

            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "description": info.get("description"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "formats_available": formats_available,
            }

    except Exception as e:
        logger.error("ytdlp_metadata_error url=%s error=%s", url[:80], type(e).__name__)
        return {"error": f"yt-dlp error: {type(e).__name__}: {str(e)[:100]}"}


def _extract_audio(url: str, audio_format: str) -> dict[str, Any]:
    """Extract audio from video (blocking).

    Args:
        url: Video URL
        audio_format: Output format (mp3, wav, etc.)

    Returns:
        Dict with audio file path or error.
    """
    try:
        import yt_dlp
    except ImportError:
        return {"error": "yt-dlp not installed"}

    # Map audio format to codec
    codec_map = {
        "mp3": ("libmp3lame", "192"),
        "wav": ("pcm_s16le", "192"),
        "m4a": ("aac", "192"),
        "opus": ("libopus", "128"),
        "vorbis": ("libvorbis", "128"),
        "flac": ("flac", "192"),
        "alac": ("alac", "192"),
    }

    codec, quality = codec_map.get(audio_format, ("libmp3lame", "192"))

    # Prepare output template
    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": quality,
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first
            logger.info("ytdlp_extracting_audio url=%s format=%s", url[:80], audio_format)
            info = ydl.extract_info(url, download=False)

            if not info:
                return {"error": "Failed to extract audio information"}

            duration = info.get("duration", 0)

            # Download and convert
            logger.info("ytdlp_downloading_audio url=%s", url[:80])
            info = ydl.extract_info(url, download=True)

            if not info:
                return {"error": "Download failed"}

            # Get output file path
            file_path = ydl.prepare_filename(info)

            # FFmpeg may change the extension
            base_path = os.path.splitext(file_path)[0]
            possible_paths = [
                base_path + f".{audio_format}",
                file_path,
            ]

            actual_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    actual_path = path
                    break

            if not actual_path:
                return {"error": f"Output audio file not found"}

            file_size = os.path.getsize(actual_path)

            return {
                "title": info.get("title"),
                "duration": duration,
                "file_path": actual_path,
                "file_size": file_size,
            }

    except Exception as e:
        logger.error("ytdlp_audio_error url=%s error=%s", url[:80], type(e).__name__)
        return {"error": f"yt-dlp error: {type(e).__name__}: {str(e)[:100]}"}
