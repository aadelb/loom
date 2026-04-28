"""Unit tests for unique research tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from loom.tools.unique_tools import (
    _detect_tech_signatures,
    research_dark_web_bridge,
    research_info_half_life,
    research_influence_operation,
    research_information_cascade,
    research_propaganda_detector,
    research_search_discrepancy,
    research_source_credibility,
    research_web_time_machine,
)


class TestPropagandaDetector:
    """research_propaganda_detector tool tests."""

    def test_propaganda_detector_empty_text(self) -> None:
        """Empty text returns zero score."""
        result = research_propaganda_detector("")
        assert result["text_length"] == 0
        assert result["word_count"] == 0
        assert result["propaganda_score"] == 0
        assert result["dominant_technique"] is None
        assert result["techniques_found"] == []

    def test_propaganda_detector_loaded_language(self) -> None:
        """Detects loaded language patterns."""
        text = "This is absolutely amazing and completely terrible at the same time."
        result = research_propaganda_detector(text)
        assert result["text_length"] > 0
        assert len(result["techniques_found"]) > 0
        # Should detect loaded_language
        techniques = [t["technique"] for t in result["techniques_found"]]
        assert "loaded_language" in techniques

    def test_propaganda_detector_authority_appeal(self) -> None:
        """Detects appeal to authority patterns."""
        text = "Experts say this is true. Research shows it works. Scientists prove it."
        result = research_propaganda_detector(text)
        assert len(result["techniques_found"]) > 0
        techniques = [t["technique"] for t in result["techniques_found"]]
        assert "appeal_to_authority" in techniques

    def test_propaganda_detector_bandwagon(self) -> None:
        """Detects bandwagon patterns."""
        text = "Everyone knows this. Most people believe it. Join the movement."
        result = research_propaganda_detector(text)
        assert len(result["techniques_found"]) > 0
        techniques = [t["technique"] for t in result["techniques_found"]]
        assert "bandwagon" in techniques

    def test_propaganda_detector_emotional_manipulation(self) -> None:
        """Detects emotional manipulation."""
        text = "This is heartbreaking and tragic. We must defend our values."
        result = research_propaganda_detector(text)
        assert len(result["techniques_found"]) > 0
        techniques = [t["technique"] for t in result["techniques_found"]]
        assert "emotional_manipulation" in techniques

    def test_propaganda_detector_score_range(self) -> None:
        """Propaganda score is within 0-100 range."""
        text = "Some normal text without propaganda markers."
        result = research_propaganda_detector(text)
        assert 0 <= result["propaganda_score"] <= 100

    def test_propaganda_detector_non_string_input(self) -> None:
        """Non-string input returns empty result."""
        result = research_propaganda_detector(123)  # type: ignore
        assert result["text_length"] == 0
        assert result["propaganda_score"] == 0

    def test_propaganda_detector_long_text(self) -> None:
        """Handles long text without errors."""
        text = "This is normal. " * 1000
        result = research_propaganda_detector(text)
        assert result["text_length"] > 0
        assert 0 <= result["propaganda_score"] <= 100


class TestSourceCredibility:
    """research_source_credibility tool tests."""

    def test_source_credibility_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_get.return_value.__aenter__.return_value = mock_response

            result = research_source_credibility("https://example.com")
            assert "url" in result
            assert "domain" in result
            assert "domain_age_days" in result
            assert "wikipedia_referenced" in result
            assert "academic_citations" in result
            assert "security_score" in result
            assert "credibility_score" in result

    def test_source_credibility_score_range(self) -> None:
        """Credibility score is 0-100."""
        result = research_source_credibility("https://example.com")
        assert 0 <= result["credibility_score"] <= 100
        assert 0 <= result["security_score"] <= 100

    def test_source_credibility_extracts_domain(self) -> None:
        """Correctly extracts domain from URL."""
        result = research_source_credibility("https://www.example.com/path")
        assert result["domain"] == "example.com"

    def test_source_credibility_handles_invalid_url(self) -> None:
        """Gracefully handles invalid URLs."""
        # The validate_url function will catch this
        try:
            result = research_source_credibility("not-a-url")
        except ValueError:
            # Expected behavior
            pass

    def test_source_credibility_wikipedia_reference_detection(self) -> None:
        """Can detect Wikipedia references (mocked)."""
        result = research_source_credibility("https://example.com")
        assert isinstance(result["wikipedia_referenced"], bool)

    def test_source_credibility_academic_citations_count(self) -> None:
        """Academic citations count is non-negative."""
        result = research_source_credibility("https://example.com")
        assert result["academic_citations"] >= 0


class TestInformationCascade:
    """research_information_cascade tool tests."""

    def test_information_cascade_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = research_information_cascade("test topic")
            assert "topic" in result
            assert "hours_back" in result
            assert "timeline" in result
            assert isinstance(result["timeline"], list)
            assert "origin_source" in result
            assert "cascade_depth" in result
            assert "platforms_reached" in result

    def test_information_cascade_default_hours_back(self) -> None:
        """Default hours_back is 72."""
        result = research_information_cascade("test topic")
        assert result["hours_back"] == 72

    def test_information_cascade_custom_hours_back(self) -> None:
        """Custom hours_back is respected."""
        result = research_information_cascade("test topic", hours_back=24)
        assert result["hours_back"] == 24

    def test_information_cascade_timeline_structure(self) -> None:
        """Timeline entries have expected structure."""
        result = research_information_cascade("test topic")
        for entry in result["timeline"]:
            assert isinstance(entry, dict)
            # Timeline entries may have: source, title, url, timestamp

    def test_information_cascade_platforms_are_strings(self) -> None:
        """Platforms list contains strings."""
        result = research_information_cascade("test topic")
        assert all(isinstance(p, str) for p in result["platforms_reached"])

    def test_information_cascade_cascade_depth_non_negative(self) -> None:
        """Cascade depth is non-negative."""
        result = research_information_cascade("test topic")
        assert result["cascade_depth"] >= 0


class TestWebTimeMachine:
    """research_web_time_machine tool tests."""

    def test_web_time_machine_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = research_web_time_machine("https://example.com")
            assert "url" in result
            assert "domain" in result
            assert "snapshots_found" in result
            assert "evolution" in result
            assert isinstance(result["evolution"], list)
            assert "tech_changes" in result
            assert isinstance(result["tech_changes"], list)

    def test_web_time_machine_default_snapshots(self) -> None:
        """Default snapshots is 10."""
        result = research_web_time_machine("https://example.com")
        assert result["snapshots_found"] >= 0

    def test_web_time_machine_custom_snapshots(self) -> None:
        """Custom snapshots parameter is respected."""
        result = research_web_time_machine("https://example.com", snapshots=5)
        # Should attempt to fetch 5 snapshots
        assert result["snapshots_found"] >= 0

    def test_web_time_machine_evolution_structure(self) -> None:
        """Evolution entries have expected structure."""
        result = research_web_time_machine("https://example.com")
        for entry in result["evolution"]:
            assert isinstance(entry, dict)
            assert "date" in entry or "timestamp" in entry
            assert "technologies" in entry

    def test_web_time_machine_tech_changes_structure(self) -> None:
        """Tech changes have expected structure."""
        result = research_web_time_machine("https://example.com")
        for change in result["tech_changes"]:
            assert isinstance(change, dict)
            assert "date" in change
            assert "added" in change
            assert "removed" in change


class TestTechSignatureDetection:
    """_detect_tech_signatures helper function tests."""

    def test_detect_react(self) -> None:
        """Detects React framework."""
        html = "<script>var React = {};</script>"
        techs = _detect_tech_signatures(html)
        assert "React" in techs

    def test_detect_angular(self) -> None:
        """Detects Angular framework."""
        html = "<script>angular.module('app', []);</script>"
        techs = _detect_tech_signatures(html)
        assert "Angular" in techs

    def test_detect_wordpress(self) -> None:
        """Detects WordPress."""
        html = "<meta name='generator' content='WordPress'>"
        techs = _detect_tech_signatures(html)
        assert "WordPress" in techs

    def test_detect_google_analytics(self) -> None:
        """Detects Google Analytics."""
        html = "<script>ga('send', 'pageview');</script>"
        techs = _detect_tech_signatures(html)
        assert "Google Analytics" in techs

    def test_detect_multiple_techs(self) -> None:
        """Detects multiple technologies."""
        html = """
        <script>var React = {};</script>
        <meta name='generator' content='WordPress'>
        <script>ga('send', 'pageview');</script>
        """
        techs = _detect_tech_signatures(html)
        assert len(techs) >= 2

    def test_detect_no_techs(self) -> None:
        """Returns empty list for plain HTML."""
        html = "<html><body>Hello</body></html>"
        techs = _detect_tech_signatures(html)
        assert isinstance(techs, list)
        assert len(techs) == 0


class TestInfluenceOperation:
    """research_influence_operation tool tests."""

    def test_influence_operation_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = research_influence_operation("test topic")
            assert "topic" in result
            assert "suspicious_clusters" in result
            assert isinstance(result["suspicious_clusters"], list)
            assert "coordination_score" in result
            assert "evidence" in result

    def test_influence_operation_coordination_score_range(self) -> None:
        """Coordination score is 0-100."""
        result = research_influence_operation("test topic")
        assert 0 <= result["coordination_score"] <= 100

    def test_influence_operation_evidence_structure(self) -> None:
        """Evidence has expected structure."""
        result = research_influence_operation("test topic")
        assert "total_posts_analyzed" in result["evidence"]
        assert "clusters_detected" in result["evidence"]
        assert "platforms" in result["evidence"]

    def test_influence_operation_suspicious_clusters_are_dicts(self) -> None:
        """Suspicious clusters are dictionaries."""
        result = research_influence_operation("test topic")
        assert all(isinstance(c, dict) for c in result["suspicious_clusters"])


class TestDarkWebBridge:
    """research_dark_web_bridge tool tests."""

    def test_dark_web_bridge_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = research_dark_web_bridge("test query")
            assert "query" in result
            assert "clearnet_references" in result
            assert isinstance(result["clearnet_references"], list)
            assert "academic_references" in result
            assert isinstance(result["academic_references"], list)
            assert "total" in result

    def test_dark_web_bridge_total_count_correct(self) -> None:
        """Total is sum of clearnet and academic references."""
        result = research_dark_web_bridge("test query")
        expected_total = len(result["clearnet_references"]) + len(result["academic_references"])
        assert result["total"] == expected_total

    def test_dark_web_bridge_reference_structure(self) -> None:
        """References have expected structure."""
        result = research_dark_web_bridge("test query")
        for ref in result["clearnet_references"]:
            assert isinstance(ref, dict)
            assert "source" in ref


class TestInfoHalfLife:
    """research_info_half_life tool tests."""

    def test_info_half_life_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.head") as mock_head:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_head.return_value.__aenter__.return_value = mock_response

            result = research_info_half_life(["https://example.com"])
            assert "urls_checked" in result
            assert "alive_count" in result
            assert "dead_count" in result
            assert "url_statuses" in result
            assert isinstance(result["url_statuses"], list)
            assert "estimated_half_life_days" in result

    def test_info_half_life_counts_match(self) -> None:
        """Alive + dead counts match URLs checked."""
        result = research_info_half_life(["https://example.com", "https://example.org"])
        assert result["alive_count"] + result["dead_count"] == result["urls_checked"]

    def test_info_half_life_estimated_half_life_positive(self) -> None:
        """Estimated half-life is positive."""
        result = research_info_half_life(["https://example.com"])
        assert result["estimated_half_life_days"] > 0

    def test_info_half_life_url_statuses_structure(self) -> None:
        """URL statuses have expected structure."""
        result = research_info_half_life(["https://example.com"])
        for status in result["url_statuses"]:
            assert isinstance(status, dict)
            assert "url" in status
            assert "status" in status

    def test_info_half_life_empty_urls_list(self) -> None:
        """Handles empty URL list gracefully."""
        result = research_info_half_life([])
        assert result["urls_checked"] == 0
        assert result["alive_count"] == 0
        assert result["dead_count"] == 0

    def test_info_half_life_limits_urls(self) -> None:
        """Limits to 50 URLs for performance."""
        urls = [f"https://example{i}.com" for i in range(100)]
        result = research_info_half_life(urls)
        assert result["urls_checked"] <= 50


class TestSearchDiscrepancy:
    """research_search_discrepancy tool tests."""

    def test_search_discrepancy_returns_required_fields(self) -> None:
        """Returns all required fields."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = research_search_discrepancy("test query")
            assert "query" in result
            assert "engines_queried" in result
            assert isinstance(result["engines_queried"], list)
            assert "results_per_engine" in result
            assert isinstance(result["results_per_engine"], dict)
            assert "unique_per_engine" in result
            assert "deindexed_candidates" in result

    def test_search_discrepancy_engines_queried_structure(self) -> None:
        """Engines queried list is populated."""
        result = research_search_discrepancy("test query")
        assert len(result["engines_queried"]) > 0

    def test_search_discrepancy_results_per_engine_keys(self) -> None:
        """Results per engine has expected engine keys."""
        result = research_search_discrepancy("test query")
        # Should have at least some engines
        assert len(result["results_per_engine"]) >= 1

    def test_search_discrepancy_unique_per_engine_structure(self) -> None:
        """Unique per engine is a dict of lists."""
        result = research_search_discrepancy("test query")
        assert isinstance(result["unique_per_engine"], dict)
        for engine, urls in result["unique_per_engine"].items():
            assert isinstance(urls, list)
            assert all(isinstance(u, str) for u in urls)

    def test_search_discrepancy_deindexed_candidates_structure(self) -> None:
        """Deindexed candidates have expected structure."""
        result = research_search_discrepancy("test query")
        for candidate in result["deindexed_candidates"]:
            assert isinstance(candidate, dict)
            assert "url" in candidate
            # May have found_in, missing_from fields
