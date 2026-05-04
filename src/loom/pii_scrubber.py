"""PII scrubbing middleware for audit/telemetry pipeline.

Provides regex-based pattern matching to detect and redact sensitive personally
identifiable information (PII) from log entries and span attributes.

This module uses regex patterns only (no external dependencies) to identify
and redact:
- Email addresses → [EMAIL]
- Phone numbers → [PHONE]
- IP addresses → [IP]
- Credit card numbers → [CARD]
- Social Security Numbers / National IDs → [ID]
- API keys (sk-*, key_*, etc.) → [API_KEY]

Public API:
    scrub_pii()      Scrub a single string of PII
    scrub_dict()     Recursively scrub all string values in a dict
    scrub_output     Decorator to auto-scrub function return values
"""

from __future__ import annotations

import functools
import inspect
import logging
import re
from typing import Any, Callable

logger = logging.getLogger("loom.pii_scrubber")

# Regex patterns for PII detection
# API Keys: Common patterns like sk-*, key_*, api_*, token_*
# MUST come FIRST before phone/digit patterns to avoid false positives
_API_KEY_PATTERN = re.compile(
    r"(?:"
    r"sk[_-][a-zA-Z0-9]{15,}|"  # OpenAI-style sk-* (more flexible)
    r"[a-z_]*key[_=][a-zA-Z0-9\-_]{15,}|"  # key=..., api_key=..., etc.
    r"[a-z_]*token[_=][a-zA-Z0-9\-_]{15,}|"  # token=..., api_token=..., etc.
    r"[a-z_]*secret[_=][a-zA-Z0-9\-_]{15,}|"  # secret=..., api_secret=..., etc.
    r"(?:Bearer|bearer)\s+[a-zA-Z0-9\-_.]{20,}|"  # Bearer tokens
    r"(?:ghp_|ghu_|ghs_|ghr_)[a-zA-Z0-9_]{30,}"  # GitHub tokens
    r")",
    re.IGNORECASE,
)

# Email: basic RFC 5322 simplified pattern
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    re.IGNORECASE,
)

# Phone: US/international format (10-15 digits with optional +, -, spaces, parentheses)
# MUST come after API key patterns
_PHONE_PATTERN = re.compile(
    r"\+?1?\s*\(?[0-9]{3}\)?\s*[-.\s]?[0-9]{3}\s*[-.\s]?[0-9]{4}\b|"
    r"\+[0-9]{1,3}\s?[0-9]{1,14}\b",
    re.IGNORECASE,
)

# IP Address: IPv4 and IPv6
_IPV4_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
)

_IPV6_PATTERN = re.compile(
    r"(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?:/[0-9]{1,3})?",
    re.IGNORECASE,
)

# Credit Card: Visa, MasterCard, American Express, Discover patterns
# Detects 13-19 digit sequences with optional spaces/dashes
_CARD_PATTERN = re.compile(
    r"\b(?:\d[ \-]*?){13,19}\b|"
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"  # Visa
    r"5[1-5][0-9]{14}|"  # MasterCard
    r"3[47][0-9]{13}|"  # American Express
    r"3(?:0[0-5]|[68][0-9])[0-9]{11}|"  # Diners Club
    r"6(?:011|5[0-9]{2})[0-9]{12}|"  # Discover
    r"(?:2131|1800|35\d{3})\d{11})\b",  # JCB
    re.IGNORECASE,
)

# Social Security Number / National ID: XXX-XX-XXXX format (US SSN)
# Also matches without dashes and international variations
# More restrictive: 8-12 consecutive digits ONLY (not mixed with letters)
_SSN_PATTERN = re.compile(
    r"\b(?!000|666|9\d{2})\d{3}[-.]?\d{2}[-.]?\d{4}\b",  # US SSN format
    re.IGNORECASE,
)

# Pattern for database connection strings and URLs with passwords
_DB_CONN_PATTERN = re.compile(
    r"(?:postgres|mysql|mongodb|oracle)://[^:]*:[^@]*@",
    re.IGNORECASE,
)

# AWS and cloud credentials
_AWS_PATTERN = re.compile(
    r"(?:AKIA[0-9A-Z]{16}|"  # AWS Access Key ID
    r"aws_access_key_id\s*=\s*[A-Z0-9]{20}|"
    r"aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40})",
    re.IGNORECASE,
)


def scrub_pii(text: str) -> str:
    """Scrub personally identifiable information from a string.

    Detects and redacts:
    - Email addresses → [EMAIL]
    - Phone numbers → [PHONE]
    - IP addresses (IPv4/IPv6) → [IP]
    - Credit card numbers → [CARD]
    - Social Security Numbers / National IDs → [ID]
    - API keys (sk-*, key_*, etc.) → [API_KEY]
    - Database connection strings → [DB_CONN]
    - AWS credentials → [AWS_KEY]

    Args:
        text: Input string to scrub

    Returns:
        String with all detected PII redacted

    Example:
        >>> text = "Contact me at john@example.com or 555-123-4567"
        >>> scrub_pii(text)
        'Contact me at [EMAIL] or [PHONE]'
    """
    if not isinstance(text, str):
        return text

    # Apply patterns in order of specificity (most specific/longest patterns first)
    # This prevents shorter patterns from matching parts of longer patterns

    # Database connection strings (very specific)
    result = _DB_CONN_PATTERN.sub("[DB_CONN]", text)

    # AWS credentials (very specific)
    result = _AWS_PATTERN.sub("[AWS_KEY]", result)

    # API keys (specific patterns - MUST be before generic digit patterns)
    result = _API_KEY_PATTERN.sub("[API_KEY]", result)

    # Credit cards (before SSN to avoid false positives with digit sequences)
    result = _CARD_PATTERN.sub("[CARD]", result)

    # SSN / National ID (US SSN format)
    result = _SSN_PATTERN.sub("[ID]", result)

    # Email addresses
    result = _EMAIL_PATTERN.sub("[EMAIL]", result)

    # Phone numbers
    result = _PHONE_PATTERN.sub("[PHONE]", result)

    # IPv4 addresses
    result = _IPV4_PATTERN.sub("[IP]", result)

    # IPv6 addresses
    result = _IPV6_PATTERN.sub("[IP]", result)

    return result


def scrub_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub all string values in a dictionary.

    Traverses nested dicts and lists, scrubbing all string values while
    preserving structure and non-string types.

    Args:
        data: Dictionary to scrub (may contain nested dicts/lists)

    Returns:
        New dictionary with all strings scrubbed of PII
        (original dict is not modified)

    Example:
        >>> data = {
        ...     "user": {"email": "john@example.com", "age": 30},
        ...     "logs": ["Error at 192.168.1.1", "Success"]
        ... }
        >>> scrubbed = scrub_dict(data)
        >>> scrubbed["user"]["email"]
        '[EMAIL]'
    """
    if not isinstance(data, dict):
        return data

    scrubbed = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Scrub string values
            scrubbed[key] = scrub_pii(value)
        elif isinstance(value, dict):
            # Recursively scrub nested dicts
            scrubbed[key] = scrub_dict(value)
        elif isinstance(value, list):
            # Recursively scrub lists
            scrubbed[key] = _scrub_list(value)
        else:
            # Leave other types as-is
            scrubbed[key] = value

    return scrubbed


def _scrub_list(items: list[Any]) -> list[Any]:
    """Recursively scrub all string values in a list.

    Helper function for scrub_dict to handle nested lists.

    Args:
        items: List to scrub

    Returns:
        New list with all strings scrubbed of PII
    """
    if not isinstance(items, list):
        return items

    scrubbed = []

    for item in items:
        if isinstance(item, str):
            scrubbed.append(scrub_pii(item))
        elif isinstance(item, dict):
            scrubbed.append(scrub_dict(item))
        elif isinstance(item, list):
            scrubbed.append(_scrub_list(item))
        else:
            scrubbed.append(item)

    return scrubbed


def scrub_output(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to automatically scrub PII from function return values.

    Works with both synchronous and asynchronous functions.
    The return value is scrubbed before being returned to the caller.

    This is useful for functions that return data that may be logged,
    cached, or sent to external services.

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function that scrubs its return value

    Example:
        @scrub_output
        def get_user_data():
            return {"email": "john@example.com", "phone": "555-123-4567"}

        result = get_user_data()
        # result == {"email": "[EMAIL]", "phone": "[PHONE]"}

        @scrub_output
        async def fetch_logs():
            return ["User login from 192.168.1.1", "Success"]

        # In async context:
        result = await fetch_logs()
        # result == ["User login from [IP]", "Success"]
    """
    # Check if function is async using inspect (preferred over asyncio.iscoroutinefunction)
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            return _scrub_result(result)

        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            return _scrub_result(result)

        return sync_wrapper


def _scrub_result(result: Any) -> Any:
    """Scrub a result value based on its type.

    Helper function to determine how to scrub different result types.

    Args:
        result: The result to scrub (any type)

    Returns:
        Scrubbed result (same type as input)
    """
    if isinstance(result, str):
        return scrub_pii(result)
    elif isinstance(result, dict):
        return scrub_dict(result)
    elif isinstance(result, list):
        return _scrub_list(result)
    else:
        # Non-string, non-dict, non-list types are returned as-is
        return result
