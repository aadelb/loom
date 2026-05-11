"""research_cert_analyze — Extract and analyze SSL/TLS certificate information."""

from __future__ import annotations

import asyncio
import logging
import socket
import ssl
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.cert_analyzer")


async def research_cert_analyze(
    hostname: str = "",
    domain: str = "",
    port: int = 443,
) -> dict[str, Any]:
    """Extract SSL/TLS certificate information from a remote server.

    Uses Python's ssl stdlib to connect to the target and retrieve the peer
    certificate. Extracts subject, issuer, validity dates, SANs, and computed
    fields like days_until_expiry and is_self_signed.

    Args:
        hostname: Domain name or IP address (alphanumeric + dots + hyphens)
        domain: Alternative parameter name for hostname (if provided, used as hostname)
        port: TCP port (default 443)

    Returns:
        Dict with keys:
          - hostname: input hostname
          - port: input port
          - subject: dict from cert subject RDN (CN, O, C, etc.)
          - issuer: dict from cert issuer RDN
          - not_before: ISO format string (UTC)
          - not_after: ISO format string (UTC)
          - days_until_expiry: int (negative if expired)
          - is_expired: bool
          - is_self_signed: bool (issuer == subject)
          - san: list of SAN strings (DNS names, IPs, etc.)
          - serial: certificate serial number (hex string)
          - version: X.509 version (1, 2, or 3)
          - error: str (if connection/parsing failed)
    """
    # Resolve hostname: prefer domain parameter if provided
    target_hostname = domain if domain else hostname

    # Validate hostname format
    if not target_hostname or not _is_valid_hostname(target_hostname):
        return {
            "hostname": target_hostname,
            "port": port,
            "error": "Invalid hostname format (alphanumeric + dots + hyphens only)",
        }

    # Validate port
    if not isinstance(port, int) or port < 1 or port > 65535:
        return {
            "hostname": target_hostname,
            "port": port,
            "error": "Port must be integer 1-65535",
        }

    logger.info("cert_analyze hostname=%s port=%d", target_hostname, port)

    try:
        def _fetch_cert() -> tuple[bytes | None, dict[str, Any] | None]:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=target_hostname) as s:
                s.settimeout(10)
                s.connect((target_hostname, port))
                der_cert = s.getpeercert(binary_form=True)
                cert_dict = s.getpeercert()
                return der_cert, cert_dict

        der_cert, cert_dict = await asyncio.to_thread(_fetch_cert)

        if not der_cert:
            return {
                "hostname": target_hostname,
                "port": port,
                "error": "No certificate returned",
            }

        if not cert_dict:
            return {
                "hostname": target_hostname,
                "port": port,
                "error": "Failed to parse certificate",
            }

        # Extract fields
        subject = _parse_dn(cert_dict.get("subject", ()))
        issuer = _parse_dn(cert_dict.get("issuer", ()))

        # Parse dates (format: 'Jan  1 00:00:00 2025 GMT')
        not_before = _parse_cert_date(cert_dict.get("notBefore", ""))
        not_after = _parse_cert_date(cert_dict.get("notAfter", ""))

        # Compute days until expiry
        days_until_expiry = None
        is_expired = False
        if not_after:
            delta = not_after - datetime.now(UTC)
            days_until_expiry = delta.days
            is_expired = delta.total_seconds() < 0

        # Check self-signed
        is_self_signed = subject == issuer if subject and issuer else False

        # Extract SANs
        san_list = _extract_san(cert_dict.get("subjectAltName", ()))

        # Get version (1=v1, 2=v2, 3=v3 in pyOpenSSL convention)
        version = cert_dict.get("version", 3)

        serial_hex = format(cert_dict.get("serialNumber", 0), "X") if cert_dict.get("serialNumber") else ""

        return {
            "hostname": target_hostname,
            "port": port,
            "subject": subject or {},
            "issuer": issuer or {},
            "not_before": not_before.isoformat() if not_before else None,
            "not_after": not_after.isoformat() if not_after else None,
            "days_until_expiry": days_until_expiry,
            "is_expired": is_expired,
            "is_self_signed": is_self_signed,
            "san": san_list,
            "serial": serial_hex,
            "version": version,
        }

    except TimeoutError:
        return {
            "hostname": target_hostname,
            "port": port,
            "error": "Connection timeout",
        }
    except socket.gaierror as e:
        return {
            "hostname": target_hostname,
            "port": port,
            "error": f"DNS resolution failed: {e}",
        }
    except ssl.SSLError as e:
        return {
            "hostname": target_hostname,
            "port": port,
            "error": f"SSL error: {e}",
        }
    except Exception as e:
        logger.exception("Unexpected error during cert analysis")
        return {
            "hostname": target_hostname,
            "port": port,
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        }


def _is_valid_hostname(hostname: str) -> bool:
    """Check if hostname contains only allowed characters.

    Allows:
      - Alphanumeric (a-z, A-Z, 0-9)
      - Dots (.)
      - Hyphens (-)

    Does not allow:
      - Underscores or other special chars
      - Empty strings or whitespace
    """
    if not hostname or not isinstance(hostname, str):
        return False

    # Check for whitespace before processing
    if hostname != hostname.strip():
        return False

    # Check length
    if len(hostname) > 255:
        return False

    # Check character set
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if not all(c in allowed for c in hostname):
        return False

    # Hyphens/dots should not be at start/end of entire hostname
    if hostname.startswith("-") or hostname.startswith(".") or hostname.endswith("-") or hostname.endswith("."):
        return False

    # Each label (part between dots) should not start or end with hyphen
    for label in hostname.split("."):
        if label.startswith("-") or label.endswith("-"):
            return False

    return True


def _parse_dn(dn_tuple: tuple[tuple[tuple[str, str], ...], ...]) -> dict[str, str]:
    """Parse X.509 DN (Distinguished Name) tuple to dict.

    SSL cert DNs are: ((('commonName', 'example.com'),), (('organizationName', 'Acme'),))
    """
    result = {}
    for rdn in dn_tuple:
        for type_name, value in rdn:
            # Map common OID names to short keys
            short_name = {
                "commonName": "CN",
                "organizationName": "O",
                "countryName": "C",
                "stateOrProvinceName": "ST",
                "localityName": "L",
                "organizationalUnitName": "OU",
                "emailAddress": "EMAIL",
            }.get(type_name, type_name)

            result[short_name] = value

    return result


def _parse_cert_date(date_str: str) -> datetime | None:
    """Parse SSL certificate date string.

    Format: 'Jan  1 00:00:00 2025 GMT'
    """
    if not date_str:
        return None

    try:
        # strptime with %b (abbreviated month), %d (day), %H:%M:%S, %Y, 'GMT'
        # Handle variable spacing
        date_str_clean = " ".join(date_str.replace("GMT", "").split())
        dt = datetime.strptime(date_str_clean, "%b %d %H:%M:%S %Y")
        # Assume UTC since the original format includes 'GMT'
        return dt.replace(tzinfo=UTC)
    except ValueError as e:
        logger.warning("Failed to parse certificate date '%s': %s", date_str, e)
        return None


def _extract_san(san_tuple: tuple[tuple[str, str], ...]) -> list[str]:
    """Extract Subject Alternative Names from cert.

    SAN tuple format: (('DNS', 'example.com'), ('DNS', 'www.example.com'), ('IP Address', '1.2.3.4'))
    """
    result = []
    for san_type, san_value in san_tuple:
        # Typically 'DNS', 'IP Address', 'URI', 'email', 'othername', etc.
        result.append(f"{san_type}:{san_value}")
    return result
