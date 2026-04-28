"""Tests for career trajectory and market velocity tools.

Tests research_career_trajectory and research_market_velocity tools.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.career_trajectory import (
    research_career_trajectory,
    research_market_velocity,
)


@pytest.mark.asyncio
class TestCareerTrajectory:
    """Tests for research_career_trajectory tool."""

    def test_invalid_person_name_empty(self) -> None:
        """Empty person name returns error."""
        result = research_career_trajectory("")
        assert "error" in result
        assert "must be 1-200 characters" in result["error"]

    def test_invalid_person_name_too_long(self) -> None:
        """Person name > 200 chars returns error."""
        long_name = "A" * 201
        result = research_career_trajectory(long_name)
        assert "error" in result

    def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")

            required_fields = [
                "person_name",
                "domain_filter",
                "academic_publications",
                "github_activity",
                "orcid_profile",
                "career_stages",
                "growth_trajectory",
                "experience_level",
                "combined_impact_score",
            ]
            for field in required_fields:
                assert field in result

    def test_person_name_trimmed(self) -> None:
        """Person name is trimmed."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("  John Doe  ")
            assert result["person_name"] == "John Doe"

    def test_domain_filter_optional(self) -> None:
        """Domain filter is optional."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe", domain="machine-learning")
            assert result["domain_filter"] == "machine-learning"

    def test_academic_publications_structure(self) -> None:
        """Academic publications result has correct structure."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_Scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")

            pub = result["academic_publications"]
            required_pub_fields = ["count", "h_index", "topics", "semantic_scholar_id"]
            for field in required_pub_fields:
                assert field in pub

    def test_github_activity_structure(self) -> None:
        """GitHub activity result has correct structure."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")

            github = result["github_activity"]
            required_github_fields = [
                "username",
                "profile_url",
                "repo_count",
                "total_stars",
                "primary_languages",
                "company",
                "location",
            ]
            for field in required_github_fields:
                assert field in github

    def test_orcid_profile_structure(self) -> None:
        """ORCID profile result has correct structure."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")

            orcid = result["orcid_profile"]
            required_orcid_fields = [
                "orcid_id",
                "profile_url",
                "work_count",
                "biography",
            ]
            for field in required_orcid_fields:
                assert field in orcid

    def test_growth_trajectory_valid_values(self) -> None:
        """Growth trajectory is one of valid values."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")
            assert result["growth_trajectory"] in [
                "rising",
                "stable",
                "declining",
                "unknown",
            ]

    def test_experience_level_valid_values(self) -> None:
        """Experience level is valid."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")
            assert result["experience_level"] in [
                "Junior",
                "Mid-Level",
                "Senior",
                "Unknown",
            ]

    def test_impact_score_in_valid_range(self) -> None:
        """Combined impact score is between 0-100."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_Scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")
            assert 0.0 <= result["combined_impact_score"] <= 100.0

    def test_with_scholar_data(self) -> None:
        """Impact score increases with Semantic Scholar data."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {
                "author_id": "123",
                "name": "John Doe",
                "paper_count": 50,
                "h_index": 25,
                "topics": [("ML", 30), ("AI", 25)],
            }
            mock_github.return_value = {}
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")
            assert result["academic_publications"]["count"] == 50
            assert result["academic_publications"]["h_index"] == 25
            assert result["combined_impact_score"] > 0

    def test_with_github_data(self) -> None:
        """Impact score increases with GitHub data."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_Scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {}
            mock_github.return_value = {
                "username": "johndoe",
                "profile_url": "https://github.com/johndoe",
                "repo_count": 75,
                "total_stars": 5000,
                "languages": [("Python", 20), ("Go", 15)],
                "company": "Google",
                "location": "Mountain View",
            }
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")
            assert result["github_activity"]["username"] == "johndoe"
            assert result["github_activity"]["repo_count"] == 75
            assert result["github_activity"]["total_stars"] == 5000
            assert result["combined_impact_score"] > 0

    def test_career_stages_generated(self) -> None:
        """Career stages are generated from available data."""
        with patch(
            "loom.tools.career_trajectory._search_semantic_Scholar"
        ) as mock_scholar, patch(
            "loom.tools.career_trajectory._search_github_user"
        ) as mock_github, patch(
            "loom.tools.career_trajectory._search_orcid"
        ) as mock_orcid:
            mock_scholar.return_value = {
                "author_id": "123",
                "name": "John Doe",
                "paper_count": 100,
                "h_index": 35,
                "topics": [("ML", 50)],
            }
            mock_github.return_value = {
                "username": "johndoe",
                "profile_url": "https://github.com/johndoe",
                "repo_count": 75,
                "total_stars": 5000,
                "languages": [("Python", 20)],
                "company": "Google",
                "location": "Mountain View",
            }
            mock_orcid.return_value = {}

            result = research_career_trajectory("John Doe")
            stages = result["career_stages"]
            assert len(stages) >= 2  # Should have academic and GitHub stages
            assert all("stage" in s and "source" in s for s in stages)


@pytest.mark.asyncio
class TestMarketVelocity:
    """Tests for research_market_velocity tool."""

    def test_invalid_skill_empty(self) -> None:
        """Empty skill returns error."""
        result = research_market_velocity("")
        assert "error" in result
        assert "must be 1-100 characters" in result["error"]

    def test_invalid_skill_too_long(self) -> None:
        """Skill > 100 chars returns error."""
        long_skill = "A" * 101
        result = research_market_velocity(long_skill)
        assert "error" in result

    def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("kubernetes")

            required_fields = [
                "skill",
                "location",
                "github_momentum",
                "discussion_velocity",
                "academic_momentum",
                "overall_velocity",
                "demand_trend",
                "confidence_score",
            ]
            for field in required_fields:
                assert field in result

    def test_skill_trimmed(self) -> None:
        """Skill name is trimmed and lowercased."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("  Kubernetes  ")
            assert result["skill"] == "kubernetes"

    def test_location_optional(self) -> None:
        """Location is optional parameter."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust", location="silicon-valley")
            assert result["location"] == "silicon-valley"

    def test_github_momentum_structure(self) -> None:
        """GitHub momentum has correct structure."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust")

            momentum = result["github_momentum"]
            required_fields = [
                "total_stars",
                "avg_stars_per_repo",
                "top_repos_analyzed",
                "repo_count",
            ]
            for field in required_fields:
                assert field in momentum

    def test_discussion_velocity_structure(self) -> None:
        """Discussion velocity has correct structure."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust")

            velocity = result["discussion_velocity"]
            required_fields = [
                "recent_discussions",
                "avg_points_per_story",
                "top_stories",
            ]
            for field in required_fields:
                assert field in velocity

    def test_academic_momentum_structure(self) -> None:
        """Academic momentum has correct structure."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust")

            momentum = result["academic_momentum"]
            required_fields = [
                "total_papers",
                "avg_papers_per_month",
                "months_with_papers",
            ]
            for field in required_fields:
                assert field in momentum

    def test_overall_velocity_valid_values(self) -> None:
        """Overall velocity is valid value."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust")
            assert result["overall_velocity"] in [
                "hot",
                "warm",
                "stable",
                "cooling",
                "unknown",
            ]

    def test_demand_trend_valid_values(self) -> None:
        """Demand trend is valid value."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust")
            assert result["demand_trend"] in [
                "rapidly_growing",
                "growing",
                "stable",
                "declining",
                "unknown",
            ]

    def test_confidence_score_in_valid_range(self) -> None:
        """Confidence score is between 0-100."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {}
            mock_hn.return_value = {}
            mock_arxiv.return_value = {}

            result = research_market_velocity("rust")
            assert 0.0 <= result["confidence_score"] <= 100.0

    def test_hot_skill_detection(self) -> None:
        """Hot skill is detected when all signals are strong."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {
                "total_count": 10000,
                "top_repos": 20,
                "total_stars": 50000,
                "avg_stars": 2500,
                "creation_momentum": {"2024-01": 5, "2024-02": 5},
            }
            mock_hn.return_value = {
                "total_hits": 500,
                "recent_discussions": 50,
                "top_stories": [
                    {"title": "Hot tech", "points": 200, "num_comments": 50}
                ] * 5,
            }
            mock_arxiv.return_value = {
                "total_papers": 100,
                "papers_by_month": {"2024-01": 5, "2024-02": 5},
                "recent_months": 2,
            }

            result = research_market_velocity("hot-new-tech")
            assert result["overall_velocity"] == "hot"
            assert result["demand_trend"] == "rapidly_growing"

    def test_cooling_skill_detection(self) -> None:
        """Cooling skill is detected when all signals are weak."""
        with patch(
            "loom.tools.career_trajectory._search_github_trending"
        ) as mock_gh, patch(
            "loom.tools.career_trajectory._search_hacker_news"
        ) as mock_hn, patch(
            "loom.tools.career_trajectory._search_arxiv_papers"
        ) as mock_arxiv:
            mock_gh.return_value = {
                "total_count": 10,
                "top_repos": 5,
                "total_stars": 50,
                "avg_stars": 10,
                "creation_momentum": {},
            }
            mock_hn.return_value = {
                "total_hits": 5,
                "recent_discussions": 1,
                "top_stories": [],
            }
            mock_arxiv.return_value = {
                "total_papers": 2,
                "papers_by_month": {},
                "recent_months": 0,
            }

            result = research_market_velocity("old-tech")
            assert result["overall_velocity"] == "cooling"
            assert result["demand_trend"] == "declining"
