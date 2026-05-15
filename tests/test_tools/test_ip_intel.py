"""Tests for IP intelligence tools (reputation and geolocation)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest


class TestResearchIpReputation:
    def test_invalid_ip_address(self):
        """Test rejection of invalid IP addresses."""
        from loom.tools.intelligence.ip_intel import research_ip_reputation

        result = research_ip_reputation("not-an-ip")

        assert result["error"] == "Invalid IP address or private IP not allowed"
        assert result["abuse_score"] is None

    def test_private_ip_rejection(self):
        """Test rejection of private IP addresses."""
        from loom.tools.intelligence.ip_intel import research_ip_reputation

        result = research_ip_reputation("192.168.1.1")

        assert "error" in result
        assert "private" in result["error"].lower()

    def test_localhost_rejection(self):
        """Test rejection of localhost."""
        from loom.tools.intelligence.ip_intel import research_ip_reputation

        result = research_ip_reputation("127.0.0.1")

        assert "error" in result

    def test_successful_reputation_check(self):
        """Test successful IP reputation check."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "country": "United States",
            "city": "San Francisco",
            "org": "Google LLC",
            "isp": "Google LLC",
            "lat": 37.7749,
            "lon": -122.4194,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_reputation

            result = research_ip_reputation("8.8.8.8")

            assert result["ip"] == "8.8.8.8"
            assert result["geolocation"] is not None
            assert result["geolocation"]["country"] == "United States"

    def test_reverse_dns_lookup(self):
        """Test reverse DNS lookup."""
        with patch("socket.gethostbyaddr") as mock_gethostbyaddr:
            mock_gethostbyaddr.return_value = ("dns.google.com", [], ["8.8.8.8"])

            from loom.tools.intelligence.ip_intel import research_ip_reputation

            result = research_ip_reputation("8.8.8.8")

            assert result["reverse_dns"] == "dns.google.com"

    def test_reverse_dns_failure(self):
        """Test handling of reverse DNS failure."""
        with patch("socket.gethostbyaddr", side_effect=Exception("DNS error")):
            from loom.tools.intelligence.ip_intel import research_ip_reputation

            result = research_ip_reputation("8.8.8.8")

            # Should still work, just without reverse DNS
            assert result["reverse_dns"] is None

    def test_abuseipdb_integration(self):
        """Test AbuseIPDB integration when API key is set."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "abuseConfidenceScore": 45,
                "isTor": False,
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"ABUSEIPDB_API_KEY": "test-key"}), patch(
            "httpx.Client"
        ) as mock_client_cls, patch("socket.gethostbyaddr", side_effect=Exception()):
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_reputation

            result = research_ip_reputation("8.8.8.8")

            assert result["abuse_score"] == 45
            assert result["is_tor_exit"] is False

    def test_abuseipdb_missing_key(self):
        """Test that AbuseIPDB is skipped when API key is missing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "country": "US",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {}, clear=True), patch("httpx.Client") as mock_client_cls, patch(
            "socket.gethostbyaddr",
            side_effect=Exception(),
        ):
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_reputation

            result = research_ip_reputation("8.8.8.8")

            # Should still have geolocation from ip-api
            assert result["abuse_score"] is None

    def test_response_structure(self):
        """Test that response has all required keys."""
        from loom.tools.intelligence.ip_intel import research_ip_reputation

        result = research_ip_reputation("not-valid")

        required_keys = ["ip", "geolocation", "abuse_score", "is_tor_exit", "reverse_dns"]
        for key in required_keys:
            assert key in result


class TestResearchIpGeolocation:
    def test_invalid_ip_geolocation(self):
        """Test rejection of invalid IP."""
        from loom.tools.intelligence.ip_intel import research_ip_geolocation

        result = research_ip_geolocation("invalid")

        assert "error" in result
        assert "Invalid" in result["error"]

    def test_private_ip_geolocation_rejection(self):
        """Test rejection of private IP for geolocation."""
        from loom.tools.intelligence.ip_intel import research_ip_geolocation

        result = research_ip_geolocation("10.0.0.1")

        assert "error" in result

    def test_successful_geolocation(self):
        """Test successful geolocation lookup."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "country": "United States",
            "regionName": "California",
            "city": "San Francisco",
            "lat": 37.7749,
            "lon": -122.4194,
            "timezone": "America/Los_Angeles",
            "isp": "Google LLC",
            "org": "Google",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_geolocation

            result = research_ip_geolocation("8.8.8.8")

            assert result["country"] == "United States"
            assert result["city"] == "San Francisco"
            assert result["region"] == "California"
            assert result["lat"] == 37.7749
            assert result["timezone"] == "America/Los_Angeles"

    def test_geolocation_failed_status(self):
        """Test handling of failed geolocation status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "fail",
            "message": "private range",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_geolocation

            result = research_ip_geolocation("8.8.8.8")

            assert "error" in result
            assert result["country"] is None

    def test_geolocation_exception_handling(self):
        """Test handling of exceptions during geolocation."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_geolocation

            result = research_ip_geolocation("8.8.8.8")

            assert "error" in result
            assert result["country"] is None

    def test_geolocation_timeout(self):
        """Test handling of timeout during geolocation."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_geolocation

            result = research_ip_geolocation("8.8.8.8")

            assert "error" in result

    def test_geolocation_response_structure(self):
        """Test that geolocation response has all expected keys."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "country": "US",
            "regionName": "CA",
            "city": "SF",
            "lat": 37.7,
            "lon": -122.4,
            "timezone": "America/Los_Angeles",
            "isp": "ISP",
            "org": "ORG",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.intelligence.ip_intel import research_ip_geolocation

            result = research_ip_geolocation("8.8.8.8")

            expected_keys = ["ip", "country", "region", "city", "lat", "lon", "timezone", "isp", "org"]
            for key in expected_keys:
                assert key in result


class TestIsValidIp:
    def test_valid_ipv4(self):
        """Test validation of valid IPv4."""
        from loom.tools.intelligence.ip_intel import _is_valid_ip

        assert _is_valid_ip("8.8.8.8") is True
        assert _is_valid_ip("1.1.1.1") is True

    def test_valid_ipv6(self):
        """Test validation of valid IPv6."""
        from loom.tools.intelligence.ip_intel import _is_valid_ip

        assert _is_valid_ip("2001:4860:4860::8888") is True

    def test_invalid_ipv4(self):
        """Test rejection of invalid IPv4."""
        from loom.tools.intelligence.ip_intel import _is_valid_ip

        assert _is_valid_ip("256.256.256.256") is False
        assert _is_valid_ip("invalid.ip.addr") is False

    def test_private_ipv4_range(self):
        """Test rejection of all private IPv4 ranges."""
        from loom.tools.intelligence.ip_intel import _is_valid_ip

        # 10.0.0.0/8
        assert _is_valid_ip("10.0.0.1") is False
        # 172.16.0.0/12
        assert _is_valid_ip("172.16.0.1") is False
        # 192.168.0.0/16
        assert _is_valid_ip("192.168.0.1") is False
        # 127.0.0.0/8
        assert _is_valid_ip("127.0.0.1") is False

    def test_private_ipv6_range(self):
        """Test rejection of private IPv6 ranges."""
        from loom.tools.intelligence.ip_intel import _is_valid_ip

        # IPv6 loopback
        assert _is_valid_ip("::1") is False
        # IPv6 link-local
        assert _is_valid_ip("fe80::1") is False
