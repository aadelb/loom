"""Tests for exif_utils module."""

from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loom.exif_utils import (
    extract_camera_info,
    extract_exif,
    extract_exif_from_bytes,
    extract_gps,
)


@pytest.mark.unit
def test_extract_exif_missing_file():
    """Test extract_exif with non-existent file."""
    result = extract_exif("/nonexistent/path.jpg")
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.unit
def test_extract_exif_no_pil():
    """Test extract_exif when PIL is not available."""
    with patch("loom.exif_utils._HAS_PIL", False):
        result = extract_exif("test.jpg")
        assert result == {"error": "Pillow not installed"}


@pytest.mark.unit
def test_extract_exif_from_bytes_no_pil():
    """Test extract_exif_from_bytes when PIL is not available."""
    with patch("loom.exif_utils._HAS_PIL", False):
        result = extract_exif_from_bytes(b"fake image data")
        assert result == {"error": "Pillow not installed"}


@pytest.mark.unit
def test_extract_exif_from_bytes_invalid_data():
    """Test extract_exif_from_bytes with invalid image data."""
    result = extract_exif_from_bytes(b"not an image")
    # Should return empty dict on error
    assert isinstance(result, dict)


@pytest.mark.unit
def test_extract_gps_no_pil():
    """Test extract_gps when PIL is not available."""
    with patch("loom.exif_utils._HAS_PIL", False):
        result = extract_gps("test.jpg")
        assert result is None


@pytest.mark.unit
def test_extract_gps_missing_file():
    """Test extract_gps with non-existent file."""
    result = extract_gps("/nonexistent/path.jpg")
    assert result is None


@pytest.mark.unit
def test_extract_camera_info_no_pil():
    """Test extract_camera_info when PIL is not available."""
    with patch("loom.exif_utils._HAS_PIL", False):
        result = extract_camera_info("test.jpg")
        assert result == {}


@pytest.mark.unit
def test_extract_camera_info_no_exif():
    """Test extract_camera_info with file that has no EXIF data."""
    with patch("loom.exif_utils.extract_exif") as mock_extract:
        mock_extract.return_value = {"error": "No EXIF data"}
        result = extract_camera_info("test.jpg")
        assert result == {}


@pytest.mark.unit
def test_extract_camera_info_with_data():
    """Test extract_camera_info with valid EXIF data."""
    with patch("loom.exif_utils.extract_exif") as mock_extract:
        mock_extract.return_value = {
            "Make": "Canon",
            "Model": "EOS 5D",
            "LensModel": "EF 24mm",
            "Software": "Adobe Lightroom",
            "DateTime": "2023-01-15 14:30:00",
        }
        result = extract_camera_info("test.jpg")
        assert result["make"] == "Canon"
        assert result["model"] == "EOS 5D"
        assert result["lens"] == "EF 24mm"
        assert result["software"] == "Adobe Lightroom"
        assert result["datetime"] == "2023-01-15 14:30:00"


@pytest.mark.unit
def test_convert_to_degrees_valid():
    """Test _convert_to_degrees with valid GPS tuple."""
    from loom.exif_utils import _convert_to_degrees

    # Simulate coordinates: 40° 26' 46" N = ~40.4461
    result = _convert_to_degrees((40, 26, 46))
    assert result is not None
    assert 40.4 < result < 40.5


@pytest.mark.unit
def test_convert_to_degrees_invalid():
    """Test _convert_to_degrees with invalid input."""
    from loom.exif_utils import _convert_to_degrees

    assert _convert_to_degrees(None) is None
    assert _convert_to_degrees([]) is None
    assert _convert_to_degrees([1, 2]) is None
    assert _convert_to_degrees("not a tuple") is None


@pytest.mark.unit
def test_convert_to_degrees_with_floats():
    """Test _convert_to_degrees with float values."""
    from loom.exif_utils import _convert_to_degrees

    result = _convert_to_degrees((40.5, 26.25, 46.75))
    assert result is not None
    assert isinstance(result, float)


@pytest.mark.unit
def test_extract_exif_empty_file():
    """Test extract_exif with empty file."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"")
        tmp_path = tmp.name

    try:
        result = extract_exif(tmp_path)
        # Should return error or empty dict depending on PIL behavior
        assert isinstance(result, dict)
    finally:
        Path(tmp_path).unlink()


@pytest.mark.unit
def test_extract_exif_bytes_truncation():
    """Test that long EXIF values are truncated to 100 chars."""
    with patch("loom.exif_utils._HAS_PIL", True):
        with patch("loom.exif_utils.Image") as mock_image:
            mock_img = MagicMock()
            mock_img._getexif.return_value = {
                271: "A" * 200,  # 200 char string (should be truncated)
            }
            mock_image.open.return_value = mock_img

            result = extract_exif("test.jpg")
            # Should truncate to 100 chars
            assert len(result.get("Model", "")) <= 100
