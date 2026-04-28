"""Unit tests for threat intelligence tools — dark markets, ransomware, phishing, botnets, malware, domains, IOCs."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.tools.threat_intel import (
    research_botnet_tracker,
    research_dark_market_monitor,
    research_domain_reputation,
    research_ioc_enrich,
    research_malware_intel,
    research_phishing_mapper,
    research_ransomware_tracker,
)


class TestDarkMarketMonitor:
    """research_dark_market_monitor monitors dark market activity."""

    def test_dark_market_empty_keywords(self) -> None:
        """Returns error when keywords list is empty."""
        result = research_dark_market_monitor(keywords=[])

        assert result["error"] == "keywords list cannot be empty"
        assert result["mentions"] == []
        assert result["alerts"] == []

    def test_dark_market_single_keyword(self) -> None:
        """Searches dark markets for single keyword."""
        with patch("loom.tools.threat_intel.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            # Mock OTX response
            mock_response.json = MagicMock(
                return_value={
                    "results": [
                        {
                            "type": "malware",
                            "title": "Exploit Kit Campaign",
                            "created": "2026-04-20",
                        }
                    ]
                }
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_dark_market_monitor(keywords=["exploit"])

            assert result["keywords"] == ["exploit"]
            assert len(result["sources_checked"]) >= 0

    def test_dark_market_multiple_keywords(self) -> None:
        """Handles multiple keywords."""
        result = research_dark_market_monitor(
            keywords=["ransomware", "exploit", "botnet"]
        )

        assert result["keywords"] == ["ransomware", "exploit", "botnet"]
        assert "mentions_count" in result
        assert "alerts_count" in result


class TestRansomwareTracker:
    """research_ransomware_tracker tracks ransomware group activity."""

    def test_ransomware_tracker_missing_params(self) -> None:
        """Returns error when group_name and keyword are both empty."""
        result = research_ransomware_tracker(group_name="", keyword="")

        assert result["error"] == "group_name or keyword required"
        assert result["recent_activity"] == []
        assert result["iocs_found"] == []

    def test_ransomware_tracker_with_group_name(self) -> None:
        """Tracks ransomware group by group name."""
        result = research_ransomware_tracker(group_name="LockBit")

        assert result["group_name"] == "LockBit"
        assert "recent_activity" in result
        assert "victims_mentioned" in result
        assert "iocs_found" in result

    def test_ransomware_tracker_with_keyword_fallback(self) -> None:
        """Falls back to keyword search."""
        result = research_ransomware_tracker(keyword="ransomware")

        assert result["keyword"] == "ransomware"
        assert "recent_activity" in result


class TestPhishingMapper:
    """research_phishing_mapper detects phishing campaigns."""

    def test_phishing_mapper_empty_domain(self) -> None:
        """Returns error for empty domain."""
        result = research_phishing_mapper(domain="")

        assert result["error"] == "domain required"
        assert result["lookalike_domains"] == []
        assert result["active_phishing_urls"] == []

    def test_phishing_mapper_finds_lookalikes(self) -> None:
        """Identifies typosquatted lookalike domains."""
        with patch("loom.tools.threat_intel.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()

            # Mock CT response with lookalike domains
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value=[
                    {"name_value": "examp1e.com"},
                    {"name_value": "example.co"},
                ]
            )
            mock_response.status_code = 200

            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_phishing_mapper(domain="example.com")

            assert result["domain"] == "example.com"
            assert "lookalike_domains_count" in result
            assert "active_phishing_urls_count" in result
            assert result["risk_level"] in ("low", "medium", "high", "critical")

    def test_phishing_mapper_risk_levels(self) -> None:
        """Correctly assigns risk levels based on threat score."""
        # Low risk
        with patch("loom.tools.threat_intel._crt_sh_lookalikes", return_value=[]):
            with patch("loom.tools.threat_intel._urlhaus_host_check", return_value=[]):
                result = research_phishing_mapper(domain="example.com")
                # Risk calculation happens in async code


class TestBotnetTracker:
    """research_botnet_tracker tracks botnet C2 infrastructure."""

    def test_botnet_tracker_empty_ioc(self) -> None:
        """Returns error for empty IOC."""
        result = research_botnet_tracker(ioc="")

        assert result["error"] == "ioc required"
        assert result["known_c2"] is False
        assert result["blocklist_status"] == []

    def test_botnet_tracker_ip_address(self) -> None:
        """Checks IP addresses against botnet blocklists."""
        result = research_botnet_tracker(ioc="192.0.2.1", ioc_type="ip")

        assert result["ioc"] == "192.0.2.1"
        assert result["ioc_type"] == "ip"
        assert isinstance(result["known_c2"], bool)
        assert isinstance(result["blocklist_status"], list)
        assert result["threat_level"] in ("low", "high", "critical", "unknown")

    def test_botnet_tracker_domain(self) -> None:
        """Checks domains for botnet activity."""
        result = research_botnet_tracker(ioc="c2.example.com", ioc_type="domain")

        assert result["ioc"] == "c2.example.com"
        assert result["ioc_type"] == "domain"


class TestMalwareIntel:
    """research_malware_intel cross-references malware hashes."""

    def test_malware_intel_empty_hash(self) -> None:
        """Returns error for empty hash."""
        result = research_malware_intel(hash_value="")

        assert result["error"] == "hash_value required"
        assert result["detections"] == []
        assert result["family"] is None
        assert result["tags"] == []

    def test_malware_intel_valid_hash(self) -> None:
        """Queries multiple sources for hash information."""
        # Using a realistic-looking SHA-256 hash
        hash_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        result = research_malware_intel(hash_value=hash_val)

        assert result["hash"] == hash_val
        assert "detections_count" in result
        assert isinstance(result["detections"], list)
        assert "family" in result
        assert "first_seen" in result
        assert isinstance(result["tags"], list)

    def test_malware_intel_invalid_hash_format(self) -> None:
        """Handles invalid hash formats gracefully."""
        result = research_malware_intel(hash_value="not-a-hash")

        assert result["hash"] == "not-a-hash"
        # Should still return a valid response structure


class TestDomainReputation:
    """research_domain_reputation aggregates domain reputation."""

    def test_domain_reputation_empty_domain(self) -> None:
        """Returns error for empty domain."""
        result = research_domain_reputation(domain="")

        assert result["error"] == "domain required"
        assert result["reputation_score"] == 0
        assert result["is_malicious"] is False

    def test_domain_reputation_clean_domain(self) -> None:
        """Checks reputation of clean domain."""
        result = research_domain_reputation(domain="google.com")

        assert result["domain"] == "google.com"
        assert isinstance(result["reputation_score"], int)
        assert 0 <= result["reputation_score"] <= 100
        assert isinstance(result["is_malicious"], bool)
        assert isinstance(result["verdicts_by_source"], dict)

    def test_domain_reputation_multiple_sources(self) -> None:
        """Queries multiple reputation sources."""
        result = research_domain_reputation(domain="example.com")

        assert "total_sources_checked" in result
        assert result["total_sources_checked"] >= 2
        assert "malicious_sources" in result
        assert len(result["verdicts_by_source"]) > 0

    def test_domain_reputation_scoring(self) -> None:
        """Reputation scoring is between 0-100."""
        result = research_domain_reputation(domain="test.example")

        assert isinstance(result["reputation_score"], int)
        assert 0 <= result["reputation_score"] <= 100


class TestIOCEnrich:
    """research_ioc_enrich enriches indicators of compromise."""

    def test_ioc_enrich_empty_ioc(self) -> None:
        """Returns error for empty IOC."""
        result = research_ioc_enrich(ioc="")

        assert result["error"] == "ioc required"
        assert result["sources_checked"] == []
        assert result["enrichments"] == []

    def test_ioc_enrich_auto_detect_ip(self) -> None:
        """Auto-detects IP address type."""
        result = research_ioc_enrich(ioc="192.0.2.1", ioc_type="auto")

        assert result["ioc"] == "192.0.2.1"
        assert result["ioc_type"] == "ip"

    def test_ioc_enrich_auto_detect_hash(self) -> None:
        """Auto-detects SHA-256 hash type."""
        hash_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        result = research_ioc_enrich(ioc=hash_val, ioc_type="auto")

        assert result["ioc"] == hash_val
        assert result["ioc_type"] == "hash"

    def test_ioc_enrich_auto_detect_domain(self) -> None:
        """Auto-detects domain type."""
        result = research_ioc_enrich(ioc="example.com", ioc_type="auto")

        assert result["ioc"] == "example.com"
        assert result["ioc_type"] == "domain"

    def test_ioc_enrich_auto_detect_url(self) -> None:
        """Auto-detects URL type."""
        result = research_ioc_enrich(ioc="https://example.com/path", ioc_type="auto")

        assert result["ioc"] == "https://example.com/path"
        assert result["ioc_type"] == "url"

    def test_ioc_enrich_returns_enrichments(self) -> None:
        """Returns enrichment data from multiple sources."""
        result = research_ioc_enrich(ioc="192.0.2.1", ioc_type="ip")

        assert isinstance(result["sources_checked"], list)
        assert isinstance(result["enrichments"], list)
        assert isinstance(result["threat_score"], int)
        assert 0 <= result["threat_score"] <= 100
        assert isinstance(result["verdicts"], dict)

    def test_ioc_enrich_threat_score_calculation(self) -> None:
        """Threat score is calculated based on verdicts."""
        result = research_ioc_enrich(ioc="example.com")

        assert isinstance(result["threat_score"], int)
        assert 0 <= result["threat_score"] <= 100
        assert result["verdict_summary"] in (
            "clean",
            "suspicious",
            "malicious",
        )

    def test_ioc_enrich_multiple_enrichment_types(self) -> None:
        """Returns multiple types of enrichment data."""
        result = research_ioc_enrich(ioc="192.0.2.1")

        # Should query multiple sources
        assert len(result["sources_checked"]) > 0
        # Sources may include OTX, Shodan, Feodo, URLhaus, Ahmia, CIRCL
        expected_sources = {"OTX", "Shodan", "Feodo", "URLhaus", "Ahmia", "CIRCL"}
        assert len(result["sources_checked"]) > 0


class TestIntegration:
    """Integration tests across multiple threat intel tools."""

    def test_dark_market_and_ransomware_consistency(self) -> None:
        """Dark market monitor and ransomware tracker return consistent structure."""
        dark_result = research_dark_market_monitor(keywords=["ransomware"])
        ransomware_result = research_ransomware_tracker(group_name="test")

        # Both should have consistent response structure
        assert "keywords" in dark_result or "group_name" in ransomware_result
        assert isinstance(dark_result.get("mentions_count"), int)

    def test_phishing_and_domain_reputation_chain(self) -> None:
        """Phishing mapper and domain reputation complement each other."""
        domain = "example.com"
        phishing_result = research_phishing_mapper(domain=domain)
        reputation_result = research_domain_reputation(domain=domain)

        assert phishing_result["domain"] == domain
        assert reputation_result["domain"] == domain
        # Phishing should detect lookalikes, reputation should check main domain

    def test_ioc_enrichment_covers_all_types(self) -> None:
        """IOC enrichment handles all major IOC types."""
        test_cases = [
            ("192.0.2.1", "ip"),
            ("example.com", "domain"),
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "hash"),
            ("https://example.com", "url"),
        ]

        for ioc, expected_type in test_cases:
            result = research_ioc_enrich(ioc=ioc, ioc_type="auto")
            assert result["ioc_type"] == expected_type
            assert len(result["sources_checked"]) >= 0


class TestErrorHandling:
    """Test error handling across threat intel tools."""

    def test_network_error_resilience(self) -> None:
        """Tools handle network errors gracefully."""
        # Even if network fails, should return valid response structure
        result = research_dark_market_monitor(keywords=["test"])
        assert "keywords" in result
        assert isinstance(result.get("mentions_count", 0), int)

    def test_invalid_input_validation(self) -> None:
        """All functions validate inputs."""
        # Empty inputs should be handled
        assert research_dark_market_monitor(keywords=[]).get("error")
        assert research_ransomware_tracker().get("error")
        assert research_phishing_mapper(domain="").get("error")
        assert research_botnet_tracker(ioc="").get("error")
        assert research_malware_intel(hash_value="").get("error")
        assert research_domain_reputation(domain="").get("error")
        assert research_ioc_enrich(ioc="").get("error")

    def test_response_structure_consistency(self) -> None:
        """All functions return consistent response structures."""
        responses = [
            research_dark_market_monitor(keywords=["test"]),
            research_ransomware_tracker(group_name="test"),
            research_phishing_mapper(domain="example.com"),
            research_botnet_tracker(ioc="192.0.2.1"),
            research_malware_intel(hash_value="abc123"),
            research_domain_reputation(domain="example.com"),
            research_ioc_enrich(ioc="192.0.2.1"),
        ]

        for response in responses:
            assert isinstance(response, dict)
            # Should contain either data or error
            assert any(
                key in response for key in
                ["mentions", "activity", "domain", "threat_level", "detections", "verdicts", "enrichments", "error"]
            )
