"""Tests for job research tools: research_job_search and research_job_market."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from loom.tools.career.job_research import (
    _extract_skills,
    _search_adzuna,
    _search_github_jobs,
    _search_hn_hiring,
    _search_remoteok,
    research_job_market,
    research_job_search,
)


class TestExtractSkills:
    """_extract_skills extracts tech keywords from text."""

    def test_extract_skills_empty(self) -> None:
        """Empty text returns empty list."""
        result = _extract_skills("")
        assert result == []

    def test_extract_skills_python(self) -> None:
        """Extracts Python keyword."""
        text = "We are looking for a Python developer with 5 years experience"
        result = _extract_skills(text)
        assert "python" in result

    def test_extract_skills_multiple(self) -> None:
        """Extracts multiple keywords."""
        text = "Python Django React AWS developer"
        result = _extract_skills(text)
        assert "python" in result
        assert "django" in result
        assert "react" in result
        assert "aws" in result

    def test_extract_skills_respects_limit(self) -> None:
        """Results respect limit parameter."""
        text = (
            "Python Python Python Django Django React AWS "
            "Kubernetes Docker Jenkins Terraform PostgreSQL MongoDB"
        )
        result = _extract_skills(text, limit=5)
        assert len(result) <= 5

    def test_extract_skills_case_insensitive(self) -> None:
        """Skills are extracted case-insensitively."""
        text = "PYTHON, javascript, React"
        result = _extract_skills(text)
        assert "python" in result
        assert "javascript" in result
        assert "react" in result


@pytest.mark.asyncio
class TestSearchAdzuna:
    """_search_adzuna fetches from Adzuna API."""

    async def test_adzuna_missing_credentials(self) -> None:
        """Returns empty list if credentials missing."""
        # Ensure env vars are not set
        os.environ.pop("ADZUNA_APP_ID", None)
        os.environ.pop("ADZUNA_APP_KEY", None)

        result = await _search_adzuna("Python Developer")
        assert result == []

    async def test_adzuna_success(self) -> None:
        """Returns formatted job results from Adzuna API."""
        os.environ["ADZUNA_APP_ID"] = "test_id"
        os.environ["ADZUNA_APP_KEY"] = "test_key"

        mock_response = {
            "results": [
                {
                    "title": "Python Developer",
                    "company": {"display_name": "Tech Corp"},
                    "location": {"display_name": "London"},
                    "redirect_url": "https://adzuna.com/job/123",
                    "salary_min": 40000,
                    "salary_max": 60000,
                    "created": "2024-01-15T10:00:00Z",
                }
            ]
        }

        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_client.get.return_value = mock_resp

            result = await _search_adzuna("Python Developer", location="London", limit=10)

            assert len(result) == 1
            assert result[0]["title"] == "Python Developer"
            assert result[0]["company"] == "Tech Corp"
            assert result[0]["location"] == "London"
            assert result[0]["salary"] == "£40,000 - £60,000"
            assert result[0]["source"] == "adzuna"
            assert result[0]["remote"] is False

    async def test_adzuna_api_error(self) -> None:
        """Handles API errors gracefully."""
        os.environ["ADZUNA_APP_ID"] = "test_id"
        os.environ["ADZUNA_APP_KEY"] = "test_key"

        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            mock_client.get.side_effect = Exception("API Error")

            result = await _search_adzuna("Python Developer")
            assert result == []


@pytest.mark.asyncio
class TestSearchRemoteOK:
    """_search_remoteok fetches from RemoteOK API."""

    async def test_remoteok_success(self) -> None:
        """Returns formatted remote job results."""
        mock_response = [
            {
                "title": "Remote Python Developer",
                "company": "Remote Company",
                "description": "Build Python applications",
                "tags": ["python", "remote"],
                "url": "https://remoteok.com/job/456",
                "salary": "$80,000 - $120,000",
                "date": "2024-01-15T10:00:00Z",
            }
        ]

        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_client.get.return_value = mock_resp

            result = await _search_remoteok("python", limit=10)

            assert len(result) == 1
            assert result[0]["title"] == "Remote Python Developer"
            assert result[0]["remote"] is True
            assert result[0]["location"] == "Remote"
            assert result[0]["source"] == "remoteok"

    async def test_remoteok_query_filter(self) -> None:
        """Filters jobs by query in title or tags."""
        mock_response = [
            {
                "title": "Python Developer",
                "tags": ["python"],
                "company": "Company1",
                "url": "https://remoteok.com/1",
            },
            {
                "title": "JavaScript Developer",
                "tags": ["javascript"],
                "company": "Company2",
                "url": "https://remoteok.com/2",
            },
            {
                "title": "DevOps Engineer",
                "tags": ["python", "devops"],
                "company": "Company3",
                "url": "https://remoteok.com/3",
            },
        ]

        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_client.get.return_value = mock_resp

            result = await _search_remoteok("python", limit=10)

            # Should match both "Python Developer" (in title) and "DevOps Engineer" (in tags)
            assert len(result) == 2
            assert all(job["remote"] for job in result)


@pytest.mark.asyncio
class TestSearchHNHiring:
    """_search_hn_hiring fetches from HN Who's Hiring."""

    async def test_hn_hiring_success(self) -> None:
        """Returns formatted HN job results."""
        stories_response = {
            "hits": [
                {
                    "objectID": "12345",
                    "title": "Ask HN: Who is Hiring",
                }
            ]
        }

        comments_response = {
            "hits": [
                {
                    "objectID": "comment_123",
                    "text": "Looking for Python developers. Remote. $100k",
                    "created_at_i": 1705316400,
                }
            ]
        }

        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            # First call returns stories, second returns comments
            mock_resp_stories = AsyncMock()
            mock_resp_stories.json.return_value = stories_response

            mock_resp_comments = AsyncMock()
            mock_resp_comments.json.return_value = comments_response

            mock_client.get.side_effect = [mock_resp_stories, mock_resp_comments]

            result = await _search_hn_hiring("python", limit=10)

            assert len(result) == 1
            assert result[0]["source"] == "hn_hiring"
            assert result[0]["remote"] is True
            assert "python" in result[0]["title"].lower()

    async def test_hn_hiring_empty(self) -> None:
        """Handles no results gracefully."""
        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.json.return_value = {"hits": []}
            mock_client.get.return_value = mock_resp

            result = await _search_hn_hiring("python", limit=10)
            assert result == []


@pytest.mark.asyncio
class TestSearchGithubJobs:
    """_search_github_jobs fetches job postings from job boards."""

    async def test_github_jobs_success(self) -> None:
        """Returns formatted job board results."""
        mock_response = {
            "Results": [
                {
                    "Result": "Senior Python Developer - Tech Corp",
                    "FirstURL": "https://tech-corp.greenhouse.io/jobs/123",
                }
            ]
        }

        with patch("loom.tools.job_research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_client.get.return_value = mock_resp

            result = await _search_github_jobs("python", limit=10)

            assert len(result) > 0
            assert all(job["remote"] for job in result)
            assert all(job["source"] == "job_boards" for job in result)


@pytest.mark.asyncio
class TestResearchJobSearch:
    """research_job_search aggregates results from multiple sources."""

    async def test_job_search_success(self) -> None:
        """Returns aggregated job results."""
        with patch("loom.tools.career.job_research._search_adzuna") as mock_adzuna, patch(
            "loom.tools.career.job_research._search_remoteok"
        ) as mock_remoteok, patch(
            "loom.tools.career.job_research._search_hn_hiring"
        ) as mock_hn, patch(
            "loom.tools.career.job_research._search_github_jobs"
        ) as mock_github:
            mock_adzuna.return_value = [
                {
                    "title": "Python Dev",
                    "company": "Corp1",
                    "url": "http://corp1.com/job1",
                    "remote": False,
                    "source": "adzuna",
                }
            ]
            mock_remoteok.return_value = [
                {
                    "title": "Remote Python Dev",
                    "company": "Corp2",
                    "url": "http://corp2.com/job2",
                    "remote": True,
                    "source": "remoteok",
                }
            ]
            mock_hn.return_value = []
            mock_github.return_value = []

            result = await research_job_search("Python Developer", limit=20)

            assert result["query"] == "Python Developer"
            assert result["remote_only"] is False
            assert len(result["results"]) == 2
            assert result["sources_searched"] == 2
            assert result["total_results"] == 2

    async def test_job_search_remote_only(self) -> None:
        """Filters to remote jobs only."""
        with patch("loom.tools.career.job_research._search_adzuna") as mock_adzuna, patch(
            "loom.tools.career.job_research._search_remoteok"
        ) as mock_remoteok, patch(
            "loom.tools.career.job_research._search_hn_hiring"
        ) as mock_hn, patch(
            "loom.tools.career.job_research._search_github_jobs"
        ) as mock_github:
            mock_adzuna.return_value = [
                {
                    "title": "On-site Python Dev",
                    "company": "Corp1",
                    "url": "http://corp1.com/1",
                    "remote": False,
                    "source": "adzuna",
                }
            ]
            mock_remoteok.return_value = [
                {
                    "title": "Remote Python Dev",
                    "company": "Corp2",
                    "url": "http://corp2.com/2",
                    "remote": True,
                    "source": "remoteok",
                }
            ]
            mock_hn.return_value = []
            mock_github.return_value = []

            result = await research_job_search(
                "Python Developer", remote_only=True, limit=20
            )

            assert result["remote_only"] is True
            assert len(result["results"]) == 1
            assert all(job["remote"] for job in result["results"])

    async def test_job_search_deduplication(self) -> None:
        """Deduplicates results by URL."""
        with patch("loom.tools.career.job_research._search_adzuna") as mock_adzuna, patch(
            "loom.tools.career.job_research._search_remoteok"
        ) as mock_remoteok, patch(
            "loom.tools.career.job_research._search_hn_hiring"
        ) as mock_hn, patch(
            "loom.tools.career.job_research._search_github_jobs"
        ) as mock_github:
            duplicate_url = "http://example.com/job"
            mock_adzuna.return_value = [
                {
                    "title": "Python Dev",
                    "company": "Corp",
                    "url": duplicate_url,
                    "remote": False,
                    "source": "adzuna",
                }
            ]
            mock_remoteok.return_value = [
                {
                    "title": "Python Dev (Remote)",
                    "company": "Corp",
                    "url": duplicate_url,
                    "remote": True,
                    "source": "remoteok",
                }
            ]
            mock_hn.return_value = []
            mock_github.return_value = []

            result = await research_job_search("Python Developer", limit=20)

            # Should have only 1 result despite duplicate URL
            assert len(result["results"]) == 1

    async def test_job_search_respects_limit(self) -> None:
        """Respects the limit parameter."""
        with patch("loom.tools.career.job_research._search_adzuna") as mock_adzuna, patch(
            "loom.tools.career.job_research._search_remoteok"
        ) as mock_remoteok, patch(
            "loom.tools.career.job_research._search_hn_hiring"
        ) as mock_hn, patch(
            "loom.tools.career.job_research._search_github_jobs"
        ) as mock_github:
            # Return many results
            mock_adzuna.return_value = [
                {
                    "title": f"Job {i}",
                    "company": "Corp",
                    "url": f"http://example.com/{i}",
                    "remote": False,
                    "source": "adzuna",
                }
                for i in range(20)
            ]
            mock_remoteok.return_value = []
            mock_hn.return_value = []
            mock_github.return_value = []

            result = await research_job_search("Python Developer", limit=5)

            assert len(result["results"]) == 5

    async def test_job_search_with_location(self) -> None:
        """Passes location parameter to search functions."""
        with patch("loom.tools.career.job_research._search_adzuna") as mock_adzuna, patch(
            "loom.tools.career.job_research._search_remoteok"
        ) as mock_remoteok, patch(
            "loom.tools.career.job_research._search_hn_hiring"
        ) as mock_hn, patch(
            "loom.tools.career.job_research._search_github_jobs"
        ) as mock_github:
            mock_adzuna.return_value = []
            mock_remoteok.return_value = []
            mock_hn.return_value = []
            mock_github.return_value = []

            await research_job_search("Python Developer", location="London", limit=20)

            # Verify location was passed to adzuna
            mock_adzuna.assert_called_once()
            call_args = mock_adzuna.call_args
            assert call_args[1]["location"] == "London"


@pytest.mark.asyncio
class TestResearchJobMarket:
    """research_job_market aggregates market intelligence."""

    async def test_job_market_success(self) -> None:
        """Returns market intelligence with all fields."""
        mock_jobs = [
            {
                "title": "Python Developer (Remote)",
                "company": "Tech Corp",
                "location": "Remote",
                "url": "http://example.com/1",
                "salary": "£50,000 - £70,000",
                "remote": True,
                "source": "remoteok",
            },
            {
                "title": "Senior Python Engineer (Django, AWS)",
                "company": "Another Corp",
                "location": "London",
                "url": "http://example.com/2",
                "salary": "£80,000 - £120,000",
                "remote": False,
                "source": "adzuna",
            },
        ]

        with patch("loom.tools.career.job_research.research_job_search") as mock_search:
            mock_search.return_value = {
                "query": "Python Developer",
                "results": mock_jobs,
                "sources_searched": 2,
                "total_results": 2,
            }

            result = await research_job_market("Python Developer")

            assert result["role"] == "Python Developer"
            assert result["total_listings"] == 2
            assert result["salary_range"]["min"] == "£50,000"
            assert result["salary_range"]["max"] == "£120,000"
            assert result["remote_percentage"] == 50.0
            assert len(result["top_skills"]) > 0
            assert result["demand_score"] > 0
            assert len(result["sources"]) > 0

    async def test_job_market_no_results(self) -> None:
        """Returns empty market data when no jobs found."""
        with patch("loom.tools.career.job_research.research_job_search") as mock_search:
            mock_search.return_value = {
                "query": "Nonexistent Role",
                "results": [],
                "sources_searched": 0,
                "total_results": 0,
            }

            result = await research_job_market("Nonexistent Role")

            assert result["total_listings"] == 0
            assert result["top_skills"] == []
            assert result["demand_score"] == 0.0
            assert result["remote_percentage"] == 0.0

    async def test_job_market_with_location(self) -> None:
        """Passes location to job search."""
        with patch("loom.tools.career.job_research.research_job_search") as mock_search:
            mock_search.return_value = {
                "query": "Python Developer",
                "results": [],
                "sources_searched": 0,
                "total_results": 0,
            }

            await research_job_market("Python Developer", location="London")

            mock_search.assert_called_once()
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["location"] == "London"

    async def test_job_market_extracts_skills(self) -> None:
        """Extracts and ranks skills from job titles."""
        mock_jobs = [
            {
                "title": "Python Django Developer",
                "salary": "£50,000",
                "remote": False,
                "source": "adzuna",
            },
            {
                "title": "Python Django AWS Engineer",
                "salary": "£60,000",
                "remote": False,
                "source": "adzuna",
            },
            {
                "title": "Python Flask API Developer",
                "salary": "£55,000",
                "remote": True,
                "source": "remoteok",
            },
        ]

        with patch("loom.tools.career.job_research.research_job_search") as mock_search:
            mock_search.return_value = {
                "query": "Python",
                "results": mock_jobs,
                "sources_searched": 2,
                "total_results": 3,
            }

            result = await research_job_market("Python")

            # Python should be most mentioned
            assert result["top_skills"][0]["skill"] == "python"
            # Django should be second most
            skills_list = [s["skill"] for s in result["top_skills"]]
            assert "django" in skills_list


@pytest.mark.parametrize(
    "query",
    [
        "Python Developer",
        "DevOps Engineer",
        "Data Scientist",
        "Product Manager",
    ],
)
async def test_job_search_parametrized(query: str) -> None:
    """Test job search with various queries."""
    with patch("loom.tools.career.job_research._search_adzuna") as mock_adzuna, patch(
        "loom.tools.career.job_research._search_remoteok"
    ) as mock_remoteok, patch(
        "loom.tools.career.job_research._search_hn_hiring"
    ) as mock_hn, patch(
        "loom.tools.career.job_research._search_github_jobs"
    ) as mock_github:
        mock_adzuna.return_value = []
        mock_remoteok.return_value = []
        mock_hn.return_value = []
        mock_github.return_value = []

        result = await research_job_search(query, limit=20)

        assert result["query"] == query
        assert result["results"] == []
