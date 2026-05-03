"""Unit tests for trend_predictor tool — research trend analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.tools.trend_predictor import (
    _arxiv_publication_rate,
    _compute_trend_direction,
    _github_repo_momentum,
    _hackernews_discussion,
    _predict_next_3_months,
    _semantic_scholar_citations,
    research_trend_predict,
)


pytestmark = pytest.mark.asyncio

class TestArxivPublicationRate:
    """_arxiv_publication_rate extracts publication trends."""

    async def test_valid_arxiv_response(self) -> None:
        """Parse arXiv XML and extract monthly publication counts."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            # Mock arXiv XML response
            arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <published>2026-04-20T10:30:00Z</published>
    </entry>
    <entry>
        <published>2026-04-15T11:00:00Z</published>
    </entry>
    <entry>
        <published>2026-03-10T09:00:00Z</published>
    </entry>
</feed>"""

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = arxiv_xml
            mock_client.get.return_value = mock_response

            result = await _arxiv_publication_rate(mock_client, "transformers")
            assert result["total_papers"] == 3
            assert "2026-04" in result["papers_per_month"]
            assert "2026-03" in result["papers_per_month"]
            assert result["papers_per_month"]["2026-04"] == 2
            assert result["papers_per_month"]["2026-03"] == 1

        await test()

    async def test_empty_arxiv_response(self) -> None:
        """Handle empty arXiv response gracefully."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_client.get.return_value = mock_response

            result = await _arxiv_publication_rate(mock_client, "xyz")
            assert result["total_papers"] == 0
            assert result["papers_per_month"] == {}

        await test()


class TestSemanticScholarCitations:
    """_semantic_scholar_citations analyzes citation velocity."""

    async def test_valid_scholar_response(self) -> None:
        """Parse Semantic Scholar response and compute citation stats."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            scholar_data = {
                "data": [
                    {
                        "year": 2024,
                        "citationCount": 50,
                    },
                    {
                        "year": 2025,
                        "citationCount": 100,
                    },
                    {
                        "year": 2025,
                        "citationCount": 75,
                    },
                ]
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = scholar_data
            mock_client.get.return_value = mock_response

            result = await _semantic_scholar_citations(mock_client, "llm")
            assert result["max_citations"] == 100
            assert result["avg_citations"] > 0
            assert 2024 in result["citations_per_year"]
            assert 2025 in result["citations_per_year"]

        await test()

    async def test_empty_scholar_response(self) -> None:
        """Handle empty Semantic Scholar response."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            result = await _semantic_scholar_citations(mock_client, "xyz")
            assert result["avg_citations"] == 0
            assert result["max_citations"] == 0
            assert result["citations_per_year"] == {}

        await test()


class TestGithubRepoMomentum:
    """_github_repo_momentum analyzes repository growth."""

    async def test_valid_github_response(self) -> None:
        """Parse GitHub search response and compute momentum."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            github_data = {
                "items": [
                    {
                        "stargazers_count": 5000,
                        "forks_count": 500,
                    },
                    {
                        "stargazers_count": 3000,
                        "forks_count": 300,
                    },
                ]
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = github_data
            mock_client.get.return_value = mock_response

            result = await _github_repo_momentum(mock_client, "transformers")
            assert result["repos"] == 2
            assert result["total_stars"] == 8000
            assert result["avg_stars"] == 4000.0
            assert result["avg_forks"] == 400.0

        await test()

    async def test_empty_github_response(self) -> None:
        """Handle empty GitHub response."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"items": []}
            mock_client.get.return_value = mock_response

            result = await _github_repo_momentum(mock_client, "xyz")
            assert result["repos"] == 0
            assert result["total_stars"] == 0

        await test()


class TestHackernewsDiscussion:
    """_hackernews_discussion analyzes community engagement."""

    async def test_valid_hn_response(self) -> None:
        """Parse HackerNews response and compute engagement metrics."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            hn_data = {
                "hits": [
                    {
                        "points": 200,
                        "num_comments": 50,
                    },
                    {
                        "points": 150,
                        "num_comments": 30,
                    },
                ]
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = hn_data
            mock_client.get.return_value = mock_response

            result = await _hackernews_discussion(mock_client, "ai")
            assert result["stories"] == 2
            assert result["avg_points"] == 175.0
            assert result["avg_comments"] == 40.0

        await test()


class TestComputeTrendDirection:
    """_compute_trend_direction determines trend based on signals."""

    async def test_rising_trend(self) -> None:
        """Detect rising trend from strong signals."""
        arxiv_data = {
            "papers_per_month": {
                "2026-01": 10,
                "2026-02": 12,
                "2026-03": 15,
                "2026-04": 18,
                "2026-05": 20,
                "2026-06": 25,
            },
            "total_papers": 100,
        }
        semantic_data = {
            "citations_per_year": {2024: 50, 2025: 100},
            "avg_citations": 75.0,
            "max_citations": 200,
        }
        github_data = {
            "repos": 10,
            "total_stars": 50000,
            "avg_stars": 5000.0,
            "avg_forks": 500.0,
        }
        hn_data = {
            "stories": 25,
            "avg_points": 200.0,
            "avg_comments": 50.0,
        }

        trend, confidence = _compute_trend_direction(
            arxiv_data, semantic_data, github_data, hn_data
        )
        assert trend == "rising"
        assert confidence > 0.5

    async def test_declining_trend(self) -> None:
        """Detect declining trend from weak signals."""
        arxiv_data = {
            "papers_per_month": {
                "2026-01": 50,
                "2026-02": 40,
                "2026-03": 30,
                "2026-04": 20,
                "2026-05": 10,
                "2026-06": 5,
            },
            "total_papers": 155,
        }
        semantic_data = {
            "citations_per_year": {2023: 500, 2024: 100},
            "avg_citations": 0.5,
            "max_citations": 5,
        }
        github_data = {
            "repos": 2,
            "total_stars": 10,
            "avg_stars": 5.0,
            "avg_forks": 1.0,
        }
        hn_data = {
            "stories": 1,
            "avg_points": 10.0,
            "avg_comments": 2.0,
        }

        trend, confidence = _compute_trend_direction(
            arxiv_data, semantic_data, github_data, hn_data
        )
        assert trend == "declining"


class TestPredictNext3Months:
    """_predict_next_3_months forecasts future activity."""

    async def test_predict_rising_trend(self) -> None:
        """Predict increased activity for rising trend."""
        arxiv_data = {
            "papers_per_month": {
                "2026-01": 10,
                "2026-02": 12,
                "2026-03": 15,
                "2026-04": 18,
                "2026-05": 20,
                "2026-06": 25,
            },
            "total_papers": 100,
        }

        prediction = _predict_next_3_months(arxiv_data, "rising")
        assert prediction["predicted_papers"] > 0
        assert prediction["growth_rate"] != 0

    async def test_predict_stable_trend(self) -> None:
        """Predict stable activity for stable trend."""
        arxiv_data = {
            "papers_per_month": {
                "2026-01": 15,
                "2026-02": 15,
                "2026-03": 15,
                "2026-04": 15,
                "2026-05": 15,
                "2026-06": 15,
            },
            "total_papers": 90,
        }

        prediction = _predict_next_3_months(arxiv_data, "stable")
        assert prediction["predicted_papers"] == 15


class TestResearchTrendPredict:
    """research_trend_predict main function."""

    async def test_basic_trend_prediction(self) -> None:
        """Basic trend prediction returns expected structure."""
        with patch("loom.tools.trend_predictor._arxiv_publication_rate") as mock_arxiv:
            with patch(
                "loom.tools.trend_predictor._semantic_scholar_citations"
            ) as mock_semantic:
                with patch(
                    "loom.tools.trend_predictor._github_repo_momentum"
                ) as mock_github:
                    with patch(
                        "loom.tools.trend_predictor._hackernews_discussion"
                    ) as mock_hn:
                        mock_arxiv.return_value = {
                            "papers_per_month": {"2026-06": 10},
                            "total_papers": 10,
                        }
                        mock_semantic.return_value = {
                            "citations_per_year": {2026: 100},
                            "avg_citations": 50.0,
                            "max_citations": 200,
                        }
                        mock_github.return_value = {
                            "repos": 5,
                            "total_stars": 1000,
                            "avg_stars": 200.0,
                            "avg_forks": 50.0,
                        }
                        mock_hn.return_value = {
                            "stories": 5,
                            "avg_points": 100.0,
                            "avg_comments": 20.0,
                        }

                        result = await research_trend_predict("transformers")

                        assert result["topic"] == "transformers"
                        assert "trend_direction" in result
                        assert "confidence" in result
                        assert "publication_rate" in result
                        assert "citation_velocity" in result
                        assert "github_momentum" in result
                        assert "community_buzz" in result
                        assert "prediction_next_3_months" in result
                        assert "analysis_timestamp" in result

    async def test_invalid_topic_handles_gracefully(self) -> None:
        """Invalid topic still returns valid structure."""
        with patch("loom.tools.trend_predictor._arxiv_publication_rate") as mock_arxiv:
            with patch(
                "loom.tools.trend_predictor._semantic_scholar_citations"
            ) as mock_semantic:
                with patch(
                    "loom.tools.trend_predictor._github_repo_momentum"
                ) as mock_github:
                    with patch(
                        "loom.tools.trend_predictor._hackernews_discussion"
                    ) as mock_hn:
                        mock_arxiv.return_value = {
                            "papers_per_month": {},
                            "total_papers": 0,
                        }
                        mock_semantic.return_value = {
                            "citations_per_year": {},
                            "avg_citations": 0,
                            "max_citations": 0,
                        }
                        mock_github.return_value = {
                            "repos": 0,
                            "total_stars": 0,
                            "avg_stars": 0,
                            "avg_forks": 0,
                        }
                        mock_hn.return_value = {
                            "stories": 0,
                            "avg_points": 0.0,
                            "avg_comments": 0.0,
                        }

                        result = await research_trend_predict("nonexistent_topic_xyz")

                        assert result["topic"] == "nonexistent_topic_xyz"
                        assert "trend_direction" in result
                        assert result["trend_direction"] in ("rising", "stable", "declining")
