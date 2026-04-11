"""URL and input validation for SSRF prevention.

Provides SSRF-safe URL validation, character capping, and GitHub query
sanitization.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

# Security & capacity constants
MAX_CHARS_HARD_CAP = 200_000
MAX_SPIDER_URLS = 100
SPIDER_CONCURRENCY = 5
EXTERNAL_TIMEOUT_SECS = 30
MAX_REQ_TIMEOUT = 120

# Default cap for per-fetch text extraction (aliases MAX_CHARS_HARD_CAP for tools).
MAX_FETCH_CHARS = MAX_CHARS_HARD_CAP

# Default timeout (seconds) for stealth browser tools (camoufox, botasaurus).
STEALTH_TIMEOUT = 60

# GitHub CLI query allow-list regex (prevents flag injection)
GH_QUERY_RE = re.compile(r"^[\w\s\-./:@#'\"?!()+,=\[\]&*~|<>]+$")


class UrlSafetyError(ValueError):
    """Raised when a URL fails SSRF / scheme safety checks."""


def validate_url(url: str) -> str:
    """Reject URLs that would allow SSRF into internal or cloud-metadata
    endpoints. Forces http(s) scheme, resolves DNS, and blocks private,
    link-local, loopback, multicast, reserved, and unspecified IPs.

    Args:
        url: candidate URL to validate

    Returns:
        The validated URL (unchanged if valid).

    Raises:
        UrlSafetyError: if URL is invalid, has wrong scheme, or resolves to
                        a blocked IP address (private, loopback, link-local,
                        multicast, reserved, unspecified).
    """
    if not isinstance(url, str) or len(url) > 4096:
        raise UrlSafetyError("url missing, wrong type, or too long")

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise UrlSafetyError(f"url parse failed: {exc}") from None

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UrlSafetyError(f"scheme '{scheme}' not allowed (http/https only)")

    host = parsed.hostname or ""
    if not host:
        raise UrlSafetyError("url missing hostname")

    # Resolve to IPs and check each. getaddrinfo handles both v4 and v6.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UrlSafetyError(f"dns resolve failed for {host}: {exc}") from None

    for _family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise UrlSafetyError(f"invalid resolved ip: {ip_str}") from None

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UrlSafetyError(
                f"host {host} resolves to blocked address {ip_str} "
                "(private/loopback/link-local/multicast/reserved/unspecified)"
            )

    return url


def cap_chars(n: int | None) -> int:
    """Clamp character count to [1, MAX_CHARS_HARD_CAP].

    Args:
        n: candidate character count (may be None, invalid, or out of range)

    Returns:
        Clamped character count in valid range.
    """
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        n = 0
    if n <= 0 or n > MAX_CHARS_HARD_CAP:
        return MAX_CHARS_HARD_CAP
    return n
