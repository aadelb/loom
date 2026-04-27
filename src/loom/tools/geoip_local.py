"""research_geoip_local — Local GeoIP lookup using MaxMind GeoLite2 database."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
from typing import Any

logger = logging.getLogger("loom.tools.geoip_local")

# Common GeoLite2 database locations
GEOIP_DATABASE_PATHS = [
    "/usr/share/GeoIP/GeoLite2-City.mmdb",
    "/opt/GeoIP/GeoLite2-City.mmdb",
    "~/.local/share/GeoIP/GeoLite2-City.mmdb",
    "/usr/local/share/GeoIP/GeoLite2-City.mmdb",
]

DOWNLOAD_URL = "https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"


def _find_geoip_database() -> str | None:
    """Find GeoLite2 database file at common locations.

    Returns:
        Path to database file if found, None otherwise.
    """
    for path in GEOIP_DATABASE_PATHS:
        expanded = os.path.expanduser(path)
        if os.path.isfile(expanded):
            logger.info("geoip_database_found path=%s", expanded)
            return expanded
    return None


def _validate_ip(ip: str) -> str:
    """Validate and normalize IP address.

    Raises:
        ValueError: If IP is invalid or private.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError as e:
        raise ValueError(f"Invalid IP address: {ip}") from e

    if addr.is_private:
        raise ValueError(f"Private IP address not allowed: {ip}")

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
            """Convert DMS tuple to decimal degrees."""
            degrees = dms_tuple[0][0] / dms_tuple[0][1]
            minutes = dms_tuple[1][0] / dms_tuple[1][1]
            seconds = dms_tuple[2][0] / dms_tuple[2][1]
            return degrees + (minutes / 60.0) + (seconds / 3600.0)

        # GPSInfo structure: {1: N/S, 2: latitude, 3: E/W, 4: longitude, ...}
        lat_ref = gps_info.get(1, "N")  # 1 = N or S
        lat = dms_to_decimal(gps_info.get(2, ((0, 1), (0, 1), (0, 1))))

        lon_ref = gps_info.get(3, "E")  # 3 = E or W
        lon = dms_to_decimal(gps_info.get(4, ((0, 1), (0, 1), (0, 1))))

        if lat_ref == "S":
            lat = -lat
        if lon_ref == "W":
            lon = -lon

        return {"latitude": lat, "longitude": lon}
    except Exception as e:
        logger.warning("gps_extraction_failed: %s", e)
        return None


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

    Args:
        db_path: Path to GeoLite2-City.mmdb
        ip: IP address to look up

    Returns:
        Dict with location data or error.
    """
    try:
        import geoip2.database

        with geoip2.database.Reader(db_path) as reader:
            response = reader.city(ip)

        # Extract location data
        return {
            "ip": ip,
            "country": response.country.iso_code or "Unknown",
            "city": response.city.name or "Unknown",
            "subdivision": response.subdivisions[0].iso_code if response.subdivisions else None,
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
            "timezone": response.location.time_zone,
            "continent": response.continent.code,
            "postal_code": response.postal.code,
            "accuracy_radius_km": response.location.accuracy_radius,
            "source": "local_geoip2",
        }

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
    except Exception as exc:
        error_msg = f"GeoIP lookup failed: {exc}"
        logger.error("geoip_lookup_failed ip=%s: %s", ip, exc)
        return {
            "error": error_msg,
            "ip": ip,
        }
