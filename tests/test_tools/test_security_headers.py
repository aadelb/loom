"""Unit tests for security_headers tool — HTTP security header analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from loom.tools.security_headers import research_security_headers


class TestSecurityHeaders:
    """research_security_headers function."""

    def test_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_security_headers("not-a-url")
        assert result.get("error")

    def test_request_timeout(self) -> None:
        """Request timeout returns error."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.head.side_effect = httpx.TimeoutException("timeout")
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert result.get("error")
            assert "timeout" in result["error"].lower()

    def test_request_error(self) -> None:
        """Request error returns error."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.head.side_effect = httpx.RequestError("connection refused")
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert result.get("error")
            assert "Request failed" in result["error"]

    def test_all_headers_present(self) -> None:
        """All headers present returns grade A."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock response with all security headers
            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=()",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin",
            })
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert not result.get("error")
            assert result["grade"] == "A"
            assert result["score"] >= 90
            assert result["headers_found"]["Strict-Transport-Security"]["present"]
            assert result["headers_found"]["Content-Security-Policy"]["present"]

    def test_no_headers_present(self) -> None:
        """No headers present returns grade F."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock response with no security headers
            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({})
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert not result.get("error")
            assert result["grade"] == "F"
            assert result["score"] < 40
            assert len(result["missing"]) == 9
            assert len(result["recommendations"]) > 0

    def test_partial_headers_present(self) -> None:
        """Partial headers present returns grade B or C."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock response with some security headers
            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({
                "Strict-Transport-Security": "max-age=31536000",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
            })
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert not result.get("error")
            assert result["grade"] in ("B", "C")
            assert result["score"] > 30
            assert len(result["missing"]) == 6

    def test_unsafe_csp_warning(self) -> None:
        """CSP with unsafe-inline gets warning grade."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock response with unsafe CSP
            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({
                "Content-Security-Policy": "default-src 'self' 'unsafe-inline'",
                "Strict-Transport-Security": "max-age=31536000",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
            })
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert result["headers_found"]["Content-Security-Policy"]["grade"] == "warning"

    def test_hsts_without_maxage_warning(self) -> None:
        """HSTS without max-age gets warning grade."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock response with incomplete HSTS
            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({
                "Strict-Transport-Security": "includeSubDomains",  # Missing max-age
            })
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert result["headers_found"]["Strict-Transport-Security"]["grade"] == "warning"

    def test_recommendations_generated(self) -> None:
        """Recommendations are generated for missing headers."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({})
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            assert len(result["recommendations"]) > 0
            assert any("HSTS" in rec for rec in result["recommendations"])
            assert any("CSP" in rec or "Content-Security-Policy" in rec for rec in result["recommendations"])

    def test_score_calculation(self) -> None:
        """Score calculation matches header weights."""
        with patch("loom.tools.security_headers.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Present: HSTS (12), CSP (12), X-Frame-Options (11) = 35 points
            # Total possible: 113 points
            # Expected score: 35/113 * 100 ≈ 31
            mock_response = MagicMock()
            mock_response.headers = httpx.Headers({
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'",
                "X-Frame-Options": "DENY",
            })
            mock_client.head.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_security_headers("https://example.com")
            # Score should be between 25-35
            assert 25 < result["score"] < 40
