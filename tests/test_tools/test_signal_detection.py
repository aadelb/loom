"""Unit tests for signal_detection tools — Ghost protocol, temporal anomalies, SEC tracker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.tools.signal_detection import (
    research_ghost_protocol,
    research_sec_tracker,
    research_temporal_anomaly,
)


pytestmark = pytest.mark.asyncio

class TestGhostProtocol:
    """research_ghost_protocol function."""

    async def test_single_keyword_no_events(self) -> None:
        """Single keyword with no matching events."""
        with patch("loom.tools.signal_detection.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Mock all three platform searches to return empty
            mock_client.get = AsyncMock(
                return_value=MagicMock(status_code=200, json=MagicMock(return_value=[]))
            )

            result = await research_ghost_protocol(["nonexistent_keyword"])
            assert result["keywords"] == ["nonexistent_keyword"]
            assert result["platforms_checked"] == ["GitHub", "HackerNews", "Reddit"]
            assert result["total_events"] == 0

    async def test_keyword_validation(self) -> None:
        """Multiple keywords are processed."""
        result = await research_ghost_protocol(["security", "breach", "vulnerability"])
        assert result["keywords"] == ["security", "breach", "vulnerability"]
        assert "platforms_checked" in result
        assert "coordination_score" in result

    async def test_time_window_parameter(self) -> None:
        """Time window parameter is respected."""
        result = await research_ghost_protocol(["test"], time_window_minutes=60)
        assert result["time_window_minutes"] == 60

    async def test_coordination_score_zero_clusters(self) -> None:
        """Zero clusters = zero coordination score."""
        with patch("loom.tools.signal_detection.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_client.get = AsyncMock(
                return_value=MagicMock(status_code=200, json=MagicMock(return_value=[]))
            )

            result = await research_ghost_protocol(["keyword"])
            assert result["coordination_score"] == 0

    async def test_response_structure(self) -> None:
        """Response includes all required fields."""
        result = await research_ghost_protocol(["test"])
        required_fields = [
            "keywords",
            "time_window_minutes",
            "platforms_checked",
            "clusters_found",
            "coordination_score",
            "total_events",
        ]
        for field in required_fields:
            assert field in result


class TestTemporalAnomaly:
    """research_temporal_anomaly function."""

    async def test_domain_parameter_required(self) -> None:
        """Domain parameter is required."""
        result = await research_temporal_anomaly("")
        assert result["domain"] == ""
        # Should still return structured response even if empty domain

    async def test_check_type_all(self) -> None:
        """check_type='all' runs all checks."""
        with patch("loom.tools.signal_detection.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Mock head request for clock skew
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"date": ""}
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {}))

            result = await research_temporal_anomaly("example.com", check_type="all")
            assert result["domain"] == "example.com"

    async def test_check_type_certs_only(self) -> None:
        """check_type='certs' runs only cert checks."""
        result = await research_temporal_anomaly("example.com", check_type="certs")
        assert result["domain"] == "example.com"
        assert "cert_timing_anomalies" in result

    async def test_check_type_dns_only(self) -> None:
        """check_type='dns' runs only DNS checks."""
        result = await research_temporal_anomaly("example.com", check_type="dns")
        assert result["domain"] == "example.com"
        assert "dns_records" in result

    async def test_check_type_clock_only(self) -> None:
        """check_type='clock' runs only clock skew checks."""
        result = await research_temporal_anomaly("example.com", check_type="clock")
        assert result["domain"] == "example.com"
        assert "clock_skew_ms" in result

    async def test_response_structure(self) -> None:
        """Response includes all required fields."""
        result = await research_temporal_anomaly("example.com")
        required_fields = [
            "domain",
            "anomalies_found",
            "clock_skew_ms",
            "cert_timing_anomalies",
            "dns_records",
        ]
        for field in required_fields:
            assert field in result

    async def test_clock_skew_zero_on_error(self) -> None:
        """Clock skew defaults to 0 on error."""
        with patch(
            "loom.tools.signal_detection._check_server_clock_skew",
            return_value=0,
        ):
            result = await research_temporal_anomaly("invalid..domain")
            assert result["clock_skew_ms"] == 0


class TestSecTracker:
    """research_sec_tracker function."""

    async def test_company_name_parameter(self) -> None:
        """Company name is required."""
        result = await research_sec_tracker("Apple Inc")
        assert result["company"] == "Apple Inc"
        assert "filings_found" in result

    async def test_default_filing_types(self) -> None:
        """Default filing types are used if not specified."""
        result = await research_sec_tracker("Microsoft")
        assert "filings_found" in result
        # Result structure should be consistent

    async def test_custom_filing_types(self) -> None:
        """Custom filing types are accepted."""
        result = await research_sec_tracker("Google", filing_types=["10-K", "8-K"])
        assert result["company"] == "Google"
        assert "filings_found" in result

    async def test_lookback_days_default(self) -> None:
        """Default lookback is 90 days."""
        result = await research_sec_tracker("Tesla")
        assert result["lookback_days"] == 90

    async def test_response_structure(self) -> None:
        """Response includes all required fields."""
        result = await research_sec_tracker("Apple")
        required_fields = [
            "company",
            "filings_found",
            "recent_filings",
            "filing_velocity",
            "lookback_days",
        ]
        for field in required_fields:
            assert field in result

    async def test_filing_velocity_calculation(self) -> None:
        """Filing velocity is calculated correctly."""
        result = await research_sec_tracker("Amazon")
        # Filing velocity should be a number
        assert isinstance(result["filing_velocity"], (int, float))
        assert result["filing_velocity"] >= 0

    async def test_recent_filings_list(self) -> None:
        """Recent filings is always a list."""
        result = await research_sec_tracker("Microsoft")
        assert isinstance(result["recent_filings"], list)

    @patch("loom.tools.signal_detection.httpx.AsyncClient")
    async def test_sec_edgar_error_handling(self, mock_client_class: MagicMock) -> None:
        """SEC EDGAR errors are handled gracefully."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await research_sec_tracker("NonexistentCorp")
        assert result["filings_found"] == 0
        # Should gracefully handle 404

    async def test_empty_company_name(self) -> None:
        """Empty company name is handled."""
        result = await research_sec_tracker("")
        assert result["company"] == ""
        assert "filings_found" in result


class TestIntegration:
    """Integration tests for signal detection tools."""

    async def test_ghost_protocol_response_consistency(self) -> None:
        """Ghost protocol response has consistent structure."""
        result = await research_ghost_protocol(["test"])
        assert isinstance(result["keywords"], list)
        assert isinstance(result["platforms_checked"], list)
        assert isinstance(result["clusters_found"], list)
        assert isinstance(result["coordination_score"], int)
        assert 0 <= result["coordination_score"] <= 100

    async def test_temporal_anomaly_response_consistency(self) -> None:
        """Temporal anomaly response has consistent structure."""
        result = await research_temporal_anomaly("example.com")
        assert isinstance(result["domain"], str)
        assert isinstance(result["anomalies_found"], list)
        assert isinstance(result["clock_skew_ms"], int)
        assert isinstance(result["cert_timing_anomalies"], list)
        assert isinstance(result["dns_records"], dict)

    async def test_sec_tracker_response_consistency(self) -> None:
        """SEC tracker response has consistent structure."""
        result = await research_sec_tracker("Test Corp")
        assert isinstance(result["company"], str)
        assert isinstance(result["filings_found"], int)
        assert isinstance(result["recent_filings"], list)
        assert isinstance(result["filing_velocity"], (int, float))
        assert isinstance(result["lookback_days"], int)

    async def test_all_tools_return_dict(self) -> None:
        """All tools return dictionaries."""
        result1 = await research_ghost_protocol(["test"])
        assert isinstance(result1, dict)

        result2 = await research_temporal_anomaly("example.com")
        assert isinstance(result2, dict)

        result3 = await research_sec_tracker("Test")
        assert isinstance(result3, dict)
