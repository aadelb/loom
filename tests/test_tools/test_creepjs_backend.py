"""Unit tests for creepjs_backend tool — Privacy baseline assessment."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.creepjs_backend import (
    research_creepjs_audit,
    _extract_creepjs_metrics,
)


class TestExtractCreepjsMetrics:
    """Test metric extraction from creepjs API response."""

    def test_extract_basic_metrics(self) -> None:
        """Extract basic metrics from response."""
        response = {
            "trustScore": 85,
            "fingerprint": {"hash": "abc123"},
        }
        metrics = _extract_creepjs_metrics(response)

        assert metrics["trust_score"] == 85
        assert metrics["fingerprint_hash"] == "abc123"
        assert metrics["privacy_grade"] == "A"

    def test_extract_features(self) -> None:
        """Extract detected features."""
        response = {
            "trustScore": 75,
            "components": {
                "canvas": {"lies": True, "value": "canvas_fp"},
                "webgl": {"lies": False, "value": "webgl_fp"},
                "audio": {"lies": True, "value": "audio_fp"},
            },
        }
        metrics = _extract_creepjs_metrics(response)

        assert metrics["mismatch_score"] == 2
        assert metrics["detected_features"]["canvas"]["detected"] is True
        assert metrics["detected_features"]["webgl"]["detected"] is False

    def test_privacy_grades(self) -> None:
        """Test privacy grade calculation."""
        test_cases = [
            (85, "A"),
            (70, "B"),
            (55, "C"),
            (40, "D"),
            (20, "F"),
        ]

        for score, expected_grade in test_cases:
            response = {"trustScore": score}
            metrics = _extract_creepjs_metrics(response)
            assert metrics["privacy_grade"] == expected_grade

    def test_fonts_feature_extraction(self) -> None:
        """Extract fonts array length properly."""
        response = {
            "trustScore": 60,
            "components": {
                "fonts": {"lies": True, "value": ["Arial", "Verdana", "Times"]},
            },
        }
        metrics = _extract_creepjs_metrics(response)

        assert metrics["detected_features"]["fonts"]["value"] == 3
        assert metrics["detected_features"]["fonts"]["detected"] is True


class TestResearchCreepjsAudit:
    """Test research_creepjs_audit function."""

    def test_invalid_url_validation(self) -> None:
        """Invalid URLs are rejected."""
        result = research_creepjs_audit(target_url="not_a_url")

        assert result["success"] is False
        assert "Invalid URL" in result["error"]

    def test_empty_url_validation(self) -> None:
        """Empty URL is rejected."""
        result = research_creepjs_audit(target_url="")

        assert result["success"] is False
        assert "Invalid URL" in result["error"]

    @patch("loom.tools.creepjs_backend._run_creepjs_audit")
    def test_successful_audit(self, mock_run: MagicMock) -> None:
        """Successful audit returns expected structure."""
        mock_run.return_value = {
            "trustScore": 80,
            "fingerprint": {"hash": "test_hash_123"},
            "components": {
                "canvas": {"lies": False, "value": "canvas_data"},
                "webgl": {"lies": True, "value": "webgl_data"},
            },
        }

        result = research_creepjs_audit(target_url="https://creepjs.web.app")

        assert result["success"] is True
        assert result["trust_score"] == 80
        assert result["fingerprint_hash"] == "test_hash_123"
        assert "privacy_grade" in result
        assert "assessment" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_default_parameters(self) -> None:
        """Default parameters are used correctly."""
        result = research_creepjs_audit()

        assert "error" in result or "success" in result
        assert isinstance(result, dict)

    def test_result_structure(self) -> None:
        """Result always includes required fields."""
        result = research_creepjs_audit(target_url="https://example.com")

        required_fields = [
            "success",
            "trust_score",
            "fingerprint_hash",
            "detected_features",
            "privacy_grade",
            "mismatch_score",
            "assessment",
            "recommendations",
            "error",
        ]

        for field in required_fields:
            assert field in result
