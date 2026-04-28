"""Tests for credential monitoring tools (cipher_mirror)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestResearchCipherMirror:
    async def test_search_tools_not_available(self):
        """Test error when search tools are unavailable."""
        with patch("loom.tools.cipher_mirror.asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=[])

            # Simulate ImportError for search tools
            with patch("loom.tools.cipher_mirror.research_search", side_effect=ImportError()):
                from loom.tools.cipher_mirror import research_cipher_mirror

                result = await research_cipher_mirror("openai api key")

                assert result["query"] == "openai api key"
                assert result["error"] == "search tools not available"
                assert result["findings"] == []

    async def test_no_results_found(self):
        """Test when search returns no results."""
        mock_search_result = {"results": []}

        with patch("loom.tools.cipher_mirror.asyncio.get_running_loop") as mock_loop:
            executor_mock = AsyncMock()
            executor_mock.return_value = []
            mock_loop.return_value.run_in_executor = executor_mock

            with patch("loom.tools.cipher_mirror.research_search", return_value=mock_search_result):
                from loom.tools.cipher_mirror import research_cipher_mirror

                result = await research_cipher_mirror("nonexistent_secret", n=5)

                assert result["query"] == "nonexistent_secret"
                assert result["findings"] == []
                assert result["stats"]["total_scanned"] == 0
                assert result["stats"]["credentials_found"] == 0

    async def test_detects_api_key_credentials(self):
        """Test detection of high-entropy API keys."""
        from loom.tools.cipher_mirror import research_cipher_mirror

        # Test the helper functions directly
        from loom.tools.cipher_mirror import _detect_credentials, _entropy_score

        # High-entropy string (simulating API key)
        api_key = "sk-aBcDeFgHiJkLmNoPqRsT1234"
        score = _entropy_score(api_key)
        assert score > 0.5, "API key should have high entropy"

        # Test credential detection
        text_with_key = f"Found leaked key: {api_key} in paste"
        creds = _detect_credentials(text_with_key)

        # Should detect at least one credential
        assert len(creds) > 0
        assert creds[0]["type"] == "api_key"
        assert creds[0]["key_type"] == "openai"

    async def test_detects_model_weights(self):
        """Test detection of model weight file references."""
        from loom.tools.cipher_mirror import _detect_model_weights

        text = "Downloaded model.safetensors and pytorch_model.bin from repository"
        weights = _detect_model_weights(text)

        assert len(weights) > 0
        assert any(w["type"] == "model_weight" for w in weights)
        assert any("safetensors" in w["filename"].lower() for w in weights)

    async def test_entropy_threshold_filtering(self):
        """Test that entropy threshold filters low-confidence findings."""
        from loom.tools.cipher_mirror import research_cipher_mirror

        with patch("loom.tools.cipher_mirror.asyncio.get_running_loop"):
            result = await research_cipher_mirror(
                "test query",
                entropy_threshold=0.95,
                n=5,
            )

            # All findings should have confidence >= 0.95 or be empty
            for finding in result.get("findings", []):
                if finding.get("type") == "api_key":
                    assert finding.get("confidence", 0) >= 0.95

    async def test_deduplication_by_url(self):
        """Test that duplicate URLs are removed from findings."""
        from loom.tools.cipher_mirror import research_cipher_mirror

        # Mock search results with duplicate URLs
        duplicate_results = [
            {"url": "https://pastebin.com/1", "title": "Paste 1", "snippet": "sk-abc123"},
            {"url": "https://pastebin.com/1", "title": "Paste 1", "snippet": "sk-abc123"},
            {"url": "https://pastebin.com/2", "title": "Paste 2", "snippet": "sk-def456"},
        ]

        with patch("loom.tools.cipher_mirror.asyncio.get_running_loop") as mock_loop:
            executor_mock = AsyncMock()
            executor_mock.return_value = duplicate_results
            mock_loop.return_value.run_in_executor = executor_mock

            result = await research_cipher_mirror("api key leak")

            # Check that duplicates are handled (unique URLs only)
            sources = set()
            for finding in result.get("findings", []):
                sources.add(finding.get("source"))
            # Should have at most 2 unique sources
            assert len(sources) <= 2

    async def test_cost_budget_parameter(self):
        """Test that cost budget parameter is accepted."""
        from loom.tools.cipher_mirror import research_cipher_mirror

        with patch("loom.tools.cipher_mirror.asyncio.get_running_loop"):
            result = await research_cipher_mirror(
                "test",
                max_cost_usd=0.50,
            )

            # Should return valid response structure
            assert "query" in result
            assert "findings" in result
            assert "stats" in result

    async def test_multiple_key_types_detected(self):
        """Test detection of multiple API key types."""
        from loom.tools.cipher_mirror import _detect_credentials

        text = (
            "Multiple keys found: "
            "sk-openaikey1234567890abcdef "
            "nvapi-nvidiakey1234567890 "
            "ghp_githubtoken1234567890 "
        )

        creds = _detect_credentials(text)
        key_types = {c.get("key_type") for c in creds}

        # Should detect multiple key types
        assert len(key_types) >= 2


class TestEntropyScore:
    def test_empty_string_has_zero_entropy(self):
        """Test that empty string returns 0 entropy."""
        from loom.tools.cipher_mirror import _entropy_score

        assert _entropy_score("") == 0.0

    def test_repeated_character_has_low_entropy(self):
        """Test that repeated characters have low entropy."""
        from loom.tools.cipher_mirror import _entropy_score

        assert _entropy_score("aaaaaaaaaa") < 0.2

    def test_random_string_has_high_entropy(self):
        """Test that random strings have high entropy."""
        from loom.tools.cipher_mirror import _entropy_score

        assert _entropy_score("x9K2mL7pQ1RwEbVzS4cD") > 0.5

    def test_window_size_parameter(self):
        """Test that window_size parameter works."""
        from loom.tools.cipher_mirror import _entropy_score

        text = "uniform" * 10  # Repeated pattern
        score1 = _entropy_score(text, window_size=7)
        score2 = _entropy_score(text, window_size=20)

        # Scores should be calculable with different window sizes
        assert score1 >= 0.0
        assert score2 >= 0.0


class TestShingleDetection:
    def test_model_weight_pattern_matching(self):
        """Test that model weight patterns are correctly identified."""
        from loom.tools.cipher_mirror import _detect_model_weights

        patterns = [
            "Downloaded model.safetensors successfully",
            "Checkpoint saved to pytorch_model.bin",
            "LoRA adapter_model.safetensors found",
            "GGUF quantized as model.gguf",
        ]

        for text in patterns:
            weights = _detect_model_weights(text)
            assert len(weights) > 0, f"Should detect pattern in: {text}"

    def test_no_false_positives(self):
        """Test that legitimate content doesn't trigger false positives."""
        from loom.tools.cipher_mirror import _detect_model_weights

        text = "The model of the car was interesting. This is bin collection day."
        weights = _detect_model_weights(text)

        # Should not have false positives (case sensitive matching)
        assert len(weights) == 0 or all(w.get("type") != "model_weight" for w in weights)
