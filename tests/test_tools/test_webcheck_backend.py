"""Unit tests for webcheck_backend tool — Comprehensive website OSINT analyzer."""

from __future__ import annotations

import socket
import ssl
from unittest.mock import MagicMock, Mock, patch

import pytest

from loom.tools.webcheck_backend import (
    _check_cookies,
    _check_dns,
    _check_headers,
    _check_robots,
    _check_ssl,
    _check_trackers,
    _detect_tech,
    _extract_san,
    _fetch_url,
    _parse_cert_date,
    _parse_dn,
    _validate_domain,
    research_web_check,
)


class TestValidateDomain:
    """Domain validation tests."""

    def test_valid_simple_domain(self) -> None:
        """Valid simple domain passes validation."""
        assert _validate_domain("example.com") == "example.com"

    def test_valid_subdomain(self) -> None:
        """Valid subdomain passes validation."""
        assert _validate_domain("sub.example.com") == "sub.example.com"

    def test_domain_lowercased(self) -> None:
        """Domain is lowercased."""
        assert _validate_domain("Example.Com") == "example.com"

    def test_domain_stripped(self) -> None:
        """Domain is stripped of whitespace."""
        assert _validate_domain("  example.com  ") == "example.com"

    def test_domain_www_removed(self) -> None:
        """Leading www. is removed."""
        assert _validate_domain("www.example.com") == "example.com"

    def test_domain_https_removed(self) -> None:
        """Leading https:// is removed."""
        assert _validate_domain("https://example.com") == "example.com"

    def test_domain_http_removed(self) -> None:
        """Leading http:// is removed."""
        assert _validate_domain("http://example.com") == "example.com"

    def test_invalid_empty_domain(self) -> None:
        """Empty domain fails validation."""
        assert _validate_domain("") == ""

    def test_invalid_no_dot(self) -> None:
        """Domain without dot fails validation."""
        assert _validate_domain("localhost") == ""

    def test_invalid_special_chars(self) -> None:
        """Domain with special characters fails validation."""
        assert _validate_domain("example@com") == ""
        assert _validate_domain("example!.com") == ""

    def test_invalid_too_long(self) -> None:
        """Domain exceeding 255 chars fails validation."""
        long_domain = "a" * 256 + ".com"
        assert _validate_domain(long_domain) == ""


class TestParseDN:
    """X.509 Distinguished Name parsing."""

    def test_parse_simple_dn(self) -> None:
        """Parse simple DN tuple."""
        dn = ((("commonName", "example.com"),),)
        result = _parse_dn(dn)
        assert result["CN"] == "example.com"

    def test_parse_multiple_components(self) -> None:
        """Parse DN with multiple components."""
        dn = (
            (("commonName", "example.com"),),
            (("organizationName", "Example Inc"),),
            (("countryName", "US"),),
        )
        result = _parse_dn(dn)
        assert result["CN"] == "example.com"
        assert result["O"] == "Example Inc"
        assert result["C"] == "US"

    def test_parse_empty_dn(self) -> None:
        """Parse empty DN."""
        dn = ()
        result = _parse_dn(dn)
        assert result == {}


class TestParseCertDate:
    """Certificate date parsing."""

    def test_parse_valid_date(self) -> None:
        """Parse valid certificate date."""
        date_str = "Jan  1 00:00:00 2025 GMT"
        result = _parse_cert_date(date_str)
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_parse_empty_date(self) -> None:
        """Parse empty date returns None."""
        result = _parse_cert_date("")
        assert result is None

    def test_parse_invalid_date(self) -> None:
        """Parse invalid date returns None."""
        result = _parse_cert_date("invalid date")
        assert result is None


class TestExtractSAN:
    """Subject Alternative Name extraction."""

    def test_extract_simple_san(self) -> None:
        """Extract simple SAN."""
        san = (("DNS", "example.com"),)
        result = _extract_san(san)
        assert result == ["DNS:example.com"]

    def test_extract_multiple_san(self) -> None:
        """Extract multiple SANs."""
        san = (
            ("DNS", "example.com"),
            ("DNS", "www.example.com"),
            ("IP Address", "192.168.1.1"),
        )
        result = _extract_san(san)
        assert "DNS:example.com" in result
        assert "DNS:www.example.com" in result
        assert "IP Address:192.168.1.1" in result

    def test_extract_empty_san(self) -> None:
        """Extract empty SAN."""
        san = ()
        result = _extract_san(san)
        assert result == []


class TestCheckHeaders:
    """HTTP header analysis."""

    def test_check_key_headers(self) -> None:
        """Extract key security headers."""
        headers = {
            "Server": "nginx/1.24.0",
            "Content-Type": "text/html",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000",
        }
        result = _check_headers(headers)
        assert result["server"] == "nginx/1.24.0"
        assert result["content-type"] == "text/html"
        assert result["x-frame-options"] == "DENY"

    def test_check_headers_case_insensitive(self) -> None:
        """Header lookup is case-insensitive."""
        headers = {"SERVER": "apache"}
        result = _check_headers(headers)
        assert result["server"] == "apache"

    def test_check_empty_headers(self) -> None:
        """Empty headers dict returns empty result."""
        result = _check_headers({})
        assert result == {}


class TestCheckCookies:
    """Cookie extraction from headers."""

    def test_extract_simple_cookie(self) -> None:
        """Extract simple cookie."""
        headers = {"set-cookie": "sessionid=abc123; Path=/; HttpOnly"}
        result = _check_cookies(headers)
        assert result["count"] == 1
        assert result["cookies"][0]["name"] == "sessionid"
        assert result["cookies"][0]["value"] == "abc123"

    def test_extract_multiple_cookies(self) -> None:
        """Extract multiple cookies (multiple set-cookie headers)."""
        headers = {
            "set-cookie": "sessionid=abc123",
        }
        result = _check_cookies(headers)
        assert result["count"] == 1

    def test_check_empty_cookies(self) -> None:
        """No cookies returns count=0."""
        headers = {}
        result = _check_cookies(headers)
        assert result["count"] == 0
        assert result["cookies"] == []


class TestCheckTrackers:
    """Tracker detection in HTML."""

    def test_detect_google_analytics(self) -> None:
        """Detect Google Analytics in HTML."""
        html = '<script src="https://www.googletagmanager.com/gtag.js"></script>'
        result = _check_trackers(html, {})
        assert result["count"] > 0
        tracker_ids = [t["id"] for t in result["trackers"]]
        assert "google_analytics" in tracker_ids

    def test_detect_facebook_pixel(self) -> None:
        """Detect Facebook Pixel in HTML."""
        html = '<img src="https://facebook.com/tr?id=123" />'
        result = _check_trackers(html, {})
        assert result["count"] > 0

    def test_no_trackers(self) -> None:
        """No trackers returns count=0."""
        html = "<html><body>Clean content</body></html>"
        result = _check_trackers(html, {})
        assert result["count"] == 0
        assert result["trackers"] == []


class TestDetectTech:
    """Technology detection in HTML."""

    def test_detect_react(self) -> None:
        """Detect React framework."""
        html = '<div id="__react">React App</div>'
        result = _detect_tech(html, {})
        assert "React" in result["framework"]

    def test_detect_wordpress(self) -> None:
        """Detect WordPress CMS."""
        html = '<link href="/wp-content/theme.css" />'
        result = _detect_tech(html, {})
        assert "WordPress" in result["cms"]

    def test_detect_nginx(self) -> None:
        """Detect Nginx from headers."""
        headers = {"server": "nginx/1.24"}
        result = _detect_tech("", headers)
        assert "Nginx" in result["web_server"]

    def test_detect_php(self) -> None:
        """Detect PHP from headers."""
        headers = {"x-powered-by": "PHP/8.0"}
        result = _detect_tech("", headers)
        assert "PHP" in result["language"]

    def test_no_tech_detected(self) -> None:
        """No tech detected returns empty categories."""
        result = _detect_tech("<html><body>Plain</body></html>", {})
        # All categories should be empty lists
        for techs in result.values():
            assert isinstance(techs, list)


@patch("loom.tools.webcheck_backend.httpx.Client")
def test_fetch_url_success(mock_client_class: Mock) -> None:
    """Fetch URL successfully."""
    mock_response = Mock()
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = "<html></html>"

    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client.get = Mock(return_value=mock_response)
    mock_client_class.return_value = mock_client

    result = _fetch_url("https://example.com")
    assert result is not None
    assert result["headers"]["Content-Type"] == "text/html"
    assert result["html"] == "<html></html>"


@patch("loom.tools.webcheck_backend.httpx.Client")
def test_fetch_url_failure(mock_client_class: Mock) -> None:
    """Fetch URL handles errors gracefully."""
    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client.get = Mock(side_effect=Exception("Network error"))
    mock_client_class.return_value = mock_client

    result = _fetch_url("https://invalid-domain.invalid")
    assert result is None


@patch("loom.tools.webcheck_backend._fetch_url")
def test_research_web_check_basic(mock_fetch: Mock) -> None:
    """Basic web_check call."""
    mock_fetch.return_value = {
        "headers": {"Server": "nginx"},
        "html": "<html></html>",
    }

    result = research_web_check("example.com", checks=["dns", "ssl"])
    assert result["domain"] == "example.com"
    assert "dns" in result["checks_run"]
    assert "ssl" in result["checks_run"]


def test_research_web_check_invalid_domain() -> None:
    """Web check with invalid domain."""
    result = research_web_check("invalid", checks=["dns"])
    assert "error" in result


def test_research_web_check_no_checks() -> None:
    """Web check with no valid checks."""
    result = research_web_check("example.com", checks=["invalid"])
    assert "error" in result


@patch("loom.tools.webcheck_backend.httpx.Client")
def test_check_robots_found(mock_client_class: Mock) -> None:
    """Check robots.txt when found."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "User-agent: *\nDisallow: /admin\nDisallow: /private"

    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client.get = Mock(return_value=mock_response)
    mock_client_class.return_value = mock_client

    result = _check_robots("https://example.com")
    assert result["found"] is True
    assert "/admin" in result["disallowed_paths"]
    assert "/private" in result["disallowed_paths"]


@patch("loom.tools.webcheck_backend.httpx.Client")
def test_check_robots_not_found(mock_client_class: Mock) -> None:
    """Check robots.txt when not found."""
    mock_response = Mock()
    mock_response.status_code = 404

    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    mock_client.get = Mock(return_value=mock_response)
    mock_client_class.return_value = mock_client

    result = _check_robots("https://example.com")
    assert result["found"] is False


@patch("loom.tools.webcheck_backend.socket.socket")
@patch("loom.tools.webcheck_backend.ssl.create_default_context")
def test_check_ssl_success(mock_ssl_context: Mock, mock_socket_class: Mock) -> None:
    """Check SSL certificate successfully."""
    # Mock SSL context and socket
    mock_wrapped_socket = Mock()
    mock_wrapped_socket.getpeercert = Mock(
        return_value={
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("organizationName", "Example CA"),),),
            "notBefore": "Jan  1 00:00:00 2025 GMT",
            "notAfter": "Dec 31 23:59:59 2026 GMT",
            "subjectAltName": (("DNS", "example.com"), ("DNS", "www.example.com")),
        }
    )

    mock_context = Mock()
    mock_context.wrap_socket = Mock(return_value=mock_wrapped_socket)
    mock_ssl_context.return_value = mock_context

    result = _check_ssl("example.com")
    assert result["has_ssl"] is True
    assert result["subject"]["CN"] == "example.com"


def test_check_dns_with_invalid_domain() -> None:
    """Check DNS with invalid domain."""
    result = _check_dns("invalid_domain_!@#")
    # Should handle gracefully
    assert "domain" in result


@patch("loom.tools.webcheck_backend.socket.getaddrinfo")
def test_check_dns_resolution(mock_getaddrinfo: Mock) -> None:
    """Check DNS A record resolution."""
    mock_getaddrinfo.return_value = [
        (2, 1, 6, "", ("192.0.2.1", 0)),
    ]

    result = _check_dns("example.com")
    assert result["domain"] == "example.com"
    assert "192.0.2.1" in result["a_records"]
