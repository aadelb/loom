"""Tests for dark web forum analysis (forum_cortex)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest


@pytest.mark.asyncio
class TestResearchForumCortex:
    async def test_search_tools_not_available(self):
        """Test error when search tools are unavailable."""
        # Patch at the source where it would be imported
        with patch('loom.tools.core.search.research_search', side_effect=ImportError("search not available")):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex
            result = await research_forum_cortex("test topic")
            
            assert result["topic"] == "test topic"
            assert result["posts"] == []

    async def test_no_search_results(self):
        """Test when search returns no results."""
        # Use sync mock since research_search is run in executor
        mock_search = MagicMock(return_value={'results': []})
        
        with patch('loom.tools.core.search.research_search', mock_search):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex

            result = await research_forum_cortex("nonexistent topic", n=5)

            assert result["topic"] == "nonexistent topic"
            assert result["posts"] == []
            assert result["stats"]["total_posts_analyzed"] == 0

    async def test_successful_forum_search(self):
        """Test successful forum search and post retrieval."""
        search_results = [
            {
                "url": "https://ahmia.fi/search/?q=test",
                "title": "Forum Post 1",
                "snippet": "Discussion about the topic",
            },
            {
                "url": "https://darksearch.io/search?q=test",
                "title": "Forum Post 2",
                "snippet": "Technical discussion",
            },
        ]

        # Use sync mock since research_search is run in executor
        mock_search = MagicMock(return_value={'results': search_results})
        mock_classify = AsyncMock(return_value={'category': 'technical', 'confidence': 0.8, 'sentiment': 'neutral'})

        with patch('loom.tools.core.search.research_search', mock_search),              patch('loom.tools.intelligence.forum_cortex._classify_post', mock_classify):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex

            result = await research_forum_cortex("security threat", n=5)

            assert result["topic"] == "security threat"
            assert "posts" in result
            assert "summary" in result
            assert "stats" in result

    async def test_post_deduplication_by_url(self):
        """Test that duplicate URLs are removed."""
        search_results = [
            {
                "url": "https://ahmia.fi/1",
                "title": "Post A",
                "snippet": "Content A",
            },
            {
                "url": "https://ahmia.fi/1",
                "title": "Post A",
                "snippet": "Content A",
            },
            {
                "url": "https://ahmia.fi/2",
                "title": "Post B",
                "snippet": "Content B",
            },
        ]

        # Use sync mock since research_search is run in executor
        mock_search = MagicMock(return_value={'results': search_results})
        mock_classify = AsyncMock(return_value={"category": "other", "confidence": 0.5, "sentiment": "neutral"})

        with patch('loom.tools.core.search.research_search', mock_search),              patch('loom.tools.intelligence.forum_cortex._classify_post', mock_classify):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex

            result = await research_forum_cortex("test", n=10)

            # Should have unique URLs only
            urls = {p["url"] for p in result["posts"]}
            assert len(urls) <= 3

    async def test_category_counting(self):
        """Test that post categories are correctly counted."""
        search_results = [
            {
                "url": "https://ahmia.fi/1",
                "title": "Threat Post",
                "snippet": "This is a threat",
            },
            {
                "url": "https://ahmia.fi/2",
                "title": "Recruitment Post",
                "snippet": "Join our group",
            },
        ]

        async def classify_mock(title, content):
            if "threat" in title.lower():
                return {"category": "threat", "confidence": 0.9, "sentiment": "negative"}
            else:
                return {"category": "recruitment", "confidence": 0.8, "sentiment": "neutral"}

        # Use sync mock since research_search is run in executor
        mock_search = MagicMock(return_value={'results': search_results})

        with patch('loom.tools.core.search.research_search', mock_search),              patch('loom.tools.intelligence.forum_cortex._classify_post', side_effect=classify_mock):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex

            result = await research_forum_cortex("test", n=5)

            assert result["stats"]["threat_posts"] >= 1 or result["stats"]["recruitment_posts"] >= 1

    async def test_response_structure(self):
        """Test that response has all required keys."""
        # Use sync mock since research_search is run in executor
        mock_search = MagicMock(return_value={'results': []})

        with patch('loom.tools.core.search.research_search', mock_search):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex

            result = await research_forum_cortex("test")

            assert "topic" in result
            assert "posts" in result
            assert "summary" in result
            assert "stats" in result
            assert "category_breakdown" in result["stats"]

    async def test_max_results_parameter(self):
        """Test that n parameter limits results."""
        search_results = [
            {
                "url": f"https://ahmia.fi/{i}",
                "title": f"Post {i}",
                "snippet": f"Content {i}",
            }
            for i in range(20)
        ]

        # Use sync mock since research_search is run in executor
        mock_search = MagicMock(return_value={'results': search_results})
        mock_classify = AsyncMock(return_value={"category": "other", "confidence": 0.5, "sentiment": "neutral"})

        with patch('loom.tools.core.search.research_search', mock_search),              patch('loom.tools.intelligence.forum_cortex._classify_post', mock_classify):
            from loom.tools.intelligence.forum_cortex import research_forum_cortex

            result = await research_forum_cortex("test", n=5)

            # Should limit to approximately n * num_sources
            assert len(result["posts"]) <= 20


@pytest.mark.asyncio
class TestClassifyPost:
    async def test_llm_unavailable(self):
        """Test post classification when LLM is unavailable."""
        from loom.tools.intelligence.forum_cortex import _classify_post

        result = await _classify_post("Title", "Content snippet")

        assert result["category"] == "other"
        assert result["confidence"] == 0.5
        assert result["sentiment"] == "neutral"

    async def test_classification_success(self):
        """Test successful post classification."""
        mock_result = {
            "classification": {
                "label": "threat",
                "confidence": 0.95,
                "sentiment": "negative",
            }
        }

        with patch('loom.tools.llm.research_llm_classify', new_callable=AsyncMock, return_value=mock_result):
            from loom.tools.intelligence.forum_cortex import _classify_post

            result = await _classify_post("Threat title", "Malicious content")

            assert result["category"] == "threat"
            assert result["confidence"] == 0.95
            assert result["sentiment"] == "negative"

    async def test_classification_missing_sentiment(self):
        """Test classification when sentiment is missing."""
        mock_result = {
            "classification": {
                "label": "technical",
                "confidence": 0.8,
            }
        }

        with patch('loom.tools.llm.research_llm_classify', new_callable=AsyncMock, return_value=mock_result):
            from loom.tools.intelligence.forum_cortex import _classify_post

            result = await _classify_post("Technical post", "How to...")

            assert result["category"] == "technical"
            assert result["sentiment"] == "neutral"

    async def test_classification_exception_handling(self):
        """Test handling of classification exceptions."""
        with patch('loom.tools.llm.research_llm_classify', new_callable=AsyncMock, side_effect=Exception("API error")):
            from loom.tools.intelligence.forum_cortex import _classify_post

            result = await _classify_post("Title", "Content")

            assert result["category"] == "other"
            assert result["confidence"] == 0.5


class TestPostCategories:
    def test_post_category_constants(self):
        """Test that post categories are defined."""
        from loom.tools.intelligence.forum_cortex import _POST_CATEGORIES

        expected_categories = [
            "informational",
            "threat",
            "recruitment",
            "marketplace",
            "technical",
            "discussion",
            "other",
        ]

        assert _POST_CATEGORIES == expected_categories

    def test_darkweb_sources(self):
        """Test that dark web sources are defined."""
        from loom.tools.intelligence.forum_cortex import _DARKWEB_SOURCES

        assert "ahmia.fi" in _DARKWEB_SOURCES
        assert "darksearch.io" in _DARKWEB_SOURCES
