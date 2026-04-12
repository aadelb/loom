"""Unit tests for loom.providers.base — cost estimation and LLMResponse."""

from __future__ import annotations

import pytest

from loom.providers.base import LLMResponse, _estimate_cost


class TestEstimateCost:
    """_estimate_cost returns sensible values for known and unknown providers."""

    def test_nvidia_is_free(self) -> None:
        """NVIDIA NIM free tier always returns 0."""
        assert _estimate_cost("nvidia", "meta/llama-3.1-8b-instruct", 1000, 500) == 0.0

    def test_vllm_is_free(self) -> None:
        """Local vLLM is always free."""
        assert _estimate_cost("vllm", "mimo_v2_flash", 5000, 2000) == 0.0

    def test_openai_positive_cost(self) -> None:
        """OpenAI has a positive cost estimate."""
        cost = _estimate_cost("openai", "gpt-5-mini", 1000, 500)
        assert cost > 0.0
        assert cost < 1.0  # sanity: 1500 tokens shouldn't cost $1+

    def test_anthropic_positive_cost(self) -> None:
        """Anthropic has a positive cost estimate."""
        cost = _estimate_cost("anthropic", "claude-opus-4-6", 1000, 500)
        assert cost > 0.0

    def test_unknown_provider_returns_zero(self) -> None:
        """Unknown providers return 0 (safe fallback, not crash)."""
        assert _estimate_cost("unknown_provider", "unknown_model", 1000, 500) == 0.0

    def test_zero_tokens_zero_cost(self) -> None:
        """Zero tokens → zero cost for all providers."""
        assert _estimate_cost("openai", "gpt-5-mini", 0, 0) == 0.0
        assert _estimate_cost("anthropic", "claude-opus-4-6", 0, 0) == 0.0


class TestLLMResponse:
    """LLMResponse dataclass behaves correctly."""

    def test_fields_accessible(self) -> None:
        """All fields set and readable."""
        r = LLMResponse(
            text="hello",
            model="test-model",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=200,
            provider="nvidia",
            finish_reason="stop",
        )
        assert r.text == "hello"
        assert r.model == "test-model"
        assert r.provider == "nvidia"
        assert r.cost_usd == 0.001
        assert r.latency_ms == 200
        assert r.finish_reason == "stop"

    def test_finish_reason_optional(self) -> None:
        """finish_reason defaults to None when not provided."""
        r = LLMResponse(
            text="hi",
            model="m",
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.0,
            latency_ms=10,
            provider="test",
        )
        assert r.finish_reason is None
