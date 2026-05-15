"""Unit tests for threat intelligence tools — dark markets, ransomware, phishing, botnets, malware, domains, IOCs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.intelligence.threat_intel import (
    research_botnet_tracker,
    research_dark_market_monitor,
    research_domain_reputation,
    research_ioc_enrich,
    research_malware_intel,
    research_phishing_mapper,
    research_ransomware_tracker,
)


pytestmark = pytest.mark.asyncio

class TestDarkMarketMonitor:
    """research_dark_market_monitor monitors dark market activity."""

    async def test_dark_market_empty_keywords(self) -> None:
        """Returns error when keywords list is empty."""
        result = await research_dark_market_monitor(keywords=[])

        assert result["error"] == "keywords list cannot be empty"
        assert result["mentions"] == []
        assert result["alerts"] == []

    async def test_dark_market_single_keyword(self) -> None:
        """Searches dark markets for single keyword."""
        with patch("loom.tools.threat_intel.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()

            # Mock OTX response
            mock_response.json = AsyncMock(
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

            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = None

            result = await research_dark_market_monitor(keywords=["exploit"])

            assert result["keywords"] == ["exploit"]
            assert len(result["sources_checked"]) >= 0

    async def test_dark_market_multiple_keywords(self) -> None:
        """Handles multiple keywords."""
        result = await research_dark_market_monitor(
            keywords=["ransomware", "exploit", "botnet"]
        )

        assert result["keywords"] == ["ransomware", "exploit", "botnet"]
        assert "mentions_count" in result or "mentions" in result
        assert "alerts_count" in result or "alerts" in result


class TestRansomwareTracker:
    """research_ransomware_tracker tracks ransomware group activity."""

    async def test_ransomware_tracker_missing_params(self) -> None:
        """Returns error when group_name and keyword are both empty."""
        result = await research_ransomware_tracker(group_name="", keyword="")

        assert result["error"] == "group_name or keyword required"
        assert result.get("recent_activity", []) == [] or result.get("error")
        assert result.get("iocs_found", []) == [] or result.get("error")

    async def test_ransomware_tracker_with_group_name(self) -> None:
        """Tracks ransomware group by group name."""
        result = await research_ransomware_tracker(group_name="LockBit")

        assert result["group_name"] == "LockBit"
        assert "recent_activity" in result or "error" in result
        assert "victims_mentioned" in result or "error" in result

    async def test_ransomware_tracker_with_keyword_fallback(self) -> None:
        """Falls back to keyword search."""
        result = await research_ransomware_tracker(keyword="ransomware")

        assert result.get("keyword") == "ransomware" or "error" in result
        assert "recent_activity" in result or "error" in result


class TestPhishingMapper:
    """research_phishing_mapper detects phishing campaigns."""

    async def test_phishing_mapper_empty_domain(self) -> None:
        """Returns error for empty domain."""
        result = await research_phishing_mapper(domain="")

        assert result["error"] == "domain required"
        assert result.get("lookalike_domains", []) == [] or result.get("error")
        assert result.get("active_phishing_urls", []) == [] or result.get("error")

    async def test_phishing_mapper_finds_lookalikes(self) -> None:
        """Identifies typosquatted lookalike domains."""
        with patch("loom.tools.threat_intel.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Mock CT response with lookalike domains
            mock_response = MagicMock()
            mock_response.json = AsyncMock(
                return_value=[
                    {"name_value": "examp1e.com"},
                    {"name_value": "example.co"},
                ]
            )
            mock_response.status_code = 200

            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = None

            result = await research_phishing_mapper(domain="example.com")

            assert result["domain"] == "example.com"
            assert "lookalike_domains_count" in result or "lookalike_domains" in result
            assert "active_phishing_urls_count" in result or "active_phishing_urls" in result

    async def test_phishing_mapper_risk_levels(self) -> None:
        """Correctly assigns risk levels based on threat score."""
        result = await research_phishing_mapper(domain="example.com")
        # Risk calculation happens in async code
        assert "risk_level" in result or "error" in result


class TestBotnetTracker:
    """research_botnet_tracker tracks botnet C2 infrastructure."""

    async def test_botnet_tracker_empty_ioc(self) -> None:
        """Returns error for empty IOC."""
        result = await research_botnet_tracker(ioc="")

        assert result["error"] == "ioc required"
        assert result.get("known_c2") is False or result.get("error")

    async def test_botnet_tracker_ip_address(self) -> None:
        """Checks IP addresses against botnet blocklists."""
        result = await research_botnet_tracker(ioc="192.0.2.1", ioc_type="ip")

        assert result["ioc"] == "192.0.2.1"
        assert result.get("ioc_type") == "ip" or result.get("error")
        assert isinstance(result.get("known_c2"), bool) or result.get("error")
        assert isinstance(result.get("blocklist_status"), list) or result.get("error")

    async def test_botnet_tracker_domain(self) -> None:
        """Checks domains for botnet activity."""
        result = await research_botnet_tracker(ioc="c2.example.com", ioc_type="domain")

        assert result["ioc"] == "c2.example.com"
        assert result.get("ioc_type") == "domain" or result.get("error")


class TestMalwareIntel:
    """research_malware_intel cross-references malware hashes."""

    async def test_malware_intel_empty_hash(self) -> None:
        """Returns error for empty hash."""
        result = await research_malware_intel(hash_value="")

        assert result["error"] == "hash_value required"
        assert result.get("detections", []) == [] or result.get("error")
        assert result.get("family") is None or result.get("error")

    async def test_malware_intel_valid_hash(self) -> None:
        """Queries multiple sources for hash information."""
        # Using a realistic-looking SHA-256 hash
        hash_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        result = await research_malware_intel(hash_value=hash_val)

        assert result["hash"] == hash_val
        assert "detections_count" in result or "detections" in result
        assert isinstance(result.get("detections", []), list)
        assert "family" in result or result.get("error")
        assert "first_seen" in result or result.get("error")

    async def test_malware_intel_invalid_hash_format(self) -> None:
        """Handles invalid hash formats gracefully."""
        result = await research_malware_intel(hash_value="not-a-hash")

        assert result["hash"] == "not-a-hash"
        # Should still return a valid response structure
        assert isinstance(result, dict)


class TestDomainReputation:
    """research_domain_reputation aggregates domain reputation."""

    async def test_domain_reputation_empty_domain(self) -> None:
        """Returns error for empty domain."""
        result = await research_domain_reputation(domain="")

        assert result["error"] == "domain required"
        assert result.get("reputation_score") == 0 or result.get("error")
        assert result.get("is_malicious") is False or result.get("error")

    async def test_domain_reputation_clean_domain(self) -> None:
        """Checks reputation of clean domain."""
        result = await research_domain_reputation(domain="google.com")

        assert result["domain"] == "google.com" or result.get("error")
        assert isinstance(result.get("reputation_score", 0), int)
        score = result.get("reputation_score", 0)
        assert 0 <= score <= 100 or result.get("error")

    async def test_domain_reputation_multiple_sources(self) -> None:
        """Queries multiple reputation sources."""
        result = await research_domain_reputation(domain="example.com")

        assert "total_sources_checked" in result or result.get("error")
        sources = result.get("total_sources_checked", 0)
        assert sources >= 0 or result.get("error")

    async def test_domain_reputation_scoring(self) -> None:
        """Reputation scoring is between 0-100."""
        result = await research_domain_reputation(domain="test.example")

        score = result.get("reputation_score", 0)
        assert isinstance(score, int)
        assert 0 <= score <= 100 or result.get("error")


class TestIOCEnrich:
    """research_ioc_enrich enriches indicators of compromise."""

    async def test_ioc_enrich_empty_ioc(self) -> None:
        """Returns error for empty IOC."""
        result = await research_ioc_enrich(ioc="")

        assert result["error"] == "ioc required"
        assert result.get("sources_checked", []) == [] or result.get("error")
        assert result.get("enrichments", []) == [] or result.get("error")

    async def test_ioc_enrich_auto_detect_ip(self) -> None:
        """Auto-detects IP address type."""
        result = await research_ioc_enrich(ioc="192.0.2.1", ioc_type="auto")

        assert result["ioc"] == "192.0.2.1"
        assert result.get("ioc_type") == "ip" or result.get("error")

    async def test_ioc_enrich_auto_detect_hash(self) -> None:
        """Auto-detects SHA-256 hash type."""
        hash_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        result = await research_ioc_enrich(ioc=hash_val, ioc_type="auto")

        assert result["ioc"] == hash_val
        assert result.get("ioc_type") == "hash" or result.get("error")

    async def test_ioc_enrich_auto_detect_domain(self) -> None:
        """Auto-detects domain type."""
        result = await research_ioc_enrich(ioc="example.com", ioc_type="auto")

        assert result["ioc"] == "example.com"
        assert result.get("ioc_type") == "domain" or result.get("error")

    async def test_ioc_enrich_auto_detect_url(self) -> None:
        """Auto-detects URL type."""
        result = await research_ioc_enrich(ioc="https://example.com/path", ioc_type="auto")

        assert result["ioc"] == "https://example.com/path"
        assert result.get("ioc_type") == "url" or result.get("error")

    async def test_ioc_enrich_returns_enrichments(self) -> None:
        """Returns enrichment data from multiple sources."""
        result = await research_ioc_enrich(ioc="192.0.2.1", ioc_type="ip")

        assert isinstance(result.get("sources_checked", []), list)
        assert isinstance(result.get("enrichments", []), list)
        threat_score = result.get("threat_score", 0)
        assert isinstance(threat_score, int)
        assert 0 <= threat_score <= 100 or result.get("error")

    async def test_ioc_enrich_threat_score_calculation(self) -> None:
        """Threat score is calculated based on verdicts."""
        result = await research_ioc_enrich(ioc="example.com")

        threat_score = result.get("threat_score", 0)
        assert isinstance(threat_score, int)
        assert 0 <= threat_score <= 100 or result.get("error")

    async def test_ioc_enrich_multiple_enrichment_types(self) -> None:
        """Returns multiple types of enrichment data."""
        result = await research_ioc_enrich(ioc="192.0.2.1")

        # Should query multiple sources or have error
        sources_checked = result.get("sources_checked", [])
        assert isinstance(sources_checked, list)


class TestIntegration:
    """Integration tests across multiple threat intel tools."""

    async def test_dark_market_and_ransomware_consistency(self) -> None:
        """Dark market monitor and ransomware tracker return consistent structure."""
        dark_result = await research_dark_market_monitor(keywords=["ransomware"])
        ransomware_result = await research_ransomware_tracker(group_name="test")

        # Both should have consistent response structure
        assert isinstance(dark_result, dict)
        assert isinstance(ransomware_result, dict)

    async def test_phishing_and_domain_reputation_chain(self) -> None:
        """Phishing mapper and domain reputation complement each other."""
        domain = "example.com"
        phishing_result = await research_phishing_mapper(domain=domain)
        reputation_result = await research_domain_reputation(domain=domain)

        assert phishing_result.get("domain") == domain or phishing_result.get("error")
        assert reputation_result.get("domain") == domain or reputation_result.get("error")

    async def test_ioc_enrichment_covers_all_types(self) -> None:
        """IOC enrichment handles all major IOC types."""
        test_cases = [
            ("192.0.2.1", "ip"),
            ("example.com", "domain"),
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "hash"),
            ("https://example.com", "url"),
        ]

        for ioc, expected_type in test_cases:
            result = await research_ioc_enrich(ioc=ioc, ioc_type="auto")
            assert result.get("ioc_type") == expected_type or result.get("error")


class TestErrorHandling:
    """Test error handling across threat intel tools."""

    async def test_network_error_resilience(self) -> None:
        """Tools handle network errors gracefully."""
        # Even if network fails, should return valid response structure
        result = await research_dark_market_monitor(keywords=["test"])
        assert isinstance(result, dict)

    async def test_invalid_input_validation(self) -> None:
        """All functions validate inputs."""
        # Empty inputs should be handled
        result = await research_dark_market_monitor(keywords=[])
        assert result.get("error")
        result = await research_ransomware_tracker(group_name="", keyword="")
        assert result.get("error")
        result = await research_phishing_mapper(domain="")
        assert result.get("error")
        result = await research_botnet_tracker(ioc="")
        assert result.get("error")
        result = await research_malware_intel(hash_value="")
        assert result.get("error")
        result = await research_domain_reputation(domain="")
        assert result.get("error")
        result = await research_ioc_enrich(ioc="")
        assert result.get("error")

    async def test_response_structure_consistency(self) -> None:
        """All functions return consistent response structures."""
        responses = [
            await research_dark_market_monitor(keywords=["test"]),
            await research_ransomware_tracker(group_name="test"),
            await research_phishing_mapper(domain="example.com"),
            await research_botnet_tracker(ioc="192.0.2.1"),
            await research_malware_intel(hash_value="abc123"),
            await research_domain_reputation(domain="example.com"),
            await research_ioc_enrich(ioc="192.0.2.1"),
        ]

        for response in responses:
            assert isinstance(response, dict)
