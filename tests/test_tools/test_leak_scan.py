"""Unit tests for leak_scan tool — Data exposure scanning across public sources."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.tools.leak_scan import (
    _check_certificate_transparency,
    _check_github_secrets,
    _check_hibp_breaches,
    _check_pastebin_dork,
    _check_shodan_internetdb,
    _check_trello_dork,
    _is_valid_domain,
    _is_valid_email,
    _is_valid_ip,
    research_leak_scan,
)


class TestIsValidEmail:
    """Email format validation."""

    def test_valid_email(self) -> None:
        """Valid emails pass validation."""
        assert _is_valid_email("user@example.com")
        assert _is_valid_email("test.name+tag@subdomain.example.org")

    def test_invalid_email_no_at(self) -> None:
        """Email without @ fails validation."""
        assert not _is_valid_email("userexample.com")

    def test_invalid_email_no_domain(self) -> None:
        """Email without domain fails validation."""
        assert not _is_valid_email("user@")
        assert not _is_valid_email("@example.com")

    def test_invalid_email_empty(self) -> None:
        """Empty email fails validation."""
        assert not _is_valid_email("")
        assert not _is_valid_email(None)

    def test_email_too_long(self) -> None:
        """Email exceeding 254 chars fails validation."""
        long_email = "a" * 250 + "@example.com"
        assert not _is_valid_email(long_email)


class TestIsValidIP:
    """IP address format validation."""

    def test_valid_ip(self) -> None:
        """Valid IPs pass validation."""
        assert _is_valid_ip("192.168.1.1")
        assert _is_valid_ip("8.8.8.8")
        assert _is_valid_ip("0.0.0.0")
        assert _is_valid_ip("255.255.255.255")

    def test_invalid_ip_format(self) -> None:
        """Malformed IPs fail validation."""
        assert not _is_valid_ip("192.168.1")
        assert not _is_valid_ip("192.168.1.1.1")
        assert not _is_valid_ip("256.1.1.1")
        assert not _is_valid_ip("192.168.-1.1")

    def test_invalid_ip_non_numeric(self) -> None:
        """Non-numeric IPs fail validation."""
        assert not _is_valid_ip("abc.def.ghi.jkl")
        assert not _is_valid_ip("192.168.a.1")

    def test_invalid_ip_empty(self) -> None:
        """Empty IP fails validation."""
        assert not _is_valid_ip("")


class TestIsValidDomain:
    """Domain format validation."""

    def test_valid_domain(self) -> None:
        """Valid domains pass validation."""
        assert _is_valid_domain("example.com")
        assert _is_valid_domain("sub.example.com")
        assert _is_valid_domain("my-site.co.uk")

    def test_invalid_domain_no_tld(self) -> None:
        """Domain without TLD fails validation."""
        assert not _is_valid_domain("localhost")
        assert not _is_valid_domain("example")

    def test_invalid_domain_no_dot(self) -> None:
        """Domain without dot fails validation."""
        assert not _is_valid_domain("example_com")

    def test_invalid_domain_empty(self) -> None:
        """Empty domain fails validation."""
        assert not _is_valid_domain("")
        assert not _is_valid_domain(None)


class TestResearchLeakScan:
    """research_leak_scan main function."""

    def test_invalid_email_target(self) -> None:
        """Invalid email target returns error."""
        result = research_leak_scan("not-an-email", target_type="email")
        assert result.get("error")
        assert "Invalid email" in result["error"]
        assert result["total_exposures"] == 0

    def test_invalid_ip_target(self) -> None:
        """Invalid IP target returns error."""
        result = research_leak_scan("999.999.999.999", target_type="ip")
        assert result.get("error")
        assert "Invalid IP" in result["error"]
        assert result["total_exposures"] == 0

    def test_invalid_domain_target(self) -> None:
        """Invalid domain target returns error."""
        result = research_leak_scan("invalid", target_type="domain")
        assert result.get("error")
        assert "Invalid domain" in result["error"]
        assert result["total_exposures"] == 0

    def test_email_scan_success(self) -> None:
        """Email scan returns results from all sources."""
        with patch("loom.tools.leak_scan._check_hibp_breaches", new_callable=AsyncMock) as mock_hibp, \
             patch("loom.tools.leak_scan._check_pastebin_dork", new_callable=AsyncMock) as mock_paste, \
             patch("loom.tools.leak_scan._check_trello_dork", new_callable=AsyncMock) as mock_trello:
            mock_hibp.return_value = (1, [
                {
                    "source": "HaveIBeenPwned",
                    "type": "email_breach",
                    "description": "Email found in breach",
                    "severity": "high",
                    "url": "https://haveibeenpwned.com",
                }
            ])
            mock_paste.return_value = (0, [])
            mock_trello.return_value = (0, [])

            result = research_leak_scan("test@example.com", target_type="email")

            assert result["target"] == "test@example.com"
            assert result["target_type"] == "email"
            assert result["total_exposures"] == 1
            assert len(result["sources_checked"]) == 3

    def test_ip_scan_success(self) -> None:
        """IP scan returns results from Shodan."""
        with patch("loom.tools.leak_scan._check_shodan_internetdb", new_callable=AsyncMock) as mock_shodan:
            mock_shodan.return_value = (1, [
                {
                    "source": "Shodan InternetDB",
                    "type": "exposed_database",
                    "description": "MongoDB exposed",
                    "severity": "critical",
                    "url": "https://internetdb.shodan.io/1.2.3.4",
                }
            ])

            result = research_leak_scan("192.168.1.1", target_type="ip")

            assert result["target"] == "192.168.1.1"
            assert result["target_type"] == "ip"
            assert result["total_exposures"] == 1

    def test_domain_scan_success(self) -> None:
        """Domain scan returns results from all sources."""
        with patch("loom.tools.leak_scan._check_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.leak_scan._check_github_secrets", new_callable=AsyncMock) as mock_gh, \
             patch("loom.tools.leak_scan._check_pastebin_dork", new_callable=AsyncMock) as mock_paste, \
             patch("loom.tools.leak_scan._check_trello_dork", new_callable=AsyncMock) as mock_trello:
            mock_ct.return_value = (1, [
                {
                    "source": "Certificate Transparency",
                    "type": "email_disclosure",
                    "description": "Email disclosed",
                    "severity": "medium",
                    "url": "https://crt.sh",
                }
            ])
            mock_gh.return_value = (0, [])
            mock_paste.return_value = (0, [])
            mock_trello.return_value = (0, [])

            result = research_leak_scan("example.com", target_type="domain")

            assert result["target"] == "example.com"
            assert result["target_type"] == "domain"
            assert result["total_exposures"] == 1
            assert len(result["sources_checked"]) == 4

    def test_keyword_scan_success(self) -> None:
        """Keyword scan returns results from GitHub, Pastebin, Trello."""
        with patch("loom.tools.leak_scan._check_github_secrets", new_callable=AsyncMock) as mock_gh, \
             patch("loom.tools.leak_scan._check_pastebin_dork", new_callable=AsyncMock) as mock_paste, \
             patch("loom.tools.leak_scan._check_trello_dork", new_callable=AsyncMock) as mock_trello:
            mock_gh.return_value = (1, [
                {
                    "source": "GitHub",
                    "type": "code_exposure",
                    "description": "Secret exposed",
                    "severity": "critical",
                    "url": "https://github.com",
                }
            ])
            mock_paste.return_value = (0, [])
            mock_trello.return_value = (0, [])

            result = research_leak_scan("aws_secret_key", target_type="keyword")

            assert result["target"] == "aws_secret_key"
            assert result["target_type"] == "keyword"
            assert result["total_exposures"] == 1

    def test_severity_sorting(self) -> None:
        """Exposures are sorted by severity (critical > high > medium)."""
        with patch("loom.tools.leak_scan._check_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.leak_scan._check_github_secrets", new_callable=AsyncMock) as mock_gh, \
             patch("loom.tools.leak_scan._check_pastebin_dork", new_callable=AsyncMock) as mock_paste, \
             patch("loom.tools.leak_scan._check_trello_dork", new_callable=AsyncMock) as mock_trello:
            mock_ct.return_value = (1, [
                {"source": "CT", "type": "email", "description": "M", "severity": "medium", "url": "u1"}
            ])
            mock_gh.return_value = (1, [
                {"source": "GH", "type": "code", "description": "C", "severity": "critical", "url": "u2"}
            ])
            mock_paste.return_value = (1, [
                {"source": "PB", "type": "paste", "description": "H", "severity": "high", "url": "u3"}
            ])
            mock_trello.return_value = (0, [])

            result = research_leak_scan("example.com", target_type="domain")

            assert result["total_exposures"] == 3
            severities = [e["severity"] for e in result["exposures"]]
            assert severities == ["critical", "high", "medium"]

    def test_response_structure(self) -> None:
        """Response has required fields."""
        with patch("loom.tools.leak_scan._check_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.leak_scan._check_github_secrets", new_callable=AsyncMock) as mock_gh, \
             patch("loom.tools.leak_scan._check_pastebin_dork", new_callable=AsyncMock) as mock_paste, \
             patch("loom.tools.leak_scan._check_trello_dork", new_callable=AsyncMock) as mock_trello:
            mock_ct.return_value = (0, [])
            mock_gh.return_value = (0, [])
            mock_paste.return_value = (0, [])
            mock_trello.return_value = (0, [])

            result = research_leak_scan("example.com", target_type="domain")

            assert "target" in result
            assert "target_type" in result
            assert "sources_checked" in result
            assert "total_exposures" in result
            assert "exposures" in result
            assert isinstance(result["sources_checked"], list)
            assert isinstance(result["exposures"], list)

    def test_default_target_type(self) -> None:
        """Default target_type is 'domain'."""
        with patch("loom.tools.leak_scan._check_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.leak_scan._check_github_secrets", new_callable=AsyncMock) as mock_gh, \
             patch("loom.tools.leak_scan._check_pastebin_dork", new_callable=AsyncMock) as mock_paste, \
             patch("loom.tools.leak_scan._check_trello_dork", new_callable=AsyncMock) as mock_trello:
            mock_ct.return_value = (0, [])
            mock_gh.return_value = (0, [])
            mock_paste.return_value = (0, [])
            mock_trello.return_value = (0, [])

            result = research_leak_scan("example.com")

            assert result["target_type"] == "domain"
