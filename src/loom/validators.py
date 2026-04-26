"""URL and input validation for SSRF prevention.

Provides SSRF-safe URL validation, character capping, and GitHub query
sanitization.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import threading
import time
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("loom.validators")

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

# DNS resolution cache for TOCTOU prevention (thread-safe, 5-minute TTL)
_dns_cache_lock = threading.Lock()
_dns_cache: dict[str, tuple[list[str], float]] = {}
_DNS_CACHE_TTL = 300  # seconds

# Header names that are safe for user-provided fetch requests.
# Security-sensitive headers (Authorization, Host, Cookie, etc.) are excluded.
SAFE_REQUEST_HEADERS: frozenset[str] = frozenset({
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "dnt",
    "pragma",
    "referer",
    "user-agent",
    "x-requested-with",
})

# Per-provider allowlists for provider_config kwargs in research_search.
PROVIDER_CONFIG_ALLOWLIST: dict[str, frozenset[str]] = {
    "exa": frozenset({"include_domains", "exclude_domains", "start_date", "end_date", "type", "category"}),
    "tavily": frozenset({"include_domains", "exclude_domains", "search_depth", "topic", "include_answer"}),
    "firecrawl": frozenset({"include_domains", "exclude_domains"}),
    "brave": frozenset({"spellcheck", "country", "search_lang", "ui_lang"}),
    "ddgs": frozenset({"region", "time_range", "search_type"}),
    "arxiv": frozenset({"sort_by", "sort_order"}),
    "wikipedia": frozenset({"language"}),
    "hackernews": frozenset({"tags", "numeric_filters"}),
    "reddit": frozenset({"subreddit", "sort", "time_filter"}),
    "newsapi": frozenset({"language", "sort_by", "from_date", "to_date", "domains"}),
    "crypto": frozenset({"convert", "sort", "sort_dir"}),
    "coindesk": frozenset({"language"}),
    "binance": frozenset({"symbol", "interval"}),
    "investing": frozenset({"interval", "range"}),
    "ahmia": frozenset({"language"}),
    "darksearch": frozenset({"page"}),
    "ummro": frozenset({"index", "context", "retrieval_mode"}),
}

# Dangerous JavaScript APIs blocked in login_script / js_before_scrape.
_JS_BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bfetch\s*\(", re.IGNORECASE),
    re.compile(r"\bXMLHttpRequest\b", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bFunction\s*\(", re.IGNORECASE),
    re.compile(r"\brequire\s*\(", re.IGNORECASE),
    re.compile(r"\bimport\s*\(", re.IGNORECASE),
    re.compile(r"\bWebSocket\b", re.IGNORECASE),
    re.compile(r"\bWorker\b", re.IGNORECASE),
    re.compile(r"\bnavigator\.sendBeacon\b", re.IGNORECASE),
    # Bracket-notation bypasses for eval/fetch
    re.compile(r"""window\s*\[\s*["']eval["']\s*\]""", re.IGNORECASE),
    re.compile(r"""window\s*\[\s*["']fetch["']\s*\]""", re.IGNORECASE),
    re.compile(r"\.constructor\s*\.\s*constructor\s*\(", re.IGNORECASE),
]


def validate_js_script(script: str) -> str:
    """Validate a JS script does not use dangerous browser APIs.

    Raises ValueError if a blocked pattern is found.
    """
    for pattern in _JS_BLOCKED_PATTERNS:
        if pattern.search(script):
            raise ValueError(
                f"JavaScript contains disallowed API matching {pattern.pattern!r}"
            )
    return script


def filter_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
    """Filter headers to the safe allowlist, logging any rejections."""
    if not headers:
        return headers
    import logging

    _log = logging.getLogger("loom.validators")
    filtered: dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() in SAFE_REQUEST_HEADERS:
            if len(value) <= 512:
                filtered[name] = value
            else:
                _log.warning("header_value_too_long name=%s len=%d", name, len(value))
        else:
            _log.warning("header_rejected name=%s", name)
    return filtered or None


def filter_provider_config(
    provider: str, config: dict[str, Any] | None
) -> dict[str, Any]:
    """Filter provider_config to the per-provider allowlist."""
    if not config:
        return {}
    import logging

    _log = logging.getLogger("loom.validators")
    allowed = PROVIDER_CONFIG_ALLOWLIST.get(provider, frozenset())
    filtered = {k: v for k, v in config.items() if k in allowed}
    rejected = set(config.keys()) - set(filtered.keys())
    if rejected:
        _log.warning(
            "provider_config_rejected provider=%s keys=%s", provider, rejected
        )
    return filtered


class UrlSafetyError(ValueError):
    """Raised when a URL fails SSRF / scheme safety checks."""


def _get_cached_dns(host: str) -> list[str] | None:
    """Retrieve cached resolved IPs for a host if fresh (within TTL).

    Args:
        host: hostname to look up in cache

    Returns:
        List of resolved IP strings, or None if cache miss or expired.
    """
    with _dns_cache_lock:
        if host in _dns_cache:
            ips, timestamp = _dns_cache[host]
            if time.time() - timestamp < _DNS_CACHE_TTL:
                logger.debug("dns_cache_hit host=%s ips=%s", host, ips)
                return ips
            else:
                del _dns_cache[host]
    return None


def _set_cached_dns(host: str, ips: list[str]) -> None:
    """Store resolved IPs for a host in the cache.

    Args:
        host: hostname
        ips: list of resolved IP strings
    """
    with _dns_cache_lock:
        _dns_cache[host] = (ips, time.time())
        logger.debug("dns_cache_set host=%s ips=%s", host, ips)


def validate_url(url: str) -> str:
    """Reject URLs that would allow SSRF into internal or cloud-metadata
    endpoints. Forces http(s) scheme, resolves DNS, and blocks private,
    link-local, loopback, multicast, reserved, and unspecified IPs.

    Also caches resolved IPs to prevent TOCTOU rebinding attacks. The cache
    uses a 5-minute TTL; downstream code should retrieve cached IPs via
    get_validated_dns() to ensure the request uses the same IP that was
    validated.

    Supports .onion URLs (Tor) if TOR_ENABLED config is true.

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

    # .onion URLs require Tor support via TOR_ENABLED config flag
    if host.endswith(".onion"):
        from loom.config import get_config
        if not get_config().get("TOR_ENABLED", False):
            raise UrlSafetyError(".onion URLs require TOR_ENABLED=true in config")
        return url  # Skip DNS resolution for .onion addresses

    # Resolve to IPs and check each. getaddrinfo handles both v4 and v6.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UrlSafetyError(f"dns resolve failed for {host}: {exc}") from None

    resolved_ips: list[str] = []
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

        resolved_ips.append(ip_str)

    # Cache the validated IPs to prevent TOCTOU rebinding
    if resolved_ips:
        _set_cached_dns(host, resolved_ips)

    return url


def get_validated_dns(host: str) -> list[str] | None:
    """Retrieve cached validated DNS resolution for a host.

    This should be called after validate_url() to get the IPs that were
    validated, ensuring downstream code uses the same IP that passed SSRF
    checks. Returns None if the cache has expired or the host was not
    validated.

    Args:
        host: hostname previously validated by validate_url()

    Returns:
        List of validated IP addresses (v4 and v6), or None if not cached.
    """
    return _get_cached_dns(host)


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
