"""research_exif_extract, research_ocr_extract — Image intelligence tools."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from typing import Any

import httpx

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.image_intel")

# Max file size for downloads (20MB)
MAX_IMAGE_SIZE = 20 * 1024 * 1024

# Valid tesseract language codes (3-char ISO codes)
VALID_LANGUAGES = {
    "afr",
    "ara",
    "asm",
    "aze",
    "bel",
    "ben",
    "bod",
    "bos",
    "bul",
    "cat",
    "ceb",
    "ces",
    "chi_sim",
    "chi_tra",
    "chr",
    "cym",
    "dan",
    "deu",
    "dzo",
    "ell",
    "eng",
    "enm",
    "epo",
    "est",
    "eus",
    "fas",
    "fin",
    "fra",
    "frk",
    "frm",
    "gle",
    "glg",
    "grc",
    "guj",
    "hat",
    "heb",
    "hin",
    "hrv",
    "hun",
    "hye",
    "iku",
    "ind",
    "isl",
    "ita",
    "jav",
    "jpn",
    "kan",
    "kat",
    "kaz",
    "khm",
    "kir",
    "kmr",
    "kok",
    "kor",
    "kur",
    "lao",
    "lat",
    "lav",
    "lit",
    "ltz",
    "mal",
    "mar",
    "mkd",
    "mlt",
    "msa",
    "mya",
    "nep",
    "nld",
    "nor",
    "oci",
    "ori",
    "osd",
    "pan",
    "pol",
    "por",
    "pus",
    "ron",
    "rus",
    "san",
    "sin",
    "slk",
    "slv",
    "snd",
    "spa",
    "sqi",
    "srp",
    "srp_latn",
    "sun",
    "swe",
    "syr",
    "tam",
    "tat",
    "tel",
    "tgk",
    "tgl",
    "tha",
    "tir",
    "ton",
    "tur",
    "uig",
    "ukr",
    "urd",
    "uzb",
    "uzb_cyrl",
    "vie",
    "yid",
    "yor",
    "zho_sim",
    "zho_tra",
}

# Map PIL ExifTags IDs to readable names (common EXIF tags)
EXIF_TAG_NAMES = {
    271: "Make",
    272: "Model",
    305: "Software",
    306: "DateTime",
    33432: "Copyright",
    36867: "DateTimeOriginal",
    36868: "DateTimeDigitized",
    37121: "ColorSpace",
    37383: "MeteringMode",
    37385: "Flash",
    37386: "FocalLength",
    37500: "MakerNote",
    40961: "ColorSpace",
    40962: "PixelXDimension",
    40963: "PixelYDimension",
}


async def _download_image(url: str) -> bytes | None:
    """Download image from URL with size limit.

    Args:
        url: Image URL

    Returns:
        Image bytes or None if download failed.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            # Check content length before downloading
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_IMAGE_SIZE:
                logger.warning(
                    "image_size_exceeded url=%s size=%s", url[:80], content_length
                )
                return None

            # Stream and check size
            if len(response.content) > MAX_IMAGE_SIZE:
                logger.warning("image_size_exceeded url=%s size=%d", url[:80], len(response.content))
                return None

            return response.content
    except Exception as exc:
        logger.warning("image_download_failed url=%s: %s", url[:80], exc)
        return None


def _extract_exif_blocking(image_data: bytes) -> dict[str, Any]:
    """Extract EXIF data from image bytes (blocking).

    Args:
        image_data: Image bytes

    Returns:
        Dict with EXIF data or error.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        image = Image.open(__import__("io").BytesIO(image_data))

        # Get basic image info
        result = {
            "format": image.format or "Unknown",
            "size": [image.width, image.height],
            "exif": {},
            "gps": None,
            "has_gps": False,
        }

        # Extract EXIF data
        exif_data = image.getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")

                # Special handling for GPSInfo (tag 34853)
                if tag_id == 34853:
                    result["has_gps"] = True
                    try:
                        gps = _parse_gps_info(value)
                        if gps:
                            result["gps"] = gps
                    except Exception as e:
                        logger.warning("gps_parse_failed: %s", e)
                    continue

                # Store safe EXIF values (strings, numbers, dates)
                if isinstance(value, (str, int, float, bytes)):
                    try:
                        if isinstance(value, bytes):
                            value = value.decode("utf-8", errors="ignore")
                        result["exif"][tag_name] = str(value)[:256]
                    except Exception:
                        pass

        return result

    except ImportError:
        return {
            "error": "Pillow library not installed. Install with: pip install Pillow",
        }
    except Exception as exc:
        logger.error("exif_extraction_failed: %s", exc)
        return {
            "error": f"EXIF extraction failed: {exc}",
        }


def _parse_gps_info(gps_data: dict[int, Any]) -> dict[str, float] | None:
    """Parse GPS info from EXIF GPSInfo tag.

    Converts DMS (degrees, minutes, seconds) to decimal degrees.

    Args:
        gps_data: GPSInfo dictionary from EXIF

    Returns:
        Dict with latitude, longitude, and altitude, or None.
    """
    try:
        def dms_to_decimal(dms_tuple: tuple[tuple[int, int], ...]) -> float:
            """Convert DMS to decimal degrees."""
            degrees = dms_tuple[0][0] / dms_tuple[0][1]
            minutes = dms_tuple[1][0] / dms_tuple[1][1]
            seconds = dms_tuple[2][0] / dms_tuple[2][1]
            return degrees + (minutes / 60.0) + (seconds / 3600.0)

        # Tag IDs in GPSInfo: 1=N/S, 2=latitude, 3=E/W, 4=longitude, 5=altitude ref, 6=altitude
        lat_ref = gps_data.get(1, "N")
        lat = dms_to_decimal(gps_data.get(2, ((0, 1), (0, 1), (0, 1))))

        lon_ref = gps_data.get(3, "E")
        lon = dms_to_decimal(gps_data.get(4, ((0, 1), (0, 1), (0, 1))))

        if lat_ref == "S":
            lat = -lat
        if lon_ref == "W":
            lon = -lon

        result = {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
        }

        # Optional altitude
        if 6 in gps_data:
            alt_tuple = gps_data[6]
            if isinstance(alt_tuple, (tuple, list)) and len(alt_tuple) == 2:
                altitude = alt_tuple[0] / alt_tuple[1]
                result["altitude"] = round(altitude, 2)

        return result
    except Exception as e:
        logger.warning("gps_dms_conversion_failed: %s", e)
        return None


async def research_exif_extract(url_or_path: str) -> dict[str, Any]:
    """Extract EXIF metadata from image URLs or file paths.

    Downloads images from URLs (max 20MB) or reads local files, then
    extracts EXIF metadata using Pillow. Includes GPS coordinates
    (converted from DMS to decimal degrees if present).

    Args:
        url_or_path: Image URL or local file path

    Returns:
        Dict with keys:
        - source: URL or path that was analyzed
        - format: image format (JPEG, PNG, etc.)
        - size: [width, height]
        - exif: dict of EXIF tags and values
        - gps: dict with latitude, longitude, altitude (if present)
        - has_gps: bool indicating GPS data presence
        - error: error message if extraction failed
    """
    url_or_path = url_or_path.strip()

    logger.info("exif_extract_start source=%s", url_or_path[:80])

    # Determine if URL or file path
    is_url = url_or_path.startswith(("http://", "https://"))

    image_data = None
    if is_url:
        try:
            validate_url(url_or_path)
        except ValueError as e:
            logger.warning("invalid_url: %s", e)
            return {"error": str(e), "source": url_or_path}

        image_data = await _download_image(url_or_path)
        if not image_data:
            return {"error": "Failed to download image", "source": url_or_path}
    else:
        # Local file path
        try:
            with open(url_or_path, "rb") as f:
                image_data = f.read()
                if len(image_data) > MAX_IMAGE_SIZE:
                    return {
                        "error": f"File too large (max {MAX_IMAGE_SIZE / 1024 / 1024}MB)",
                        "source": url_or_path,
                    }
        except FileNotFoundError:
            return {"error": "File not found", "source": url_or_path}
        except Exception as e:
            logger.error("file_read_failed: %s", e)
            return {"error": f"Failed to read file: {e}", "source": url_or_path}

    if not image_data:
        return {"error": "No image data", "source": url_or_path}

    # Run blocking extraction in executor
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _extract_exif_blocking,
        image_data,
    )

    result["source"] = url_or_path
    return result


async def research_ocr_extract(
    url_or_path: str,
    language: str = "eng",
) -> dict[str, Any]:
    """Extract text from images using Tesseract OCR.

    Downloads images from URLs (max 20MB) or reads local files, then
    performs optical character recognition using Tesseract (available
    at /usr/bin/tesseract on Hetzner).

    Supports 100+ languages via 3-character ISO 639-2 codes (e.g., eng,
    ara, deu, fra, chi_sim, chi_tra, etc.).

    Args:
        url_or_path: Image URL or local file path
        language: 3-char ISO 639-2 language code (default: "eng" for English)

    Returns:
        Dict with keys:
        - source: URL or path that was analyzed
        - text: extracted text
        - language: language code used
        - word_count: number of words in extracted text
        - confidence: OCR confidence (tesseract only, otherwise None)
        - method: "tesseract" or "pytesseract"
        - error: error message if extraction failed
    """
    url_or_path = url_or_path.strip()
    language = language.strip().lower()

    # Validate language code
    if language not in VALID_LANGUAGES:
        error_msg = (
            f"Unsupported language: {language}. "
            f"Must be 3-char ISO 639-2 code (e.g., eng, ara, deu). "
            f"Partial list: {', '.join(sorted(list(VALID_LANGUAGES)[:10]))}"
        )
        return {
            "error": error_msg,
            "source": url_or_path,
            "language": language,
        }

    logger.info("ocr_extract_start source=%s language=%s", url_or_path[:80], language)

    # Determine if URL or file path
    is_url = url_or_path.startswith(("http://", "https://"))

    image_data = None
    if is_url:
        try:
            validate_url(url_or_path)
        except ValueError as e:
            logger.warning("invalid_url: %s", e)
            return {"error": str(e), "source": url_or_path, "language": language}

        image_data = await _download_image(url_or_path)
        if not image_data:
            return {
                "error": "Failed to download image",
                "source": url_or_path,
                "language": language,
            }
    else:
        # Local file path
        try:
            with open(url_or_path, "rb") as f:
                image_data = f.read()
                if len(image_data) > MAX_IMAGE_SIZE:
                    return {
                        "error": f"File too large (max {MAX_IMAGE_SIZE / 1024 / 1024}MB)",
                        "source": url_or_path,
                        "language": language,
                    }
        except FileNotFoundError:
            return {
                "error": "File not found",
                "source": url_or_path,
                "language": language,
            }
        except Exception as e:
            logger.error("file_read_failed: %s", e)
            return {
                "error": f"Failed to read file: {e}",
                "source": url_or_path,
                "language": language,
            }

    if not image_data:
        return {
            "error": "No image data",
            "source": url_or_path,
            "language": language,
        }

    # Run blocking OCR in executor
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _ocr_blocking,
        image_data,
        language,
    )

    result["source"] = url_or_path
    result["language"] = language
    return result


def _ocr_blocking(image_data: bytes, language: str) -> dict[str, Any]:
    """Blocking OCR extraction using tesseract (blocking).

    Args:
        image_data: Image bytes
        language: Tesseract language code

    Returns:
        Dict with extracted text or error.
    """
    temp_image = None
    temp_output = None
    try:
        # Write to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_data)
            temp_image = tmp.name

        temp_output_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        temp_output = temp_output_file.name.replace(".txt", "")
        temp_output_file.close()

        # Try tesseract first
        try:
            result = subprocess.run(
                ["tesseract", temp_image, temp_output, "-l", language],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning("tesseract_error: %s", result.stderr)
                # Fall back to pytesseract if tesseract binary failed
                return _ocr_pytesseract_blocking(image_data, language)

            # Read output file
            try:
                with open(f"{temp_output}.txt", encoding="utf-8") as f:
                    text = f.read().strip()
            except FileNotFoundError:
                return {"error": "Tesseract output file not found", "text": "", "word_count": 0, "confidence": None, "method": "tesseract"}

            word_count = len(text.split())

            return {
                "text": text,
                "word_count": word_count,
                "confidence": None,  # tesseract binary doesn't return confidence
                "method": "tesseract",
            }

        except FileNotFoundError:
            logger.warning("tesseract_binary_not_found, trying pytesseract")
            return _ocr_pytesseract_blocking(image_data, language)

    except Exception as exc:
        logger.error("ocr_extraction_failed: %s", exc)
        return {
            "error": f"OCR extraction failed: {exc}",
            "text": "",
            "word_count": 0,
            "confidence": None,
            "method": "unknown",
        }
    finally:
        # Cleanup temp files
        if temp_image and os.path.exists(temp_image):
            try:
                os.unlink(temp_image)
            except Exception:
                pass
        if temp_output:
            for ext in ['', '.txt']:
                path = f"{temp_output}{ext}"
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass


def _ocr_pytesseract_blocking(image_data: bytes, language: str) -> dict[str, Any]:
    """Fallback OCR using pytesseract Python library.

    Args:
        image_data: Image bytes
        language: Tesseract language code

    Returns:
        Dict with extracted text or error.
    """
    try:
        import io

        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image, lang=language)
        word_count = len(text.split())

        return {
            "text": text.strip(),
            "word_count": word_count,
            "confidence": None,  # pytesseract doesn't easily provide per-word confidence
            "method": "pytesseract",
        }

    except ImportError:
        return {
            "error": (
                "Neither tesseract binary nor pytesseract library available. "
                "Install with: apt-get install tesseract-ocr (binary) "
                "or pip install pytesseract (Python)"
            ),
            "text": "",
            "word_count": 0,
            "confidence": None,
            "method": "unknown",
        }
    except Exception as exc:
        logger.error("pytesseract_ocr_failed: %s", exc)
        return {
            "error": f"PyTesseract OCR failed: {exc}",
            "text": "",
            "word_count": 0,
            "confidence": None,
            "method": "pytesseract",
        }
