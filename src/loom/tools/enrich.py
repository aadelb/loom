"""Content enrichment tools — language detection, Wayback Machine recovery."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.enrich")

_WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"


def research_detect_language(text: str) -> dict[str, Any]:
    """Detect the language of text content (free, no API key).

    Uses langdetect for fast, lightweight language identification
    across 55+ languages.

    Args:
        text: text to analyze (at least 20 chars recommended)

    Returns:
        Dict with ``language`` (ISO 639-1 code), ``confidence``,
        and ``alternatives`` list.
    """
    if not text or len(text.strip()) < 10:
        return {"language": "unknown", "confidence": 0.0, "error": "text too short"}

    try:
        from langdetect import detect, detect_langs  # type: ignore[import-untyped]
    except ImportError:
        return {"language": "unknown", "confidence": 0.0, "error": "langdetect not installed"}

    try:
        language = detect(text[:5000])
        langs = detect_langs(text[:5000])
        alternatives = [
            {"lang": str(lang).split(":")[0], "prob": round(lang.prob, 3)} for lang in langs[:5]
        ]
        confidence = alternatives[0]["prob"] if alternatives else 0.0

        return {
            "language": language,
            "confidence": confidence,
            "alternatives": alternatives,
        }

    except Exception as exc:
        logger.warning("language_detection_failed: %s", exc)
        return {"language": "unknown", "confidence": 0.0, "error": str(exc)}


def research_wayback(
    url: str,
    limit: int = 1,
) -> dict[str, Any]:
    """Retrieve archived versions of a URL from the Wayback Machine (free).

    Uses the Internet Archive CDX API to find the most recent snapshot.
    Useful for recovering content from dead links (404, timeouts).

    Args:
        url: the original URL to look up
        limit: max number of snapshots to return

    Returns:
        Dict with ``snapshots`` list (each has ``timestamp``,
        ``archive_url``, ``status_code``) and ``original_url``.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                _WAYBACK_CDX_URL,
                params={
                    "url": url,
                    "output": "json",
                    "limit": limit,
                    "fl": "timestamp,original,statuscode,mimetype,digest",
                    "sort": "reverse",
                    "filter": "statuscode:200",
                },
            )
            resp.raise_for_status()
            rows = resp.json()

        if len(rows) <= 1:
            return {"original_url": url, "snapshots": [], "error": "no snapshots found"}

        snapshots = []
        for row in rows[1:]:
            timestamp = row[0]
            archive_url = f"https://web.archive.org/web/{timestamp}/{url}"
            snapshots.append(
                {
                    "timestamp": timestamp,
                    "archive_url": archive_url,
                    "status_code": row[2],
                    "mimetype": row[3],
                }
            )

        return {"original_url": url, "snapshots": snapshots}

    except Exception as exc:
        logger.warning("wayback_lookup_failed url=%s: %s", url, exc)
        return {"original_url": url, "snapshots": [], "error": str(exc)}
