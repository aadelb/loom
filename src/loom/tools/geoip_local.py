"""research_geoip_local — Local GeoIP lookup using MaxMind GeoLite2 database."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.geoip_local")

# Common GeoLite2 database locations
GEOIP_DATABASE_PATHS = [
    "/usr/share/GeoIP/GeoLite2-City.mmdb",
    "/opt/GeoIP/GeoLite2-City.mmdb",
    "~/.local/share/GeoIP/GeoLite2-City.mmdb",
    "/usr/local/share/GeoIP/GeoLite2-City.mmdb",
]

DOWNLOAD_URL = "https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"

# Cache database path to avoid repeated filesystem checks
_cached_db_path: str | None = None


def _find_geoip_database() -> str | None:
    """Find GeoLite2 database file at common locations.

    Uses cached path if already found. Returns None if database not found.
    Note: TOCTOU race exists between path check and actual read; callers
    should handle FileNotFoundError.
    """
    global _cached_db_path
    if _cached_db_path is not None:
        return _cached_db_path

    for path in GEOIP_DATABASE_PATHS:
        expanded = os.path.expanduser(path)
        if os.path.isfile(expanded):
            logger.info("geoip_database_found path=%s", expanded)
            _cached_db_path = expanded
            return expanded
    return None


def _validate_ip(ip: str) -> str:
    """Validate and normalize IP address.

    Rejects RFC 1918 private, loopback, link-local, and reserved addresses.

    Args:
        ip: IPv4 or IPv6 address string

    Raises:
        ValueError: If IP is invalid, private, or reserved.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError as e:
        raise ValueError(f"Invalid IP address: {ip}") from e

    # Reject private, loopback, link-local, multicast, and reserved IPs
    if addr.is_private:
        raise ValueError(f"Private IP address not allowed: {ip}")
    if addr.is_loopback:
        raise ValueError(f"Loopback IP address not allowed: {ip}")
    if addr.is_link_local:
        raise ValueError(f"Link-local IP address not allowed: {ip}")
    if addr.is_multicast:
        raise ValueError(f"Multicast IP address not allowed: {ip}")
    if addr.is_reserved:
        raise ValueError(f"Reserved IP address not allowed: {ip}")

    return str(addr)


def _extract_gps_info(exif_dict: dict[int, Any]) -> dict[str, float] | None:
    """Extract GPS coordinates from EXIF GPSInfo.

    Converts DMS (degrees, minutes, seconds) to decimal degrees.

    Args:
        exif_dict: EXIF data dictionary with tag IDs as keys.

    Returns:
        Dict with latitude and longitude in decimal degrees, or None.
    """
    try:
        gps_info = exif_dict.get(34853)  # GPSInfo tag ID
        if not gps_info:
            return None

        def dms_to_decimal(dms_tuple: tuple[tuple[int, int], ...]) -> float:
            """Convert DMS tuple to decimal degrees.

            Raises:
                ValueError: If tuple is malformed or denominators are zero.
            """
            if not isinstance(dms_tuple, (list, tuple)) or len(dms_tuple) < 3:
                raise ValueError(
                    f"DMS tuple must have >= 3 elements, got {len(dms_tuple) if isinstance(dms_tuple, (list, tuple)) else 'non-tuple'}"
                )

            if dms_tuple[0][1] == 0:
                raise ValueError("DMS degree denominator is zero")
            degrees = dms_tuple[0][0] / dms_tuple[0][1]

            if dms_tuple[1][1] == 0:
                raise ValueError("DMS minute denominator is zero")
            minutes = dms_tuple[1][0] / dms_tuple[1][1]

            if dms_tuple[2][1] == 0:
                raise ValueError("DMS second denominator is zero")
            seconds = dms_tuple[2][0] / dms_tuple[2][1]

            return degrees + (minutes / 60.0) + (seconds / 3600.0)

        # GPSInfo structure: {1: N/S, 2: latitude, 3: E/W, 4: longitude, ...}
        # Require all 4 GPS tags; don't use unsafe defaults
        if not all(tag in gps_info for tag in (1, 2, 3, 4)):
            logger.debug("incomplete_gps_tags: missing latitude or longitude reference")
            return None

        lat_ref = gps_info.get(1)  # 1 = N or S
        if lat_ref not in ("N", "S"):
            logger.warning("invalid_latitude_ref: expected N or S, got %s", lat_ref)
            return None

        lon_ref = gps_info.get(3)  # 3 = E or W
        if lon_ref not in ("E", "W"):
            logger.warning("invalid_longitude_ref: expected E or W, got %s", lon_ref)
            return None

        lat = dms_to_decimal(gps_info[2])
        lon = dms_to_decimal(gps_info[4])

        if lat_ref == "S":
            lat = -lat
        if lon_ref == "W":
            lon = -lon

        return {"latitude": lat, "longitude": lon}
    except (ValueError, TypeError, IndexError, ZeroDivisionError) as e:
        logger.warning("gps_extraction_failed: %s", e)
        return None


@handle_tool_errors("research_geoip_local")
async def research_geoip_local(ip: str) -> dict[str, Any]:
    """Look up geographic information for an IP address using local MaxMind database.

    Uses the MaxMind GeoLite2-City database (free tier). No API calls or
    network access required — operates entirely offline.

    **Note**: Private IP addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
    127.0.0.0/8) are rejected for security and privacy reasons.

    Args:
        ip: IP address to look up (IPv4 or IPv6)

    Returns:
        Dict with keys:
        - ip: validated IP address
        - country: country code (e.g., "US")
        - city: city name (e.g., "New York")
        - subdivision: state/province code (e.g., "NY")
        - latitude: decimal degrees
        - longitude: decimal degrees
        - timezone: IANA timezone (e.g., "America/New_York")
        - continent: continent code (e.g., "NA")
        - postal_code: postal/zip code
        - accuracy_radius_km: accuracy radius in kilometers
        - source: "local_geoip2"
        - error: error message if lookup failed
    """
    # Validate IP
    try:
        ip = _validate_ip(ip.strip())
    except ValueError as e:
        logger.warning("invalid_ip ip=%s: %s", ip, e)
        return {"error": str(e), "ip": ip}

    # Check for database
    db_path = _find_geoip_database()
    if not db_path:
        error_msg = (
            f"GeoLite2-City.mmdb not found. Download free database from {DOWNLOAD_URL}"
        )
        logger.warning("geoip_database_not_found: %s", error_msg)
        return {"error": error_msg, "ip": ip}

    logger.info("geoip_lookup_start ip=%s db=%s", ip, db_path)

    # Run blocking geoip2 lookup in executor
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _lookup_ip,
        db_path,
        ip,
    )

    return result


def _lookup_ip(db_path: str, ip: str) -> dict[str, Any]:
    """Blocking GeoIP lookup using geoip2.

    Defensive re-validation of IP before lookup.

    Args:
        db_path: Path to GeoLite2-City.mmdb
        ip: IP address to look up (must be pre-validated, but re-checked)

    Returns:
        Dict with location data or error.
    """
    # Defensive re-validation: never trust executor caller
    try:
        ip = _validate_ip(ip)
    except ValueError as e:
        return {"error": str(e), "ip": ip}

    try:
        import geoip2.database
    except ImportError:
        error_msg = (
            "geoip2 library not installed. "
            "Install with: pip install geoip2 maxminddb"
        )
        logger.error("geoip2_import_failed: %s", error_msg)
        return {
            "error": error_msg,
            "ip": ip,
        }

    try:
        with geoip2.database.Reader(db_path) as reader:
            response = reader.city(ip)

        # Extract location data, handling None values from incomplete database entries
        return {
            "ip": ip,
            "country": response.country.iso_code if response.country.iso_code else "Unknown",
            "city": response.city.name if response.city.name else "Unknown",
            "subdivision": (
                response.subdivisions[0].iso_code
                if response.subdivisions and response.subdivisions[0].iso_code
                else None
            ),
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
            "timezone": response.location.time_zone if response.location.time_zone else "Unknown",
            "continent": response.continent.code if response.continent.code else "Unknown",
            "postal_code": response.postal.code if response.postal.code else None,
            "accuracy_radius_km": response.location.accuracy_radius,
            "source": "local_geoip2",
        }
    except FileNotFoundError as exc:
        error_msg = f"Database file not found: {db_path}"
        logger.error("geoip_database_notfound db=%s: %s", db_path, exc)
        return {"error": error_msg, "ip": ip}
    except PermissionError as exc:
        error_msg = f"Permission denied reading database: {db_path}"
        logger.error("geoip_permission_denied db=%s: %s", db_path, exc)
        return {"error": error_msg, "ip": ip}
    except Exception as exc:
        error_msg = f"GeoIP lookup failed: {type(exc).__name__}: {exc}"
        logger.error("geoip_lookup_failed ip=%s db=%s: %s", ip, db_path, exc)
        return {"error": error_msg, "ip": ip}
