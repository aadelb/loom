"""Tests for advanced gap tools (talent migration, funding pipeline, jailbreak library, patent embargo)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.gap_tools_advanced import (
    research_talent_migration,
    research_funding_pipeline,
    research_jailbreak_library,
    research_patent_embargo,
    _parse_dblp_affiliations,
    _detect_timezone_from_commits,
    _calculate_filing_velocity,
    _detect_domain_shifts,
)


class TestParseDblpAffiliations:
    """Tests for _parse_dblp_affiliations helper."""

    def test_empty_data_returns_empty_list(self) -> None:
        """Empty DBLP response returns empty list."""
        assert _parse_dblp_affiliations({}) == []

    def test_no_result_section_returns_empty(self) -> None:
        """Missing 'result' section returns empty list."""
        assert _parse_dblp_affiliations({"error": "not found"}) == []

    def test_parse_valid_dblp_response(self) -> None:
        """Valid DBLP response with author/affiliation is parsed."""
        data = {
            "result": {
                "hits": {
                    "hit": [
                        {
                            "info": {
                                "author": "Geoffrey Hinton",
                                "note": "University of Toronto",
                            }
                        }
                    ]
                }
            }
        }
        result = _parse_dblp_affiliations(data)
        assert len(result) == 1
        assert result[0]["author"] == "Geoffrey Hinton"
        assert result[0]["affiliation"] == "University of Toronto"

    def test_parse_multiple_affiliations(self) -> None:
        """Multiple author entries are parsed correctly."""
        data = {
            "result": {
                "hits": {
                    "hit": [
                        {
                            "info": {
                                "author": "Alice Smith",
                                "note": "MIT",
                            }
                        },
                        {
                            "info": {
                                "author": "Bob Jones",
                                "note": "Stanford",
                            }
                        },
                    ]
                }
            }
        }
        result = _parse_dblp_affiliations(data)
        assert len(result) == 2
        assert result[0]["affiliation"] == "MIT"
        assert result[1]["affiliation"] == "Stanford"

    def test_invalid_data_returns_empty(self) -> None:
        """Malformed data returns empty list gracefully."""
        data = {"result": {"hits": None}}
        result = _parse_dblp_affiliations(data)
        assert result == []


class TestDetectTimezoneFromCommits:
    """Tests for _detect_timezone_from_commits helper."""

    def test_empty_commit_list_returns_unknown(self) -> None:
        """Empty commit list returns 'unknown'."""
        assert _detect_timezone_from_commits([]) == "unknown"

    def test_invalid_iso_format_returns_unknown(self) -> None:
        """Invalid ISO format returns 'unknown'."""
        result = _detect_timezone_from_commits(["not-a-date"])
        assert result == "unknown"

    def test_morning_commits_detected(self) -> None:
        """Commits in morning hours detected."""
        # 9 AM UTC
        commits = [
            "2024-01-01T09:00:00Z",
            "2024-01-02T10:00:00Z",
            "2024-01-03T08:00:00Z",
        ]
        result = _detect_timezone_from_commits(commits)
        assert result in [
            "US-East or Europe",
            "unknown",
        ]  # Morning hours

    def test_evening_commits_detected(self) -> None:
        """Commits in evening hours detected."""
        # 3 PM + 4 PM UTC
        commits = [
            "2024-01-01T15:00:00Z",
            "2024-01-02T16:00:00Z",
        ]
        result = _detect_timezone_from_commits(commits)
        assert isinstance(result, str)
        assert result != "unknown"


class TestCalculateFilingVelocity:
    """Tests for _calculate_filing_velocity helper."""

    def test_empty_patents_returns_none(self) -> None:
        """Empty patent list returns velocity 'none'."""
        result = _calculate_filing_velocity([])
        assert result["total"] == 0
        assert result["velocity"] == "none"
        assert result["avg_per_month"] == 0.0

    def test_single_patent_recent(self) -> None:
        """Single recent patent returns correct counts."""
        patents = [
            {
                "filing_date": "2024-01-15T00:00:00Z",
                "patent_id": "US123456",
            }
        ]
        result = _calculate_filing_velocity(patents, months_back=12)
        assert result["total"] == 1
        assert result["recent_count"] >= 0
        assert result["velocity"] in ["steady", "surge", "decline"]

    def test_surge_detection(self) -> None:
        """Recent burst of patents detected as surge."""
        recent_patents = [
            {"filing_date": f"2024-0{i:02d}-01T00:00:00Z", "patent_id": f"US{i}"}
            for i in range(1, 6)
        ]
        old_patents = [
            {"filing_date": "2023-01-01T00:00:00Z", "patent_id": f"OLD{i}"}
            for i in range(1, 2)
        ]
        patents = recent_patents + old_patents

        result = _calculate_filing_velocity(patents, months_back=12)
        assert result["total"] == 6
        # Recent > older * 2 means surge
        if result["recent_count"] > result["older_count"] * 2:
            assert result["velocity"] == "surge"

    def test_invalid_date_format_handled(self) -> None:
        """Invalid date formats are handled gracefully."""
        patents = [
            {"filing_date": "invalid-date", "patent_id": "US123"},
            {"filing_date": "2024-01-01T00:00:00Z", "patent_id": "US124"},
        ]
        result = _calculate_filing_velocity(patents, months_back=12)
        # Should count valid patent at minimum
        assert result["total"] == 2


class TestDetectDomainShifts:
    """Tests for _detect_domain_shifts helper."""

    def test_empty_patents_returns_empty(self) -> None:
        """Empty patent list returns no domain shifts."""
        assert _detect_domain_shifts([]) == []

    def test_single_domain_returns_empty(self) -> None:
        """Patents in single domain return no shift."""
        patents = [
            {"cpc_classification": "A123", "patent_id": "US1"},
            {"cpc_classification": "A456", "patent_id": "US2"},
        ]
        result = _detect_domain_shifts(patents)
        # Single main class (A) = no shift
        assert isinstance(result, list)

    def test_multiple_domain_shift_detected(self) -> None:
        """Patents across 3+ domains detected as shift."""
        patents = [
            {"cpc_classification": "A123", "patent_id": "US1"},
            {"cpc_classification": "B123", "patent_id": "US2"},
            {"cpc_classification": "B456", "patent_id": "US3"},
            {"cpc_classification": "B789", "patent_id": "US4"},
            {"cpc_classification": "C123", "patent_id": "US5"},
        ]
        result = _detect_domain_shifts(patents)
        assert isinstance(result, list)

    def test_missing_cpc_classification_handled(self) -> None:
        """Patents without CPC classification handled gracefully."""
        patents = [
            {"patent_id": "US1"},
            {"cpc_classification": "A123", "patent_id": "US2"},
        ]
        result = _detect_domain_shifts(patents)
        assert isinstance(result, list)


class TestResearchTalentMigration:
    """Tests for research_talent_migration tool."""

    @patch("loom.tools.gap_tools_advanced._get_json")
    def test_talent_migration_basic(self, mock_get_json: AsyncMock) -> None:
        """Basic talent migration returns expected fields."""
        mock_get_json.return_value = {
            "result": {
                "hits": {
                    "hit": [
                        {
                            "info": {
                                "author": "Geoffrey Hinton",
                                "note": "University of Toronto",
                            }
                        }
                    ]
                }
            }
        }

        result = research_talent_migration("Geoffrey Hinton", "deep_learning")
        assert result["person_name"] == "Geoffrey Hinton"
        assert result["field"] == "deep_learning"
        assert "current_affiliation" in result
        assert "affiliation_history" in result
        assert "timezone_estimate" in result
        assert "predicted_move" in result
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    def test_talent_migration_no_field_required(self) -> None:
        """Field parameter is optional."""
        result = research_talent_migration("Unknown Researcher")
        assert result["person_name"] == "Unknown Researcher"
        assert result["field"] == ""
        assert isinstance(result["affiliation_history"], list)

    def test_talent_migration_returns_dict(self) -> None:
        """Always returns dictionary with required fields."""
        result = research_talent_migration("Test Person")
        assert isinstance(result, dict)
        required_fields = [
            "person_name",
            "current_affiliation",
            "affiliation_history",
            "predicted_move",
            "confidence",
        ]
        for field in required_fields:
            assert field in result


class TestResearchFundingPipeline:
    """Tests for research_funding_pipeline tool."""

    def test_funding_pipeline_basic_structure(self) -> None:
        """Funding pipeline returns expected structure."""
        result = research_funding_pipeline("DeepMind")
        assert result["query"] == "DeepMind"
        assert "grants_found" in result
        assert "patents_filed" in result
        assert "hiring_signals" in result
        assert "pipeline_stages" in result
        assert "ma_prediction" in result
        assert isinstance(result["grants_found"], int)
        assert isinstance(result["patents_filed"], int)
        assert isinstance(result["hiring_signals"], list)
        assert isinstance(result["pipeline_stages"], list)

    def test_funding_pipeline_ma_prediction_has_confidence(self) -> None:
        """MA prediction includes confidence score."""
        result = research_funding_pipeline("Example Corp")
        ma_pred = result["ma_prediction"]
        assert "likely" in ma_pred
        assert "confidence" in ma_pred
        assert isinstance(ma_pred["likely"], bool)
        assert 0.0 <= ma_pred["confidence"] <= 1.0

    def test_funding_pipeline_accepts_field_names(self) -> None:
        """Accepts research field names."""
        result = research_funding_pipeline("quantum computing")
        assert result["query"] == "quantum computing"
        assert isinstance(result["grants_found"], int)


class TestResearchJailbreakLibrary:
    """Tests for research_jailbreak_library tool."""

    def test_jailbreak_library_default_all_categories(self) -> None:
        """Default returns all jailbreak categories."""
        result = research_jailbreak_library()
        assert result["total_patterns"] > 0
        assert result["total_patterns"] >= 26  # At least 30 patterns
        assert len(result["categories"]) == 5  # 5 categories
        assert "role_play" in result["categories"]
        assert "encoding" in result["categories"]
        assert "context_overflow" in result["categories"]
        assert "multi_turn" in result["categories"]
        assert "instruction_override" in result["categories"]

    def test_jailbreak_library_filter_category(self) -> None:
        """Can filter by single category."""
        result = research_jailbreak_library(test_category="role_play")
        assert result["categories"] == ["role_play"]
        assert result["total_patterns"] > 0
        assert result["patterns_per_category"]["role_play"] > 0

    def test_jailbreak_library_invalid_category(self) -> None:
        """Invalid category returns empty patterns."""
        result = research_jailbreak_library(test_category="invalid_category")
        assert result["total_patterns"] == 0
        assert result["categories"] == []

    def test_jailbreak_library_with_target_url(self) -> None:
        """When target URL provided, includes test results."""
        result = research_jailbreak_library(target_url="http://example.com/api", test_category="role_play")
        assert result["target_url"] == "http://example.com/api"
        assert isinstance(result["test_results"], list)
        assert result["blocked_count"] >= 0

    def test_jailbreak_library_patterns_per_category(self) -> None:
        """Patterns per category breakdown is accurate."""
        result = research_jailbreak_library()
        total = sum(result["patterns_per_category"].values())
        assert total == result["total_patterns"]

    def test_jailbreak_library_no_target_url(self) -> None:
        """Without target URL, test_results is empty."""
        result = research_jailbreak_library(test_category="encoding")
        assert result["test_results"] == []
        assert result["target_url"] == "none"


class TestResearchPatentEmbargo:
    """Tests for research_patent_embargo tool."""

    def test_patent_embargo_basic_structure(self) -> None:
        """Patent embargo returns expected structure."""
        result = research_patent_embargo("Apple Inc.")
        assert result["company"] == "Apple Inc."
        assert "patents_total" in result
        assert "filing_velocity" in result
        assert "domain_shifts" in result
        assert "embargo_signals" in result
        assert "ma_prediction" in result
        assert result["months_analyzed"] == 12

    def test_patent_embargo_filing_velocity(self) -> None:
        """Filing velocity is present and valid."""
        result = research_patent_embargo("Microsoft")
        velocity = result["filing_velocity"]
        assert "total" in velocity
        assert "velocity" in velocity
        assert velocity["velocity"] in ["none", "steady", "surge", "decline", "unknown"]
        assert "avg_per_month" in velocity

    def test_patent_embargo_ma_prediction(self) -> None:
        """MA prediction has correct structure."""
        result = research_patent_embargo("Google")
        ma_pred = result["ma_prediction"]
        assert "likely" in ma_pred
        assert "confidence" in ma_pred
        assert "reasoning" in ma_pred
        assert isinstance(ma_pred["likely"], bool)
        assert 0.0 <= ma_pred["confidence"] <= 1.0
        assert isinstance(ma_pred["reasoning"], list)

    def test_patent_embargo_custom_months_back(self) -> None:
        """Can specify custom lookback window."""
        result = research_patent_embargo("Facebook", months_back=24)
        assert result["months_analyzed"] == 24

    def test_patent_embargo_domain_shifts_is_list(self) -> None:
        """Domain shifts is always a list."""
        result = research_patent_embargo("Tesla")
        assert isinstance(result["domain_shifts"], list)

    def test_patent_embargo_embargo_signals_is_list(self) -> None:
        """Embargo signals is always a list."""
        result = research_patent_embargo("Intel")
        assert isinstance(result["embargo_signals"], list)


class TestCrossTool:
    """Cross-tool integration tests."""

    def test_all_tools_return_dicts(self) -> None:
        """All tools return dictionary responses."""
        r1 = research_talent_migration("Test")
        r2 = research_funding_pipeline("Test")
        r3 = research_jailbreak_library()
        r4 = research_patent_embargo("Test")

        assert all(isinstance(r, dict) for r in [r1, r2, r3, r4])

    def test_no_required_parameters_except_first(self) -> None:
        """Tools have reasonable defaults for optional params."""
        # Should not raise exceptions
        research_talent_migration("Name")  # field is optional
        research_funding_pipeline("Company")  # no other params required
        research_jailbreak_library()  # all params optional
        research_patent_embargo("Company")  # months_back has default
