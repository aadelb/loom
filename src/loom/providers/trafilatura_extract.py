"""Trafilatura text extraction fallback (free, no API key, fast)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.providers.trafilatura_extract")


def extract_with_trafilatura(
    url: str | None = None,
    html: str | None = None,
    include_tables: bool = True,
    include_links: bool = False,
    target_language: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Extract clean text from HTML or URL using trafilatura.

    Fast, lightweight alternative to Crawl4AI. Supports 60+ languages,
    boilerplate removal, and table extraction. No browser needed.

    Args:
        url: URL to fetch and extract (if html not provided)
        html: raw HTML to extract from (takes precedence over url)
        include_tables: extract table content
        include_links: include hyperlinks in output
        target_language: filter to specific language
        **kwargs: passed through to trafilatura.extract

    Returns:
        Dict with ``text``, ``title``, ``tool``.
    """
    try:
        import trafilatura  # type: ignore[import-untyped]
    except ImportError:
        return {"text": "", "error": "trafilatura not installed (pip install trafilatura)"}

    try:
        if html is None and url:
            html = trafilatura.fetch_url(url)
        if html is None:
            return {"text": "", "error": "no HTML content to extract"}

        text = (
            trafilatura.extract(
                html,
                include_comments=False,
                include_tables=include_tables,
                include_links=include_links,
                target_language=target_language,
                **kwargs,
            )
            or ""
        )

        metadata = trafilatura.extract_metadata(html)
        title = ""
        if metadata:
            title = getattr(metadata, "title", "") or ""

        return {
            "text": text,
            "title": title,
            "tool": "trafilatura",
        }

    except Exception as exc:
        logger.exception("trafilatura_extract_failed url=%s", url or "html")
        return {"text": "", "error": str(exc)}
