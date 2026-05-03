"""Unit tests for research_onion_spectra — .onion site classification."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.onion_spectra import (
    research_onion_spectra,
    _detect_language,
    _classify_safety,
)


class TestOnionSpectra:
    """research_onion_spectra classifies .onion content by language and safety."""

    @pytest.mark.asyncio
    async def test_onion_spectra_invalid_url(self) -> None:
        """Tool rejects non-.onion URLs."""
        result = await research_onion_spectra(url="https://example.com")

        assert result["error"] is not None
        assert "onion address" in result["error"].lower()
        assert result["category"] == "suspicious"

    @pytest.mark.asyncio
    async def test_onion_spectra_valid_onion_no_fetch(self) -> None:
        """Tool accepts valid .onion URL without fetching content."""
        result = await research_onion_spectra(
            url="http://example.onion", fetch_content=False
        )

        assert "error" not in result or result.get("error") is None
        assert result["url"] == "http://example.onion"
        assert "category" in result
        assert "language" in result

    @pytest.mark.asyncio
    async def test_onion_spectra_with_content_fetch(self) -> None:
        """Tool fetches and analyzes content from .onion URL."""
        with patch("loom.tools.onion_spectra.research_fetch") as mock_fetch:
            mock_fetch.return_value = {
                "content": "This is a benign informational site about privacy",
                "title": "Privacy Guide",
                "html": "<html>content</html>",
            }

            with patch(
                "loom.tools.onion_spectra.research_llm_classify",
                new_callable=AsyncMock,
            ) as mock_classify:
                # Mock language detection
                mock_classify.side_effect = [
                    {
                        "classification": {
                            "label": "en",
                            "confidence": 0.95,
                        }
                    },
                    # Mock safety classification
                    {
                        "classification": {
                            "label": "benign",
                            "confidence": 0.85,
                        }
                    },
                ]

                result = await research_onion_spectra(
                    url="http://example.onion", fetch_content=True, max_chars=5000
                )

                assert result["url"] == "http://example.onion"
                assert result["language"]["code"] == "en"
                assert result["category"] == "benign"
                assert result["confidence"] == 0.85
                assert "summary" in result

    @pytest.mark.asyncio
    async def test_onion_spectra_fetch_failure_handled(self) -> None:
        """Tool handles fetch failures gracefully."""
        with patch("loom.tools.onion_spectra.research_fetch") as mock_fetch:
            mock_fetch.side_effect = Exception("Connection timeout")

            result = await research_onion_spectra(
                url="http://example.onion", fetch_content=True
            )

            assert "error" in result
            assert "Failed to fetch page" in result["error"]
            assert result["category"] == "suspicious"
            assert result["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_detect_language_heuristic_chinese(self) -> None:
        """Language detection uses character heuristic for Chinese."""
        text = "这是中文文本 This is mixed Chinese"

        result = await _detect_language(text)

        assert result["language_code"] == "zh"
        assert result["language_name"] == "Chinese"
        assert 0 <= result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_detect_language_heuristic_arabic(self) -> None:
        """Language detection uses character heuristic for Arabic."""
        text = "هذا نص عربي مثال"

        result = await _detect_language(text)

        assert result["language_code"] == "ar"
        assert result["language_name"] == "Arabic"

    @pytest.mark.asyncio
    async def test_detect_language_heuristic_russian(self) -> None:
        """Language detection uses character heuristic for Russian."""
        text = "Это русский текст образец"

        result = await _detect_language(text)

        assert result["language_code"] == "ru"
        assert result["language_name"] == "Russian"

    @pytest.mark.asyncio
    async def test_detect_language_llm_fallback(self) -> None:
        """Language detection falls back to English on LLM unavailable."""
        with patch(
            "loom.tools.onion_spectra.research_llm_classify", None
        ) as mock_classify:
            result = await _detect_language("Some random text")

            # Should fall back to English (no heuristic match)
            assert result["language_code"] == "en"

    @pytest.mark.asyncio
    async def test_classify_safety_benign(self) -> None:
        """Safety classification identifies benign content."""
        with patch(
            "loom.tools.onion_spectra.research_llm_classify",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = {
                "classification": {
                    "label": "benign",
                    "confidence": 0.9,
                }
            }

            result = await _classify_safety(
                title="Public Library", content="Books and resources for the public"
            )

            assert result["category"] == "benign"
            assert result["confidence"] == 0.9
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_classify_safety_illegal(self) -> None:
        """Safety classification flags illegal content."""
        with patch(
            "loom.tools.onion_spectra.research_llm_classify",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = {
                "classification": {
                    "label": "illegal",
                    "confidence": 0.95,
                }
            }

            result = await _classify_safety(
                title="Underground Market",
                content="Buy illegal drugs weapons stolen goods",
            )

            assert result["category"] == "illegal"
            assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_classify_safety_llm_unavailable(self) -> None:
        """Safety classification falls back on LLM unavailable."""
        with patch("loom.tools.onion_spectra.research_llm_classify", None):
            result = await _classify_safety(
                title="Test Site", content="Some content here"
            )

            assert result["category"] == "suspicious"
            assert result["confidence"] == 0.5
            assert "LLM unavailable" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_onion_spectra_max_chars_respected(self) -> None:
        """Tool respects max_chars limit for content analysis."""
        with patch("loom.tools.onion_spectra.research_fetch") as mock_fetch:
            # Create content longer than max_chars
            long_content = "x" * 10000
            mock_fetch.return_value = {
                "content": long_content,
                "title": "Test",
                "html": "<html></html>",
            }

            with patch(
                "loom.tools.onion_spectra.research_llm_classify",
                new_callable=AsyncMock,
            ) as mock_classify:
                mock_classify.side_effect = [
                    {"classification": {"label": "en", "confidence": 0.5}},
                    {"classification": {"label": "benign", "confidence": 0.5}},
                ]

                result = await research_onion_spectra(
                    url="http://example.onion", fetch_content=True, max_chars=1000
                )

                # Content passed to LLM should be capped
                assert len(result.get("content_preview", "")) <= 1000

    @pytest.mark.asyncio
    async def test_onion_spectra_summary_format(self) -> None:
        """Tool generates properly formatted summary."""
        with patch("loom.tools.onion_spectra.research_fetch") as mock_fetch:
            mock_fetch.return_value = {
                "content": "Test content",
                "title": "Test Title",
                "html": "<html></html>",
            }

            with patch(
                "loom.tools.onion_spectra.research_llm_classify",
                new_callable=AsyncMock,
            ) as mock_classify:
                mock_classify.side_effect = [
                    {"classification": {"label": "en", "confidence": 0.8}},
                    {"classification": {"label": "harmful", "confidence": 0.75}},
                ]

                result = await research_onion_spectra(url="http://example.onion")

                assert "summary" in result
                assert "harmful" in result["summary"].lower()
                assert "English" in result["summary"] or "en" in result["summary"]
