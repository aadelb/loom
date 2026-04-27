"""Unit tests for cert_analyzer tool — SSL/TLS certificate extraction."""

from __future__ import annotations

import socket
import ssl
from unittest.mock import MagicMock, Mock, patch

import pytest

from loom.tools.cert_analyzer import (
    _extract_san,
    _is_valid_hostname,
    _parse_cert_date,
    _parse_dn,
    research_cert_analyze,
)


class TestIsValidHostname:
    """Hostname validation for certificate analysis."""

    def test_valid_domain(self) -> None:
        """Valid domains pass validation."""
        assert _is_valid_hostname("example.com")
        assert _is_valid_hostname("subdomain.example.org")
        assert _is_valid_hostname("my-domain.co.uk")
        assert _is_valid_hostname("test123.example.com")

    def test_valid_ip(self) -> None:
        """Valid IP addresses pass validation."""
        assert _is_valid_hostname("192.168.1.1")
        assert _is_valid_hostname("8.8.8.8")
        assert _is_valid_hostname("127.0.0.1")

    def test_hostname_empty(self) -> None:
        """Empty hostname fails validation."""
        assert not _is_valid_hostname("")
        assert not _is_valid_hostname(None)

    def test_hostname_whitespace(self) -> None:
        """Hostname with whitespace fails validation."""
        assert not _is_valid_hostname("example .com")
        assert not _is_valid_hostname(" example.com")

    def test_hostname_disallowed_chars(self) -> None:
        """Hostname with special chars fails validation."""
        assert not _is_valid_hostname("example@com")
        assert not _is_valid_hostname("example_com.net")
        assert not _is_valid_hostname("example!.com")

    def test_hostname_start_end_hyphen(self) -> None:
        """Hostname starting or ending with hyphen fails validation."""
        assert not _is_valid_hostname("-example.com")
        assert not _is_valid_hostname("example-.com")

    def test_hostname_start_end_dot(self) -> None:
        """Hostname starting or ending with dot fails validation."""
        assert not _is_valid_hostname(".example.com")
        assert not _is_valid_hostname("example.com.")

    def test_hostname_too_long(self) -> None:
        """Hostname exceeding 255 chars fails validation."""
        long_hostname = "a" * 256 + ".com"
        assert not _is_valid_hostname(long_hostname)


class TestParseDN:
    """X.509 Distinguished Name parsing."""

    def test_parse_simple_dn(self) -> None:
        """Parse simple DN tuple."""
        dn = ((("commonName", "example.com"),),)
        result = _parse_dn(dn)
        assert result["CN"] == "example.com"

    def test_parse_multiple_components(self) -> None:
        """Parse DN with multiple RDN components."""
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

    def test_parse_unknown_oid(self) -> None:
        """Parse DN with unknown OID (uses OID name as-is)."""
        dn = ((("unknownOID", "value123"),),)
        result = _parse_dn(dn)
        assert result["unknownOID"] == "value123"


class TestParseCertDate:
    """SSL certificate date parsing."""

    def test_parse_valid_date(self) -> None:
        """Parse valid certificate date."""
        date_str = "Jan  1 00:00:00 2025 GMT"
        result = _parse_cert_date(date_str)
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_parse_date_with_padding(self) -> None:
        """Parse date with variable spacing."""
        date_str = "Dec 31 23:59:59 2024 GMT"
        result = _parse_cert_date(date_str)
        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 31

    def test_parse_invalid_date(self) -> None:
        """Parse invalid date returns None."""
        result = _parse_cert_date("invalid-date")
        assert result is None

    def test_parse_empty_date(self) -> None:
        """Parse empty date returns None."""
        result = _parse_cert_date("")
        assert result is None


class TestExtractSAN:
    """Subject Alternative Name extraction."""

    def test_extract_dns_names(self) -> None:
        """Extract DNS SANs."""
        san_tuple = (
            ("DNS", "example.com"),
            ("DNS", "www.example.com"),
        )
        result = _extract_san(san_tuple)
        assert "DNS:example.com" in result
        assert "DNS:www.example.com" in result

    def test_extract_ip_addresses(self) -> None:
        """Extract IP address SANs."""
        san_tuple = (
            ("IP Address", "192.168.1.1"),
            ("IP Address", "10.0.0.1"),
        )
        result = _extract_san(san_tuple)
        assert "IP Address:192.168.1.1" in result
        assert "IP Address:10.0.0.1" in result

    def test_extract_mixed_san(self) -> None:
        """Extract mixed DNS and IP SANs."""
        san_tuple = (
            ("DNS", "example.com"),
            ("IP Address", "93.184.216.34"),
        )
        result = _extract_san(san_tuple)
        assert len(result) == 2

    def test_extract_empty_san(self) -> None:
        """Extract from empty SAN tuple."""
        san_tuple = ()
        result = _extract_san(san_tuple)
        assert result == []


class TestCertAnalyze:
    """Main research_cert_analyze function."""

    def test_invalid_hostname_format(self) -> None:
        """Invalid hostname format returns error."""
        result = research_cert_analyze("invalid@hostname")
        assert result["error"]
        assert "Invalid hostname" in result["error"]

    def test_invalid_port_range(self) -> None:
        """Invalid port returns error."""
        result = research_cert_analyze("example.com", port=0)
        assert result["error"]
        assert "Port" in result["error"]

        result = research_cert_analyze("example.com", port=99999)
        assert result["error"]
        assert "Port" in result["error"]

    @patch("loom.tools.cert_analyzer.socket.socket")
    def test_socket_timeout(self, mock_socket_class: MagicMock) -> None:
        """Socket timeout returns error."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.timeout()
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        with patch("loom.tools.cert_analyzer.ssl.create_default_context") as mock_ctx:
            mock_ssl_ctx = MagicMock()
            mock_ctx.return_value = mock_ssl_ctx
            mock_ssl_ctx.wrap_socket.return_value.__enter__.return_value = mock_socket

            result = research_cert_analyze("example.com")
            assert result["error"]
            assert "timeout" in result["error"].lower()

    @patch("loom.tools.cert_analyzer.socket.socket")
    def test_socket_gaierror(self, mock_socket_class: MagicMock) -> None:
        """DNS resolution failure returns error."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.gaierror("DNS failed")
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        with patch("loom.tools.cert_analyzer.ssl.create_default_context") as mock_ctx:
            mock_ssl_ctx = MagicMock()
            mock_ctx.return_value = mock_ssl_ctx
            mock_ssl_ctx.wrap_socket.return_value.__enter__.return_value = mock_socket

            result = research_cert_analyze("invalid-dns.example")
            assert result["error"]
            assert "DNS" in result["error"]

    def test_missing_certificate(self) -> None:
        """Missing certificate returns error."""
        with patch("loom.tools.cert_analyzer.socket.socket"):
            with patch("loom.tools.cert_analyzer.ssl.create_default_context") as mock_ctx:
                mock_ssl_ctx = MagicMock()
                mock_ctx.return_value = mock_ssl_ctx
                mock_socket = MagicMock()
                mock_socket.getpeercert.return_value = None
                mock_ssl_ctx.wrap_socket.return_value.__enter__.return_value = mock_socket

                result = research_cert_analyze("example.com")
                assert result["error"]

    @patch("loom.tools.cert_analyzer.socket.socket")
    def test_valid_certificate(self, mock_socket_class: MagicMock) -> None:
        """Valid certificate returns parsed fields."""
        with patch("loom.tools.cert_analyzer.ssl.create_default_context") as mock_ctx:
            mock_ssl_ctx = MagicMock()
            mock_ctx.return_value = mock_ssl_ctx

            mock_socket = MagicMock()
            mock_cert_dict = {
                "subject": ((("commonName", "example.com"),),),
                "issuer": ((("commonName", "Example CA"),),),
                "notBefore": "Jan  1 00:00:00 2025 GMT",
                "notAfter": "Jan  1 00:00:00 2026 GMT",
                "subjectAltName": (
                    ("DNS", "example.com"),
                    ("DNS", "www.example.com"),
                ),
                "version": 3,
            }
            mock_socket.getpeercert.return_value = mock_cert_dict
            mock_socket.getpeercert.return_value.__bool__ = lambda x: True
            mock_ssl_ctx.wrap_socket.return_value.__enter__.return_value = mock_socket

            result = research_cert_analyze("example.com")
            assert result["hostname"] == "example.com"
            assert result["port"] == 443
            assert not result.get("error")
            assert result["subject"]["CN"] == "example.com"
            assert result["is_self_signed"] is False
            assert "DNS:example.com" in result["san"]
            assert result["version"] == 3
