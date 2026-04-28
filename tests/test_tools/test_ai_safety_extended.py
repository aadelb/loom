"""Unit tests for AI safety extended tools — hallucination benchmarking and adversarial robustness."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.ai_safety_extended import (
    _encode_rot13,
    _unicode_confusables,
    research_adversarial_robustness,
    research_hallucination_benchmark,
)


class TestEncodeRot13:
    """ROT13 encoding utility tests."""

    def test_encode_lowercase(self) -> None:
        """ROT13 encodes lowercase letters correctly."""
        assert _encode_rot13("hello") == "uryyb"
        assert _encode_rot13("abc") == "nop"

    def test_encode_uppercase(self) -> None:
        """ROT13 encodes uppercase letters correctly."""
        assert _encode_rot13("HELLO") == "URYYB"
        assert _encode_rot13("ABC") == "NOP"

    def test_encode_mixed_case(self) -> None:
        """ROT13 preserves case for mixed text."""
        assert _encode_rot13("Hello") == "Uryyb"

    def test_encode_non_alphabetic(self) -> None:
        """ROT13 leaves non-alphabetic chars unchanged."""
        assert _encode_rot13("hello123") == "uryyb123"
        assert _encode_rot13("a!b@c#") == "n!o@p#"

    def test_encode_empty_string(self) -> None:
        """ROT13 handles empty string."""
        assert _encode_rot13("") == ""


class TestUnicodeConfusables:
    """Unicode confusables utility tests."""

    def test_confusable_lowercase_letters(self) -> None:
        """Unicode confusables replace lowercase letters."""
        result = _unicode_confusables("abc")
        # Should contain Greek letters or confusables
        assert result != "abc"
        assert len(result) == 3

    def test_confusable_mixed_input(self) -> None:
        """Unicode confusables handle mixed case input."""
        result = _unicode_confusables("SELECT FROM")
        # Should have replaced some characters
        assert len(result) > 0

    def test_confusable_numbers(self) -> None:
        """Unicode confusables can replace numbers."""
        result = _unicode_confusables("0123")
        assert len(result) == 4

    def test_confusable_preserves_length(self) -> None:
        """Unicode confusables output same length as input."""
        inputs = ["hello", "password", "admin"]
        for inp in inputs:
            result = _unicode_confusables(inp)
            assert len(result) == len(inp)


class TestHallucinationBenchmark:
    """research_hallucination_benchmark tests."""

    def test_hallucination_benchmark_default_facts(self) -> None:
        """Benchmark runs with default facts."""
        result = research_hallucination_benchmark(
            target_url="http://example.com/api"
        )

        assert result["target"] == "http://example.com/api"
        assert result["questions_asked"] == 10
        assert "correct" in result
        assert "hallucinated" in result
        assert "accuracy_rate" in result
        assert 0 <= result["accuracy_rate"] <= 1
        assert isinstance(result["hallucination_examples"], list)

    def test_hallucination_benchmark_custom_facts(self) -> None:
        """Benchmark accepts custom facts."""
        custom_facts = [
            {
                "question": "What is 2+2?",
                "expected": ["4"],
                "category": "math",
            },
        ]

        result = research_hallucination_benchmark(
            target_url="http://example.com/api", facts=custom_facts
        )

        assert result["questions_asked"] == 1
        assert "accuracy_rate" in result

    def test_hallucination_benchmark_empty_facts(self) -> None:
        """Benchmark handles empty facts list."""
        result = research_hallucination_benchmark(
            target_url="http://example.com/api", facts=[]
        )

        assert result["questions_asked"] == 0
        assert result["correct"] == 0
        assert result["hallucinated"] == 0
        assert result["accuracy_rate"] == 0.0

    def test_hallucination_benchmark_returns_required_fields(self) -> None:
        """Benchmark returns all required fields."""
        result = research_hallucination_benchmark(
            target_url="http://example.com/api"
        )

        required_fields = [
            "target",
            "questions_asked",
            "correct",
            "hallucinated",
            "accuracy_rate",
            "hallucination_examples",
        ]
        for field in required_fields:
            assert field in result

    def test_hallucination_benchmark_examples_structure(self) -> None:
        """Hallucination examples have correct structure."""
        custom_facts = [
            {
                "question": "Test?",
                "expected": ["answer"],
                "category": "test",
            },
        ]

        result = research_hallucination_benchmark(
            target_url="http://example.com/api", facts=custom_facts
        )

        examples = result["hallucination_examples"]
        for example in examples:
            assert "question" in example
            assert "expected" in example
            assert "actual" in example
            assert "category" in example


class TestAdversarialRobustness:
    """research_adversarial_robustness tests."""

    def test_adversarial_robustness_default_test_count(self) -> None:
        """Robustness test runs with default 5 tests."""
        result = research_adversarial_robustness(
            target_url="http://example.com/api"
        )

        assert result["target"] == "http://example.com/api"
        assert result["tests_run"] >= 0
        assert result["tests_run"] <= 5
        assert 0 <= result["robustness_score"] <= 1
        assert isinstance(result["failures"], list)

    def test_adversarial_robustness_custom_test_count(self) -> None:
        """Robustness test respects custom test count."""
        result = research_adversarial_robustness(
            target_url="http://example.com/api", test_count=3
        )

        assert result["tests_run"] <= 3

    def test_adversarial_robustness_max_test_count(self) -> None:
        """Robustness test caps test count at 20."""
        result = research_adversarial_robustness(
            target_url="http://example.com/api", test_count=100
        )

        assert result["tests_run"] <= 20

    def test_adversarial_robustness_min_test_count(self) -> None:
        """Robustness test minimum is 1."""
        result = research_adversarial_robustness(
            target_url="http://example.com/api", test_count=0
        )

        assert result["tests_run"] >= 1

    def test_adversarial_robustness_failure_structure(self) -> None:
        """Failures have correct structure."""
        result = research_adversarial_robustness(
            target_url="http://example.com/api", test_count=1
        )

        for failure in result["failures"]:
            assert "test_type" in failure
            assert "payload" in failure
            assert "error" in failure

    def test_adversarial_robustness_score_range(self) -> None:
        """Robustness score is between 0 and 1."""
        for i in range(5):
            result = research_adversarial_robustness(
                target_url="http://example.com/api", test_count=i + 1
            )

            assert 0 <= result["robustness_score"] <= 1

    def test_adversarial_robustness_returns_required_fields(self) -> None:
        """Robustness test returns all required fields."""
        result = research_adversarial_robustness(
            target_url="http://example.com/api"
        )

        required_fields = ["target", "tests_run", "failures", "robustness_score"]
        for field in required_fields:
            assert field in result

    def test_adversarial_robustness_with_mock_http(self) -> None:
        """Robustness test handles HTTP errors gracefully."""
        # Mock httpx.AsyncClient to return errors
        with patch(
            "loom.tools.ai_safety_extended.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client

            # Simulate HTTP 500 errors
            async def mock_get(*args, **kwargs):  # type: ignore
                resp = MagicMock()
                resp.status_code = 500
                return resp

            mock_client.get = mock_get

            mock_client_class.return_value = mock_client

            # Should still return a valid response
            result = research_adversarial_robustness(
                target_url="http://example.com/api", test_count=1
            )

            assert "target" in result
            assert "robustness_score" in result
