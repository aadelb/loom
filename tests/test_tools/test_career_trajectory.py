"""Tests for career trajectory and market velocity tools.

Tests research_career_trajectory and research_market_velocity tools.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from loom.tools.career.career_trajectory import (
    research_career_trajectory,
    research_market_velocity,
)


pytestmark = pytest.mark.asyncio

class TestCareerTrajectory:
    """Tests for research_career_trajectory tool."""

    async def test_invalid_person_name_empty(self) -> None:
        """Empty person name returns error."""
        result = await research_career_trajectory("")
        assert "error" in result
        assert "must be 1-200 characters" in result["error"]

    async def test_invalid_person_name_too_long(self) -> None:
        """Person name > 200 chars returns error."""
        long_name = "A" * 201
        result = await research_career_trajectory(long_name)
        assert "error" in result

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

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

    async def test_person_name_trimmed(self) -> None:
        """Person name is trimmed."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("  John Doe  ")
            assert result["person_name"] == "John Doe"

    async def test_domain_filter_optional(self) -> None:
        """Domain filter is optional."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe", domain="machine-learning")
            assert result["domain_filter"] == "machine-learning"

    async def test_academic_publications_structure(self) -> None:
        """Academic publications result has correct structure."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

            pub = result["academic_publications"]
            required_pub_fields = ["count", "h_index", "topics", "semantic_scholar_id"]
            for field in required_pub_fields:
                assert field in pub

    async def test_github_activity_structure(self) -> None:
        """GitHub activity result has correct structure."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

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

    async def test_orcid_profile_structure(self) -> None:
        """ORCID profile result has correct structure."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

            orcid = result["orcid_profile"]
            required_orcid_fields = ["orcid_id", "biography", "profile_url", "work_count"]
            for field in required_orcid_fields:
                assert field in orcid

    async def test_impact_score_in_valid_range(self) -> None:
        """Combined impact score is 0-100."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

            score = result["combined_impact_score"]
            assert 0 <= score <= 100

    async def test_with_github_data(self) -> None:
        """GitHub data is included in result."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={"username": "johndoe"},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

            assert result["github_activity"]["username"] == "johndoe"

    async def test_career_stages_generated(self) -> None:
        """Career stages are generated."""
        with patch(
            "loom.tools.career.career_trajectory._search_semantic_scholar",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_github_user",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_orcid",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_career_trajectory("John Doe")

            stages = result["career_stages"]
            assert isinstance(stages, list)
            assert len(stages) >= 0


class TestMarketVelocity:
    """Tests for research_market_velocity tool."""

    async def test_invalid_skill_empty(self) -> None:
        """Empty skill returns error."""
        result = await research_market_velocity("")
        assert "error" in result

    async def test_invalid_skill_too_long(self) -> None:
        """Skill > 100 chars returns error."""
        long_skill = "A" * 101
        result = await research_market_velocity(long_skill)
        assert "error" in result

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch(
            "loom.tools.career.career_trajectory._search_github_trending",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_hacker_news",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_arxiv_papers",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_market_velocity("python")

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

    async def test_skill_trimmed(self) -> None:
        """Skill is trimmed."""
        with patch(
            "loom.tools.career.career_trajectory._search_github_trending",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_hacker_news",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_arxiv_papers",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_market_velocity("  python  ")
            assert result["skill"] == "python"

    async def test_location_optional(self) -> None:
        """Location parameter is optional."""
        with patch(
            "loom.tools.career.career_trajectory._search_github_trending",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_hacker_news",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_arxiv_papers",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_market_velocity("rust", location="silicon-valley")
            assert result["location"] == "silicon-valley"

    async def test_confidence_score_in_range(self) -> None:
        """Confidence score is 0-100."""
        with patch(
            "loom.tools.career.career_trajectory._search_github_trending",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_hacker_news",
            new_callable=AsyncMock,
            return_value={},
        ), patch(
            "loom.tools.career.career_trajectory._search_arxiv_papers",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await research_market_velocity("go")
            assert 0 <= result["confidence_score"] <= 100

    async def test_hot_skill_detection(self) -> None:
        """Hot skill is detected when all signals are strong."""
        with patch(
            "loom.tools.career.career_trajectory._search_github_trending",
            new_callable=AsyncMock,
            return_value={
                "total_count": 100,
                "top_repos": 50,
                "total_stars": 10000,
                "avg_stars": 200,
                "creation_momentum": {},
            },
        ), patch(
            "loom.tools.career.career_trajectory._search_hacker_news",
            new_callable=AsyncMock,
            return_value={
                "total_hits": 500,
                "recent_discussions": 50,
                "top_stories": [
                    {"title": "Hot tech", "points": 200, "num_comments": 50}
                ] * 5,
            },
        ), patch(
            "loom.tools.career.career_trajectory._search_arxiv_papers",
            new_callable=AsyncMock,
            return_value={
                "total_papers": 100,
                "papers_by_month": {"2024-01": 5, "2024-02": 5},
                "recent_months": 2,
            },
        ):
            result = await research_market_velocity("hot-new-tech")
            assert result["overall_velocity"] == "hot"
            assert result["demand_trend"] == "rapidly_growing"

    async def test_cooling_skill_detection(self) -> None:
        """Cooling skill is detected when all signals are weak."""
        with patch(
            "loom.tools.career.career_trajectory._search_github_trending",
            new_callable=AsyncMock,
            return_value={
                "total_count": 10,
                "top_repos": 5,
                "total_stars": 50,
                "avg_stars": 10,
                "creation_momentum": {},
            },
        ), patch(
            "loom.tools.career.career_trajectory._search_hacker_news",
            new_callable=AsyncMock,
            return_value={
                "total_hits": 0,
                "recent_discussions": 0,
                "top_stories": [],
            },
        ), patch(
            "loom.tools.career.career_trajectory._search_arxiv_papers",
            new_callable=AsyncMock,
            return_value={
                "total_papers": 0,
                "papers_by_month": {},
                "recent_months": 0,
            },
        ):
            result = await research_market_velocity("old-tech")
            assert result["overall_velocity"] == "cooling"
            assert result["demand_trend"] == "declining"
