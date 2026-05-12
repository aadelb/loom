"""EXIF/image metadata extraction utilities.

Extracts GPS coordinates, camera info, timestamps, and other metadata
from image files. Uses Pillow if available, falls back to basic parsing.
"""

from __future__ import annotations

import contextlib
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.exif_utils")

try:
    from PIL import Image
    from PIL.ExifTags import GPSTAGS, TAGS

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def extract_exif(path: str | Path) -> dict[str, Any]:
    """Extract EXIF metadata from an image file.

    Returns dict with human-readable tag names as keys.
    Returns empty dict if file has no EXIF or Pillow is unavailable.

    Args:
        path: Path to image file

    Returns:
        Dict with EXIF data, or {"error": message} if extraction fails
    """
    if not _HAS_PIL:
        return {"error": "Pillow not installed"}

    path = Path(path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    try:
        img = Image.open(path)
        exif_data = img._getexif() if hasattr(img, "_getexif") else None
        if not exif_data:
            return {}

        result: dict[str, Any] = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = f"<binary {len(value)} bytes>"
            result[str(tag_name)] = str(value)[:100]

        return result
    except Exception as exc:
        logger.debug("exif_extraction_failed path=%s error=%s", path, exc)
        return {"error": str(exc)}


def extract_exif_from_bytes(image_data: bytes) -> dict[str, Any]:
    """Extract EXIF metadata from image bytes.

    Args:
        image_data: Binary image data

    Returns:
        Dict with EXIF data, or empty dict if none found
    """
    if not _HAS_PIL:
        return {"error": "Pillow not installed"}

    try:
        img = Image.open(BytesIO(image_data))
        exif_data = img._getexif() if hasattr(img, "_getexif") else None
        if not exif_data:
            return {}

        result: dict[str, Any] = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
            result[str(tag_name)] = str(value)[:100]

        return result
    except Exception as exc:
        logger.debug("exif_extraction_from_bytes failed: %s", exc)
        return {}


def extract_gps(path: str | Path) -> dict[str, float | str] | None:
    """Extract GPS coordinates from image EXIF data.

    Returns {"latitude": float, "longitude": float} or None if no GPS data found.

    Args:
        path: Path to image file

    Returns:
        Dict with GPS data, or None if not available
    """
    if not _HAS_PIL:
        return None

    path = Path(path)
    try:
        img = Image.open(path)
        exif_data = img._getexif() if hasattr(img, "_getexif") else None
        if not exif_data:
            return None

        gps_info = exif_data.get(34853)  # GPSInfo tag
        if not gps_info:
            return None

        gps: dict[str, Any] = {}
        for key, val in gps_info.items():
            gps[GPSTAGS.get(key, key)] = val

        lat = _convert_to_degrees(gps.get("GPSLatitude"))
        lon = _convert_to_degrees(gps.get("GPSLongitude"))

        if lat is None or lon is None:
            return None

        if gps.get("GPSLatitudeRef") == "S":
            lat = -lat
        if gps.get("GPSLongitudeRef") == "W":
            lon = -lon

        result: dict[str, float | str] = {"latitude": lat, "longitude": lon}

        alt = gps.get("GPSAltitude")
        if alt:
            with contextlib.suppress(TypeError, ValueError):
                result["altitude"] = float(alt)

        return result
    except Exception:
        return None


def extract_camera_info(path: str | Path) -> dict[str, str]:
    """Extract camera make, model, and lens from image.

    Args:
        path: Path to image file

    Returns:
        Dict with camera metadata (make, model, lens, software, datetime)
    """
    exif = extract_exif(path)
    if "error" in exif:
        return {}
    return {
        k: str(v)
        for k, v in {
            "make": exif.get("Make", ""),
            "model": exif.get("Model", ""),
            "lens": exif.get("LensModel", ""),
            "software": exif.get("Software", ""),
            "datetime": exif.get("DateTime", ""),
        }.items()
        if v
    }


def _convert_to_degrees(value: Any) -> float | None:
    """Convert GPS coordinate tuple to decimal degrees.

    Args:
        value: Tuple of (degrees, minutes, seconds)

    Returns:
        Decimal degrees or None if conversion fails
    """
    if not value or len(value) != 3:
        return None
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
