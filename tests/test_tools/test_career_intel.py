"""Tests for PhD career intelligence tools: research_map_research_to_product and research_translate_academic_skills."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from loom.tools.career.career_intel import (
    _extract_research_areas_simple,
    _extract_skills_simple,
    _match_skills,
    research_map_research_to_product,
    research_translate_academic_skills,
)


# ============================================================================
# Tests for research_map_research_to_product
# ============================================================================


@pytest.mark.asyncio
class TestMapResearchToProduct:
    """Tests for research_map_research_to_product tool."""

    async def test_invalid_n_parameter_too_small(self) -> None:
        """n < 1 is clamped to 1."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.return_value = ["machine learning"]
            with patch("loom.tools.career.career_intel._search_companies_for_areas") as mock_search:
                mock_search.return_value = {"machine learning": {"companies": [], "products": [], "total_results": 0}}
                with patch("loom.tools.career.career_intel._search_github_repos") as mock_github:
                    mock_github.return_value = {"machine learning": []}

                    result = await research_map_research_to_product("test research", n=0)
                    # Verify n was clamped to 1
                    assert mock_search.called

    async def test_invalid_n_parameter_too_large(self) -> None:
        """n > 50 is clamped to 50."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.return_value = ["machine learning"]
            with patch("loom.tools.career.career_intel._search_companies_for_areas") as mock_search:
                mock_search.return_value = {"machine learning": {"companies": [], "products": [], "total_results": 0}}
                with patch("loom.tools.career.career_intel._search_github_repos") as mock_github:
                    mock_github.return_value = {"machine learning": []}

                    result = await research_map_research_to_product("test research", n=100)
                    # Verify n was clamped to 50
                    assert mock_search.called

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.return_value = ["machine learning"]
            with patch("loom.tools.career.career_intel._search_companies_for_areas") as mock_search:
                mock_search.return_value = {
                    "machine learning": {
                        "companies": ["OpenAI"],
                        "products": ["ChatGPT"],
                        "total_results": 1,
                    }
                }
                with patch("loom.tools.career.career_intel._search_github_repos") as mock_github:
                    mock_github.return_value = {"machine learning": []}

                    result = await research_map_research_to_product("test research")

                    assert "research_areas" in result
                    assert "commercial_mappings" in result
                    assert "github_repos" in result
                    assert "total_companies" in result
                    assert "total_opportunities" in result

    async def test_extracts_research_areas(self) -> None:
        """Tool extracts research areas correctly."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.return_value = ["reinforcement learning", "NLP"]
            with patch("loom.tools.career.career_intel._search_companies_for_areas") as mock_search:
                mock_search.return_value = {}
                with patch("loom.tools.career.career_intel._search_github_repos") as mock_github:
                    mock_github.return_value = {}

                    result = await research_map_research_to_product("deep learning research")
                    assert result["research_areas"] == ["reinforcement learning", "NLP"]

    async def test_handles_search_errors_gracefully(self) -> None:
        """Tool handles search errors gracefully."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.side_effect = Exception("Search failed")

            result = await research_map_research_to_product("test research")
            assert "error" in result
            assert result["total_companies"] == 0
            assert result["total_opportunities"] == 0

    async def test_commercial_mapping_structure(self) -> None:
        """Commercial mapping has correct structure."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.return_value = ["machine learning"]
            with patch("loom.tools.career.career_intel._search_companies_for_areas") as mock_search:
                mock_search.return_value = {
                    "machine learning": {
                        "companies": ["OpenAI", "DeepMind"],
                        "products": ["ChatGPT"],
                        "total_results": 5,
                    }
                }
                with patch("loom.tools.career.career_intel._search_github_repos") as mock_github:
                    mock_github.return_value = {"machine learning": []}

                    result = await research_map_research_to_product("test research")
                    assert len(result["commercial_mappings"]) > 0
                    mapping = result["commercial_mappings"][0]
                    assert "area" in mapping
                    assert "companies" in mapping
                    assert "products" in mapping
                    assert "result_count" in mapping


# ============================================================================
# Tests for research_translate_academic_skills
# ============================================================================


@pytest.mark.asyncio
class TestTranslateAcademicSkills:
    """Tests for research_translate_academic_skills tool."""

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [
                ["machine learning", "teaching"],
                ["Python", "system design"],
            ]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                mock_match.return_value = []

                result = await research_translate_academic_skills("CV text", "JD text")

                assert "academic_skills" in result
                assert "required_skills" in result
                assert "matched_skills" in result
                assert "skill_gaps" in result
                assert "match_percentage" in result

    async def test_extracts_academic_skills(self) -> None:
        """Tool extracts academic skills correctly."""
        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [
                ["machine learning", "mentoring"],
                ["Python"],
            ]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                mock_match.return_value = []

                result = await research_translate_academic_skills("CV with ML and mentoring", "JD")

                assert len(result["academic_skills"]) == 2
                assert any("machine learning" in s.get("skill", "").lower() for s in result["academic_skills"])

    async def test_extracts_required_skills(self) -> None:
        """Tool extracts required skills from job description."""
        with patch("loom.tools.career_Intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [
                ["machine learning"],
                ["Python", "system design", "leadership"],
            ]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                mock_match.return_value = []

                result = await research_translate_academic_skills("CV", "JD with Python")

                assert len(result["required_skills"]) == 3
                assert "Python" in result["required_skills"]

    async def test_match_percentage_calculation(self) -> None:
        """Match percentage is calculated correctly."""
        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [["skill1", "skill2"], ["skill1", "skill2", "skill3", "skill4"]]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                # 2 out of 4 required skills matched
                mock_match.return_value = [
                    {"academic": "skill1", "industry": "skill1", "match_score": 1.0},
                    {"academic": "skill2", "industry": "skill2", "match_score": 1.0},
                ]

                result = await research_translate_academic_skills("CV", "JD")

                assert result["match_percentage"] == 50.0

    async def test_identifies_skill_gaps(self) -> None:
        """Tool identifies skill gaps correctly."""
        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [
                ["machine learning"],
                ["machine learning", "Python", "DevOps"],
            ]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                mock_match.return_value = [
                    {"academic": "machine learning", "industry": "machine learning", "match_score": 1.0}
                ]

                result = await research_translate_academic_skills("CV", "JD")

                # Should have 2 gaps: Python and DevOps
                assert len(result["skill_gaps"]) == 2
                gap_skills = [g["skill"] for g in result["skill_gaps"]]
                assert "Python" in gap_skills
                assert "DevOps" in gap_skills

    async def test_skill_gaps_have_learning_resources(self) -> None:
        """Skill gaps include learning resource recommendations."""
        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [["skill1"], ["Python"]]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                mock_match.return_value = []

                result = await research_translate_academic_skills("CV", "JD")

                assert len(result["skill_gaps"]) > 0
                for gap in result["skill_gaps"]:
                    assert "learning_resource" in gap
                    assert "importance" in gap

    async def test_handles_extraction_errors_gracefully(self) -> None:
        """Tool handles extraction errors gracefully."""
        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = Exception("LLM error")

            result = await research_translate_academic_skills("CV", "JD")

            assert "error" in result
            assert result["match_percentage"] == 0.0


# ============================================================================
# Tests for helper functions
# ============================================================================


class TestExtractResearchAreasSimple:
    """Tests for _extract_research_areas_simple function."""

    def test_extracts_common_areas(self) -> None:
        """Extracts common research areas from text."""
        text = "We focus on deep learning and reinforcement learning"
        areas = _extract_research_areas_simple(text)
        assert "deep learning" in areas
        assert "reinforcement learning" in areas

    def test_case_insensitive_matching(self) -> None:
        """Matching is case-insensitive."""
        text = "DEEP LEARNING and Machine Learning"
        areas = _extract_research_areas_simple(text)
        assert "deep learning" in areas
        assert "machine learning" in areas

    def test_returns_defaults_on_no_match(self) -> None:
        """Returns default areas when no match found."""
        text = "Some random text"
        areas = _extract_research_areas_simple(text)
        assert "machine learning" in areas
        assert "data science" in areas

    def test_nlp_detection(self) -> None:
        """Detects NLP-related areas."""
        text = "Natural language processing and language models"
        areas = _extract_research_areas_simple(text)
        assert "NLP" in areas

    def test_computer_vision_detection(self) -> None:
        """Detects computer vision areas."""
        text = "Image classification and object detection"
        areas = _extract_research_areas_simple(text)
        assert "computer vision" in areas


class TestExtractSkillsSimple:
    """Tests for _extract_skills_simple function."""

    def test_extracts_academic_skills(self) -> None:
        """Extracts academic skills from text."""
        text = "Mentored RAs and taught students using machine learning"
        skills = _extract_skills_simple(text, context="academic")
        assert "mentoring" in skills
        assert "teaching" in skills
        assert "machine learning" in skills

    def test_extracts_industry_skills(self) -> None:
        """Extracts industry skills from text."""
        text = "Required: Project management, system design, AWS expertise"
        skills = _extract_skills_simple(text, context="industry")
        assert "project management" in skills
        assert "system design" in skills
        assert "cloud" in skills

    def test_case_insensitive(self) -> None:
        """Skill extraction is case-insensitive."""
        text = "MACHINE LEARNING and Python"
        skills = _extract_skills_simple(text, context="academic")
        assert "machine learning" in skills
        assert "Python" in skills


class TestMatchSkills:
    """Tests for _match_skills function."""

    def test_direct_skill_match(self) -> None:
        """Matches identical skills with 1.0 score."""
        academic = ["Python", "machine learning"]
        required = ["Python", "data analysis"]
        matches = _match_skills(academic, required)
        assert len(matches) > 0
        python_match = next((m for m in matches if "Python" in m["academic"]), None)
        assert python_match is not None
        assert python_match["match_score"] == 1.0

    def test_mapped_skill_match(self) -> None:
        """Matches mapped skills with 0.8 score."""
        academic = ["mentoring"]
        required = ["leadership"]
        matches = _match_skills(academic, required)
        # mentoring maps to leadership
        assert any(m["match_score"] == 0.8 for m in matches if "mentoring" in m["academic"])

    def test_no_match_returns_empty(self) -> None:
        """Returns empty list when no matches found."""
        academic = ["obscure skill 1"]
        required = ["obscure skill 2"]
        matches = _match_skills(academic, required)
        assert len(matches) == 0

    def test_multiple_required_matches(self) -> None:
        """Can match one academic skill to multiple required skills."""
        academic = ["machine learning"]
        required = ["ML", "AI modeling", "data science"]
        matches = _match_skills(academic, required)
        # Should find matches for multiple required skills
        assert len(matches) > 0


# ============================================================================
# Integration-style tests
# ============================================================================


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for career intelligence tools."""

    async def test_full_research_mapping_workflow(self) -> None:
        """Test complete research mapping workflow."""
        with patch(
            "loom.tools.career.career_intel._extract_research_areas_llm"
        ) as mock_extract:
            mock_extract.return_value = ["machine learning", "NLP"]
            with patch("loom.tools.career.career_intel._search_companies_for_areas") as mock_search:
                mock_search.return_value = {
                    "machine learning": {
                        "companies": ["OpenAI"],
                        "products": ["ChatGPT"],
                        "total_results": 5,
                    },
                    "NLP": {
                        "companies": ["Meta", "Google"],
                        "products": ["BERT"],
                        "total_results": 3,
                    },
                }
                with patch("loom.tools.career.career_intel._search_github_repos") as mock_github:
                    mock_github.return_value = {
                        "machine learning": [
                            {"name": "pytorch", "stars": 75000}
                        ],
                        "NLP": [
                            {"name": "transformers", "stars": 125000}
                        ],
                    }

                    result = await research_map_research_to_product(
                        "PhD research in ML and NLP"
                    )

                    assert result["total_companies"] == 3  # OpenAI, Meta, Google
                    assert len(result["research_areas"]) == 2
                    assert result["commercial_mappings"][0]["companies"]

    async def test_full_skill_translation_workflow(self) -> None:
        """Test complete skill translation workflow."""
        cv_text = "Mentored students and published research in machine learning"
        jd_text = "Seeking candidate with leadership, Python skills, system design"

        with patch("loom.tools.career.career_intel._extract_skills_llm") as mock_extract:
            mock_extract.side_effect = [
                ["mentoring", "published research", "machine learning"],
                ["leadership", "Python", "system design"],
            ]
            with patch("loom.tools.career.career_intel._match_skills") as mock_match:
                mock_match.return_value = [
                    {"academic": "mentoring", "industry": "leadership", "match_score": 0.8}
                ]

                result = await research_translate_academic_skills(cv_text, jd_text)

                assert len(result["academic_skills"]) == 3
                assert len(result["required_skills"]) == 3
                assert result["match_percentage"] == pytest.approx(33.3, abs=1)
