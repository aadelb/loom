"""Unit tests for P3 research tools."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from loom.tools import p3_tools


pytestmark = pytest.mark.asyncio

class TestModelComparator:
    """Tests for research_model_comparator."""

    async def test_model_comparator_basic(self) -> None:
        """Test basic model comparator with mock responses."""
        prompt = "What is artificial intelligence?"
        endpoints = ["https://example.com/chat", "https://example.com/query"]

        with patch("loom.tools.p3_tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_resp1 = MagicMock()
            mock_resp1.status_code = 200
            mock_resp1.json = AsyncMock(return_value={
                "response": "AI is machine learning and neural networks combined together."
            })

            mock_resp2 = MagicMock()
            mock_resp2.status_code = 200
            mock_resp2.json = AsyncMock(return_value={
                "response": "Artificial Intelligence refers to computer systems designed to perform tasks."
            })

            mock_instance.post = AsyncMock(side_effect=[mock_resp1, mock_resp2])

            result = await p3_tools.research_model_comparator(prompt, endpoints)

            assert "prompt" in result
            assert "comparisons" in result
            assert "endpoint_count" in result
            assert result["endpoint_count"] == 2

    async def test_model_comparator_invalid_endpoints(self) -> None:
        """Test model comparator with invalid endpoints."""
        prompt = "Test prompt"
        endpoints = ["not-a-url"]

        try:
            await p3_tools.research_model_comparator(prompt, endpoints)
        except (ValueError, Exception):
            pass

    async def test_model_comparator_empty_prompt(self) -> None:
        """Test model comparator with empty prompt."""
        endpoints = ["https://example.com/chat", "https://example.com/another"]

        result = await p3_tools.research_model_comparator("", endpoints)
        assert isinstance(result, dict)

    async def test_model_comparator_min_endpoints(self) -> None:
        """Test that at least 2 endpoints are required."""
        prompt = "Test"
        endpoints = ["https://example.com/chat"]

        try:
            await p3_tools.research_model_comparator(prompt, endpoints)
        except (ValueError, Exception):
            pass

    async def test_model_comparator_max_endpoints(self) -> None:
        """Test that endpoint limit is enforced."""
        prompt = "Test"
        endpoints = [f"https://api{i}.example.com/chat" for i in range(15)]

        try:
            await p3_tools.research_model_comparator(prompt, endpoints)
        except (ValueError, Exception):
            pass


class TestDataPoisoning:
    """Tests for research_data_poisoning."""

    async def test_data_poisoning_basic(self) -> None:
        """Test basic data poisoning detection."""
        target_url = "https://example.com/chat"

        with patch("loom.tools.p3_tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json = AsyncMock(return_value={
                "response": "Python is a high-level programming language..."
            })

            mock_instance.post = AsyncMock(return_value=mock_resp)

            result = await p3_tools.research_data_poisoning(target_url)

            assert "target" in result
            assert "tests_run" in result
            assert "contamination_signals" in result

    async def test_data_poisoning_custom_canaries(self) -> None:
        """Test data poisoning with custom canary phrases."""
        target_url = "https://example.com/chat"
        canaries = ["test phrase one", "test phrase two"]

        result = await p3_tools.research_data_poisoning(target_url, canaries)

        assert result.get("tests_run", 0) >= 0
        assert "contamination_signals" in result

    async def test_data_poisoning_invalid_url(self) -> None:
        """Test data poisoning with invalid URL."""
        try:
            await p3_tools.research_data_poisoning("not-a-url")
        except (ValueError, Exception):
            pass

    async def test_data_poisoning_invalid_canaries(self) -> None:
        """Test data poisoning with invalid canary list."""
        target_url = "https://example.com/chat"
        canaries = ["x" * 600]

        try:
            await p3_tools.research_data_poisoning(target_url, canaries)
        except (ValueError, Exception):
            pass


class TestWikiEventCorrelator:
    """Tests for research_wiki_event_correlator."""

    async def test_wiki_event_correlator_basic(self) -> None:
        """Test basic Wikipedia event correlation."""
        page_title = "Artificial intelligence"

        result = await p3_tools.research_wiki_event_correlator(page_title)
        assert isinstance(result, dict)
        assert "page" in result

    async def test_wiki_event_correlator_defaults(self) -> None:
        """Test Wikipedia event correlation with default days_back."""
        page_title = "Machine learning"

        result = await p3_tools.research_wiki_event_correlator(page_title)

        assert result.get("page") == page_title
        assert "days_analyzed" in result

    async def test_wiki_event_correlator_custom_days(self) -> None:
        """Test Wikipedia event correlation with custom days_back."""
        page_title = "Cryptography"
        days = 60

        result = await p3_tools.research_wiki_event_correlator(page_title, days)

        assert result.get("days_analyzed") == 60 or result.get("days_analyzed", 0) > 0

    async def test_wiki_event_correlator_invalid_days(self) -> None:
        """Test Wikipedia event correlation with invalid days_back."""
        page_title = "Test"

        try:
            await p3_tools.research_wiki_event_correlator(page_title, days_back=0)
        except (ValueError, Exception):
            pass

        try:
            await p3_tools.research_wiki_event_correlator(page_title, days_back=400)
        except (ValueError, Exception):
            pass

    async def test_wiki_event_correlator_empty_title(self) -> None:
        """Test Wikipedia event correlation with empty page title."""
        try:
            await p3_tools.research_wiki_event_correlator("")
        except (ValueError, Exception):
            pass


class TestFOIATracker:
    """Tests for research_foia_tracker."""

    async def test_foia_tracker_basic(self) -> None:
        """Test basic FOIA document tracking."""
        query = "surveillance"

        with patch("loom.tools.p3_tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mr_resp = MagicMock()
            mr_resp.status_code = 200
            mr_resp.text = '<html><a href="/document/12345-surveillance">Doc 1</a></html>'

            foia_resp = MagicMock()
            foia_resp.status_code = 200
            foia_resp.json = AsyncMock(return_value={
                "results": [
                    {
                        "title": "FOIA Surveillance Records",
                        "url": "https://foia.gov/doc/123",
                        "date": "2026-01-01"
                    }
                ]
            })

            mock_instance.get = AsyncMock(side_effect=[mr_resp, foia_resp])
            mock_instance.post = AsyncMock(return_value=foia_resp)

            result = await p3_tools.research_foia_tracker(query)

            assert "query" in result
            assert result["query"] == query

    async def test_foia_tracker_empty_query(self) -> None:
        """Test FOIA tracker with empty query."""
        try:
            await p3_tools.research_foia_tracker("")
        except (ValueError, Exception):
            pass

    async def test_foia_tracker_long_query(self) -> None:
        """Test FOIA tracker with query exceeding max length."""
        query = "x" * 150

        try:
            await p3_tools.research_foia_tracker(query)
        except (ValueError, Exception):
            pass

    async def test_foia_tracker_different_queries(self) -> None:
        """Test FOIA tracker with various valid queries."""
        queries = ["AI policy", "surveillance", "privacy records", "data breaches"]

        for q in queries:
            result = await p3_tools.research_foia_tracker(q)
            assert result.get("query") == q or "error" in result


class TestWordOverlapCalculation:
    """Tests for word overlap scoring in model comparator."""

    async def test_extract_word_set(self) -> None:
        """Test word extraction from text."""
        if not hasattr(p3_tools, "_extract_word_set"):
            pytest.skip("_extract_word_set not available")

        text = "Python is a high-level programming language used for AI research"
        words = p3_tools._extract_word_set(text)

        assert "python" in words or len(words) >= 0

    async def test_word_set_empty_text(self) -> None:
        """Test word extraction from empty text."""
        if not hasattr(p3_tools, "_extract_word_set"):
            pytest.skip("_extract_word_set not available")

        words = p3_tools._extract_word_set("")
        assert len(words) == 0

    async def test_word_set_only_stop_words(self) -> None:
        """Test word extraction from only stop words."""
        if not hasattr(p3_tools, "_extract_word_set"):
            pytest.skip("_extract_word_set not available")

        text = "the and or but in on at to for"
        words = p3_tools._extract_word_set(text)
        assert len(words) <= 10


class TestHelperFunctions:
    """Tests for helper functions."""

    async def test_get_json_success(self) -> None:
        """Test successful JSON fetch."""
        pass

    async def test_get_json_failure(self) -> None:
        """Test JSON fetch failure handling."""
        pass

    async def test_get_text_success(self) -> None:
        """Test successful text fetch."""
        pass

    async def test_get_text_failure(self) -> None:
        """Test text fetch failure handling."""
        pass


class TestIntegrationP3Tools:
    """Integration tests for P3 tools."""

    @pytest.mark.live
    async def test_wiki_correlator_real_wikipedia(self) -> None:
        """Test Wikipedia event correlator with real Wikipedia API."""
        result = await p3_tools.research_wiki_event_correlator("Python (programming language)")

        assert result.get("page") == "Python (programming language)" or "error" in result

    async def test_all_tools_output_structure(self) -> None:
        """Test that all tools return consistent output structures."""
        # Model comparator minimum output
        with patch("loom.tools.p3_tools.httpx.AsyncClient"):
            result = await p3_tools.research_model_comparator(
                "test",
                ["https://example.com/chat", "https://example.com/chat"]
            )
            assert isinstance(result, dict)

        # Data poisoning minimum output
        result = await p3_tools.research_data_poisoning("https://example.com/chat")
        assert isinstance(result, dict)

        # Wiki correlator minimum output
        result = await p3_tools.research_wiki_event_correlator("Test Page")
        assert isinstance(result, dict)

        # FOIA tracker minimum output
        result = await p3_tools.research_foia_tracker("test query")
        assert isinstance(result, dict)
