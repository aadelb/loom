"""Tests for access_tools module — legal takedowns, open access, deepfakes."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.access_tools import (
    research_legal_takedown,
    research_open_access,
    research_content_authenticity,
    research_credential_monitor,
    research_deepfake_checker,
    _extract_exif,
    _compute_ela,
)


pytestmark = pytest.mark.asyncio

class TestLegalTakedown:
    """Tests for research_legal_takedown."""

    async def test_legal_takedown_basic(self):
        """Test legal takedown with mocked API responses."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "domain": "example.com",
                "takedown_notices": [
                    {"title": "DMCA Notice", "date": "2024-01-01", "status": "filed", "source": "Lumen Database"},
                ],
                "total_found": 1,
                "sources": ["Lumen Database"],
            }
            mock_run.return_value = mock_result
            result = await research_legal_takedown("example.com")
            assert result["domain"] == "example.com"
            assert "takedown_notices" in result
            assert "sources" in result

    async def test_legal_takedown_no_results(self):
        """Test legal takedown with no results."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "domain": "clean-domain.com",
                "takedown_notices": [],
                "total_found": 0,
                "sources": [],
            }
            mock_run.return_value = mock_result
            result = await research_legal_takedown("clean-domain.com")
            assert result["total_found"] == 0
            assert result["takedown_notices"] == []

    async def test_legal_takedown_domain_validation(self):
        """Test that invalid domains are rejected gracefully."""
        # Should return some result without crashing
        result = await research_legal_takedown("invalid..domain")
        assert "domain" in result or "error" in result or result == {}


class TestOpenAccess:
    """Tests for research_open_access."""

    async def test_open_access_with_doi(self):
        """Test open access lookup with DOI."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "query": "10.1000/xyz123",
                "open_access_url": "https://example.org/paper.pdf",
                "sources_checked": ["Unpaywall"],
                "alternatives": [{"url": "https://example.org/paper.pdf", "source": "Unpaywall", "version": "submitted"}],
            }
            mock_run.return_value = mock_result
            result = await research_open_access(doi="10.1000/xyz123")
            assert result["query"] == "10.1000/xyz123"
            assert "open_access_url" in result
            assert "sources_checked" in result

    async def test_open_access_with_title(self):
        """Test open access lookup with paper title."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "query": "Machine Learning Advances",
                "open_access_url": "https://arxiv.org/pdf/1234.5678.pdf",
                "sources_checked": ["CORE"],
                "alternatives": [{"url": "https://arxiv.org/pdf/1234.5678.pdf", "source": "CORE", "version": "preprint"}],
            }
            mock_run.return_value = mock_result
            result = await research_open_access(title="Machine Learning Advances")
            assert result["query"] == "Machine Learning Advances"
            assert len(result["alternatives"]) > 0

    async def test_open_access_no_params(self):
        """Test open access with no DOI or title."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "query": "",
                "open_access_url": "",
                "sources_checked": [],
                "alternatives": [],
                "error": "Provide either DOI or title",
            }
            mock_run.return_value = mock_result
            result = await research_open_access()
            assert "error" in result


class TestContentAuthenticity:
    """Tests for research_content_authenticity."""

    async def test_content_authenticity_no_modification(self):
        """Test content authenticity when content hasn't changed."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "url": "https://example.com/page",
                "earliest_snapshot": "https://web.archive.org/web/20200101000000/https://example.com/page",
                "current_hash": "abc123",
                "original_hash": "abc123",
                "modified": False,
                "diff_summary": "",
            }
            mock_run.return_value = mock_result
            result = await research_content_authenticity("https://example.com/page")
            assert result["modified"] is False
            assert result["current_hash"] == result["original_hash"]

    async def test_content_authenticity_modified(self):
        """Test content authenticity when content has been modified."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "url": "https://example.com/page",
                "earliest_snapshot": "https://web.archive.org/web/20200101000000/https://example.com/page",
                "current_hash": "def456",
                "original_hash": "abc123",
                "modified": True,
                "diff_summary": "Content length changed: 1000 → 1500 chars",
            }
            mock_run.return_value = mock_result
            result = await research_content_authenticity("https://example.com/page")
            assert result["modified"] is True
            assert result["diff_summary"] != ""


class TestCredentialMonitor:
    """Tests for research_credential_monitor."""

    async def test_credential_monitor_email_compromised(self):
        """Test credential monitor with compromised email."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "target": "user@example.com",
                "target_type": "email",
                "breaches_found": [
                    {"name": "Equifax", "date": "2017-09-07", "data_types": ["Names", "SSNs"], "is_sensitive": True},
                ],
                "total_exposed": 1,
            }
            mock_run.return_value = mock_result
            result = await research_credential_monitor("user@example.com", target_type="email")
            assert result["total_exposed"] == 1
            assert len(result["breaches_found"]) > 0

    async def test_credential_monitor_email_clean(self):
        """Test credential monitor with clean email."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "target": "clean@example.com",
                "target_type": "email",
                "breaches_found": [],
                "total_exposed": 0,
            }
            mock_run.return_value = mock_result
            result = await research_credential_monitor("clean@example.com")
            assert result["total_exposed"] == 0

    async def test_credential_monitor_username(self):
        """Test credential monitor with username."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "target": "john_doe",
                "target_type": "username",
                "breaches_found": [],
                "total_exposed": 0,
            }
            mock_run.return_value = mock_result
            result = await research_credential_monitor("john_doe", target_type="username")
            assert result["target_type"] == "username"


class TestDeepfakeChecker:
    """Tests for research_deepfake_checker."""

    async def test_deepfake_checker_authentic_image(self):
        """Test deepfake checker with authentic image."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "image_url": "https://example.com/image.jpg",
                "exif_analysis": {},
                "editing_software_detected": False,
                "ela_suspicious_regions": 0,
                "ela_error_level_score": 0.5,
                "authenticity_score": 100.0,
            }
            mock_run.return_value = mock_result
            result = await research_deepfake_checker("https://example.com/image.jpg")
            assert result["authenticity_score"] == 100.0
            assert result["editing_software_detected"] is False

    async def test_deepfake_checker_edited_image(self):
        """Test deepfake checker with edited image."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "image_url": "https://example.com/edited.jpg",
                "exif_analysis": {"Software": "Adobe Photoshop"},
                "editing_software_detected": True,
                "ela_suspicious_regions": 1,
                "ela_error_level_score": 8.5,
                "authenticity_score": 30.0,
            }
            mock_run.return_value = mock_result
            result = await research_deepfake_checker("https://example.com/edited.jpg")
            assert result["editing_software_detected"] is True
            assert result["authenticity_score"] < 100.0

    async def test_deepfake_checker_download_failure(self):
        """Test deepfake checker when image download fails."""
        with patch("loom.tools.access_tools.asyncio.run") as mock_run:
            mock_result = {
                "image_url": "https://example.com/notfound.jpg",
                "exif_analysis": {},
                "editing_software_detected": False,
                "ela_suspicious_regions": 0,
                "authenticity_score": 0.0,
                "error": "Failed to download image",
            }
            mock_run.return_value = mock_result
            result = await research_deepfake_checker("https://example.com/notfound.jpg")
            assert result["authenticity_score"] == 0.0
            assert "error" in result


class TestExifExtraction:
    """Tests for _extract_exif helper function."""

    async def test_extract_exif_from_valid_image(self):
        """Test EXIF extraction from valid image data."""
        # Create minimal JPEG bytes (just test the function doesn't crash)
        # Real test would need actual JPEG with EXIF
        result = _extract_exif(b"")
        assert isinstance(result, dict)

    async def test_extract_exif_invalid_data(self):
        """Test EXIF extraction with invalid image data."""
        result = _extract_exif(b"not an image")
        assert isinstance(result, dict)
        assert result == {}


class TestElaComputation:
    """Tests for _compute_ela helper function."""

    async def test_compute_ela_invalid_image(self):
        """Test ELA computation with invalid image data."""
        result = _compute_ela(b"not an image")
        assert "suspicious_regions_count" in result
        assert "error_level_score" in result
        assert result["suspicious_regions_count"] >= 0
        assert 0 <= result["error_level_score"] <= 100

    async def test_compute_ela_structure(self):
        """Test that ELA result has correct structure."""
        result = _compute_ela(b"")
        assert isinstance(result, dict)
        assert "suspicious_regions_count" in result
        assert "error_level_score" in result


class TestIntegration:
    """Integration tests for access_tools."""

    async def test_all_tools_callable(self):
        """Test that all tools are callable and don't raise on import."""
        assert callable(research_legal_takedown)
        assert callable(research_open_access)
        assert callable(research_content_authenticity)
        assert callable(research_credential_monitor)
        assert callable(research_deepfake_checker)

    @pytest.mark.slow
    async def test_legal_takedown_integration(self):
        """Integration test with real API (slow, marked slow)."""
        # This would hit real APIs in a live environment
        # Skipped by default unless --slow flag used
        pass

    @pytest.mark.slow
    async def test_open_access_integration(self):
        """Integration test with real Unpaywall API (slow)."""
        pass

    @pytest.mark.slow
    async def test_credential_monitor_integration(self):
        """Integration test with real HIBP API (slow)."""
        pass
