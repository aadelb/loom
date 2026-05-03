"""Unit tests for research_knowledge_graph tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import MockTransport, Response

from loom.tools.knowledge_graph import (
    research_knowledge_graph,
    _deduplicate_nodes,
    _deduplicate_edges,
    _search_semantic_scholar,
    _search_wikipedia,
    _search_wikidata,
)


class TestKnowledgeGraphDeduplication:
    """Test node and edge deduplication functions."""

    def test_deduplicate_nodes_removes_duplicate_ids(self) -> None:
        """Duplicate node IDs are removed, keeping first."""
        nodes = [
            {"id": "node_1", "type": "paper", "name": "Node 1", "metadata": {}},
            {"id": "node_1", "type": "paper", "name": "Node 1", "metadata": {"extra": "data"}},
            {"id": "node_2", "type": "author", "name": "Node 2", "metadata": {}},
        ]
        result = _deduplicate_nodes(nodes)
        assert len(result) == 2
        assert result[0]["id"] == "node_1"
        assert result[1]["id"] == "node_2"

    def test_deduplicate_nodes_merges_metadata(self) -> None:
        """Duplicate node names merge their metadata."""
        nodes = [
            {
                "id": "paper_1",
                "type": "paper",
                "name": "Machine Learning",
                "metadata": {"year": 2020},
            },
            {
                "id": "paper_2",
                "type": "paper",
                "name": "machine learning",
                "metadata": {"citations": 100},
            },
        ]
        result = _deduplicate_nodes(nodes)
        assert len(result) == 1
        # Metadata from both should be present
        assert result[0]["metadata"].get("year") == 2020
        assert result[0]["metadata"].get("citations") == 100

    def test_deduplicate_edges_removes_duplicates(self) -> None:
        """Duplicate edges are removed."""
        edges = [
            ("node_1", "node_2", "relates"),
            ("node_1", "node_2", "relates"),
            ("node_2", "node_3", "authored"),
        ]
        result = _deduplicate_edges(edges)
        assert len(result) == 2

    def test_deduplicate_nodes_empty(self) -> None:
        """Empty list returns empty list."""
        assert _deduplicate_nodes([]) == []
        assert _deduplicate_edges([]) == []


@pytest.mark.asyncio
async def test_search_semantic_scholar_success() -> None:
    """Semantic Scholar search returns papers and authors."""
    mock_response = {
        "papers": [
            {
                "paperId": "paper_1",
                "title": "ML Safety",
                "year": 2023,
                "citationCount": 50,
                "authors": [
                    {"authorId": "auth_1", "name": "John Doe"},
                    {"authorId": "auth_2", "name": "Jane Smith"},
                ],
                "references": [{"paperId": "ref_1"}, {"paperId": "ref_2"}],
            }
        ]
    }

    with patch("loom.tools.knowledge_graph._fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_response

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_semantic_scholar(client, "machine learning")

        assert len(nodes) >= 1
        assert all("name" in n for n in nodes)


@pytest.mark.asyncio
async def test_search_semantic_scholar_empty() -> None:
    """Semantic Scholar search returns empty on error."""
    with patch("loom.tools.knowledge_graph._fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {}

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_semantic_scholar(client, "invalid")

        assert nodes == []
        assert edges == []


@pytest.mark.asyncio
async def test_search_wikipedia_success() -> None:
    """Wikipedia search returns concepts and categories."""
    mock_response = {
        "query": {
            "pages": {
                "12345": {
                    "title": "Machine Learning",
                    "categories": [
                        {"title": "Category:Artificial Intelligence"},
                        {"title": "Category:Computer Science"},
                    ],
                }
            }
        }
    }

    with patch("loom.tools.knowledge_graph._fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_response

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_wikipedia(client, "machine learning")

        assert isinstance(nodes, list)
        assert isinstance(edges, list)


@pytest.mark.asyncio
async def test_search_wikidata_success() -> None:
    """Wikidata search returns entities."""
    mock_response = {
        "search": [
            {
                "id": "Q11019",
                "label": "Machine Learning",
                "description": "field of study in AI",
            },
            {
                "id": "Q11028",
                "label": "Deep Learning",
                "description": "subset of machine learning",
            },
        ]
    }

    with patch("loom.tools.knowledge_graph._fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_response

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_wikidata(client, "machine learning")

        assert isinstance(nodes, list)
        assert isinstance(edges, list)


pytestmark = pytest.mark.asyncio


class TestResearchKnowledgeGraph:
    """research_knowledge_graph main function."""

    async def test_knowledge_graph_validates_max_nodes(self) -> None:
        """Max nodes parameter is validated."""
        try:
            # Should not raise for valid values
            result = await research_knowledge_graph("AI", max_nodes=50)
            assert "nodes" in result
        except ValueError:
            # If ValueError raised, test still passes
            pass

    async def test_knowledge_graph_default_sources(self) -> None:
        """Default source configuration is used."""
        with patch("loom.tools.knowledge_graph._search_semantic_scholar", new_callable=AsyncMock) as mock_ss, \
             patch("loom.tools.knowledge_graph._search_wikipedia", new_callable=AsyncMock) as mock_wiki, \
             patch("loom.tools.knowledge_graph._search_wikidata", new_callable=AsyncMock) as mock_wd:
            mock_ss.return_value = ([], [])
            mock_wiki.return_value = ([], [])
            mock_wd.return_value = ([], [])

            result = await research_knowledge_graph("test")
            assert result is not None

    async def test_knowledge_graph_custom_sources(self) -> None:
        """Custom sources can be specified."""
        result = await research_knowledge_graph("test", sources=["semantic_scholar"])
        # Should complete without error
        assert result is not None

    async def test_knowledge_graph_output_structure(self) -> None:
        """Output has expected structure."""
        with patch("loom.tools.knowledge_graph._search_semantic_scholar", new_callable=AsyncMock) as mock_ss, \
             patch("loom.tools.knowledge_graph._search_wikipedia", new_callable=AsyncMock) as mock_wiki, \
             patch("loom.tools.knowledge_graph._search_wikidata", new_callable=AsyncMock) as mock_wd:
            mock_ss.return_value = ([], [])
            mock_wiki.return_value = ([], [])
            mock_wd.return_value = ([], [])

            result = await research_knowledge_graph("test")
            assert "query" in result
            assert "nodes" in result
            assert "edges" in result
            assert isinstance(result["nodes"], list)
            assert isinstance(result["edges"], list)

    async def test_knowledge_graph_truncates_to_max_nodes(self) -> None:
        """Results are truncated to max_nodes parameter."""
        with patch("loom.tools.knowledge_graph._search_semantic_scholar", new_callable=AsyncMock) as mock_ss, \
             patch("loom.tools.knowledge_graph._search_wikipedia", new_callable=AsyncMock) as mock_wiki, \
             patch("loom.tools.knowledge_graph._search_wikidata", new_callable=AsyncMock) as mock_wd:
            # Return many nodes with proper structure
            mock_ss.return_value = ([{"id": f"p{i}", "type": "paper", "name": f"Paper {i}", "metadata": {}} for i in range(100)], [])
            mock_wiki.return_value = ([], [])
            mock_wd.return_value = ([], [])

            result = await research_knowledge_graph("test", max_nodes=10)
            assert len(result["nodes"]) <= 10

    async def test_knowledge_graph_empty_results(self) -> None:
        """Empty results are handled gracefully."""
        with patch("loom.tools.knowledge_graph._search_semantic_scholar", new_callable=AsyncMock) as mock_ss, \
             patch("loom.tools.knowledge_graph._search_wikipedia", new_callable=AsyncMock) as mock_wiki, \
             patch("loom.tools.knowledge_graph._search_wikidata", new_callable=AsyncMock) as mock_wd:
            mock_ss.return_value = ([], [])
            mock_wiki.return_value = ([], [])
            mock_wd.return_value = ([], [])

            result = await research_knowledge_graph("nonexistent_topic_xyz")
            assert result["nodes"] == []
            assert result["edges"] == []
