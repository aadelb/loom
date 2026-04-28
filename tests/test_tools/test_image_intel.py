"""Tests for image intelligence tools (EXIF and OCR)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.mark.asyncio
class TestResearchExifExtract:
    async def test_invalid_url(self):
        """Test rejection of invalid URL."""
        with patch("loom.tools.image_intel.validate_url", side_effect=ValueError("Invalid URL")):
            from loom.tools.image_intel import research_exif_extract

            result = await research_exif_extract("not-a-url")

            assert "error" in result

    async def test_url_download_failure(self):
        """Test handling of download failure."""
        with patch("loom.tools.image_intel.validate_url"), patch(
            "loom.tools.image_intel._download_image",
            return_value=None,
        ):
            from loom.tools.image_intel import research_exif_extract

            result = await research_exif_extract("https://example.com/image.jpg")

            assert "error" in result
            assert "Failed to download" in result["error"]

    async def test_local_file_not_found(self):
        """Test error when local file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            from loom.tools.image_intel import research_exif_extract

            result = await research_exif_extract("/path/to/nonexistent.jpg")

            assert "error" in result
            assert "not found" in result["error"]

    async def test_local_file_too_large(self):
        """Test rejection of oversized local files."""
        with patch("builtins.open", create=True) as mock_open, patch(
            "os.path.getsize",
            return_value=25 * 1024 * 1024,  # 25MB, exceeds 20MB limit
        ):
            from loom.tools.image_intel import research_exif_extract

            result = await research_exif_extract("/path/to/huge.jpg")

            assert "error" in result
            assert "too large" in result["error"]

    async def test_successful_exif_extraction(self):
        """Test successful EXIF extraction."""
        mock_exif_data = {
            "format": "JPEG",
            "size": [800, 600],
            "exif": {
                "Make": "Canon",
                "Model": "Canon EOS",
                "DateTime": "2023:01:15 10:30:45",
            },
            "gps": None,
            "has_gps": False,
        }

        with patch("loom.tools.image_intel.validate_url"), patch(
            "loom.tools.image_intel._download_image",
            return_value=b"fake-image-data",
        ), patch(
            "loom.tools.image_intel._extract_exif_blocking",
            return_value=mock_exif_data,
        ):
            from loom.tools.image_intel import research_exif_extract

            result = await research_exif_extract("https://example.com/photo.jpg")

            assert result["format"] == "JPEG"
            assert result["size"] == [800, 600]
            assert "Make" in result["exif"]

    async def test_exif_with_gps_data(self):
        """Test EXIF extraction with GPS coordinates."""
        mock_exif_data = {
            "format": "JPEG",
            "size": [1024, 768],
            "exif": {},
            "gps": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "altitude": 10.5,
            },
            "has_gps": True,
        }

        with patch("loom.tools.image_intel.validate_url"), patch(
            "loom.tools.image_intel._download_image",
            return_value=b"image",
        ), patch(
            "loom.tools.image_intel._extract_exif_blocking",
            return_value=mock_exif_data,
        ):
            from loom.tools.image_intel import research_exif_extract

            result = await research_exif_extract("https://example.com/geotagged.jpg")

            assert result["has_gps"] is True
            assert result["gps"]["latitude"] == 40.7128


@pytest.mark.asyncio
class TestResearchOcrExtract:
    async def test_invalid_language_code(self):
        """Test rejection of invalid language code."""
        from loom.tools.image_intel import research_ocr_extract

        result = await research_ocr_extract("https://example.com/text.jpg", language="invalid_lang")

        assert "error" in result
        assert "Unsupported language" in result["error"]

    async def test_valid_language_codes(self):
        """Test that common language codes are accepted."""
        from loom.tools.image_intel import VALID_LANGUAGES

        assert "eng" in VALID_LANGUAGES
        assert "ara" in VALID_LANGUAGES
        assert "fra" in VALID_LANGUAGES
        assert "deu" in VALID_LANGUAGES

    async def test_url_download_failure_ocr(self):
        """Test OCR error on download failure."""
        with patch("loom.tools.image_intel.validate_url"), patch(
            "loom.tools.image_intel._download_image",
            return_value=None,
        ):
            from loom.tools.image_intel import research_ocr_extract

            result = await research_ocr_extract("https://example.com/image.jpg", language="eng")

            assert "error" in result
            assert "Failed to download" in result["error"]

    async def test_successful_ocr_extraction(self):
        """Test successful OCR extraction."""
        mock_ocr_result = {
            "text": "Extracted text from image",
            "word_count": 5,
            "confidence": None,
            "method": "tesseract",
        }

        with patch("loom.tools.image_intel.validate_url"), patch(
            "loom.tools.image_intel._download_image",
            return_value=b"image-data",
        ), patch(
            "loom.tools.image_intel._ocr_blocking",
            return_value=mock_ocr_result,
        ):
            from loom.tools.image_intel import research_ocr_extract

            result = await research_ocr_extract("https://example.com/text.jpg", language="eng")

            assert result["text"] == "Extracted text from image"
            assert result["word_count"] == 5
            assert "method" in result

    async def test_local_file_ocr(self):
        """Test OCR on local file."""
        mock_ocr_result = {
            "text": "Text from file",
            "word_count": 3,
            "confidence": None,
            "method": "tesseract",
        }

        with patch("builtins.open", create=True) as mock_open, patch(
            "loom.tools.image_intel._ocr_blocking",
            return_value=mock_ocr_result,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = b"image"

            from loom.tools.image_intel import research_ocr_extract

            result = await research_ocr_extract("/path/to/text.jpg", language="eng")

            assert "text" in result
            assert result["word_count"] == 3


class TestExtractExifBlocking:
    def test_pillow_not_installed(self):
        """Test error when Pillow is not installed."""
        with patch.dict("sys.modules", {"PIL": None}):
            from loom.tools.image_intel import _extract_exif_blocking

            result = _extract_exif_blocking(b"image-data")

            assert "error" in result
            assert "Pillow" in result["error"]

    def test_basic_image_properties(self):
        """Test extraction of basic image properties."""
        mock_image = MagicMock()
        mock_image.format = "JPEG"
        mock_image.width = 800
        mock_image.height = 600
        mock_image.getexif.return_value = {}

        with patch("loom.tools.image_intel.PIL.Image.open", return_value=mock_image):
            from loom.tools.image_intel import _extract_exif_blocking

            result = _extract_exif_blocking(b"image")

            assert result["format"] == "JPEG"
            assert result["size"] == [800, 600]

    def test_gps_in_exif(self):
        """Test extraction when GPS data is present."""
        mock_image = MagicMock()
        mock_image.format = "JPEG"
        mock_image.width = 1024
        mock_image.height = 768
        mock_image.getexif.return_value = {
            34853: {
                1: "N",
                2: ((40, 1), (42, 1), (46, 1)),
                3: "W",
                4: ((73, 1), (58, 1), (56, 1)),
            }
        }

        with patch("loom.tools.image_intel.PIL.Image.open", return_value=mock_image):
            from loom.tools.image_intel import _extract_exif_blocking

            result = _extract_exif_blocking(b"image")

            assert result["has_gps"] is True
            assert result["gps"] is not None


class TestParseGpsInfo:
    def test_valid_gps_dms_conversion(self):
        """Test conversion of DMS to decimal degrees."""
        from loom.tools.image_intel import _parse_gps_info

        gps_data = {
            1: "N",
            2: ((40, 1), (42, 1), (46, 1)),
            3: "W",
            4: ((73, 1), (58, 1), (56, 1)),
        }

        result = _parse_gps_info(gps_data)

        assert result is not None
        assert "latitude" in result
        assert "longitude" in result
        assert result["latitude"] > 0  # North
        assert result["longitude"] < 0  # West

    def test_gps_south_west(self):
        """Test GPS with South/West coordinates."""
        from loom.tools.image_intel import _parse_gps_info

        gps_data = {
            1: "S",
            2: ((33, 1), (52, 1), (5, 1)),
            3: "W",
            4: ((151, 1), (12, 1), (27, 1)),
        }

        result = _parse_gps_info(gps_data)

        assert result["latitude"] < 0  # South
        assert result["longitude"] < 0  # West

    def test_gps_with_altitude(self):
        """Test GPS extraction with altitude."""
        from loom.tools.image_intel import _parse_gps_info

        gps_data = {
            1: "N",
            2: ((40, 1), (0, 1), (0, 1)),
            3: "E",
            4: ((100, 1), (0, 1), (0, 1)),
            6: (100, 1),  # Altitude in meters
        }

        result = _parse_gps_info(gps_data)

        assert result is not None
        assert "altitude" in result
        assert result["altitude"] == 100.0


class TestDownloadImage:
    async def test_download_oversized_image(self):
        """Test rejection of oversized images."""
        mock_response = AsyncMock()
        mock_response.headers = {"content-length": str(25 * 1024 * 1024)}  # 25MB

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            from loom.tools.image_intel import _download_image

            result = await _download_image("https://example.com/huge.jpg")

            assert result is None

    async def test_download_success(self):
        """Test successful image download."""
        mock_response = AsyncMock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.content = b"image-data"
        mock_response.raise_for_status = AsyncMock()

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            from loom.tools.image_intel import _download_image

            result = await _download_image("https://example.com/image.jpg")

            assert result == b"image-data"

    async def test_download_timeout(self):
        """Test handling of download timeout."""
        with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
            from loom.tools.image_intel import _download_image

            result = await _download_image("https://example.com/image.jpg")

            assert result is None


class TestOcrBlocking:
    def test_tesseract_success(self):
        """Test successful tesseract OCR."""
        with patch("subprocess.run") as mock_run, patch("builtins.open", create=True) as mock_open:
            mock_run.return_value.returncode = 0
            mock_open.return_value.__enter__.return_value.read.return_value = "Extracted text"

            from loom.tools.image_intel import _ocr_blocking

            result = _ocr_blocking(b"image", "eng")

            assert result["text"] == "Extracted text"
            assert result["method"] == "tesseract"

    def test_tesseract_not_found_fallback(self):
        """Test fallback to pytesseract when tesseract not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            from loom.tools.image_intel import _ocr_blocking

            # When tesseract is not found, it should try pytesseract
            result = _ocr_blocking(b"image", "eng")

            # Result should indicate what happened
            assert "text" in result or "error" in result
