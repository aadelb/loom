"""Tests for Shodan integration tools (host lookup and device search)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestResearchShodanHost:
    @pytest.mark.asyncio
    async def test_sdk_not_installed(self):
        """Test graceful handling when Shodan SDK not installed."""
        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", False):
            from loom.tools.backends.shodan_backend import research_shodan_host

            result = await research_shodan_host("8.8.8.8")

            assert result["ip"] == "8.8.8.8"
            assert "not installed" in result["error"].lower()
            assert result["open_ports"] is None

    @pytest.mark.asyncio
    async def test_api_key_not_set(self):
        """Test graceful handling when SHODAN_API_KEY not set."""
        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch("loom.tools.backends.shodan_backend._get_shodan_api", return_value=None):
                from loom.tools.backends.shodan_backend import research_shodan_host

                result = await research_shodan_host("8.8.8.8")

                assert result["ip"] == "8.8.8.8"
                assert "SHODAN_API_KEY" in result["error"]
                assert result["open_ports"] is None

    @pytest.mark.asyncio
    async def test_successful_host_lookup(self):
        """Test successful host lookup."""
        mock_host_data = {
            "ip_str": "8.8.8.8",
            "ports": [53, 443],
            "org": "Google LLC",
            "isp": "Google LLC",
            "country_name": "United States",
            "country_code": "US",
            "region_code": "CA",
            "city": "Mountain View",
            "latitude": 37.4192,
            "longitude": -122.0574,
            "last_update": "2025-05-01T12:00:00Z",
            "hostnames": ["dns.google.com"],
            "domains": ["google.com"],
            "vulns": ["CVE-2021-1234"],
            "data": [
                {
                    "port": 53,
                    "product": "ISC BIND",
                    "version": "9.16.1",
                    "cpe": "cpe:/a:isc:bind:9.16.1",
                },
                {
                    "port": 443,
                    "product": "nginx",
                    "version": "1.18.0",
                    "cpe": None,
                },
            ],
        }

        mock_api = MagicMock()

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._fetch_host",
                    return_value=mock_host_data,
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_host

                    result = await research_shodan_host("8.8.8.8")

                    assert result["ip"] == "8.8.8.8"
                    assert result["error"] is None
                    assert result["open_ports"] == [53, 443]
                    assert result["org"] == "Google LLC"
                    assert result["country"] == "United States"
                    assert len(result["services"]) == 2
                    assert result["services"][0]["product"] == "ISC BIND"

    @pytest.mark.asyncio
    async def test_host_not_found(self):
        """Test handling of host not found in Shodan database."""
        mock_api = MagicMock()

        # Create a mock APIError without importing shodan
        class MockAPIError(Exception):
            def __init__(self, msg: str):
                self.msg = msg
                super().__init__(msg)

        error = MockAPIError("API error 404: Host not found")

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._fetch_host", side_effect=error
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_host

                    result = await research_shodan_host("192.0.2.1")

                    assert result["ip"] == "192.0.2.1"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_api_invalid_key(self):
        """Test handling of invalid API key."""
        mock_api = MagicMock()

        # Create a mock APIError without importing shodan
        class MockAPIError(Exception):
            def __init__(self, msg: str):
                self.msg = msg
                super().__init__(msg)

        error = MockAPIError("API error 401: Invalid API key")

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._fetch_host", side_effect=error
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_host

                    result = await research_shodan_host("8.8.8.8")

                    assert result["ip"] == "8.8.8.8"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_api_rate_limit(self):
        """Test handling of rate limit exceeded."""
        mock_api = MagicMock()

        # Create a mock APIError without importing shodan
        class MockAPIError(Exception):
            def __init__(self, msg: str):
                self.msg = msg
                super().__init__(msg)

        error = MockAPIError("API error 429: Rate limit exceeded")

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._fetch_host", side_effect=error
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_host

                    result = await research_shodan_host("8.8.8.8")

                    assert result["ip"] == "8.8.8.8"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Test handling of unexpected exceptions."""
        mock_api = MagicMock()

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._fetch_host",
                    side_effect=RuntimeError("Network error"),
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_host

                    result = await research_shodan_host("8.8.8.8")

                    assert result["ip"] == "8.8.8.8"
                    assert "Unexpected error" in result["error"]


class TestResearchShodanSearch:
    @pytest.mark.asyncio
    async def test_sdk_not_installed(self):
        """Test graceful handling when Shodan SDK not installed."""
        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", False):
            from loom.tools.backends.shodan_backend import research_shodan_search

            result = await research_shodan_search("apache country:US port:443")

            assert result["query"] == "apache country:US port:443"
            assert "not installed" in result["error"].lower()
            assert result["total_results"] == 0
            assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_api_key_not_set(self):
        """Test graceful handling when SHODAN_API_KEY not set."""
        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch("loom.tools.backends.shodan_backend._get_shodan_api", return_value=None):
                from loom.tools.backends.shodan_backend import research_shodan_search

                result = await research_shodan_search("apache")

                assert result["query"] == "apache"
                assert "SHODAN_API_KEY" in result["error"]
                assert result["total_results"] == 0

    @pytest.mark.asyncio
    async def test_successful_search(self):
        """Test successful device search."""
        mock_search_result = {
            "total": 1234,
            "matches": [
                {
                    "ip_str": "192.0.2.1",
                    "port": 443,
                    "product": "Apache httpd",
                    "version": "2.4.41",
                    "cpe": "cpe:/a:apache:http_server:2.4.41",
                    "org": "Example Corp",
                    "isp": "Example ISP",
                    "country_name": "United States",
                    "country_code": "US",
                    "city": "San Francisco",
                    "timestamp": "2025-05-01T12:00:00Z",
                    "data": "HTTP/1.1 200 OK\r\nServer: Apache/2.4.41",
                },
                {
                    "ip_str": "192.0.2.2",
                    "port": 80,
                    "product": "Apache httpd",
                    "version": "2.4.43",
                    "cpe": None,
                    "org": "Another Corp",
                    "isp": "Another ISP",
                    "country_name": "Canada",
                    "country_code": "CA",
                    "city": "Toronto",
                    "timestamp": "2025-05-01T11:00:00Z",
                    "data": "HTTP/1.1 200 OK\r\nServer: Apache/2.4.43",
                },
            ],
            "facets": {},
        }

        mock_api = MagicMock()

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._search_devices",
                    return_value=mock_search_result,
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_search

                    result = await research_shodan_search(
                        "apache country:US port:443", max_results=10
                    )

                    assert result["query"] == "apache country:US port:443"
                    assert result["error"] is None
                    assert result["total_results"] == 1234
                    assert len(result["matches"]) == 2
                    assert result["matches"][0]["ip"] == "192.0.2.1"
                    assert result["matches"][0]["product"] == "Apache httpd"

    @pytest.mark.asyncio
    async def test_max_results_clamping(self):
        """Test that max_results is clamped to valid range."""
        mock_search_result = {"total": 0, "matches": [], "facets": {}}

        mock_api = MagicMock()

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._search_devices",
                    return_value=mock_search_result,
                ) as mock_search:
                    from loom.tools.backends.shodan_backend import research_shodan_search

                    # Try max_results > 5000, should be clamped to 5000
                    await research_shodan_search("apache", max_results=10000)

                    # Verify _search_devices was called with clamped value
                    mock_search.assert_called_once()
                    _, call_kwargs = mock_search.call_args
                    # The third positional arg is max_results
                    assert mock_search.call_args[0][2] == 5000

    @pytest.mark.asyncio
    async def test_invalid_query_error(self):
        """Test handling of invalid search query."""
        mock_api = MagicMock()

        # Create a mock APIError without importing shodan
        class MockAPIError(Exception):
            def __init__(self, msg: str):
                self.msg = msg
                super().__init__(msg)

        error = MockAPIError('API error 400: Invalid query syntax: "port"')

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._search_devices", side_effect=error
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_search

                    result = await research_shodan_search("invalid [query")

                    assert result["query"] == "invalid [query"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_api_rate_limit_search(self):
        """Test handling of rate limit exceeded during search."""
        mock_api = MagicMock()

        # Create a mock APIError without importing shodan
        class MockAPIError(Exception):
            def __init__(self, msg: str):
                self.msg = msg
                super().__init__(msg)

        error = MockAPIError("API error 429: Rate limit exceeded")

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._search_devices", side_effect=error
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_search

                    result = await research_shodan_search("apache")

                    assert result["query"] == "apache"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_unexpected_exception_search(self):
        """Test handling of unexpected exceptions during search."""
        mock_api = MagicMock()

        with patch("loom.tools.backends.shodan_backend._HAS_SHODAN", True):
            with patch(
                "loom.tools.backends.shodan_backend._get_shodan_api", return_value=mock_api
            ):
                with patch(
                    "loom.tools.backends.shodan_backend._search_devices",
                    side_effect=ValueError("Network error"),
                ):
                    from loom.tools.backends.shodan_backend import research_shodan_search

                    result = await research_shodan_search("apache")

                    assert result["query"] == "apache"
                    assert "Unexpected error" in result["error"]


class TestShodanHelpers:
    def test_extract_services(self):
        """Test service extraction from banners."""
        from loom.tools.backends.shodan_backend import _extract_services

        banners = [
            {
                "port": 80,
                "product": "Apache httpd",
                "version": "2.4.41",
            },
            {
                "port": 443,
                "product": "nginx",
                "version": "1.18.0",
            },
            {
                "port": 22,
                "product": None,  # No product listed
                "version": None,
            },
        ]

        services = _extract_services(banners)

        assert len(services) == 2
        assert services[0]["port"] == "80"
        assert services[0]["product"] == "Apache httpd"
        assert services[1]["port"] == "443"
        assert services[1]["product"] == "nginx"

    def test_extract_services_empty(self):
        """Test service extraction with empty banners."""
        from loom.tools.backends.shodan_backend import _extract_services

        services = _extract_services([])

        assert services == []


class TestShodanParams:
    def test_shodan_host_params_valid(self):
        """Test valid ShodanHostParams."""
        from loom.params import ShodanHostParams

        params = ShodanHostParams(ip="8.8.8.8")

        assert params.ip == "8.8.8.8"

    def test_shodan_host_params_invalid_ip(self):
        """Test invalid IP address in ShodanHostParams."""
        from loom.params import ShodanHostParams

        with pytest.raises(ValueError):
            ShodanHostParams(ip="not-an-ip")

    def test_shodan_host_params_invalid_octet(self):
        """Test IP with invalid octet in ShodanHostParams."""
        from loom.params import ShodanHostParams

        with pytest.raises(ValueError):
            ShodanHostParams(ip="256.1.1.1")

    def test_shodan_host_params_whitespace(self):
        """Test ShodanHostParams with whitespace."""
        from loom.params import ShodanHostParams

        params = ShodanHostParams(ip="  8.8.8.8  ")

        assert params.ip == "8.8.8.8"

    def test_shodan_search_params_valid(self):
        """Test valid ShodanSearchParams."""
        from loom.params import ShodanSearchParams

        params = ShodanSearchParams(query="apache country:US", max_results=50)

        assert params.query == "apache country:US"
        assert params.max_results == 50

    def test_shodan_search_params_default_max_results(self):
        """Test ShodanSearchParams with default max_results."""
        from loom.params import ShodanSearchParams

        params = ShodanSearchParams(query="apache")

        assert params.max_results == 10

    def test_shodan_search_params_empty_query(self):
        """Test empty query in ShodanSearchParams."""
        from loom.params import ShodanSearchParams

        with pytest.raises(ValueError):
            ShodanSearchParams(query="")

    def test_shodan_search_params_query_too_long(self):
        """Test query too long in ShodanSearchParams."""
        from loom.params import ShodanSearchParams

        long_query = "a" * 501

        with pytest.raises(ValueError):
            ShodanSearchParams(query=long_query)

    def test_shodan_search_params_invalid_max_results(self):
        """Test invalid max_results in ShodanSearchParams."""
        from loom.params import ShodanSearchParams

        with pytest.raises(ValueError):
            ShodanSearchParams(query="apache", max_results=0)

        with pytest.raises(ValueError):
            ShodanSearchParams(query="apache", max_results=5001)

    def test_shodan_search_params_forbid_extra_fields(self):
        """Test that extra fields are forbidden in ShodanSearchParams."""
        from loom.params import ShodanSearchParams

        with pytest.raises(ValueError):
            ShodanSearchParams(query="apache", extra_field="not_allowed")
