"""Unit tests for Arabic language support module.

Tests cover detection, routing, RTL handling, caching, and JSON serialization.
All tests must pass with 100% coverage of arabic.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom.arabic import (
    detect_arabic,
    get_arabic_preferred_providers,
    is_rtl_text,
    route_by_language,
)



pytestmark = pytest.mark.asyncio
class TestDetectArabic:
    """Tests for detect_arabic() function — 5 test cases."""

    async def test_detect_arabic_true_standard(self) -> None:
        """Detect standard Arabic text."""
        text = "كيف أصبح غنياً"
        assert detect_arabic(text) is True

    async def test_detect_arabic_false_english(self) -> None:
        """Return False for English text."""
        text = "how to be rich"
        assert detect_arabic(text) is False

    async def test_detect_arabic_mixed_english_arabic(self) -> None:
        """Detect Arabic in mixed English-Arabic text."""
        text = "Hello مرحبا world"
        assert detect_arabic(text) is True

    async def test_detect_arabic_empty_string(self) -> None:
        """Return False for empty string."""
        text = ""
        assert detect_arabic(text) is False

    async def test_detect_arabic_long_arabic_text(self) -> None:
        """Detect Arabic in longer text."""
        text = "أهلا وسهلا بك في عالم اللغة العربية والتعليم الحديث"
        assert detect_arabic(text) is True


class TestGetArabicPreferredProviders:
    """Tests for get_arabic_preferred_providers() function."""

    async def test_get_providers_returns_list(self) -> None:
        """Return a list of providers."""
        providers = get_arabic_preferred_providers()
        assert isinstance(providers, list)

    async def test_get_providers_order(self) -> None:
        """Return providers in correct priority order."""
        providers = get_arabic_preferred_providers()
        assert providers == ["qwen", "gemini", "kimi", "deepseek"]

    async def test_get_providers_immutable(self) -> None:
        """Return copy to prevent external mutation."""
        providers1 = get_arabic_preferred_providers()
        providers1.append("invalid")
        providers2 = get_arabic_preferred_providers()
        assert providers2 == ["qwen", "gemini", "kimi", "deepseek"]


class TestRouteByLanguage:
    """Tests for route_by_language() function — 8 test cases."""

    async def test_route_arabic_reorders_providers(self) -> None:
        """Reorder cascade to put Arabic-capable providers first."""
        text = "كيف أصبح غنياً"
        default_cascade = ["groq", "gemini", "openai", "anthropic"]
        result = route_by_language(text, default_cascade)

        # gemini should be first (Arabic-capable), others in original order
        assert result == ["gemini", "groq", "openai", "anthropic"]

    async def test_route_english_unchanged(self) -> None:
        """Keep cascade unchanged for English text."""
        text = "how to be rich"
        default_cascade = ["groq", "gemini", "openai", "anthropic"]
        result = route_by_language(text, default_cascade)

        assert result == default_cascade

    async def test_route_arabic_multiple_providers(self) -> None:
        """Handle multiple Arabic providers in cascade."""
        text = "مرحبا بك"
        default_cascade = ["groq", "qwen", "gemini", "openai", "deepseek"]
        result = route_by_language(text, default_cascade)

        # All Arabic-capable to front in their order
        assert result == ["qwen", "gemini", "deepseek", "groq", "openai"]

    async def test_route_arabic_no_overlap(self) -> None:
        """Handle case with no Arabic-capable providers in cascade."""
        text = "السلام عليكم"
        default_cascade = ["groq", "openai", "anthropic"]
        result = route_by_language(text, default_cascade)

        # Should return unchanged since no Arabic providers available
        assert result == ["groq", "openai", "anthropic"]

    async def test_route_mixed_text_with_arabic(self) -> None:
        """Route mixed English-Arabic text to Arabic providers."""
        text = "Hello مرحبا world"
        default_cascade = ["groq", "kimi", "openai"]
        result = route_by_language(text, default_cascade)

        # kimi (Arabic-capable) should be first
        assert result == ["kimi", "groq", "openai"]

    async def test_route_empty_text(self) -> None:
        """Handle empty text gracefully."""
        text = ""
        default_cascade = ["groq", "gemini", "openai"]
        result = route_by_language(text, default_cascade)

        assert result == default_cascade

    async def test_route_empty_cascade(self) -> None:
        """Handle empty cascade gracefully."""
        text = "مرحبا"
        default_cascade = []
        result = route_by_language(text, default_cascade)

        assert result == []

    async def test_route_single_provider(self) -> None:
        """Handle single provider cascade."""
        text = "كيف حالك"
        default_cascade = ["gemini"]
        result = route_by_language(text, default_cascade)

        assert result == ["gemini"]


class TestIsRtlText:
    """Tests for is_rtl_text() function."""

    async def test_is_rtl_arabic_true(self) -> None:
        """Identify Arabic as RTL."""
        text = "مرحبا بك"
        assert is_rtl_text(text) is True

    async def test_is_rtl_english_false(self) -> None:
        """Identify English as LTR (not RTL)."""
        text = "hello world"
        assert is_rtl_text(text) is False

    async def test_is_rtl_mixed_arabic_english(self) -> None:
        """Identify mixed text with Arabic as RTL."""
        text = "Hello مرحبا"
        assert is_rtl_text(text) is True

    async def test_is_rtl_empty_string(self) -> None:
        """Return False for empty string."""
        text = ""
        assert is_rtl_text(text) is False


class TestArabicUnicodeRanges:
    """Tests for various Arabic Unicode blocks coverage."""

    async def test_arabic_main_block(self) -> None:
        """Detect Arabic main block (U+0600–U+06FF)."""
        # Sample from main block
        text = "ء ب ج د ه و ز"  # Arabic letters
        assert detect_arabic(text) is True

    async def test_arabic_supplement_block(self) -> None:
        """Detect Arabic Supplement block (U+0750–U+077F)."""
        # Sample from supplement block (if available)
        text = "ݐݑݒ"  # Supplement block characters
        assert detect_arabic(text) is True

    async def test_arabic_extended_a_block(self) -> None:
        """Detect Arabic Extended-A block (U+08A0–U+08FF)."""
        # Sample from extended-A block
        text = "ࢡࢢࢣ"  # Extended-A characters
        assert detect_arabic(text) is True


class TestArabicCaching:
    """Tests for Arabic text in caching scenarios."""

    async def test_arabic_cache_key_generation(self) -> None:
        """Arabic text produces valid cache key via SHA-256."""
        from hashlib import sha256

        text = "كيف أصبح غنياً"
        # Should not raise on encoding
        hash_key = sha256(text.encode("utf-8")).hexdigest()
        assert isinstance(hash_key, str)
        assert len(hash_key) == 64

    async def test_arabic_cache_roundtrip(self, tmp_path: Path) -> None:
        """Store and retrieve Arabic text from cache without corruption."""
        text = "السلام عليكم ورحمة الله وبركاته"
        cache_file = tmp_path / "test_arabic_cache.json"

        # Write to file
        data = {"text": text, "language": "ar"}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        # Read back
        with open(cache_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert loaded_data["text"] == text
        assert loaded_data["language"] == "ar"


class TestArabicJsonSerialization:
    """Tests for JSON serialization of Arabic text."""

    async def test_arabic_json_ensure_ascii_false(self) -> None:
        """JSON serialization with ensure_ascii=False preserves Arabic."""
        data = {"query": "كيف أصبح غنياً", "language": "ar"}
        json_str = json.dumps(data, ensure_ascii=False)

        # Should contain Arabic characters directly, not escape sequences
        assert "كيف" in json_str

    async def test_arabic_json_roundtrip(self) -> None:
        """Arabic text survives JSON dumps/loads cycle."""
        original_text = "مرحبا بك في عالم البحث الذكي"
        data = {"text": original_text}

        # Serialize with ensure_ascii=False
        json_str = json.dumps(data, ensure_ascii=False)

        # Deserialize
        loaded = json.loads(json_str)
        assert loaded["text"] == original_text

    async def test_arabic_json_ensure_ascii_true_roundtrip(self) -> None:
        """Arabic text survives JSON with ensure_ascii=True via escape sequences."""
        original_text = "مرحبا بك"
        data = {"text": original_text}

        # Serialize with ensure_ascii=True (uses escape sequences)
        json_str = json.dumps(data, ensure_ascii=True)

        # Deserialize
        loaded = json.loads(json_str)
        assert loaded["text"] == original_text


class TestArabicEdgeCases:
    """Tests for edge cases and special scenarios."""

    async def test_detect_arabic_with_numbers(self) -> None:
        """Detect Arabic text mixed with Western numerals."""
        text = "السعر 100 درهم"
        assert detect_arabic(text) is True

    async def test_detect_arabic_with_punctuation(self) -> None:
        """Detect Arabic text with punctuation."""
        text = "كيف أصبح غنياً؟ والعملات الرقمية؟"
        assert detect_arabic(text) is True

    async def test_detect_arabic_single_character(self) -> None:
        """Detect single Arabic character."""
        text = "ع"
        assert detect_arabic(text) is True

    async def test_route_preserves_order_non_arabic(self) -> None:
        """Preserve exact order of non-Arabic providers."""
        text = "hello"
        default_cascade = ["deepseek", "anthropic", "openai", "groq"]
        result = route_by_language(text, default_cascade)

        assert result == default_cascade

    async def test_route_prioritizes_by_arabic_ranking(self) -> None:
        """Prioritize Arabic providers by their ranking, not cascade order."""
        text = "مرحبا"
        # deepseek and gemini are Arabic-capable; gemini has higher ranking
        default_cascade = ["groq", "deepseek", "openai", "gemini", "anthropic"]
        result = route_by_language(text, default_cascade)

        # gemini comes before deepseek in _ARABIC_PROVIDERS priority order
        expected = ["gemini", "deepseek", "groq", "openai", "anthropic"]
        assert result == expected


class TestArabicIntegration:
    """Integration tests combining multiple functions."""

    async def test_detect_and_route_workflow(self) -> None:
        """Complete workflow: detect then route."""
        text = "كيف يمكنني تحسين مهاراتي في البرمجة؟"
        cascade = ["groq", "openai", "gemini", "anthropic"]

        # Check detection
        is_arabic = detect_arabic(text)
        assert is_arabic is True

        # Check routing
        routed = route_by_language(text, cascade)
        assert routed[0] == "gemini"

    async def test_english_and_route_workflow(self) -> None:
        """Complete workflow with English text."""
        text = "How can I improve my programming skills?"
        cascade = ["groq", "openai", "gemini", "anthropic"]

        # Check detection
        is_arabic = detect_arabic(text)
        assert is_arabic is False

        # Check routing (should be unchanged)
        routed = route_by_language(text, cascade)
        assert routed == cascade
