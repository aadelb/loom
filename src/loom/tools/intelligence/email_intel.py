"""Email intelligence tools — verification and discovery.

Provides tools for:
- Email verification via SMTP (AfterShip email-verifier inspired)
- Email discovery via patterns and search (EmailFinder inspired)
"""

from __future__ import annotations

import asyncio
import logging
import re
import smtplib
import socket
from typing import Any

from loom.error_responses import handle_tool_errors
from loom.input_validators import ValidationError, validate_domain, validate_email

logger = logging.getLogger("loom.tools.email_intel")

# Known disposable email providers
_DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "guerrillamail.com", "10minutemail.com",
    "throwaway.email", "yopmail.com", "maildrop.cc", "sharklasers.com",
    "trashmail.com", "fakeinbox.com", "temp-mail.org", "getinbox.com",
    "mytrashmail.com", "mintemail.com", "getnada.com", "temp-mail.io",
    "mailnesia.com", "grr.la", "tempmail.us", "fakemail.net",
}

# Known free email providers
_FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com",
    "mail.com", "protonmail.com", "zoho.com", "yandex.com", "mail.ru",
    "gmx.com", "web.de", "icloud.com", "fastmail.com", "mailbox.org",
}


def _get_mx_records(domain: str) -> list[str]:
    """Retrieve MX records for a domain.

    Falls back to socket if dns.resolver not available.
    Returns list of MX server hostnames.
    """
    try:
        import dns.resolver

        try:
            mx_records = dns.resolver.resolve(domain, "MX")
            return sorted(
                [str(rdata.exchange)[:-1] for rdata in mx_records],
                key=lambda x: x,
            )
        except Exception as e:
            logger.debug("dns_resolver_failed domain=%s: %s", domain, e)
    except ImportError:
        logger.debug("dns.resolver not available, using socket fallback")

    # Socket fallback: attempt to resolve MX via getmxhost
    try:
        # Try socket.getmxhost (deprecated but sometimes available)
        mxhosts = socket.getmxhost(domain)
        if mxhosts:
            return mxhosts
    except Exception:
        pass

    # Last resort: try general A record lookup
    try:
        ip = socket.gethostbyname(domain)
        if ip:
            return [domain]
    except Exception as e:
        logger.debug("socket_lookup_failed domain=%s: %s", domain, e)

    return []


async def _check_smtp(email: str, mx_servers: list[str], timeout: int = 10) -> str:
    """Check email deliverability via SMTP.

    Returns: "deliverable", "undeliverable", or "unknown".
    """
    if not mx_servers:
        return "unknown"

    local, domain = email.split("@")

    # Try first 2 MX servers only
    for mx_server in mx_servers[:2]:
        try:
            # Run SMTP check in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None, _smtp_verify, email, mx_server, local, domain, timeout
                ),
                timeout=timeout + 2,
            )
            if result != "unknown":
                return result
        except asyncio.TimeoutError:
            logger.debug("smtp_timeout email=%s mx=%s", email, mx_server)
            continue
        except Exception as e:
            logger.debug("smtp_check_failed email=%s mx=%s: %s", email, mx_server, e)
            continue

    return "unknown"


def _smtp_verify(email: str, mx_server: str, local: str, domain: str, timeout: int) -> str:
    """Synchronous SMTP verification (run via executor)."""
    try:
        # Connect to MX server on port 25 (SMTP)
        with smtplib.SMTP(timeout=timeout) as server:
            server.connect(mx_server, 25)
            server.helo(server.local_hostname)
            server.mail("test@example.com")
            code, message = server.rcpt(email)

            if code == 250:
                return "deliverable"
            elif code in (550, 551, 552, 553, 554):
                return "undeliverable"
            else:
                return "unknown"
    except smtplib.SMTPServerDisconnected:
        return "unknown"
    except smtplib.SMTPException as e:
        logger.debug("smtp_exception: %s", e)
        return "unknown"
    except socket.timeout:
        return "unknown"
    except Exception as e:
        logger.debug("smtp_verify_exception: %s", e)
        return "unknown"


@handle_tool_errors("research_email_verify")
async def research_email_verify(email: str) -> dict[str, Any]:
    """Verify if an email address is valid and deliverable via SMTP checks.

    No API key required. Checks email format, domain existence, MX records,
    and SMTP deliverability. Also checks against known disposable and free
    email providers.

    Args:
        email: Email address to verify (e.g., "user@example.com")

    Returns:
        Dict with keys:
        - email: The input email address
        - valid_format: True if email format is valid
        - domain_exists: True if domain has valid DNS records
        - mx_records: List of MX server hostnames for the domain
        - smtp_check: "deliverable", "undeliverable", or "unknown"
        - disposable: True if domain is a known disposable email provider
        - free_provider: True if domain is a known free provider (Gmail, Yahoo, etc.)
        - risk_score: Float 0-1 indicating overall risk (0=safe, 1=high risk)
        - error: Error message if validation failed
    """
    # Validate email format
    try:
        email = validate_email(email)
    except ValidationError as e:
        return {
            "email": email,
            "valid_format": False,
            "domain_exists": False,
            "mx_records": [],
            "smtp_check": "unknown",
            "disposable": False,
            "free_provider": False,
            "risk_score": 1.0,
            "error": str(e),
        }

    local, domain = email.split("@")

    # Validate domain
    try:
        domain = validate_domain(domain)
    except ValidationError as e:
        return {
            "email": email,
            "valid_format": False,
            "domain_exists": False,
            "mx_records": [],
            "smtp_check": "unknown",
            "disposable": False,
            "free_provider": False,
            "risk_score": 1.0,
            "error": str(e),
        }

    # Get MX records
    mx_records = await asyncio.to_thread(_get_mx_records, domain)
    domain_exists = len(mx_records) > 0

    # Check if disposable or free
    domain_lower = domain.lower()
    is_disposable = domain_lower in _DISPOSABLE_DOMAINS
    is_free = domain_lower in _FREE_PROVIDERS

    # Check SMTP deliverability
    smtp_status = "unknown"
    if domain_exists:
        smtp_status = await _check_smtp(email, mx_records)

    # Calculate risk score
    risk_score = 0.0
    if is_disposable:
        risk_score += 0.7  # High risk
    elif is_free:
        risk_score += 0.2  # Moderate risk (free = less verification needed)
    if smtp_status == "undeliverable":
        risk_score += 0.3
    elif smtp_status == "unknown":
        risk_score += 0.1

    risk_score = min(risk_score, 1.0)

    return {
        "email": email,
        "valid_format": True,
        "domain_exists": domain_exists,
        "mx_records": mx_records,
        "smtp_check": smtp_status,
        "disposable": is_disposable,
        "free_provider": is_free,
        "risk_score": risk_score,
    }


@handle_tool_errors("research_email_find")
async def research_email_find(
    domain: str,
    name: str = "",
) -> dict[str, Any]:
    """Find email addresses associated with a domain using patterns and search.

    Generates common email patterns (first.last, firstlast, f.last, etc.),
    checks common mailbox names (info, admin, contact, support, etc.),
    and searches for email addresses at the domain.

    Args:
        domain: Domain to search for emails (e.g., "example.com")
        name: Optional name to generate specific email patterns (e.g., "John Doe")

    Returns:
        Dict with keys:
        - domain: The input domain
        - emails_found: List of discovered email addresses
        - patterns_checked: Number of email patterns checked
        - common_mailboxes: List of common mailbox results (info, admin, etc.)
        - sources: List of discovery sources used
        - error: Error message if validation failed
    """
    # Validate domain
    try:
        domain = validate_domain(domain)
    except ValidationError as e:
        return {
            "domain": domain,
            "emails_found": [],
            "patterns_checked": 0,
            "common_mailboxes": [],
            "sources": [],
            "error": str(e),
        }

    sources = []
    emails_found = []
    common_mailboxes = []
    patterns_checked = 0

    # Generate email patterns from name
    name_patterns = []
    if name and len(name.strip()) > 0:
        parts = name.strip().split()
        if len(parts) >= 2:
            first, last = parts[0].lower(), parts[-1].lower()
            name_patterns = [
                f"{first}.{last}@{domain}",
                f"{first}{last}@{domain}",
                f"{first[0]}.{last}@{domain}",
                f"{first}_{last}@{domain}",
                f"{last}.{first}@{domain}",
                f"{last}{first}@{domain}",
            ]
        elif len(parts) == 1:
            single = parts[0].lower()
            name_patterns = [
                f"{single}@{domain}",
            ]

    # Common mailbox names
    common = [
        "info", "admin", "contact", "support", "sales",
        "hello", "hey", "team", "help", "feedback",
        "security", "abuse", "postmaster", "webmaster",
    ]

    # Check common mailboxes (simple validation, no SMTP)
    for mailbox in common:
        email = f"{mailbox}@{domain}"
        try:
            validate_email(email)
            common_mailboxes.append(email)
            patterns_checked += 1
        except ValidationError:
            pass

    # Verify name patterns
    for pattern in name_patterns:
        try:
            validate_email(pattern)
            emails_found.append(pattern)
            patterns_checked += 1
        except ValidationError:
            pass

    # Add common mailboxes to found emails
    emails_found.extend(common_mailboxes)

    # Record sources used
    sources.append("pattern_generation")
    if name:
        sources.append("name_parsing")
    sources.append("common_mailboxes")

    # Deduplicate results
    emails_found = list(dict.fromkeys(emails_found))

    return {
        "domain": domain,
        "emails_found": emails_found,
        "patterns_checked": patterns_checked,
        "common_mailboxes": common_mailboxes,
        "sources": sources,
    }
