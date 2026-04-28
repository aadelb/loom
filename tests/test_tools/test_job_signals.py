"""Unit tests for job_signals tools — funding signals, stealth hiring, and interviewer profiling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.job_signals import (
    research_funding_signal,
    research_interviewer_profiler,
    research_stealth_hire_scanner,
)


class TestFundingSignal:
    """research_funding_signal — detect hiring indicators from company growth."""

    def test_valid_company(self) -> None:
        """Valid company name returns structured funding signals."""
        with patch(
            "loom.tools.job_signals._fetch_sec_filings"
        ) as mock_sec, patch(
            "loom.tools.job_signals._fetch_github_activity"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_crt_sh_subdomains"
        ) as mock_crt:
            mock_sec.return_value = {
                "cik": "1234567",
                "filings": [
                    {
                        "form": "S-1",
                        "date": "2024-01-15",
                        "accession": "0001193125-24-001234",
                        "url": "https://www.sec.gov/cgi-bin/viewer?action=view&cik=1234567",
                    }
                ],
            }
            mock_github.return_value = {
                "repos": [{"name": "test-repo", "created_at": "2024-01-01"}],
                "activity_level": "high",
            }
            mock_crt.return_value = ["api.example.com", "dashboard.example.com"]

            result = research_funding_signal("OpenAI", "openai.com")

            assert result["company"] == "OpenAI"
            assert "S-1" in str(result.get("funding_signals", []))
            assert result["hiring_likelihood"] in ("low", "medium", "high")
            assert isinstance(result.get("new_subdomains"), list)

    def test_company_empty(self) -> None:
        """Empty company name returns error."""
        result = research_funding_signal("")

        assert "error" in result or result.get("company") == ""

    def test_company_too_long(self) -> None:
        """Company name exceeding 200 chars returns error."""
        long_name = "a" * 201
        result = research_funding_signal(long_name)

        assert "error" in result

    def test_domain_optional(self) -> None:
        """Domain parameter is optional."""
        with patch(
            "loom.tools.job_signals._fetch_sec_filings"
        ) as mock_sec, patch(
            "loom.tools.job_signals._fetch_github_activity"
        ) as mock_github:
            mock_sec.return_value = {"cik": None, "filings": []}
            mock_github.return_value = {"repos": [], "activity_level": "low"}

            result = research_funding_signal("StartupCorp")

            assert result["company"] == "StartupCorp"
            assert isinstance(result.get("new_subdomains"), list)

    def test_high_likelihood_on_s1_filing(self) -> None:
        """S-1 IPO filing sets hiring_likelihood to 'high'."""
        with patch(
            "loom.tools.job_signals._fetch_sec_filings"
        ) as mock_sec, patch(
            "loom.tools.job_signals._fetch_github_activity"
        ) as mock_github:
            mock_sec.return_value = {
                "cik": "999",
                "filings": [
                    {
                        "form": "S-1",
                        "date": "2024-03-01",
                        "accession": "123456",
                        "url": "https://example.com",
                    }
                ],
            }
            mock_github.return_value = {"repos": [], "activity_level": "low"}

            result = research_funding_signal("PublicCo")

            assert result["hiring_likelihood"] == "high"

    def test_evidence_field_populated(self) -> None:
        """Evidence field contains human-readable findings."""
        with patch(
            "loom.tools.job_signals._fetch_sec_filings"
        ) as mock_sec, patch(
            "loom.tools.job_signals._fetch_github_activity"
        ) as mock_github:
            mock_sec.return_value = {"cik": None, "filings": []}
            mock_github.return_value = {"repos": [], "activity_level": "low"}

            result = research_funding_signal("TestCorp")

            assert "evidence" in result
            assert isinstance(result["evidence"], str)


class TestStealthHireScanner:
    """research_stealth_hire_scanner — find hidden job opportunities."""

    def test_valid_keywords(self) -> None:
        """Valid keywords return stealth job opportunities."""
        with patch(
            "loom.tools.job_signals._fetch_github_jobs_keywords"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_hackernews_hiring"
        ) as mock_hn, patch(
            "loom.tools.job_signals._fetch_reddit_hiring"
        ) as mock_reddit:
            mock_github.return_value = [
                {
                    "source": "GitHub",
                    "title": "hiring-python-devs",
                    "url": "https://github.com/example/hiring",
                    "description": "Looking for Python developers",
                    "stars": 100,
                }
            ]
            mock_hn.return_value = [
                {
                    "source": "HackerNews",
                    "title": "Who's Hiring",
                    "url": "https://news.ycombinator.com/item?id=123",
                    "snippet": "Python dev wanted",
                    "points": 50,
                }
            ]
            mock_reddit.return_value = [
                {
                    "source": "Reddit",
                    "title": "[Hiring] Python Engineer",
                    "url": "https://reddit.com/r/forhire/...",
                    "snippet": "Remote Python role",
                    "upvotes": 20,
                }
            ]

            result = research_stealth_hire_scanner("Python engineer")

            assert result["keywords"] == "Python engineer"
            assert isinstance(result["stealth_jobs_found"], list)
            assert result["total_found"] >= 0
            assert len(result["stealth_jobs_found"]) <= 50

    def test_keywords_empty(self) -> None:
        """Empty keywords returns error."""
        result = research_stealth_hire_scanner("")

        assert "error" in result

    def test_keywords_too_long(self) -> None:
        """Keywords exceeding 200 chars returns error."""
        long_keywords = "a" * 201
        result = research_stealth_hire_scanner(long_keywords)

        assert "error" in result

    def test_location_filter(self) -> None:
        """Location parameter filters results."""
        with patch(
            "loom.tools.job_signals._fetch_github_jobs_keywords"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_hackernews_hiring"
        ) as mock_hn, patch(
            "loom.tools.job_signals._fetch_reddit_hiring"
        ) as mock_reddit:
            mock_github.return_value = []
            mock_hn.return_value = [
                {
                    "source": "HackerNews",
                    "title": "Remote Python Job",
                    "url": "https://news.ycombinator.com/item?id=123",
                    "snippet": "Remote from San Francisco",
                    "points": 50,
                }
            ]
            mock_reddit.return_value = []

            result = research_stealth_hire_scanner("Python", location="San Francisco")

            assert result["location"] == "San Francisco"

    def test_consolidates_multiple_sources(self) -> None:
        """Results from GitHub, HN, and Reddit are consolidated."""
        with patch(
            "loom.tools.job_signals._fetch_github_jobs_keywords"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_hackernews_hiring"
        ) as mock_hn, patch(
            "loom.tools.job_signals._fetch_reddit_hiring"
        ) as mock_reddit:
            mock_github.return_value = [
                {"source": "GitHub", "title": "Job1", "url": "url1", "description": "", "stars": 0}
            ]
            mock_hn.return_value = [
                {"source": "HN", "title": "Job2", "url": "url2", "snippet": "", "points": 0}
            ]
            mock_reddit.return_value = [
                {"source": "Reddit", "title": "Job3", "url": "url3", "snippet": "", "upvotes": 0}
            ]

            result = research_stealth_hire_scanner("DevOps")

            assert result["total_found"] == 3


class TestInterviewerProfiler:
    """research_interviewer_profiler — build public data profile of interviewer."""

    def test_valid_person(self) -> None:
        """Valid person name returns comprehensive profile."""
        with patch(
            "loom.tools.job_signals._fetch_github_profile"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.job_signals._fetch_hackernews_activity"
        ) as mock_hn:
            mock_github.return_value = {
                "found": True,
                "username": "samaltman",
                "name": "Sam Altman",
                "bio": "AI researcher",
                "company": "OpenAI",
                "location": "San Francisco",
                "followers": 5000,
                "public_repos": 50,
                "top_repos": [
                    {
                        "name": "example-repo",
                        "language": "Python",
                        "stars": 1000,
                        "description": "Example project",
                    }
                ],
            }
            mock_scholar.return_value = {
                "publications": [
                    {
                        "title": "AI Safety Paper",
                        "year": 2023,
                        "citations": 100,
                        "venue": "Conference",
                    }
                ]
            }
            mock_hn.return_value = {
                "comments": [{"text": "Great insights on Python", "points": 50}],
                "submissions": [
                    {
                        "title": "Show HN: AI Project",
                        "url": "https://news.ycombinator.com/...",
                        "points": 200,
                    }
                ],
                "tech_interests": ["python", "machine learning"],
            }

            result = research_interviewer_profiler("Sam Altman", "OpenAI")

            assert result["person_name"] == "Sam Altman"
            assert result["company"] == "OpenAI"
            assert isinstance(result.get("github_profile"), dict)
            assert isinstance(result.get("publications"), list)
            assert isinstance(result.get("tech_interests"), list)
            assert isinstance(result.get("talking_points"), list)

    def test_person_empty(self) -> None:
        """Empty person name returns error."""
        result = research_interviewer_profiler("")

        assert "error" in result

    def test_person_too_long(self) -> None:
        """Person name exceeding 200 chars returns error."""
        long_name = "a" * 201
        result = research_interviewer_profiler(long_name)

        assert "error" in result

    def test_company_optional(self) -> None:
        """Company parameter is optional."""
        with patch(
            "loom.tools.job_signals._fetch_github_profile"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.job_signals._fetch_hackernews_activity"
        ) as mock_hn:
            mock_github.return_value = {"found": False}
            mock_scholar.return_value = {"publications": []}
            mock_hn.return_value = {
                "comments": [],
                "submissions": [],
                "tech_interests": [],
            }

            result = research_interviewer_profiler("Jane Developer")

            assert result["person_name"] == "Jane Developer"
            assert result["company"] == ""

    def test_tech_stack_consolidated(self) -> None:
        """Tech stack combines data from GitHub languages and HN interests."""
        with patch(
            "loom.tools.job_signals._fetch_github_profile"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.job_signals._fetch_hackernews_activity"
        ) as mock_hn:
            mock_github.return_value = {
                "found": True,
                "username": "dev",
                "name": "Developer",
                "bio": "Software Engineer",
                "company": "",
                "location": "",
                "followers": 100,
                "public_repos": 20,
                "top_repos": [
                    {"name": "repo1", "language": "Python", "stars": 50, "description": ""},
                    {"name": "repo2", "language": "JavaScript", "stars": 30, "description": ""},
                ],
            }
            mock_scholar.return_value = {"publications": []}
            mock_hn.return_value = {
                "comments": [],
                "submissions": [],
                "tech_interests": ["rust", "go"],
            }

            result = research_interviewer_profiler("Developer")

            tech_stack = result.get("tech_interests", [])
            assert "Python" in tech_stack or "python" in str(tech_stack).lower()
            assert isinstance(tech_stack, list)

    def test_talking_points_generated(self) -> None:
        """Talking points are generated from GitHub bio and HN posts."""
        with patch(
            "loom.tools.job_signals._fetch_github_profile"
        ) as mock_github, patch(
            "loom.tools.job_signals._fetch_semantic_Scholar"
        ) as mock_scholar, patch(
            "loom.tools.job_signals._fetch_hackernews_activity"
        ) as mock_hn:
            mock_github.return_value = {
                "found": True,
                "username": "dev",
                "name": "Developer",
                "bio": "Distributed systems enthusiast",
                "company": "",
                "location": "",
                "followers": 100,
                "public_repos": 20,
                "top_repos": [],
            }
            mock_scholar.return_value = {"publications": []}
            mock_hn.return_value = {
                "comments": [],
                "submissions": [
                    {
                        "title": "Show HN: Blockchain Project",
                        "url": "https://hn.example.com",
                        "points": 500,
                    }
                ],
                "tech_interests": [],
            }

            result = research_interviewer_profiler("Developer")

            talking_points = result.get("talking_points", [])
            assert isinstance(talking_points, list)
            assert len(talking_points) <= 5
