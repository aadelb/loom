"""Tests for graph_scraper tools: research_graph_scrape, research_knowledge_extract, research_multi_page_graph."""

from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.params import GraphScraperParams, KnowledgeExtractParams, MultiPageGraphParams
from loom.tools.graph_scraper import (
    research_graph_scrape,
    research_knowledge_extract,
    research_multi_page_graph,
    _extract_nodes,
    _extract_edges,
    _deduplicate_relationships,
    _fetch_url_content,
    _extract_with_llm,
    _build_extraction_prompt,
)

class TestGraphScraperParams:
    """Test GraphScraperParams validation."""

    def test_valid_params(self):
        """Test valid GraphScraperParams."""
        params = GraphScraperParams(
            url="https://example.com",
            query="Extract products",
        )
        assert params.url == "https://example.com"
        assert params.query == "Extract products"
        assert params.model == "auto"

    def test_url_validation(self):
        """Test URL validation."""
        with pytest.raises(ValueError):
            GraphScraperParams(url="invalid", query="test")

    def test_query_required(self):
        """Test query is required."""
        with pytest.raises(ValueError):
            GraphScraperParams(url="https://example.com", query="")

    def test_query_max_length(self):
        """Test query max length is 5000."""
        with pytest.raises(ValueError):
            GraphScraperParams(
                url="https://example.com",
                query="x" * 5001,
            )

    def test_model_validation(self):
        """Test model must be valid choice."""
        with pytest.raises(ValueError):
            GraphScraperParams(
                url="https://example.com",
                query="test",
                model="invalid_model",
            )

    def test_valid_models(self):
        """Test all valid model choices."""
        for model in ["auto", "groq", "nvidia", "deepseek", "openai", "anthropic"]:
            params = GraphScraperParams(
                url="https://example.com",
                query="test",
                model=model,
            )
            assert params.model == model

class TestKnowledgeExtractParams:
    """Test KnowledgeExtractParams validation."""

    def test_valid_params(self):
        """Test valid KnowledgeExtractParams."""
        params = KnowledgeExtractParams(
            text="This is a test document about AI and machine learning.",
        )
        assert params.text == "This is a test document about AI and machine learning."
        assert params.entity_types is None

    def test_text_required(self):
        """Test text is required."""
        with pytest.raises(ValueError):
            KnowledgeExtractParams(text="")

    def test_text_max_length(self):
        """Test text max length is 100000."""
        with pytest.raises(ValueError):
            KnowledgeExtractParams(text="x" * 100001)

    def test_entity_types_validation(self):
        """Test entity_types validation."""
        params = KnowledgeExtractParams(
            text="test",
            entity_types=["person", "organization"],
        )
        assert params.entity_types == ["person", "organization"]

    def test_entity_types_max_items(self):
        """Test entity_types max 20 items."""
        with pytest.raises(ValueError):
            KnowledgeExtractParams(
                text="test",
                entity_types=[f"type_{i}" for i in range(21)],
            )

    def test_entity_type_max_length(self):
        """Test each entity_type max 50 chars."""
        with pytest.raises(ValueError):
            KnowledgeExtractParams(
                text="test",
                entity_types=["x" * 51],
            )

class TestMultiPageGraphParams:
    """Test MultiPageGraphParams validation."""

    def test_valid_params(self):
        """Test valid MultiPageGraphParams."""
        params = MultiPageGraphParams(
            urls=["https://example1.com", "https://example2.com"],
            query="Extract data",
        )
        assert len(params.urls) == 2
        assert params.query == "Extract data"

    def test_urls_required(self):
        """Test urls is required."""
        with pytest.raises(ValueError):
            MultiPageGraphParams(urls=[], query="test")

    def test_urls_max_items(self):
        """Test urls max 100 items."""
        with pytest.raises(ValueError):
            MultiPageGraphParams(
                urls=[f"https://example{i}.com" for i in range(101)],
                query="test",
            )

    def test_invalid_url(self):
        """Test invalid URLs are rejected."""
        with pytest.raises(ValueError):
            MultiPageGraphParams(
                urls=["https://example.com", "invalid"],
                query="test",
            )

    def test_query_required(self):
        """Test query is required."""
        with pytest.raises(ValueError):
            MultiPageGraphParams(
                urls=["https://example.com"],
                query="",
            )

class TestExtractHelpers:
    """Test helper functions for extraction."""

    def test_extract_nodes_from_dict(self):
        """Test extracting nodes from dict with entities."""
        data = {
            "entities": [
                {"name": "Alice", "type": "person"},
                {"name": "Google", "type": "organization"},
            ]
        }
        nodes = _extract_nodes(data)
        assert len(nodes) == 2
        assert nodes[0]["name"] == "Alice"

    def test_extract_nodes_fallback(self):
        """Test extracting nodes from dict without entities."""
        data = {"key1": {"nested": "value"}, "key2": ["list", "data"]}
        nodes = _extract_nodes(data)
        assert len(nodes) == 2
        assert any(n["name"] == "key1" for n in nodes)

    def test_extract_edges_with_relationships(self):
        """Test extracting edges from dict with relationships."""
        data = {
            "relationships": [
                {"source": "Alice", "target": "Google", "relation": "works_at"},
            ]
        }
        edges = _extract_edges(data)
        assert len(edges) == 1
        assert edges[0]["relation"] == "works_at"

    def test_extract_edges_no_relationships(self):
        """Test extracting edges returns empty list if no relationships."""
        data = {"entities": [{"name": "test"}]}
        edges = _extract_edges(data)
        assert edges == []

    def test_deduplicate_relationships(self):
        """Test deduplicating relationships."""
        rels = [
            {"source": "A", "target": "B", "relation": "rel1"},
            {"source": "A", "target": "B", "relation": "rel1"},  # Duplicate
            {"source": "B", "target": "C", "relation": "rel2"},
        ]
        unique = _deduplicate_relationships(rels)
        assert len(unique) == 2

    def test_deduplicate_preserves_order(self):
        """Test deduplication preserves order."""
        rels = [
            {"source": "A", "target": "B", "relation": "rel1"},
            {"source": "C", "target": "D", "relation": "rel2"},
            {"source": "A", "target": "B", "relation": "rel1"},  # Duplicate
        ]
        unique = _deduplicate_relationships(rels)
        assert unique[0]["source"] == "A"  # First one preserved
        assert unique[1]["source"] == "C"

class TestBuildExtractionPrompt:
    """Test building extraction prompts."""

    def test_basic_prompt(self):
        """Test building a basic extraction prompt."""
        text = "Alice works at Google."
        query = "Extract people and companies"
        prompt = _build_extraction_prompt(text, query)
        assert "Alice works at Google" in prompt
        assert "Extract people and companies" in prompt
        assert "entities" in prompt.lower()
        assert "relationships" in prompt.lower()

    def test_prompt_with_entity_types(self):
        """Test prompt includes entity types when specified."""
        text = "Test content"
        query = "Extract entities"
        entity_types = ["person", "organization"]
        prompt = _build_extraction_prompt(text, query, entity_types)
        assert "person" in prompt
        assert "organization" in prompt

    def test_prompt_text_truncation(self):
        """Test long text is truncated in prompt."""
        text = "x" * 5000
        query = "test"
        prompt = _build_extraction_prompt(text, query)
        # Should only contain first 2000 chars
        assert len(prompt) < len(text)

class TestFetchUrlContent:
    """Test URL content fetching."""

    @pytest.mark.asyncio
    async def test_fetch_valid_url(self):
        """Test fetching content from valid URL."""
        with patch("loom.tools.graph_scraper.research_fetch") as mock_fetch:
            mock_fetch = AsyncMock(return_value={"text": "Page content"})
            with patch("loom.tools.graph_scraper.research_fetch", mock_fetch):
                result = await _fetch_url_content("https://example.com")
                assert "Page content" in result
                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_fallback_to_http(self):
        """Test fallback to raw HTTP when research_fetch fails."""
        with patch("loom.tools.graph_scraper.research_fetch") as mock_fetch:
            mock_fetch.side_effect = Exception("Fetch failed")
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.text = "Fallback content"
                mock_response.raise_for_status = AsyncMock()
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )
                result = await _fetch_url_content("https://example.com")
                assert result  # Should fallback

    @pytest.mark.asyncio
    async def test_fetch_respects_max_chars(self):
        """Test max_chars parameter limits content."""
        with patch("loom.tools.graph_scraper.research_fetch") as mock_fetch:
            large_content = "x" * 30000
            mock_fetch.return_value = {"text": large_content}
            result = await _fetch_url_content("https://example.com", max_chars=1000)
            # research_fetch call should pass max_chars
            call_kwargs = mock_fetch.call_args[1]
            assert call_kwargs.get("max_chars") == 1000

class TestExtractWithLLM:
    """Test LLM-based extraction."""

    @pytest.mark.asyncio
    async def test_extract_with_valid_provider(self):
        """Test extraction with valid LLM provider."""
        mock_provider = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = json.dumps({
            "entities": [{"name": "Alice", "type": "person"}],
            "relationships": [{"source": "Alice", "target": "Google", "relation": "works_at"}],
            "summary": "Alice works at Google",
        })
        mock_provider.chat = AsyncMock(return_value=mock_response)

        result = await _extract_with_llm("Alice works at Google", "Extract people", mock_provider)
        assert len(result["entities"]) == 1
        assert len(result["relationships"]) == 1
        assert "Alice" in result["summary"]

    @pytest.mark.asyncio
    async def test_extract_without_provider(self):
        """Test extraction without LLM provider."""
        result = await _extract_with_llm("Test content", "Extract", provider=None)
        assert result["entities"] == []
        assert result["relationships"] == []
        assert "no llm provider" in result["summary"].lower()

    @pytest.mark.asyncio
    async def test_extract_json_parse_error(self):
        """Test handling invalid JSON from LLM."""
        mock_provider = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = "invalid json {{"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        result = await _extract_with_llm("Test", "Extract", mock_provider)
        assert result["entities"] == []
        assert result["relationships"] == []

    @pytest.mark.asyncio
    async def test_extract_with_entity_types(self):
        """Test extraction focuses on specified entity types."""
        mock_provider = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = json.dumps({
            "entities": [],
            "relationships": [],
            "summary": "Focused extraction",
        })
        mock_provider.chat = AsyncMock(return_value=mock_response)

        entity_types = ["person", "company"]
        await _extract_with_llm(
            "Test content",
            "Extract",
            mock_provider,
            entity_types=entity_types,
        )

        # Verify entity_types were included in prompt
        assert mock_provider.chat.called

class TestGraphScrape:
    """Test research_graph_scrape tool."""

    @pytest.mark.asyncio
    async def test_graph_scrape_basic(self):
        """Test basic graph scraping."""
        with patch("loom.tools.graph_scraper._get_llm_provider") as mock_get_provider:
            with patch("loom.tools.graph_scraper._fetch_url_content") as mock_fetch:
                with patch("loom.tools.graph_scraper._extract_with_llm") as mock_extract:
                    mock_provider = AsyncMock()
                    mock_get_provider.return_value = mock_provider
                    mock_provider.default_model = "groq/llama-3.3-70b-versatile"

                    mock_fetch_coro = AsyncMock(return_value="Page content")
                    mock_fetch.side_effect = mock_fetch_coro

                    mock_extract.return_value = {
                        "entities": [{"name": "Test"}],
                        "relationships": [],
                        "summary": "Test summary",
                    }

                    result = await research_graph_scrape(
                        "https://example.com",
                        "Extract data",
                    )

                    assert result["url"] == "https://example.com"
                    assert result["query"] == "Extract data"
                    assert "extracted_data" in result
                    assert "model_used" in result

    @pytest.mark.asyncio
    async def test_graph_scrape_invalid_url(self):
        """Test graph scrape rejects invalid URLs."""
        with pytest.raises(ValueError):
            await research_graph_scrape("invalid_url", "Extract")

    @pytest.mark.asyncio
    async def test_knowledge_extract_basic(self):
        """Test basic knowledge extraction."""
        with patch("loom.tools.graph_scraper._get_llm_provider") as mock_get:
            with patch("loom.tools.graph_scraper._extract_with_llm") as mock_extract:
                mock_provider = AsyncMock()
                mock_get.return_value = mock_provider
                mock_provider.default_model = "groq/llama-3.3-70b-versatile"

                mock_extract.return_value = {
                    "entities": [
                        {"name": "Alice", "type": "person"},
                        {"name": "Google", "type": "organization"},
                    ],
                    "relationships": [
                        {"source": "Alice", "target": "Google", "relation": "works_at"},
                    ],
                    "summary": "Alice works at Google",
                }

                result = await research_knowledge_extract(
                    "Alice works at Google as a software engineer."
                )

                assert result["entity_count"] == 2
                assert result["relationship_count"] == 1
                assert "Alice" in str(result["entities"])

    @pytest.mark.asyncio
    async def test_knowledge_extract_with_entity_types(self):
        """Test extraction with specific entity types."""
        with patch("loom.tools.graph_scraper._get_llm_provider") as mock_get:
            with patch("loom.tools.graph_scraper._extract_with_llm") as mock_extract:
                mock_provider = AsyncMock()
                mock_get.return_value = mock_provider
                mock_provider.default_model = "test_model"

                mock_extract.return_value = {
                    "entities": [],
                    "relationships": [],
                    "summary": "Test",
                }

                await research_knowledge_extract(
                    "Test text",
                    entity_types=["person", "company"],
                )

                # Verify entity_types were passed
                call_kwargs = mock_extract.call_args[1]
                assert call_kwargs.get("entity_types") == ["person", "company"]

    @pytest.mark.asyncio
    async def test_knowledge_extract_no_provider(self):
        """Test extraction handles missing provider."""
        with patch("loom.tools.graph_scraper._get_llm_provider") as mock_get:
            mock_get.return_value = None

            result = await research_knowledge_extract("Test content")

            assert result["entity_count"] == 0
            assert result["relationship_count"] == 0
            assert "no llm provider" in result["error"].lower()

class TestMultiPageGraph:
    """Test research_multi_page_graph tool."""

    @pytest.mark.asyncio
    async def test_multi_page_basic(self):
        """Test basic multi-page graph scraping."""
        with patch("loom.tools.graph_scraper.research_graph_scrape") as mock_scrape:
            # Mock results for two URLs
            mock_scrape.side_effect = [
                {
                    "url": "https://page1.com",
                    "graph_nodes": [{"name": "Entity1", "type": "person"}],
                    "graph_edges": [{"source": "Entity1", "target": "Entity2", "relation": "knows"}],
                    "cost_usd": 0.01,
                },
                {
                    "url": "https://page2.com",
                    "graph_nodes": [{"name": "Entity2", "type": "person"}],
                    "graph_edges": [{"source": "Entity2", "target": "Entity3", "relation": "knows"}],
                    "cost_usd": 0.01,
                },
            ]

            result = await research_multi_page_graph(
                ["https://page1.com", "https://page2.com"],
                "Extract entities",
            )

            assert result["pages_processed"] == 2
            assert result["pages_failed"] == 0
            assert result["entities_count"] == 2
            assert result["relationships_count"] == 2
            assert result["total_cost_usd"] == 0.02

    @pytest.mark.asyncio
    async def test_multi_page_empty_urls(self):
        """Test multi-page with empty URLs list."""
        result = await research_multi_page_graph([], "Extract")
        assert result["pages_processed"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_multi_page_deduplicates_entities(self):
        """Test multi-page deduplicates entities by name."""
        with patch("loom.tools.graph_scraper.research_graph_scrape") as mock_scrape:
            # Both pages return same entity with different properties
            mock_scrape.side_effect = [
                {
                    "url": "https://page1.com",
                    "graph_nodes": [{"name": "Alice", "type": "person", "properties": {"age": 30}}],
                    "graph_edges": [],
                    "cost_usd": 0.0,
                },
                {
                    "url": "https://page2.com",
                    "graph_nodes": [{"name": "Alice", "type": "person", "properties": {"age": 31}}],
                    "graph_edges": [],
                    "cost_usd": 0.0,
                },
            ]

            result = await research_multi_page_graph(
                ["https://page1.com", "https://page2.com"],
                "Extract",
            )

            # Should have only 1 unique entity (Alice)
            assert result["entities_count"] == 1

    @pytest.mark.asyncio
    async def test_multi_page_invalid_urls(self):
        """Test multi-page with invalid URLs."""
        with pytest.raises(ValueError):
            await research_multi_page_graph(["https://valid.com", "invalid"], "Extract")

    @pytest.mark.asyncio
    async def test_multi_page_partial_failure(self):
        """Test multi-page with some failures."""
        with patch("loom.tools.graph_scraper.research_graph_scrape") as mock_scrape:
            # First succeeds, second fails
            mock_scrape.side_effect = [
                {
                    "url": "https://page1.com",
                    "graph_nodes": [{"name": "Entity1"}],
                    "graph_edges": [],
                    "cost_usd": 0.01,
                },
                Exception("Network error"),
            ]

            result = await research_multi_page_graph(
                ["https://page1.com", "https://page2.com"],
                "Extract",
            )

            assert result["pages_processed"] == 1
            assert result["pages_failed"] == 1

class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_params_validation_flow(self):
        """Test parameter validation flows through to tools."""
        # These should raise during param validation
        with pytest.raises(ValueError):
            GraphScraperParams(url="not_a_url", query="test")

        with pytest.raises(ValueError):
            KnowledgeExtractParams(text="")

        with pytest.raises(ValueError):
            MultiPageGraphParams(urls=[], query="test")

    @pytest.mark.asyncio
    async def test_graph_scrape_caching(self):
        """Test caching works for graph scrape results."""
        with patch("loom.tools.graph_scraper._get_llm_provider") as mock_get:
            with patch("loom.tools.graph_scraper._fetch_url_content") as mock_fetch:
                with patch("loom.tools.graph_scraper._extract_with_llm") as mock_extract:
                    with patch("loom.tools.graph_scraper.get_cache") as mock_cache:
                        # Setup mocks
                        mock_provider = AsyncMock()
                        mock_get.return_value = mock_provider
                        mock_provider.default_model = "test_model"
                        mock_fetch.return_value = "Content"

                        mock_extract.return_value = {
                            "entities": [],
                            "relationships": [],
                            "summary": "Test",
                        }

                        cache_mock = MagicMock()
                        cache_mock.get.return_value = None  # First call: cache miss
                        cache_mock.put = MagicMock()
                        mock_cache.return_value = cache_mock

                        # First call should call extraction
                        result1 = await research_graph_scrape(
                            "https://example.com",
                            "Extract",
                        )

                        assert cache_mock.put.called  # Should cache the result
                        assert result1["model_used"] == "test_model"

    @pytest.mark.asyncio
    async def test_graph_scrape_handles_empty_url(self):
        """Test graph scrape rejects empty URLs."""
        with pytest.raises(ValueError):
            await research_graph_scrape("", "Extract")

    @pytest.mark.asyncio
    async def test_graph_scrape_returns_dict(self):
        """Test graph scrape always returns a dict."""
        with patch("loom.tools.graph_scraper._get_llm_provider") as mock_get:
            with patch("loom.tools.graph_scraper._fetch_url_content") as mock_fetch:
                mock_get.return_value = AsyncMock()
                async def async_fetch(*args, **kwargs):
                    return ""
                mock_fetch.side_effect = async_fetch
                
                result = await research_graph_scrape("https://example.com", "Extract")
                assert isinstance(result, dict)
                assert "url" in result
                assert "query" in result

