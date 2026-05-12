"""Sanitization utilities for sensitive data redaction.

Provides consistent API key masking, URL sanitization, and log-safe
formatting across all tools and providers.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Pattern for API key/token values in both key=value and Python dict repr formats
# Matches: key=value, key:value, key="value", 'key': 'value', etc.
_KEY_PATTERN = re.compile(
    r"(?i)(?:['\"](api[_-]?key|token|secret|password|auth|credential)['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]|"
    r"(api[_-]?key|token|secret|password|authorization|bearer|auth|credential)\s*[=:]\s*['\"]?([^\s'\"&,]+))",
)

_SENSITIVE_PARAMS = frozenset({
    "api_key", "apikey", "key", "token", "secret", "password",
    "access_token", "refresh_token", "authorization", "auth",
    "credential", "bearer", "x-api-key", "apitoken",
})

_SENSITIVE_HEADERS = frozenset({
    "authorization", "x-api-key", "x-auth-token", "cookie",
    "set-cookie", "x-access-token", "x-secret",
})


def mask_key(key: str, *, visible_chars: int = 4) -> str:
    """Mask API key/token, showing only first N characters and last 2."""
    if not key or len(key) <= visible_chars:
        return "***"
    return key[:visible_chars] + "..." + key[-2:]


def sanitize_url(url: str) -> str:
    """Remove sensitive query parameters from a URL.

    Replaces values of params like api_key, token, secret with masked version.
    """
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qs(parsed.query, keep_blank_values=True)
        sanitized = {
            k: ["***"] if k.lower() in _SENSITIVE_PARAMS else v
            for k, v in params.items()
        }
        clean_query = urlencode(sanitized, doseq=True)
        return urlunparse(parsed._replace(query=clean_query))
    except Exception:
        return url


def sanitize_text(text: str) -> str:
    """Redact API keys and tokens found in free text.

    Matches patterns like "api_key=<value>" and replaces value with masked version.
    Works with both key=value and 'key': 'value' formats (Python dicts).
    """
    def _replace(match: re.Match[str]) -> str:
        groups = match.groups()
        # Group 1: dict-style key name, Group 2: dict-style value
        # Group 3: other key name, Group 4: other value
        if groups[1]:  # dict-style match
            key = groups[0]
            value = groups[1]
            return f"'{key}': '{mask_key(value)}'"
        else:  # key=value style match
            key = groups[2]
            value = groups[3]
            return f"{key}={mask_key(value)}"

    return _KEY_PATTERN.sub(_replace, text)


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Mask sensitive header values for safe logging.

    Returns new dict with masked values for Authorization, X-API-Key, etc.
    """
    return {
        k: mask_key(v) if k.lower() in _SENSITIVE_HEADERS else v
        for k, v in headers.items()
    }


def safe_repr(obj: object, *, max_length: int = 200) -> str:
    """Safe string representation with length cap and key masking."""
    text = repr(obj)
    text = sanitize_text(text)
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text
