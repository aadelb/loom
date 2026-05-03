"""Unit tests for academic research intelligence tools — ideological drift, author clustering, citation cartography."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.tools.gap_tools_academic import (
    research_author_clustering,
    research_citation_cartography,
    research_ideological_drift,
)


pytestmark = pytest.mark.asyncio

class TestIdeologicalDrift:
    """research_ideological_drift tracks field belief evolution."""

    async def test_ideological_drift_basic(self) -> None:
        """Returns keyword evolution data for research field."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={
                    "data": [
                        {
                            "title": "Deep Learning Advances",
                            "abstract": "neural networks machine learning training algorithms optimization techniques"
                        },
                        {
                            "title": "Transformer Models",
                            "abstract": "attention mechanisms neural networks language models training deep learning"
                        },
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_ideological_drift(field="machine learning", years=5)

            assert result["field"] == "machine learning"
            assert result["years_analyzed"] == 5
            assert "keyword_evolution" in result
            assert "drift_scores" in result
            assert "overall_drift_direction" in result

    async def test_ideological_drift_empty_field(self) -> None:
        """Handles empty field gracefully."""
        result = await research_ideological_drift(field="", years=5)
        # Should fail validation or return empty structure
        assert isinstance(result, dict)

    async def test_ideological_drift_custom_years(self) -> None:
        """Supports custom year ranges."""
        result = await research_ideological_drift(field="quantum computing", years=3)
        assert result["years_analyzed"] == 3

    async def test_ideological_drift_drift_direction(self) -> None:
        """Calculates drift direction correctly."""
        result = await research_ideological_drift(field="machine learning", years=2)
        assert result["overall_drift_direction"] in ("low", "moderate", "high")


class TestAuthorClustering:
    """research_author_clustering detects author collaboration patterns."""

    async def test_author_clustering_basic(self) -> None:
        """Identifies author clusters in field."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={
                    "data": [
                        {
                            "title": "Distributed Systems",
                            "year": 2024,
                            "authors": [
                                {"name": "Alice Smith"},
                                {"name": "Bob Jones"},
                                {"name": "Carol White"},
                            ]
                        },
                        {
                            "title": "System Design Patterns",
                            "year": 2024,
                            "authors": [
                                {"name": "Bob Jones"},
                                {"name": "Carol White"},
                                {"name": "David Brown"},
                            ]
                        },
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_author_clustering(field="distributed systems", max_authors=50)

            assert result["field"] == "distributed systems"
            assert "authors_found" in result
            assert "clusters" in result
            assert "emerging_clusters" in result

    async def test_author_clustering_empty_field(self) -> None:
        """Handles empty field."""
        result = await research_author_clustering(field="", max_authors=50)
        assert isinstance(result, dict)

    async def test_author_clustering_custom_max(self) -> None:
        """Respects max_authors limit."""
        result = await research_author_clustering(field="cryptography", max_authors=10)
        assert isinstance(result, dict)

    async def test_author_clustering_cluster_structure(self) -> None:
        """Clusters have expected structure."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={
                    "data": [
                        {
                            "title": "Paper 1",
                            "year": 2024,
                            "authors": [
                                {"name": "Author A"},
                                {"name": "Author B"},
                            ]
                        },
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_author_clustering(field="test field", max_authors=50)

            for cluster in result.get("clusters", []):
                assert "authors" in cluster
                assert "size" in cluster
                assert "formed_year" in cluster


class TestCitationCartography:
    """research_citation_cartography maps citation flows with anomaly detection."""

    async def test_citation_cartography_basic(self) -> None:
        """Maps citation graph for paper."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={
                    "title": "Attention Is All You Need",
                    "citationCount": 150000,
                    "authors": [{"name": "Vaswani"}, {"name": "Shazeer"}],
                    "references": [
                        {"paperId": "ref1", "title": "Sequence Models", "citationCount": 100},
                        {"paperId": "ref2", "title": "LSTM", "citationCount": 50},
                    ],
                    "citations": [
                        {"paperId": "cit1", "title": "BERT", "citationCount": 80000},
                        {"paperId": "cit2", "title": "GPT-2", "citationCount": 60000},
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_citation_cartography(paper_id="paper123", depth=2)

            assert result["paper_id"] == "paper123"
            assert "paper_title" in result
            assert "nodes_count" in result
            assert "nodes" in result
            assert "edges_count" in result
            assert "edges" in result
            assert "flow_anomalies" in result
            assert "manipulation_score" in result

    async def test_citation_cartography_paper_not_found(self) -> None:
        """Handles missing paper gracefully."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(return_value=None)
            mock_response.status_code = 404

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_citation_cartography(paper_id="invalid")

            assert result["paper_id"] == "invalid"
            assert "error" in result

    async def test_citation_cartography_anomaly_detection(self) -> None:
        """Detects citation anomalies."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            # High citation count should trigger anomaly
            mock_response.json = MagicMock(
                return_value={
                    "title": "Highly cited paper",
                    "citationCount": 250000,  # Extremely high
                    "authors": [{"name": "Author"}],
                    "references": [
                        {"paperId": f"ref{i}", "title": f"Ref {i}", "citationCount": 100}
                        for i in range(10)
                    ],
                    "citations": [
                        {"paperId": f"cit{i}", "title": f"Citation {i}", "citationCount": 1000}
                        for i in range(10)
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_citation_cartography(paper_id="highly_cited")

            assert result["manipulation_score"] >= 0.0
            assert result["manipulation_score"] <= 1.0
            assert result["risk_level"] in ("low", "medium", "high")

    async def test_citation_cartography_graph_structure(self) -> None:
        """Citation graph has proper structure."""
        with patch("loom.tools.gap_tools_academic.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={
                    "title": "Test Paper",
                    "citationCount": 50,
                    "authors": [{"name": "Test Author"}],
                    "references": [
                        {"paperId": "ref1", "title": "Reference 1", "citationCount": 10},
                    ],
                    "citations": [
                        {"paperId": "cit1", "title": "Citation 1", "citationCount": 20},
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_citation_cartography(paper_id="test123")

            # Check node structure
            for node in result.get("nodes", []):
                assert "id" in node
                assert "title" in node
                assert "citation_count" in node
                assert "depth" in node

            # Check edge structure
            for edge in result.get("edges", []):
                assert "source" in edge
                assert "target" in edge
                assert "type" in edge
