"""HTML processing utilities shared across tools.

Provides tag stripping, text extraction, link extraction, and meta
extraction. Uses regex for lightweight operations; tools needing full
DOM parsing should use selectolax or BeautifulSoup directly.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

# Regex patterns for HTML processing
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
_META_RE = re.compile(
    r'<meta\s+[^>]*(?:name|property)\s*=\s*["\']([^"\']+)["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def strip_tags(html: str) -> str:
    """Remove all HTML tags, returning plain text."""
    text = _SCRIPT_STYLE_RE.sub("", html)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(html: str, *, max_chars: int = 0) -> str:
    """Extract readable text from HTML, removing scripts/styles/tags."""
    text = strip_tags(html)
    return text[:max_chars] if max_chars > 0 else text


def extract_links(html: str, base_url: str = "") -> list[str]:
    """Extract all href links from HTML, resolving relative URLs."""
    raw_links = _LINK_RE.findall(html)
    return [urljoin(base_url, link) for link in raw_links] if base_url else raw_links


def extract_meta(html: str) -> dict[str, str]:
    """Extract meta tags (name/property → content) from HTML."""
    return {name.lower(): content for name, content in _META_RE.findall(html)}


def extract_title(html: str) -> str:
    """Extract and clean <title> content from HTML."""
    match = _TITLE_RE.search(html)
    return strip_tags(match.group(1)).strip() if match else ""
