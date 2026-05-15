"""Unit tests for extended OSINT tools — social engineering assessment and behavioral fingerprinting."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from loom.tools.intelligence.osint_extended import (
    _estimate_timezone_from_hours,
    _extract_interests_from_text,
    _extract_skills_from_repos,
    research_behavioral_fingerprint,
    research_social_engineering_score,
)


pytestmark = pytest.mark.asyncio

class TestEstimateTimezoneFromHours:
    """Timezone estimation utility tests."""

    async def test_estimate_utc_timezone(self) -> None:
        """Estimate UTC timezone from 0-4 hours."""
        result = _estimate_timezone_from_hours([0, 1, 2, 3])
        assert "UTC+0" in result or "London" in result

    async def test_estimate_asia_timezone(self) -> None:
        """Estimate Asia timezone from 8-12 hours."""
        result = _estimate_timezone_from_hours([8, 9, 10, 11])
        assert "UTC+8" in result or "Asia" in result or "Singapore" in result

    async def test_estimate_us_pacific_timezone(self) -> None:
        """Estimate US Pacific timezone from 16-20 hours."""
        result = _estimate_timezone_from_hours([16, 17, 18, 19])
        assert "UTC-" in result or "Pacific" in result or "Mountain" in result

    async def test_estimate_empty_hours(self) -> None:
        """Handle empty hours list."""
        result = _estimate_timezone_from_hours([])
        assert result == "Unknown"

    async def test_estimate_mixed_hours(self) -> None:
        """Average mixed hours across day."""
        # Mix of early morning (2) and evening (20)
        result = _estimate_timezone_from_hours([2, 20])
        # Should estimate something reasonable
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_estimate_single_hour(self) -> None:
        """Handle single hour."""
        result = _estimate_timezone_from_hours([12])
        assert isinstance(result, str)


class TestExtractInterestsFromText:
    """Interest extraction utility tests."""

    async def test_extract_tech_interests(self) -> None:
        """Extract technology-related interests."""
        text = "I love Python and JavaScript programming"
        interests = _extract_interests_from_text(text)

        assert "Python" in interests or "python" in str(interests).lower()
        assert "Javascript" in interests or "javascript" in str(interests).lower()

    async def test_extract_multiple_interests(self) -> None:
        """Extract multiple interest categories."""
        text = "Interested in Rust, Docker, and Machine Learning. Also love gaming."
        interests = _extract_interests_from_text(text)

        assert len(interests) > 0

    async def test_extract_case_insensitive(self) -> None:
        """Interest extraction is case-insensitive."""
        text1 = "I like PYTHON"
        text2 = "I like python"

        interests1 = _extract_interests_from_text(text1)
        interests2 = _extract_interests_from_text(text2)

        # Both should identify Python
        assert len(interests1) == len(interests2)

    async def test_extract_empty_text(self) -> None:
        """Handle empty text."""
        result = _extract_interests_from_text("")
        assert isinstance(result, list)
        assert len(result) == 0

    async def test_extract_sorted_output(self) -> None:
        """Interests returned in sorted order."""
        text = "Python JavaScript Rust"
        interests = _extract_interests_from_text(text)

        if len(interests) > 1:
            assert interests == sorted(interests)

    async def test_extract_no_duplicates(self) -> None:
        """No duplicate interests."""
        text = "Python Python Python"
        interests = _extract_interests_from_text(text)

        # Should have at most 1 Python entry
        python_count = sum(1 for i in interests if "python" in i.lower())
        assert python_count <= 1


class TestExtractSkillsFromRepos:
    """Skill extraction from repositories tests."""

    async def test_extract_language_skills(self) -> None:
        """Extract programming languages from repos."""
        repos = [
            {"language": "Python", "topics": []},
            {"language": "JavaScript", "topics": []},
            {"language": "Rust", "topics": []},
        ]

        skills = _extract_skills_from_repos(repos)

        assert "Python" in skills
        assert "JavaScript" in skills
        assert "Rust" in skills

    async def test_extract_topic_skills(self) -> None:
        """Extract topics as skills."""
        repos = [
            {"language": "Python", "topics": ["machine-learning", "nlp"]},
            {"language": None, "topics": ["kubernetes", "devops"]},
        ]

        skills = _extract_skills_from_repos(repos)

        assert "machine-learning" in skills or "machine_learning" in str(
            skills
        ).lower()
        assert "kubernetes" in skills

    async def test_extract_mixed_repo_data(self) -> None:
        """Handle repos with missing language or topics."""
        repos = [
            {"language": "Python"},  # Missing topics
            {"topics": ["AI"]},  # Missing language
            {"language": None, "topics": None},  # Both missing
        ]

        skills = _extract_skills_from_repos(repos)

        assert isinstance(skills, list)

    async def test_extract_empty_repos(self) -> None:
        """Handle empty repos list."""
        skills = _extract_skills_from_repos([])
        assert skills == []

    async def test_extract_sorted_skills(self) -> None:
        """Skills returned in sorted order."""
        repos = [
            {"language": "Rust", "topics": []},
            {"language": "Python", "topics": []},
        ]

        skills = _extract_skills_from_repos(repos)

        if len(skills) > 1:
            assert skills == sorted(skills)

    async def test_extract_no_duplicate_skills(self) -> None:
        """No duplicate skills."""
        repos = [
            {"language": "Python", "topics": ["python-package"]},
        ]

        skills = _extract_skills_from_repos(repos)

        # Should not have duplicate Python entries
        python_count = sum(1 for s in skills if "python" in s.lower())
        assert python_count <= 2  # Language + topic


class TestSocialEngineeringScore:
    """research_social_engineering_score tests."""

    async def test_social_engineering_person_type(self) -> None:
        """Assess social engineering risk for person."""
        result = await research_social_engineering_score(
            target="john@example.com", target_type="person"
        )

        assert result["target"] == "john@example.com"
        assert result["target_type"] == "person"
        assert 0 <= result["exposure_score"] <= 100
        assert isinstance(result["exposed_data_types"], list)
        assert isinstance(result["recommendations"], list)
        assert result["risk_level"] in ["low", "medium", "high", "critical"]

    async def test_social_engineering_organization_type(self) -> None:
        """Assess social engineering risk for organization."""
        result = await research_social_engineering_score(
            target="acme.com", target_type="organization"
        )

        assert result["target"] == "acme.com"
        assert result["target_type"] == "organization"
        assert result["risk_level"] in ["low", "medium", "high", "critical"]
        assert len(result["recommendations"]) > 0

    async def test_social_engineering_domain_type(self) -> None:
        """Assess social engineering risk for domain."""
        result = await research_social_engineering_score(
            target="example.com", target_type="domain"
        )

        assert result["target"] == "example.com"
        assert result["target_type"] == "domain"
        assert "whois_data" in result["exposed_data_types"]
        assert "dns_records" in result["exposed_data_types"]

    async def test_social_engineering_exposure_with_email(self) -> None:
        """Email presence increases exposure score."""
        result = await research_social_engineering_score(
            target="user@example.com", target_type="person"
        )

        # Email should contribute to exposure
        assert "email_address" in result["exposed_data_types"]

    async def test_social_engineering_risk_scaling(self) -> None:
        """Risk level scales with exposure score."""
        # Low exposure
        low_result = await research_social_engineering_score(
            target="example.local", target_type="person"
        )

        # High exposure (organization)
        high_result = await research_social_engineering_score(
            target="example.com", target_type="organization"
        )

        # Organization should have higher or equal exposure
        assert high_result["exposure_score"] >= low_result["exposure_score"]

    async def test_social_engineering_recommendations_provided(self) -> None:
        """Recommendations provided for all risk levels."""
        for target_type in ["person", "organization", "domain"]:
            result = await research_social_engineering_score(
                target="test", target_type=target_type
            )

            assert len(result["recommendations"]) > 0
            assert all(isinstance(r, str) for r in result["recommendations"])

    async def test_social_engineering_required_fields(self) -> None:
        """All required fields present in response."""
        result = await research_social_engineering_score(target="test", target_type="person")

        required = [
            "target",
            "target_type",
            "exposure_score",
            "exposed_data_types",
            "recommendations",
            "risk_level",
        ]

        for field in required:
            assert field in result


class TestBehavioralFingerprint:
    """research_behavioral_fingerprint tests."""

    async def test_behavioral_fingerprint_github_user(self) -> None:
        """Build fingerprint for GitHub user."""
        result = await research_behavioral_fingerprint(username="torvalds")

        assert result["username"] == "torvalds"
        assert "timezone_estimate" in result
        assert "active_hours" in result
        assert "interests" in result
        assert "technical_skills" in result
        assert "activity_pattern" in result

    async def test_behavioral_fingerprint_active_hours(self) -> None:
        """Active hours is list of integers 0-23."""
        result = await research_behavioral_fingerprint(username="test_user")

        hours = result["active_hours"]
        assert isinstance(hours, list)
        for hour in hours:
            assert 0 <= hour <= 23

    async def test_behavioral_fingerprint_timezone_valid(self) -> None:
        """Timezone estimate is reasonable string."""
        result = await research_behavioral_fingerprint(username="test_user")

        tz = result["timezone_estimate"]
        assert isinstance(tz, str)
        assert len(tz) > 0

    async def test_behavioral_fingerprint_interests_list(self) -> None:
        """Interests returned as sorted list."""
        result = await research_behavioral_fingerprint(username="test_user")

        interests = result["interests"]
        assert isinstance(interests, list)
        if len(interests) > 1:
            assert interests == sorted(interests)

    async def test_behavioral_fingerprint_skills_list(self) -> None:
        """Technical skills returned as sorted list."""
        result = await research_behavioral_fingerprint(username="test_user")

        skills = result["technical_skills"]
        assert isinstance(skills, list)
        if len(skills) > 1:
            assert skills == sorted(skills)

    async def test_behavioral_fingerprint_activity_pattern(self) -> None:
        """Activity pattern is non-empty string."""
        result = await research_behavioral_fingerprint(username="test_user")

        pattern = result["activity_pattern"]
        assert isinstance(pattern, str)
        assert len(pattern) > 0

    async def test_behavioral_fingerprint_required_fields(self) -> None:
        """All required fields present."""
        result = await research_behavioral_fingerprint(username="test_user")

        required = [
            "username",
            "timezone_estimate",
            "active_hours",
            "interests",
            "technical_skills",
            "activity_pattern",
        ]

        for field in required:
            assert field in result

    async def test_behavioral_fingerprint_empty_username(self) -> None:
        """Handle empty username."""
        result = await research_behavioral_fingerprint(username="")

        assert result["username"] == ""
        assert "activity_pattern" in result

    async def test_behavioral_fingerprint_special_username(self) -> None:
        """Handle username with special characters."""
        result = await research_behavioral_fingerprint(username="user-123_test")

        assert result["username"] == "user-123_test"
        assert "timezone_estimate" in result

    async def test_behavioral_fingerprint_no_data(self) -> None:
        """Handle user with no public activity."""
        # Non-existent user
        result = await research_behavioral_fingerprint(
            username="definitely_nonexistent_user_12345"
        )

        assert result["username"] == "definitely_nonexistent_user_12345"
        # Should still return valid structure
        assert isinstance(result["active_hours"], list)
        assert isinstance(result["interests"], list)
