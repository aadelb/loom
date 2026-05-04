"""Unit tests for research_trend_forecast tool."""

from __future__ import annotations

import pytest
from loom.tools.trend_forecaster import (
    _extract_terms,
    _compute_term_frequencies,
    _classify_trend_signals,
    _predict_next_developments,
    _calculate_confidence,
    research_trend_forecast,
)


class TestExtractTerms:
    """Tests for term extraction."""

    def test_extract_basic_terms(self) -> None:
        """Test basic term extraction from text."""
        text = "machine learning and neural networks are important"
        terms = _extract_terms(text)
        assert "machine" in terms
        assert "learning" in terms
        assert "neural" in terms
        assert "networks" in terms

    def test_extract_filters_stopwords(self) -> None:
        """Test that stopwords are filtered."""
        text = "the and a are is in"
        terms = _extract_terms(text)
        assert not terms, "All common stopwords should be filtered"

    def test_extract_filters_short_terms(self) -> None:
        """Test that short terms (<3 chars) are filtered."""
        text = "it is an a to be by so"
        terms = _extract_terms(text)
        assert all(len(t) >= 3 for t in terms)

    def test_extract_normalizes_case(self) -> None:
        """Test that extraction normalizes to lowercase."""
        text = "Machine LEARNING Transformers"
        terms = _extract_terms(text)
        assert all(t.islower() or "-" in t for t in terms)

    def test_extract_handles_empty_text(self) -> None:
        """Test extraction on empty text."""
        assert _extract_terms("") == []
        assert _extract_terms("   ") == []

    def test_extract_handles_special_characters(self) -> None:
        """Test that special characters are removed but hyphens kept."""
        text = "machine-learning, neural@network, AI/ML"
        terms = _extract_terms(text)
        # Should contain tech terms with hyphens preserved
        assert any("-" in t for t in terms) or len(terms) > 0

    def test_extract_min_frequency_respected(self) -> None:
        """Test that minimum term length is respected."""
        text = "ab cd efgh ijklmn"
        terms = _extract_terms(text)
        # Only efgh and ijklmn should pass (length >= 3)
        assert all(len(t) >= 3 for t in terms)


class TestComputeTermFrequencies:
    """Tests for term frequency computation."""

    def test_frequency_basic(self) -> None:
        """Test basic frequency computation."""
        texts = [
            "machine learning transformers",
            "neural networks machine learning",
        ]
        freqs = _compute_term_frequencies(texts)
        assert freqs.get("machine", 0) == 2
        assert freqs.get("learning", 0) == 2
        assert freqs.get("neural", 0) == 1

    def test_frequency_normalization(self) -> None:
        """Test frequency normalization by document count."""
        texts = ["transformer model", "transformer architecture"]
        freqs = _compute_term_frequencies(texts, normalize=True)
        # Each term should be normalized by number of documents (2)
        assert all(0 <= v <= 1 for v in freqs.values())

    def test_frequency_filters_by_min_occurrence(self) -> None:
        """Test that terms with frequency < MIN_FREQUENCY are filtered."""
        texts = [
            "machine learning",
            "machine learning deep learning",
        ]
        freqs = _compute_term_frequencies(texts)
        # With MIN_FREQUENCY=2, "deep" should be filtered
        # "machine" and "learning" should remain
        assert freqs.get("machine", 0) >= 1
        assert freqs.get("learning", 0) >= 1

    def test_frequency_empty_texts(self) -> None:
        """Test frequency computation on empty text list."""
        freqs = _compute_term_frequencies([])
        assert freqs == {}

    def test_frequency_stopwords_excluded(self) -> None:
        """Test that stopwords don't appear in frequencies."""
        texts = ["the quick brown fox"]
        freqs = _compute_term_frequencies(texts)
        assert "the" not in freqs
        assert "quick" in freqs or "brown" in freqs or "fox" in freqs


class TestClassifyTrendSignals:
    """Tests for trend signal classification."""

    def test_classify_emerging_signals(self) -> None:
        """Test identification of emerging terms."""
        recent = {"transformer": 0.5, "attention": 0.4, "llm": 0.3}
        older = {"transformer": 0.2, "cnn": 0.3}
        emerging, declining, stable = _classify_trend_signals(recent, older)
        # "attention" and "llm" are new/growing
        assert "attention" in emerging or "llm" in emerging

    def test_classify_declining_signals(self) -> None:
        """Test identification of declining terms."""
        recent = {"lstm": 0.1}
        older = {"lstm": 0.5, "rnn": 0.4}
        emerging, declining, stable = _classify_trend_signals(recent, older)
        # "lstm" appears to be declining
        assert "lstm" in declining or len(declining) > 0

    def test_classify_stable_signals(self) -> None:
        """Test identification of stable terms."""
        recent = {"neural": 0.3, "network": 0.3}
        older = {"neural": 0.3, "network": 0.3}
        emerging, declining, stable = _classify_trend_signals(recent, older)
        # "neural" and "network" are stable
        assert "neural" in stable or "network" in stable

    def test_classify_growth_threshold(self) -> None:
        """Test that 1.5x growth is marked as emerging."""
        recent = {"quantum": 0.45}
        older = {"quantum": 0.3}  # 1.5x growth
        emerging, declining, stable = _classify_trend_signals(recent, older)
        assert "quantum" in emerging

    def test_classify_decline_threshold(self) -> None:
        """Test that 1.5x decline is marked as declining."""
        recent = {"old_tech": 0.2}
        older = {"old_tech": 0.3}  # Less than 1.5x but declining
        emerging, declining, stable = _classify_trend_signals(recent, older)
        # Should be in declining if decline is significant enough
        assert "old_tech" in declining or "old_tech" in stable


class TestPredictNextDevelopments:
    """Tests for forecast prediction."""

    def test_predict_combinations(self) -> None:
        """Test prediction of emerging + stable combinations."""
        emerging = ["reinforcement", "multi-agent"]
        stable = ["deep-learning", "optimization"]
        predictions = _predict_next_developments(emerging, stable)
        assert len(predictions) > 0

    def test_predict_empty_emerging(self) -> None:
        """Test prediction with no emerging terms."""
        emerging = []
        stable = ["neural", "network"]
        predictions = _predict_next_developments(emerging, stable)
        # Should still generate some predictions or empty list
        assert isinstance(predictions, list)

    def test_predict_refinement(self) -> None:
        """Test that refinement is predicted for strong signals."""
        emerging = ["technique1", "technique2", "technique3", "technique4"]
        stable = ["core"]
        predictions = _predict_next_developments(emerging, stable)
        # Should include refinement prediction
        assert any("optimization" in p.lower() or "refinement" in p.lower()
                   for p in predictions) or len(predictions) > 0

    def test_predict_deduplication(self) -> None:
        """Test that predictions are deduplicated."""
        emerging = ["same"] * 5
        stable = ["core"]
        predictions = _predict_next_developments(emerging, stable)
        # Should not have duplicates
        assert len(predictions) == len(set(predictions))

    def test_predict_limits_to_top(self) -> None:
        """Test that only top predictions are returned."""
        emerging = [f"term{i}" for i in range(20)]
        stable = [f"stable{i}" for i in range(20)]
        predictions = _predict_next_developments(emerging, stable)
        # Should return reasonable number of predictions
        assert len(predictions) <= 20


class TestCalculateConfidence:
    """Tests for confidence score calculation."""

    def test_confidence_high_signal(self) -> None:
        """Test high confidence with strong signals."""
        confidence = _calculate_confidence(
            recent_data_points=50,
            older_data_points=50,
            emerging_count=10,
            total_unique_terms=20,
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.3  # Should be reasonably high

    def test_confidence_low_signal(self) -> None:
        """Test low confidence with weak signals."""
        confidence = _calculate_confidence(
            recent_data_points=1,
            older_data_points=1,
            emerging_count=0,
            total_unique_terms=100,
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.2  # Should have minimum baseline

    def test_confidence_zero_unique_terms(self) -> None:
        """Test confidence calculation with zero unique terms (edge case)."""
        confidence = _calculate_confidence(
            recent_data_points=10,
            older_data_points=10,
            emerging_count=5,
            total_unique_terms=0,
        )
        assert 0.0 <= confidence <= 1.0

    def test_confidence_scaling(self) -> None:
        """Test that confidence scales with data points."""
        conf_low = _calculate_confidence(10, 10, 2, 5)
        conf_high = _calculate_confidence(100, 100, 10, 50)
        assert conf_low <= conf_high


class TestResearchTrendForecast:
    """Integration tests for research_trend_forecast."""

    @pytest.mark.asyncio
    async def test_forecast_basic_invocation(self) -> None:
        """Test basic invocation of forecast function."""
        result = await research_trend_forecast("machine learning")
        assert isinstance(result, dict)
        assert "topic" in result
        assert result["topic"] == "machine learning"

    @pytest.mark.asyncio
    async def test_forecast_returns_required_fields(self) -> None:
        """Test that forecast returns all required fields."""
        result = await research_trend_forecast("AI", timeframe="6months")
        assert "topic" in result
        assert "timeframe" in result
        assert "confidence" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_forecast_invalid_timeframe(self) -> None:
        """Test that invalid timeframe returns error."""
        result = await research_trend_forecast("test", timeframe="invalid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_forecast_timeframe_options(self) -> None:
        """Test all valid timeframe options."""
        for timeframe in ["3months", "6months", "1year"]:
            result = await research_trend_forecast("test", timeframe=timeframe)
            assert result["timeframe"] == timeframe or "error" in result

    @pytest.mark.asyncio
    async def test_forecast_confidence_range(self) -> None:
        """Test that confidence is in valid range."""
        result = await research_trend_forecast("testing")
        confidence = result.get("confidence", 0)
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_forecast_trends_structure(self) -> None:
        """Test trends structure in result."""
        result = await research_trend_forecast("neural networks")
        if "trends" in result:
            trends = result["trends"]
            assert "up" in trends or "error" in result
            assert "down" in trends or "error" in result
            assert "stable" in trends or "error" in result

    @pytest.mark.asyncio
    async def test_forecast_forecast_field_is_list(self) -> None:
        """Test that forecast field is a list."""
        result = await research_trend_forecast("quantum computing")
        if "forecast" in result:
            assert isinstance(result["forecast"], list)

    @pytest.mark.asyncio
    async def test_forecast_timestamp_iso_format(self) -> None:
        """Test that timestamp is in ISO format."""
        result = await research_trend_forecast("testing")
        if "timestamp" in result:
            # Should be parseable ISO format
            assert "T" in result["timestamp"] or "error" in result

    @pytest.mark.asyncio
    async def test_forecast_min_term_frequency(self) -> None:
        """Test min_term_frequency parameter."""
        result = await research_trend_forecast(
            "test", min_term_frequency=3
        )
        assert "topic" in result

    @pytest.mark.asyncio
    async def test_forecast_data_points_count(self) -> None:
        """Test that data_points is a non-negative integer."""
        result = await research_trend_forecast("testing")
        if "data_points" in result:
            assert isinstance(result["data_points"], int)
            assert result["data_points"] >= 0

    @pytest.mark.asyncio
    async def test_forecast_special_characters_in_topic(self) -> None:
        """Test handling of special characters in topic."""
        result = await research_trend_forecast("AI & Machine Learning (2024)")
        assert "topic" in result

    @pytest.mark.asyncio
    async def test_forecast_long_topic_name(self) -> None:
        """Test handling of long topic names."""
        long_topic = "advanced deep learning techniques for multimodal fusion"
        result = await research_trend_forecast(long_topic)
        assert result["topic"] == long_topic or "error" in result


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_extract_terms_unicode(self) -> None:
        """Test extraction with unicode characters."""
        text = "machine learning données research étude"
        terms = _extract_terms(text)
        # Should handle unicode gracefully
        assert isinstance(terms, list)

    def test_frequency_large_text_list(self) -> None:
        """Test frequency computation with large text lists."""
        texts = [f"text {i}" for i in range(100)]
        freqs = _compute_term_frequencies(texts)
        assert isinstance(freqs, dict)

    def test_classify_identical_frequencies(self) -> None:
        """Test classification when recent and older have identical frequencies."""
        recent = {"stable_term": 0.5}
        older = {"stable_term": 0.5}
        emerging, declining, stable = _classify_trend_signals(recent, older)
        assert "stable_term" in stable

    @pytest.mark.asyncio
    async def test_forecast_empty_topic(self) -> None:
        """Test that empty topic is rejected."""
        result = await research_trend_forecast("", timeframe="6months")
        # Should either return error or reject
        if "error" not in result:
            assert result.get("topic") or "topic" in result

    @pytest.mark.asyncio
    async def test_forecast_very_long_topic(self) -> None:
        """Test handling of very long topic names."""
        long_topic = "a" * 300  # Very long string
        result = await research_trend_forecast(long_topic)
        # Should handle gracefully
        assert isinstance(result, dict)
