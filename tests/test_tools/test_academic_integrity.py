"""Unit tests for academic integrity tools — citation analysis, retractions, predatory journals."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from loom.tools.academic_integrity import (
    research_citation_analysis,
    research_predatory_journal_check,
    research_retraction_check,
)


pytestmark = pytest.mark.asyncio

class TestCitationAnalysis:
    """research_citation_analysis function."""

    async def test_paper_not_found(self) -> None:
        """Paper not found in Semantic Scholar returns error."""
        with patch("loom.tools.academic_integrity.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Mock get_json returns None (paper not found)
            mock_get = MagicMock()
            mock_get.return_value = None

            with patch(
                "loom.tools.academic_integrity._get_json", return_value=None
            ):
                result = await research_citation_analysis("invalid_paper_id")
                assert "error" in result
                assert "not found" in result["error"].lower()

    async def test_valid_paper_structure(self) -> None:
        """Valid paper returns expected structure."""
        mock_paper_data = {
            "paperId": "test123",
            "title": "Test Paper",
            "authors": [
                {"name": "John Doe"},
                {"name": "Jane Smith"},
            ],
            "citationCount": 150,
            "references": [
                {
                    "paperId": "ref1",
                    "authors": [{"name": "John Doe"}],
                },
                {
                    "paperId": "ref2",
                    "authors": [{"name": "Other Author"}],
                },
            ],
            "citations": [
                {
                    "citingPaper": {"paperId": "ref1"},
                },
            ],
            "year": 2020,
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_paper_data,
        ):
            result = await research_citation_analysis("test123", depth=1)

            # Check expected keys
            assert "paper_id" in result
            assert "title" in result
            assert "authors_count" in result
            assert "citation_count" in result
            assert "reference_count" in result
            assert "self_citation_rate" in result
            assert "mutual_citations_count" in result
            assert "anomaly_score" in result

            # Check values
            assert result["paper_id"] == "test123"
            assert result["title"] == "Test Paper"
            assert result["authors_count"] == 2
            assert result["citation_count"] == 150

    async def test_self_citation_detection(self) -> None:
        """High self-citation rate is detected and reflected in anomaly score."""
        mock_paper_data = {
            "paperId": "test123",
            "title": "Test Paper",
            "authors": [
                {"name": "John Doe"},
            ],
            "citationCount": 100,
            "references": [
                {"paperId": "ref1", "authors": [{"name": "John Doe"}]},
                {"paperId": "ref2", "authors": [{"name": "John Doe"}]},
                {"paperId": "ref3", "authors": [{"name": "John Doe"}]},
                {"paperId": "ref4", "authors": [{"name": "Other Author"}]},
            ],
            "citations": [],
            "year": 2020,
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_paper_data,
        ):
            result = await research_citation_analysis("test123", depth=1)

            # 3 out of 4 references are self-citations = 75%
            assert result["self_citation_rate"] > 50
            # High self-citation should increase anomaly score
            assert result["anomaly_score"] > 0

    async def test_mutual_citations_detection(self) -> None:
        """Mutual citations (papers citing each other) are detected."""
        mock_paper_data = {
            "paperId": "test123",
            "title": "Test Paper",
            "authors": [
                {"name": "John Doe"},
            ],
            "citationCount": 50,
            "references": [
                {"paperId": "mutual1", "authors": [{"name": "Other Author"}]},
            ],
            "citations": [
                {"citingPaper": {"paperId": "mutual1"}},
            ],
            "year": 2020,
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_paper_data,
        ):
            result = await research_citation_analysis("test123", depth=1)

            # Should detect mutual citation
            assert result["mutual_citations_count"] == 1
            assert "mutual1" in result["mutual_citations"]
            # Mutual citations increase anomaly score
            assert result["anomaly_score"] > 0

    async def test_depth_parameter_validation(self) -> None:
        """Depth parameter is passed through correctly."""
        mock_paper_data = {
            "paperId": "test123",
            "title": "Test Paper",
            "authors": [],
            "citationCount": 0,
            "references": [],
            "citations": [],
            "year": 2020,
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_paper_data,
        ):
            # Should accept depth 1-3
            result1 = await research_citation_analysis("test123", depth=1)
            assert result1["paper_id"] == "test123"

            result2 = await research_citation_analysis("test123", depth=2)
            assert result2["paper_id"] == "test123"

            result3 = await research_citation_analysis("test123", depth=3)
            assert result3["paper_id"] == "test123"


class TestRetractionCheck:
    """research_retraction_check function."""

    async def test_no_results_found(self) -> None:
        """Empty search results return zeros."""
        mock_crossref_data = {
            "message": {
                "items": [],
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_retraction_check("nonexistent query", max_results=20)

            assert result["query"] == "nonexistent query"
            assert result["papers_checked"] == 0
            assert result["retractions_found"] == 0
            assert result["retraction_details"] == []
            assert result["pubpeer_comments_found"] == 0

    async def test_crossref_api_failure(self) -> None:
        """API failure returns gracefully."""
        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=None,
        ):
            result = await research_retraction_check("test query")

            assert result["papers_checked"] == 0
            assert result["retractions_found"] == 0

    async def test_retraction_detection(self) -> None:
        """Retracted papers are detected in Crossref metadata."""
        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/example",
                        "title": ["Retracted Paper"],
                        "published-print": {"date-parts": [[2020, 1, 15]]},
                        "relation": {
                            "is-retraction-of": [
                                {
                                    "id-type": "doi",
                                    "id": "10.5678/original",
                                }
                            ]
                        },
                    }
                ],
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_retraction_check("test author")

            assert result["papers_checked"] == 1
            assert result["retractions_found"] == 1
            assert len(result["retraction_details"]) > 0

    async def test_max_results_limit(self) -> None:
        """max_results parameter limits paper checks."""
        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "DOI": f"10.1234/paper{i}",
                        "title": [f"Paper {i}"],
                        "published-print": {"date-parts": [[2020, 1, i % 30 + 1]]},
                    }
                    for i in range(50)
                ],
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_retraction_check("test", max_results=10)

            # Should only check up to max_results
            assert result["papers_checked"] <= 10


class TestPredatoryJournalCheck:
    """research_predatory_journal_check function."""

    async def test_legitimate_journal_in_doaj(self) -> None:
        """Legitimate journal registered in DOAJ gets low risk score."""
        mock_doaj_data = {
            "results": [
                {
                    "journal_name": "Nature",
                    "issn": "0028-0836",
                }
            ]
        }

        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "title": "Nature",
                        "issn": ["0028-0836"],
                        "counts": {
                            "total-dois": 5000,
                        },
                        "coverage": {
                            "publication-count": 500,
                        },
                    }
                ]
            }
        }

        async def mock_get_json(client, url, timeout=None):
            if "doaj.org" in url:
                return mock_doaj_data
            else:
                return mock_crossref_data

        with patch(
            "loom.tools.academic_integrity._get_json",
            side_effect=mock_get_json,
        ):
            result = await research_predatory_journal_check("Nature")

            assert result["journal_name"] == "Nature"
            assert result["is_in_doaj"] is True
            assert result["crossref_registered"] is True
            # Legitimate journal should have low risk
            assert result["predatory_score"] < 50

    async def test_unregistered_journal_high_risk(self) -> None:
        """Unregistered journal gets high risk score."""
        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=None,
        ):
            result = await research_predatory_journal_check("Unknown Journal XYZ")

            assert result["journal_name"] == "Unknown Journal XYZ"
            assert result["is_in_doaj"] is False
            assert result["crossref_registered"] is False
            # Unregistered journal should have high risk
            assert result["predatory_score"] > 50

    async def test_journal_name_validation(self) -> None:
        """Journal name is trimmed and validated."""
        mock_data = None

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_data,
        ):
            result = await research_predatory_journal_check("  Journal Name  ")

            # Should handle trimmed names gracefully
            assert "journal_name" in result

    async def test_risk_indicators(self) -> None:
        """Risk indicators are identified and included in response."""
        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "title": "Suspicious Journal",
                        "issn": [],
                        "counts": {
                            "total-dois": 5,
                        },
                        "coverage": {},
                    }
                ]
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_predatory_journal_check("Suspicious Journal")

            # Should identify risk indicators
            assert "risk_indicators" in result
            assert isinstance(result["risk_indicators"], list)
            # Low publication count should be flagged
            assert len(result["risk_indicators"]) > 0

    async def test_publication_count_included(self) -> None:
        """Publication count is extracted and included."""
        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "title": "Test Journal",
                        "counts": {
                            "total-dois": 1234,
                        },
                    }
                ]
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_predatory_journal_check("Test Journal")

            assert result["publication_count"] == 1234


class TestParameterValidation:
    """Parameter validation in Pydantic models."""

    async def test_citation_analysis_params(self) -> None:
        """CitationAnalysisParams validates correctly."""
        from loom.params import CitationAnalysisParams

        # Valid parameters
        params = CitationAnalysisParams(paper_id="test123", depth=2)
        assert params.paper_id == "test123"
        assert params.depth == 2

        # Invalid depth (too high)
        with pytest.raises(ValueError):
            CitationAnalysisParams(paper_id="test123", depth=5)

        # Invalid depth (too low)
        with pytest.raises(ValueError):
            CitationAnalysisParams(paper_id="test123", depth=0)

    async def test_retraction_check_params(self) -> None:
        """RetractionCheckParams validates correctly."""
        from loom.params import RetractionCheckParams

        # Valid parameters
        params = RetractionCheckParams(query="author name", max_results=20)
        assert params.query == "author name"
        assert params.max_results == 20

        # Empty query should fail
        with pytest.raises(ValueError):
            RetractionCheckParams(query="")

        # Query too long
        with pytest.raises(ValueError):
            RetractionCheckParams(query="a" * 1000)

        # max_results too high
        with pytest.raises(ValueError):
            RetractionCheckParams(query="test", max_results=200)

    async def test_predatory_journal_check_params(self) -> None:
        """PredatoryJournalCheckParams validates correctly."""
        from loom.params import PredatoryJournalCheckParams

        # Valid parameters
        params = PredatoryJournalCheckParams(journal_name="Nature")
        assert params.journal_name == "Nature"

        # Empty journal name should fail
        with pytest.raises(ValueError):
            PredatoryJournalCheckParams(journal_name="")

        # Journal name too long
        with pytest.raises(ValueError):
            PredatoryJournalCheckParams(journal_name="a" * 1000)


class TestIntegration:
    """Integration tests combining multiple components."""

    async def test_citation_analysis_complete_workflow(self) -> None:
        """Complete workflow: fetch paper, analyze citations, return results."""
        mock_paper_data = {
            "paperId": "complete123",
            "title": "Complete Test",
            "authors": [{"name": "A"}],
            "citationCount": 100,
            "references": [
                {"paperId": "r1", "authors": [{"name": "B"}]},
            ],
            "citations": [],
            "year": 2020,
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_paper_data,
        ):
            result = await research_citation_analysis("complete123")

            # Verify complete response structure
            assert all(
                key in result
                for key in [
                    "paper_id",
                    "title",
                    "authors_count",
                    "citation_count",
                    "reference_count",
                    "self_citation_rate",
                    "mutual_citations_count",
                    "anomaly_score",
                ]
            )

    async def test_retraction_check_complete_workflow(self) -> None:
        """Complete workflow: search papers, check retractions, return results."""
        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/test",
                        "title": ["Test"],
                        "published-print": {"date-parts": [[2020, 1, 1]]},
                    }
                ]
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_retraction_check("test query")

            # Verify complete response structure
            assert all(
                key in result
                for key in [
                    "query",
                    "papers_checked",
                    "retractions_found",
                    "retraction_details",
                    "pubpeer_comments_found",
                ]
            )

    async def test_predatory_journal_complete_workflow(self) -> None:
        """Complete workflow: check journal, analyze metadata, return score."""
        mock_crossref_data = {
            "message": {
                "items": [
                    {
                        "title": "Journal",
                        "counts": {"total-dois": 100},
                    }
                ]
            }
        }

        with patch(
            "loom.tools.academic_integrity._get_json",
            return_value=mock_crossref_data,
        ):
            result = await research_predatory_journal_check("Journal")

            # Verify complete response structure
            assert all(
                key in result
                for key in [
                    "journal_name",
                    "is_in_doaj",
                    "crossref_registered",
                    "publication_count",
                    "risk_indicators",
                    "predatory_score",
                ]
            )
            # Predatory score should be 0-100
            assert 0 <= result["predatory_score"] <= 100
