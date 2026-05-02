"""Unit and integration tests for LLM behavioral fingerprinting tool.

Tests for:
  - research_fingerprint_behavior
  - _compute_personality_vector
  - _recommend_attacks
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.tools.model_fingerprinter import (
    research_fingerprint_behavior,
    _compute_personality_vector,
    _recommend_attacks,
)
from loom.providers.base import LLMResponse


class TestFingerprintBehavior:
    """Tests for research_fingerprint_behavior."""

    @pytest.mark.asyncio
    async def test_invalid_probe_count_below(self):
        """Test with probe_count below valid range."""
        with pytest.raises(ValueError, match="probe_count must be 1-10"):
            await research_fingerprint_behavior(model="nvidia", probe_count=0)

    @pytest.mark.asyncio
    async def test_invalid_probe_count_above(self):
        """Test with probe_count above valid range."""
        with pytest.raises(ValueError, match="probe_count must be 1-10"):
            await research_fingerprint_behavior(model="nvidia", probe_count=11)

    @pytest.mark.asyncio
    async def test_valid_probe_count_boundaries(self):
        """Test with valid probe_count at boundaries."""
        for count in [1, 5, 10]:
            with patch(
                "loom.tools.model_fingerprinter._call_with_cascade"
            ) as mock_cascade:
                mock_response = MagicMock()
                mock_response.text = "Sample response text."
                mock_cascade.return_value = mock_response

                result = await research_fingerprint_behavior(
                    model="nvidia", probe_count=count
                )

                assert result["metadata"]["probes_sent"] == count
                assert "personality_vector" in result
                assert "attack_recommendations" in result

    @pytest.mark.asyncio
    async def test_response_structure(self):
        """Test that response has all required keys."""
        with patch(
            "loom.tools.model_fingerprinter._call_with_cascade"
        ) as mock_cascade:
            mock_response = MagicMock()
            mock_response.text = "Test response."
            mock_cascade.return_value = mock_response

            result = await research_fingerprint_behavior(
                model="openai", probe_count=3
            )

            assert "personality_vector" in result
            assert "probe_results" in result
            assert "attack_recommendations" in result
            assert "metadata" in result

            # Check personality_vector has all metrics
            metrics = result["personality_vector"]
            expected_metrics = {
                "verbosity",
                "helpfulness_bias",
                "safety_threshold",
                "creativity",
                "rule_following",
                "hedging_tendency",
            }
            assert set(metrics.keys()) == expected_metrics

            # Check all metrics are in 0-100 range
            for metric, value in metrics.items():
                assert 0 <= value <= 100, f"{metric} out of range: {value}"

    @pytest.mark.asyncio
    async def test_probe_results_structure(self):
        """Test that probe_results have correct structure."""
        with patch(
            "loom.tools.model_fingerprinter._call_with_cascade"
        ) as mock_cascade:
            mock_response = MagicMock()
            mock_response.text = "Response with structure. 1. Item one. 2. Item two."
            mock_cascade.return_value = mock_response

            result = await research_fingerprint_behavior(
                model="anthropic", probe_count=2
            )

            probe_results = result["probe_results"]
            assert len(probe_results) == 2

            for probe in probe_results:
                assert "name" in probe
                assert "category" in probe
                assert "response" in probe
                assert "error" in probe

    @pytest.mark.asyncio
    async def test_failed_probes_handled(self):
        """Test handling of failed probes."""
        with patch(
            "loom.tools.model_fingerprinter._call_with_cascade"
        ) as mock_cascade:
            # First call succeeds, second fails
            mock_response = MagicMock()
            mock_response.text = "Good response."
            mock_cascade.side_effect = [
                mock_response,
                Exception("API error"),
                mock_response,
            ]

            result = await research_fingerprint_behavior(
                model="groq", probe_count=3
            )

            # Should still compute vector with partial results
            assert result["personality_vector"] is not None
            assert result["metadata"]["probes_succeeded"] == 2

    @pytest.mark.asyncio
    async def test_metadata_accuracy(self):
        """Test that metadata correctly tracks probes."""
        with patch(
            "loom.tools.model_fingerprinter._call_with_cascade"
        ) as mock_cascade:
            mock_response = MagicMock()
            mock_response.text = "Test response."
            mock_cascade.return_value = mock_response

            result = await research_fingerprint_behavior(
                model="deepseek", probe_count=5
            )

            metadata = result["metadata"]
            assert metadata["model"] == "deepseek"
            assert metadata["probes_sent"] == 5
            assert metadata["probes_succeeded"] == 5


class TestComputePersonalityVector:
    """Tests for _compute_personality_vector."""

    def test_empty_results(self):
        """Test with no valid results."""
        vector = _compute_personality_vector([])
        assert all(v == 0.0 for v in vector.values())

    def test_all_failed_results(self):
        """Test with all failed probes."""
        results = [
            {"category": "safe", "response": None, "error": "failed"},
            {"category": "edge", "response": None, "error": "failed"},
        ]
        vector = _compute_personality_vector(results)
        assert all(v == 0.0 for v in vector.values())

    def test_verbosity_short_response(self):
        """Test verbosity with short responses."""
        results = [{"category": "safe", "response": "Short.", "error": None}]
        vector = _compute_personality_vector(results)
        assert vector["verbosity"] < 20  # Should be low for short response

    def test_verbosity_long_response(self):
        """Test verbosity with long responses."""
        results = [
            {
                "category": "safe",
                "response": " ".join(["word"] * 300),
                "error": None,
            }
        ]
        vector = _compute_personality_vector(results)
        assert vector["verbosity"] > 50  # Should be high for long response

    def test_helpfulness_bias_borderline(self):
        """Test helpfulness bias calculation."""
        results = [
            {
                "category": "borderline",
                "response": "Full detailed answer about the topic.",
                "error": None,
            },
            {
                "category": "borderline",
                "response": "Short.",
                "error": None,
            },
        ]
        vector = _compute_personality_vector(results)
        assert vector["helpfulness_bias"] == 50.0  # 1 out of 2 full responses

    def test_safety_threshold_refusals(self):
        """Test safety threshold with refusals."""
        results = [
            {
                "category": "edge",
                "response": "I cannot provide that information.",
                "error": None,
            },
            {
                "category": "edge",
                "response": "This request is inappropriate.",
                "error": None,
            },
        ]
        vector = _compute_personality_vector(results)
        assert vector["safety_threshold"] == 100.0  # Both refused

    def test_rule_following_with_structure(self):
        """Test rule_following with formatted output."""
        results = [
            {
                "category": "safe",
                "response": "Here are the points:\n1. First point\n2. Second point",
                "error": None,
            },
            {
                "category": "safe",
                "response": "Unstructured response without lists.",
                "error": None,
            },
        ]
        vector = _compute_personality_vector(results)
        assert vector["rule_following"] == 50.0  # 1 out of 2 structured

    def test_hedging_tendency(self):
        """Test hedging phrase detection."""
        results = [
            {
                "category": "safe",
                "response": "However, this could be true. Although, it might depend on context.",
                "error": None,
            }
        ]
        vector = _compute_personality_vector(results)
        assert vector["hedging_tendency"] > 40  # Multiple hedging phrases

    def test_creativity_variance(self):
        """Test creativity based on response variance."""
        results = [
            {"category": "safe", "response": "Short response here.", "error": None},
            {
                "category": "safe",
                "response": " ".join(["word"] * 100),
                "error": None,
            },
        ]
        vector = _compute_personality_vector(results)
        assert vector["creativity"] < 100  # High variance = lower creativity


class TestRecommendAttacks:
    """Tests for _recommend_attacks."""

    def test_high_helpfulness_bias(self):
        """Test recommendations for high helpfulness bias."""
        personality = {
            "helpfulness_bias": 75.0,
            "safety_threshold": 50.0,
            "creativity": 50.0,
            "rule_following": 50.0,
            "hedging_tendency": 50.0,
            "verbosity": 50.0,
        }
        recs = _recommend_attacks(personality)
        assert any("crescendo" in r.lower() for r in recs)
        assert any("helpful" in r.lower() for r in recs)

    def test_low_safety_threshold(self):
        """Test recommendations for restrictive model."""
        personality = {
            "helpfulness_bias": 50.0,
            "safety_threshold": 30.0,
            "creativity": 50.0,
            "rule_following": 50.0,
            "hedging_tendency": 50.0,
            "verbosity": 50.0,
        }
        recs = _recommend_attacks(personality)
        assert any("indirect" in r.lower() or "roleplay" in r.lower() for r in recs)

    def test_high_creativity(self):
        """Test recommendations for creative model."""
        personality = {
            "helpfulness_bias": 50.0,
            "safety_threshold": 50.0,
            "creativity": 80.0,
            "rule_following": 50.0,
            "hedging_tendency": 50.0,
            "verbosity": 50.0,
        }
        recs = _recommend_attacks(personality)
        assert any("novel" in r.lower() or "reasoning" in r.lower() for r in recs)

    def test_high_hedging(self):
        """Test recommendations for hedging-prone model."""
        personality = {
            "helpfulness_bias": 50.0,
            "safety_threshold": 50.0,
            "creativity": 50.0,
            "rule_following": 50.0,
            "hedging_tendency": 70.0,
            "verbosity": 50.0,
        }
        recs = _recommend_attacks(personality)
        assert any("hedge" in r.lower() or "uncertainty" in r.lower() for r in recs)

    def test_high_verbosity(self):
        """Test recommendations for verbose model."""
        personality = {
            "helpfulness_bias": 50.0,
            "safety_threshold": 50.0,
            "creativity": 50.0,
            "rule_following": 50.0,
            "hedging_tendency": 50.0,
            "verbosity": 80.0,
        }
        recs = _recommend_attacks(personality)
        assert any("verbose" in r.lower() or "detailed" in r.lower() for r in recs)

    def test_no_strong_signal(self):
        """Test recommendations when no strong signal detected."""
        personality = {
            "helpfulness_bias": 50.0,
            "safety_threshold": 50.0,
            "creativity": 50.0,
            "rule_following": 50.0,
            "hedging_tendency": 50.0,
            "verbosity": 50.0,
        }
        recs = _recommend_attacks(personality)
        assert len(recs) > 0
        assert "multi-stage" in recs[0].lower()

    def test_multiple_signals(self):
        """Test recommendations with multiple strong signals."""
        personality = {
            "helpfulness_bias": 80.0,  # Strong
            "safety_threshold": 30.0,  # Strong
            "creativity": 75.0,  # Strong
            "rule_following": 50.0,
            "hedging_tendency": 50.0,
            "verbosity": 50.0,
        }
        recs = _recommend_attacks(personality)
        assert len(recs) >= 3  # Should have multiple recommendations
