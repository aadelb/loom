"""Shared input validation functions for Loom tool modules.

Consolidates duplicated validation functions (_validate_domain, _validate_email,
_validate_ip, _validate_username, _validate_timeout) across 20+ tool files into
single authoritative implementations.

Functions handle common types: domains, emails, IPs, usernames, timeouts, ports,
and generic queries with length bounds.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any


class ValidationError(ValueError):
    """Raised when input validation fails."""


def validate_domain(domain: str) -> str:
    """Validate domain name to prevent command injection.

    Allows alphanumeric, dots, and hyphens. No leading/trailing dots.
    Length 1-253 characters.

    Args:
        domain: domain name to validate (e.g., "example.com")

    Returns:
        The validated domain string

    Raises:
        ValidationError: if domain is invalid
    """
    if not isinstance(domain, str):
        raise ValidationError("domain must be a string")

    domain = domain.strip()
    if not domain or len(domain) > 253:
        raise ValidationError("domain must be 1-253 characters")

    if domain.startswith(".") or domain.endswith("."):
        raise ValidationError("domain cannot start or end with a dot")

    # Allow alphanumeric, dots, hyphens only
    if not re.match(r"^[a-z0-9.-]+$", domain, re.IGNORECASE):
        raise ValidationError("domain contains disallowed characters")

    return domain


def validate_email(email: str) -> str:
    """Validate email address (RFC 5321 simplified).

    Format: user@domain where user and domain follow basic rules.
    Length 1-254 characters.

    Args:
        email: email address to validate

    Returns:
        The validated email string

    Raises:
        ValidationError: if email is invalid
    """
    if not isinstance(email, str):
        raise ValidationError("email must be a string")

    email = email.strip()
    if not email or len(email) > 254:
        raise ValidationError("email must be 1-254 characters")

    # Simplified RFC 5321: user@domain
    # user: alphanumeric + dots, hyphens, underscores
    # domain: alphanumeric + dots, hyphens
    pattern = r"^[a-z0-9._-]+@[a-z0-9.-]+$"
    if not re.match(pattern, email, re.IGNORECASE):
        raise ValidationError("email format invalid")

    return email


def validate_ip(ip: str) -> str:
    """Validate IPv4 or IPv6 address.

    Uses ipaddress.ip_address() for strict validation.

    Args:
        ip: IP address string (IPv4 or IPv6)

    Returns:
        The validated IP string

    Raises:
        ValidationError: if IP is invalid
    """
    if not isinstance(ip, str):
        raise ValidationError("ip must be a string")

    ip = ip.strip()
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError as exc:
        raise ValidationError(f"invalid ip address: {exc}") from None


def validate_username(username: str) -> str:
    """Validate username for OSINT/social lookups.

    Allows alphanumeric, underscores, dots, hyphens, plus.
    Length 1-64 characters.

    Args:
        username: username to validate

    Returns:
        The validated username string

    Raises:
        ValidationError: if username is invalid
    """
    if not isinstance(username, str):
        raise ValidationError("username must be a string")

    username = username.strip()
    if not username or len(username) > 64:
        raise ValidationError("username must be 1-64 characters")

    # Allow alphanumeric, underscore, hyphen, period, plus
    if not re.match(r"^[a-z0-9._\-+]+$", username, re.IGNORECASE):
        raise ValidationError("username contains disallowed characters")

    return username


def validate_timeout(
    timeout: float | int, min_val: float = 1.0, max_val: float = 300.0
) -> float:
    """Validate and clamp timeout to allowed range.

    Converts to float, clamps to [min_val, max_val].

    Args:
        timeout: timeout value in seconds
        min_val: minimum allowed timeout (default 1.0)
        max_val: maximum allowed timeout (default 300.0)

    Returns:
        Clamped timeout value as float

    Raises:
        ValidationError: if timeout cannot be converted to float
    """
    try:
        t = float(timeout)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"timeout must be numeric: {exc}") from None

    if t < min_val:
        return min_val
    if t > max_val:
        return max_val
    return t


def validate_port(port: int) -> int:
    """Validate port number (1-65535).

    Args:
        port: port number to validate

    Returns:
        The validated port number

    Raises:
        ValidationError: if port is out of range
    """
    if not isinstance(port, int):
        raise ValidationError("port must be an integer")

    if port < 1 or port > 65535:
        raise ValidationError("port must be 1-65535")

    return port


def validate_query(
    query: str, min_len: int = 1, max_len: int = 5000
) -> str:
    """Validate and clean a search query string.

    Strips whitespace, validates length, returns cleaned string.

    Args:
        query: search query string
        min_len: minimum length (default 1)
        max_len: maximum length (default 5000)

    Returns:
        The cleaned query string

    Raises:
        ValidationError: if query is empty or exceeds max_len
    """
    if not isinstance(query, str):
        raise ValidationError("query must be a string")

    query = query.strip()
    if len(query) < min_len or len(query) > max_len:
        raise ValidationError(
            f"query must be {min_len}-{max_len} characters"
        )

    return query
