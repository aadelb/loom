"""Unit tests for Censys host lookup and search tools."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestCensysHost:
    """research_censys_host returns expected shape and handles errors."""

    async def test_invalid_ip_returns_error(self) -> None:
        """Invalid IP address returns error dict."""
        from loom.tools.censys_backend import research_censys_host

        result = await research_censys_host("not-an-ip")
        assert "error" in result
        assert result["ip"] == "not-an-ip"
        assert result["censys_available"] is False

    async def test_missing_credentials_returns_error(self) -> None:
        """Missing API credentials returns error with helpful message."""
        from loom.tools.censys_backend import research_censys_host

        # Ensure env vars are not set
        old_id = os.environ.pop("CENSYS_API_ID", None)
        old_secret = os.environ.pop("CENSYS_API_SECRET", None)

        try:
            result = await research_censys_host("192.0.2.1")
            assert "error" in result
            assert "credentials not found" in result["error"].lower()
            assert result["censys_available"] is False
        finally:
            if old_id:
                os.environ["CENSYS_API_ID"] = old_id
            if old_secret:
                os.environ["CENSYS_API_SECRET"] = old_secret

    async def test_censys_not_installed_returns_error(self) -> None:
        """Missing censys library returns error with install instruction."""
        from loom.tools.censys_backend import research_censys_host

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", False):
                result = await research_censys_host("192.0.2.1")
                assert "error" in result
                assert "not installed" in result["error"].lower()
                assert result["censys_available"] is False
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)

    async def test_successful_host_lookup(self) -> None:
        """Successful host lookup returns structured data."""
        from loom.tools.censys_backend import research_censys_host

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            mock_host_data = {
                "services": [
                    {
                        "port": 80,
                        "service_name": "HTTP",
                        "banner": "Apache/2.4.41",
                    },
                    {
                        "port": 443,
                        "service_name": "HTTPS",
                        "banner": "Apache/2.4.41",
                    },
                ],
                "tls": {
                    "certificates": [
                        {
                            "subject": {"common_name": "example.com"},
                            "issuer": {"common_name": "Let's Encrypt"},
                            "validity": {
                                "not_before": "2024-01-01",
                                "not_after": "2025-01-01",
                            },
                            "fingerprint": "abc123def456789",
                        }
                    ]
                },
                "location": {
                    "country": "US",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                },
                "protocols": ["HTTP", "HTTPS"],
                "autonomous_system": {
                    "asn": 15169,
                    "name": "Google LLC",
                },
            }

            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", True):
                with patch(
                    "loom.tools.censys_backend.CensysHosts"
                ) as mock_censys_class:
                    mock_client = MagicMock()
                    mock_client.view.return_value = mock_host_data
                    mock_censys_class.return_value = mock_client

                    result = await research_censys_host("192.0.2.1")

                    assert result["ip"] == "192.0.2.1"
                    assert result["censys_available"] is True
                    assert "error" not in result
                    assert len(result["services"]) == 2
                    assert result["services"][0]["port"] == 80
                    assert result["services"][0]["protocol"] == "HTTP"
                    assert len(result["tls_certs"]) == 1
                    assert result["tls_certs"][0]["subject"] == "example.com"
                    assert result["location"]["country"] == "US"
                    assert result["autonomous_system"]["asn"] == 15169
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)

    async def test_api_exception_handling(self) -> None:
        """API exceptions are caught and returned gracefully."""
        from loom.tools.censys_backend import research_censys_host

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", True):
                with patch(
                    "loom.tools.censys_backend.CensysHosts"
                ) as mock_censys_class:
                    mock_client = MagicMock()
                    mock_client.view.side_effect = Exception("API rate limit exceeded")
                    mock_censys_class.return_value = mock_client

                    result = await research_censys_host("192.0.2.1")

                    assert result["ip"] == "192.0.2.1"
                    assert "error" in result
                    assert "rate limit" in result["error"]
                    assert result["censys_available"] is True
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)

    async def test_ipv6_validation(self) -> None:
        """IPv6 addresses are validated correctly."""
        from loom.tools.censys_backend import research_censys_host

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", True):
                with patch(
                    "loom.tools.censys_backend.CensysHosts"
                ) as mock_censys_class:
                    mock_client = MagicMock()
                    mock_client.view.return_value = {
                        "services": [],
                        "tls": {"certificates": []},
                        "location": {},
                        "protocols": [],
                    }
                    mock_censys_class.return_value = mock_client

                    result = await research_censys_host("2001:db8::1")

                    assert result["ip"] == "2001:db8::1"
                    assert "error" not in result
                    assert result["censys_available"] is True
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)


@pytest.mark.asyncio
class TestCensysSearch:
    """research_censys_search returns expected shape and handles errors."""

    async def test_invalid_query_returns_error(self) -> None:
        """Invalid query returns error dict."""
        from loom.tools.censys_backend import research_censys_search

        result = await research_censys_search("<script>alert('xss')</script>")
        assert "error" in result
        assert result["censys_available"] is False

    async def test_invalid_max_results_returns_error(self) -> None:
        """Invalid max_results returns error."""
        from loom.tools.censys_backend import research_censys_search

        result = await research_censys_search("services.service_name: HTTP", max_results=5001)
        assert "error" in result
        assert "max_results" in result["error"].lower()

    async def test_missing_credentials_returns_error(self) -> None:
        """Missing API credentials returns error."""
        from loom.tools.censys_backend import research_censys_search

        old_id = os.environ.pop("CENSYS_API_ID", None)
        old_secret = os.environ.pop("CENSYS_API_SECRET", None)

        try:
            result = await research_censys_search("services.service_name: HTTP")
            assert "error" in result
            assert "credentials not found" in result["error"].lower()
            assert result["censys_available"] is False
        finally:
            if old_id:
                os.environ["CENSYS_API_ID"] = old_id
            if old_secret:
                os.environ["CENSYS_API_SECRET"] = old_secret

    async def test_successful_search(self) -> None:
        """Successful search returns structured results."""
        from loom.tools.censys_backend import research_censys_search

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            mock_results = [
                {
                    "ip": "192.0.2.1",
                    "services": [
                        {"port": 80, "service_name": "HTTP"},
                        {"port": 443, "service_name": "HTTPS"},
                    ],
                    "last_updated": "2024-01-15T10:00:00Z",
                    "score": 95.5,
                },
                {
                    "ip": "192.0.2.2",
                    "services": [{"port": 22, "service_name": "SSH"}],
                    "last_updated": "2024-01-15T11:00:00Z",
                    "score": 78.2,
                },
            ]

            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", True):
                with patch(
                    "loom.tools.censys_backend.CensysHosts"
                ) as mock_censys_class:
                    mock_client = MagicMock()
                    mock_client.search.return_value = mock_results
                    mock_censys_class.return_value = mock_client

                    result = await research_censys_search(
                        "services.service_name: HTTP",
                        max_results=10,
                    )

                    assert result["query"] == "services.service_name: HTTP"
                    assert result["max_results"] == 10
                    assert result["censys_available"] is True
                    assert "error" not in result
                    assert len(result["results"]) == 2
                    assert result["results"][0]["ip"] == "192.0.2.1"
                    assert len(result["results"][0]["services"]) == 2
                    assert result["results"][0]["services"][0]["port"] == 80
                    assert result["results"][1]["ip"] == "192.0.2.2"
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)

    async def test_search_respects_max_results(self) -> None:
        """Search limits results to max_results parameter."""
        from loom.tools.censys_backend import research_censys_search

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            # Generate 20 mock results
            mock_results = [
                {
                    "ip": f"192.0.2.{i}",
                    "services": [{"port": 80, "service_name": "HTTP"}],
                    "last_updated": "2024-01-15T10:00:00Z",
                    "score": 90.0,
                }
                for i in range(1, 21)
            ]

            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", True):
                with patch(
                    "loom.tools.censys_backend.CensysHosts"
                ) as mock_censys_class:
                    mock_client = MagicMock()
                    mock_client.search.return_value = mock_results
                    mock_censys_class.return_value = mock_client

                    result = await research_censys_search(
                        "services.service_name: HTTP",
                        max_results=5,
                    )

                    # Should limit to 5 even though API returned 20
                    assert len(result["results"]) <= 5
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)

    async def test_api_exception_handling(self) -> None:
        """API exceptions are caught and returned gracefully."""
        from loom.tools.censys_backend import research_censys_search

        os.environ["CENSYS_API_ID"] = "test-id"
        os.environ["CENSYS_API_SECRET"] = "test-secret"

        try:
            with patch("loom.tools.censys_backend.CENSYS_AVAILABLE", True):
                with patch(
                    "loom.tools.censys_backend.CensysHosts"
                ) as mock_censys_class:
                    mock_client = MagicMock()
                    mock_client.search.side_effect = Exception("Invalid query syntax")
                    mock_censys_class.return_value = mock_client

                    result = await research_censys_search("INVALID QUERY <<<>>>")

                    assert "error" in result
                    assert result["censys_available"] is True
        finally:
            os.environ.pop("CENSYS_API_ID", None)
            os.environ.pop("CENSYS_API_SECRET", None)


@pytest.mark.asyncio
class TestCensysParamValidation:
    """Parameter validation models for Censys tools."""

    async def test_censys_host_params_valid(self) -> None:
        """Valid CensysHostParams passes validation."""
        from loom.params import CensysHostParams

        params = CensysHostParams(ip="192.0.2.1")
        assert params.ip == "192.0.2.1"

    async def test_censys_host_params_invalid_ip(self) -> None:
        """Invalid IP in CensysHostParams raises validation error."""
        from pydantic import ValidationError

        from loom.params import CensysHostParams

        with pytest.raises(ValidationError):
            CensysHostParams(ip="not-an-ip-address")

    async def test_censys_host_params_forbids_extra_fields(self) -> None:
        """CensysHostParams forbids extra fields."""
        from pydantic import ValidationError

        from loom.params import CensysHostParams

        with pytest.raises(ValidationError) as exc_info:
            CensysHostParams(ip="192.0.2.1", extra_field="not allowed")
        assert "extra_field" in str(exc_info.value)

    async def test_censys_search_params_valid(self) -> None:
        """Valid CensysSearchParams passes validation."""
        from loom.params import CensysSearchParams

        params = CensysSearchParams(
            query="services.service_name: HTTP",
            max_results=10,
        )
        assert params.query == "services.service_name: HTTP"
        assert params.max_results == 10

    async def test_censys_search_params_default_max_results(self) -> None:
        """CensysSearchParams uses default max_results of 10."""
        from loom.params import CensysSearchParams

        params = CensysSearchParams(query="services.service_name: HTTP")
        assert params.max_results == 10

    async def test_censys_search_params_invalid_max_results(self) -> None:
        """Invalid max_results raises validation error."""
        from pydantic import ValidationError

        from loom.params import CensysSearchParams

        with pytest.raises(ValidationError):
            CensysSearchParams(
                query="services.service_name: HTTP",
                max_results=5001,  # exceeds max of 1000
            )

    async def test_censys_search_params_empty_query(self) -> None:
        """Empty query raises validation error."""
        from pydantic import ValidationError

        from loom.params import CensysSearchParams

        with pytest.raises(ValidationError):
            CensysSearchParams(query="")

    async def test_censys_search_params_forbids_extra_fields(self) -> None:
        """CensysSearchParams forbids extra fields."""
        from pydantic import ValidationError

        from loom.params import CensysSearchParams

        with pytest.raises(ValidationError) as exc_info:
            CensysSearchParams(
                query="services.service_name: HTTP",
                unknown_param="not allowed",
            )
        assert "unknown_param" in str(exc_info.value)
