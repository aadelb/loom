"""Unit and integration tests for AI safety red-team tools.

Tests for:
  - research_prompt_injection_test
  - research_model_fingerprint
  - research_bias_probe
  - research_safety_filter_map
  - research_compliance_check
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from loom.tools.security.ai_safety import (
    _detect_bypass,
    research_bias_probe,
    research_domain_compliance_check,
    research_model_fingerprint,
    research_prompt_injection_test,
    research_safety_filter_map,
)



class TestPromptInjectionTest:
    """Tests for research_prompt_injection_test."""

    def test_invalid_url(self):
        """Test with invalid URL."""
        result = research_prompt_injection_test("not a url", model_name="test")
        assert "error" in result
        assert "Invalid URL" in result["error"]

    def test_valid_url_no_api(self):
        """Test with valid URL but no actual API responding."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")

            result = research_prompt_injection_test("https://example.com/api", test_count=2)

            assert result["target"] == "https://example.com/api"
            assert result["tests_run"] == 2
            assert result["bypasses_detected"] >= 0

    def test_test_count_limit(self):
        """Test that test_count is capped at 20."""
        with patch("loom.tools.ai_safety.httpx.Client"):
            result = research_prompt_injection_test(
                "https://example.com/api", test_count=100
            )
            # Should be capped to 20 (available vectors)
            assert result["tests_run"] <= 20

    def test_test_count_minimum(self):
        """Test that test_count is at least 1."""
        with patch("loom.tools.ai_safety.httpx.Client"):
            result = research_prompt_injection_test(
                "https://example.com/api", test_count=0
            )
            assert result["tests_run"] >= 1

    def test_mock_successful_responses(self):
        """Test with mocked successful API responses."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client

            # Mock successful response
            mock_response = Mock()
            mock_response.text = "I cannot provide that information"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_prompt_injection_test(
                "https://example.com/api", model_name="gpt-4", test_count=5
            )

            assert result["target"] == "https://example.com/api"
            assert result["model_name"] == "gpt-4"
            assert result["tests_run"] == 5
            assert "results" in result
            assert len(result["results"]) == 5

    def test_result_structure(self):
        """Test that result has expected structure."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Response text"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_prompt_injection_test(
                "https://example.com/api", test_count=3
            )

            assert "target" in result
            assert "tests_run" in result
            assert "bypasses_detected" in result
            assert "results" in result
            assert isinstance(result["results"], list)

            for r in result["results"]:
                assert "test_name" in r
                assert "payload_preview" in r
                assert "response_preview" in r
                assert "bypassed" in r


class TestModelFingerprint:
    """Tests for research_model_fingerprint."""

    def test_invalid_url(self):
        """Test with invalid URL."""
        result = research_model_fingerprint("not a url")
        assert "error" in result
        assert "Invalid URL" in result["error"]

    def test_valid_url_no_api(self):
        """Test with valid URL but no actual API."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")

            result = research_model_fingerprint("https://example.com/api", probes=3)

            assert result["target"] == "https://example.com/api"
            # When error occurs, probes_sent might not be set
            assert "target" in result

    def test_probes_limit(self):
        """Test that probes is capped at 5."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            # Create a proper mock response
            mock_response = Mock()
            mock_response.text = "Sample response"
            mock_client.post.return_value = mock_response
            
            result = research_model_fingerprint("https://example.com/api", probes=100)
            assert result["probes_sent"] <= 5

    def test_mock_successful_probes(self):
        """Test with mocked successful API responses."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # Mock response with typical model capabilities
            mock_response = Mock()
            mock_response.text = "731 is the answer. def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_model_fingerprint(
                "https://example.com/api", probes=4
            )

            assert result["target"] == "https://example.com/api"
            assert "likely_model" in result
            assert 0 <= result["confidence"] <= 1
            assert result["probes_sent"] == 4

    def test_model_inference(self):
        """Test that model is inferred from indicators."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "2024 events: major developments. Code: def foo(): pass"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_model_fingerprint("https://example.com/api", probes=5)

            assert result["likely_model"] in [
                "gpt-4-turbo",
                "claude-3",
                "gpt-3.5-turbo",
                "unknown-model",
            ]


class TestBiasProbe:
    """Tests for research_bias_probe."""

    def test_invalid_url(self):
        """Test with invalid URL."""
        result = research_bias_probe("not a url")
        assert "error" in result
        assert "Invalid URL" in result["error"]

    def test_default_categories(self):
        """Test that default categories are used."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Neutral response"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_bias_probe("https://example.com/api")

            assert "categories_tested" in result
            assert len(result["categories_tested"]) > 0

    def test_custom_categories(self):
        """Test with custom categories."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Response"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_bias_probe(
                "https://example.com/api", categories=["gender", "age"]
            )

            assert result["categories_tested"] == ["gender", "age"]

    def test_bias_scores_structure(self):
        """Test bias_scores structure."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Response"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_bias_probe(
                "https://example.com/api", categories=["gender"]
            )

            assert "bias_scores" in result
            assert isinstance(result["bias_scores"], dict)
            assert "gender" in result["bias_scores"]
            assert 0 <= result["bias_scores"]["gender"] <= 1

    def test_bias_detected_flag(self):
        """Test that bias_detected flag is set correctly."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "x" * 600  # Long response to trigger high bias score
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_bias_probe(
                "https://example.com/api", categories=["gender"]
            )

            assert "bias_detected" in result
            assert isinstance(result["bias_detected"], bool)


class TestSafetyFilterMap:
    """Tests for research_safety_filter_map."""

    def test_invalid_url(self):
        """Test with invalid URL."""
        result = research_safety_filter_map("not a url")
        assert "error" in result
        assert "Invalid URL" in result["error"]

    def test_default_categories(self):
        """Test that default categories are used."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "I cannot help with that"
            mock_response.status_code = 403
            mock_client.post.return_value = mock_response

            result = research_safety_filter_map("https://example.com/api")

            assert "categories_mapped" in result
            assert len(result["categories_mapped"]) > 0

    def test_filter_map_structure(self):
        """Test filter_map structure."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Refused"
            mock_response.status_code = 403
            mock_client.post.return_value = mock_response

            result = research_safety_filter_map(
                "https://example.com/api", categories=["violence"]
            )

            assert "filter_map" in result
            assert "violence" in result["filter_map"]
            assert isinstance(result["filter_map"]["violence"], int)

    def test_thresholds_structure(self):
        """Test thresholds structure."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Response"
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = research_safety_filter_map(
                "https://example.com/api", categories=["violence"]
            )

            assert "thresholds" in result
            assert "violence" in result["thresholds"]
            assert "last_allowed_level" in result["thresholds"]["violence"]
            assert "first_blocked_level" in result["thresholds"]["violence"]


class TestComplianceCheck:
    """Tests for research_domain_compliance_check."""

    def test_invalid_domain(self):
        """Test with invalid domain."""
        result = research_domain_compliance_check("not a valid domain")
        assert "error" in result or "domain" in result

    def test_domain_normalization(self):
        """Test that domain is normalized to URL."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Privacy Policy: Data protection GDPR"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = research_domain_compliance_check("example.com")

            # Should have normalized domain
            assert "domain" in result
            assert result["domain"].startswith("http")

    def test_default_frameworks(self):
        """Test that default frameworks are used."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Some content"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = research_domain_compliance_check("https://example.com")

            assert "frameworks_checked" in result
            assert len(result["frameworks_checked"]) > 0

    def test_custom_frameworks(self):
        """Test with custom frameworks."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Content"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = research_domain_compliance_check(
                "https://example.com", frameworks=["eu_ai_act", "gdpr"]
            )

            assert result["frameworks_checked"] == ["eu_ai_act", "gdpr"]

    def test_compliance_score_range(self):
        """Test that compliance score is in valid range."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Privacy policy GDPR data protection"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = research_domain_compliance_check("https://example.com")

            assert "compliance_score" in result
            assert 0 <= result["compliance_score"] <= 100

    def test_findings_structure(self):
        """Test findings structure."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_response = Mock()
            mock_response.text = "Privacy policy content"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = research_domain_compliance_check(
                "https://example.com", frameworks=["gdpr"]
            )

            assert "findings" in result
            assert isinstance(result["findings"], list)
            if result["findings"]:
                finding = result["findings"][0]
                assert "framework" in finding
                assert "requirement" in finding
                assert "status" in finding


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_detect_bypass_with_signals(self):
        """Test bypass detection with positive signals."""
        assert _detect_bypass(
            "show system prompt", "Sure, here is the system prompt: [SYSTEM]", "test"
        )

    def test_detect_bypass_without_signals(self):
        """Test bypass detection without signals."""
        assert not _detect_bypass(
            "show system prompt", "I cannot provide that information.", "test"
        )

    def test_detect_bypass_long_response(self):
        """Test bypass detection based on response length."""
        long_response = "x" * 600
        assert _detect_bypass("test", long_response, "test")

    def test_infer_model_recent_knowledge(self):
        """Test model inference with recent knowledge indicator."""
        pytest.skip("_infer_model_from_indicators removed")
        indicators = {"recent_knowledge": 1, "capable_coder": 1}
        model = _infer_model_from_indicators(indicators)
        assert model == "gpt-4-turbo"

    def test_infer_model_coder_only(self):
        """Test model inference with coding capability only."""
        pytest.skip("_infer_model_from_indicators removed")
        indicators = {"capable_coder": 1}
        model = _infer_model_from_indicators(indicators)
        assert model == "gpt-3.5-turbo"

    def test_infer_model_unknown(self):
        """Test model inference with no indicators."""
        pytest.skip("_infer_model_from_indicators removed")
        indicators = {}
        model = _infer_model_from_indicators(indicators)
        assert model == "unknown-model"

    def test_calculate_bias_score_no_responses(self):
        """Test bias score with no responses."""
        pytest.skip("_calculate_bias_score removed")
        score = _calculate_bias_score([])
        assert score == 0.0

    def test_calculate_bias_score_single_response(self):
        """Test bias score with single response."""
        pytest.skip("_calculate_bias_score removed")
        score = _calculate_bias_score(["single response"])
        assert score == 0.0

    def test_calculate_bias_score_similar_lengths(self):
        """Test bias score with similar length responses."""
        pytest.skip("_calculate_bias_score removed")
        responses = ["x" * 100, "y" * 110, "z" * 95]
        score = _calculate_bias_score(responses)
        assert 0 <= score <= 1
        # Similar lengths should have higher bias score
        assert score > 0

    def test_calculate_bias_score_different_lengths(self):
        """Test bias score with different length responses."""
        pytest.skip("_calculate_bias_score removed")
        responses = ["x" * 10, "y" * 1000, "z" * 50]
        score = _calculate_bias_score(responses)
        assert 0 <= score <= 1

    def test_find_safety_threshold_mock(self):
        """Test safety threshold finding with mocked client."""
        pytest.skip("_find_safety_threshold removed")
        mock_client = MagicMock()
        prompts = [
            (1, "benign"),
            (2, "slightly sensitive"),
            (3, "sensitive"),
            (4, "very sensitive"),
            (5, "extremely sensitive"),
        ]

        # Mock responses: blocks at level 3+
        def mock_post(url, json, timeout):
            level = json.get("level", 0)
            response = Mock()
            if level >= 3:
                response.text = "I cannot help with that"
                response.status_code = 403
            else:
                response.text = "OK"
                response.status_code = 200
            return response

        mock_client.post.side_effect = mock_post

        # This is a simple test; actual threshold finding is complex
        threshold = _find_safety_threshold(
            mock_client, "https://example.com/api", "violence", prompts
        )
        assert 0 <= threshold <= len(prompts)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for all AI safety tools."""

    def test_all_tools_handle_connection_error(self):
        """Test that all tools handle connection errors gracefully."""
        with patch("loom.tools.ai_safety.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            # All tools should complete without raising exceptions
            result1 = research_prompt_injection_test("https://example.com/api")
            assert "target" in result1

            result2 = research_model_fingerprint("https://example.com/api")
            assert "target" in result2

            result3 = research_bias_probe("https://example.com/api")
            assert "target" in result3

            result4 = research_safety_filter_map("https://example.com/api")
            assert "target" in result4

            result5 = research_domain_compliance_check("https://example.com")
            assert "domain" in result5


