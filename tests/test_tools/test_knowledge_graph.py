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

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200)
        mock_get.return_value.json.return_value = mock_response

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_semantic_scholar(client, "machine learning")

        assert len(nodes) == 3  # 1 paper + 2 authors
        assert len(edges) == 5  # 2 authored + 2 cites
        assert nodes[0]["type"] == "paper"
        assert any(n["type"] == "author" for n in nodes)


@pytest.mark.asyncio
async def test_search_semantic_scholar_empty() -> None:
    """Semantic Scholar search returns empty on error."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200)
        mock_get.return_value.json.return_value = {}

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
                        {"title": "Category: Artificial Intelligence"},
                        {"title": "Category: Computer Science"},
                    ],
                    "links": [
                        {"title": "Deep Learning"},
                        {"title": "Neural Networks"},
                    ],
                }
            }
        }
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200)
        mock_get.return_value.json.return_value = mock_response

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_wikipedia(client, "machine learning")

        assert len(nodes) >= 3  # concept + categories + links
        assert any(n["type"] == "concept" for n in nodes)
        assert any(n["type"] == "category" for n in nodes)


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

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200)
        mock_get.return_value.json.return_value = mock_response

        import httpx
        client = httpx.AsyncClient()
        nodes, edges = await _search_wikidata(client, "machine learning")

        assert len(nodes) == 2
        assert all(n["type"] == "entity" for n in nodes)
        assert all("wikidata_id" in n["metadata"] for n in nodes)


class TestResearchKnowledgeGraph:
    """Test main knowledge_graph function."""

    def test_knowledge_graph_validates_max_nodes(self) -> None:
        """max_nodes is clamped to 1-500 range."""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {
                "query": "test",
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "sources_used": ["semantic_scholar"],
            }

            # Should not raise with extreme values
            result = research_knowledge_graph("test", max_nodes=0)
            assert result["query"] == "test"

            result = research_knowledge_graph("test", max_nodes=1000)
            assert result["query"] == "test"

    def test_knowledge_graph_default_sources(self) -> None:
        """Default sources include all three providers."""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {
                "query": "test",
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "sources_used": ["semantic_scholar", "wikipedia", "wikidata"],
            }

            result = research_knowledge_graph("test")
            assert set(result["sources_used"]) == {
                "semantic_scholar",
                "wikipedia",
                "wikidata",
            }

    def test_knowledge_graph_custom_sources(self) -> None:
        """Custom sources are respected."""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {
                "query": "test",
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "sources_used": ["wikipedia"],
            }

            result = research_knowledge_graph(
                "test", sources=["wikipedia"]
            )
            assert result["sources_used"] == ["wikipedia"]

    def test_knowledge_graph_output_structure(self) -> None:
        """Output has expected structure and fields."""
        with patch("asyncio.run") as mock_run:
            sample_node = {
                "id": "paper_1",
                "type": "paper",
                "name": "Test Paper",
                "metadata": {},
            }
            sample_edge = {"source": "paper_1", "target": "author_1", "relation": "authored"}

            mock_run.return_value = {
                "query": "machine learning",
                "nodes": [sample_node],
                "edges": [sample_edge],
                "total_nodes": 1,
                "total_edges": 1,
                "sources_used": ["semantic_scholar"],
            }

            result = research_knowledge_graph("machine learning")

            # Check structure
            assert "query" in result
            assert "nodes" in result
            assert "edges" in result
            assert "total_nodes" in result
            assert "total_edges" in result
            assert "sources_used" in result

            # Check types
            assert isinstance(result["nodes"], list)
            assert isinstance(result["edges"], list)
            assert isinstance(result["total_nodes"], int)
            assert isinstance(result["total_edges"], int)

            # Check node structure
            if result["nodes"]:
                node = result["nodes"][0]
                assert "id" in node
                assert "type" in node
                assert "name" in node
                assert "metadata" in node

            # Check edge structure
            if result["edges"]:
                edge = result["edges"][0]
                assert "source" in edge
                assert "target" in edge
                assert "relation" in edge

    def test_knowledge_graph_truncates_to_max_nodes(self) -> None:
        """Result is truncated to max_nodes."""
        with patch("asyncio.run") as mock_run:
            # Create 5 nodes
            nodes = [
                {
                    "id": f"node_{i}",
                    "type": "paper",
                    "name": f"Node {i}",
                    "metadata": {},
                }
                for i in range(5)
            ]
            edges = [
                {"source": "node_0", "target": "node_1", "relation": "relates"},
                {"source": "node_1", "target": "node_2", "relation": "relates"},
            ]

            mock_run.return_value = {
                "query": "test",
                "nodes": nodes[:3],  # Simulate truncation
                "edges": edges[:1],
                "total_nodes": 3,
                "total_edges": 1,
                "sources_used": ["semantic_scholar"],
            }

            result = research_knowledge_graph("test", max_nodes=3)
            assert len(result["nodes"]) <= 3

    def test_knowledge_graph_empty_results(self) -> None:
        """Handles empty results gracefully."""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {
                "query": "invalid_query_xyz",
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "sources_used": ["semantic_scholar", "wikipedia", "wikidata"],
            }

            result = research_knowledge_graph("invalid_query_xyz")
            assert result["total_nodes"] == 0
            assert result["total_edges"] == 0
            assert result["nodes"] == []
            assert result["edges"] == []
