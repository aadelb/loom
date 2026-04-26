"""YouTube transcript extraction (free, no API key, uses yt-dlp)."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("loom.providers.youtube_transcripts")


def fetch_youtube_transcript(
    url: str,
    language: str = "en",
    **kwargs: Any,
) -> dict[str, Any]:
    """Extract auto-generated subtitles from a YouTube video (free).

    Uses yt-dlp to download subtitle tracks without downloading the video.
    Falls back to auto-generated captions if manual subs not available.

    Args:
        url: YouTube video URL
        language: subtitle language code (default "en")

    Returns:
        Dict with ``transcript`` (text), ``title``, ``duration``, ``url``.
    """
    # Validate URL to prevent subprocess injection (CRITICAL #1)
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"url": url, "transcript": "", "error": "invalid URL scheme"}
        if not parsed.netloc:
            return {"url": url, "transcript": "", "error": "invalid URL"}
    except Exception:
        return {"url": url, "transcript": "", "error": "invalid URL format"}

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "--skip-download",
                "--write-auto-sub",
                "--sub-lang",
                language,
                "--sub-format",
                "json3",
                "--dump-json",
                "--no-warnings",
                "--quiet",
                "--",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"url": url, "transcript": "", "error": f"yt-dlp failed: {result.stderr[:200]}"}

        metadata = json.loads(result.stdout)
        title = metadata.get("title", "")
        duration = metadata.get("duration")

        subs = metadata.get("automatic_captions", {}).get(language) or metadata.get(
            "subtitles", {}
        ).get(language)
        if not subs:
            return {
                "url": url,
                "title": title,
                "transcript": metadata.get("description", "")[:2000],
                "duration": duration,
                "note": "no subtitles available, using description",
            }

        sub_url = None
        for sub in subs:
            if sub.get("ext") in ("json3", "vtt", "srv3"):
                sub_url = sub.get("url")
                break
        if not sub_url and subs:
            sub_url = subs[0].get("url")

        if not sub_url:
            return {
                "url": url,
                "title": title,
                "transcript": "",
                "duration": duration,
                "error": "subtitle URL not found",
            }

        import httpx

        resp = httpx.get(sub_url, timeout=15.0)
        resp.raise_for_status()

        transcript_text = ""
        if resp.headers.get("content-type", "").startswith("application/json"):
            sub_data = resp.json()
            events = sub_data.get("events", [])
            segments = []
            for event in events:
                segs = event.get("segs", [])
                for seg in segs:
                    text = seg.get("utf8", "").strip()
                    if text and text != "\n":
                        segments.append(text)
            transcript_text = " ".join(segments)
        else:
            transcript_text = resp.text

        return {
            "url": url,
            "title": title,
            "transcript": transcript_text[:20000],
            "duration": duration,
            "tool": "yt-dlp",
        }

    except FileNotFoundError:
        return {"url": url, "transcript": "", "error": "yt-dlp not installed (pip install yt-dlp)"}
    except subprocess.TimeoutExpired:
        return {"url": url, "transcript": "", "error": "yt-dlp timed out"}
    except Exception as exc:
        # Don't log full exception to avoid leaking data (HIGH #9)
        logger.error("youtube_transcript_failed url=%s: %s", url, type(exc).__name__)
        return {"url": url, "transcript": "", "error": "transcript extraction failed"}
