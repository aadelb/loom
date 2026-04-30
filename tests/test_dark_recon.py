"""Unit tests for dark_recon tools — TorBot and OWASP Amass integration."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from loom.tools.dark_recon import (
    _is_tool_available,
    _validate_domain,
    research_amass_enum,
    research_amass_intel,
    research_torbot,
)


class TestValidateDomain:
    """Domain validation for OWASP Amass tools."""

    def test_valid_domain(self) -> None:
        """Valid domains pass validation."""
        assert _validate_domain("example.com") == "example.com"
        assert _validate_domain("sub.example.org") == "sub.example.org"
        assert _validate_domain("test-domain.co.uk") == "test-domain.co.uk"
        assert _validate_domain("my_domain.net") == "my_domain.net"

    def test_domain_too_long(self) -> None:
        """Domain exceeding 255 chars raises error."""
        long_domain = "a" * 256 + ".com"
        with pytest.raises(ValueError, match="1-255 characters"):
            _validate_domain(long_domain)

    def test_domain_empty(self) -> None:
        """Empty domain raises error."""
        with pytest.raises(ValueError):
            _validate_domain("")

    def test_domain_disallowed_chars(self) -> None:
        """Domain with spaces or special chars raises error."""
        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_domain("example .com")
        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_domain("example@com")
        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_domain("example/com")


class TestIsToolAvailable:
    """Tool availability detection."""

    @patch("loom.tools.dark_recon.shutil.which")
    def test_tool_available(self, mock_which: MagicMock) -> None:
        """shutil.which returns path for available tool."""
        mock_which.return_value = "/usr/bin/torbot"
        assert _is_tool_available("torbot") is True
        mock_which.assert_called_once_with("torbot")

    @patch("loom.tools.dark_recon.shutil.which")
    def test_tool_not_available(self, mock_which: MagicMock) -> None:
        """shutil.which returns None for unavailable tool."""
        mock_which.return_value = None
        assert _is_tool_available("torbot") is False
        mock_which.assert_called_once_with("torbot")


class TestTorbot:
    """research_torbot command execution and output parsing."""

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    @patch("loom.tools.dark_recon.validate_url")
    def test_torbot_success_json(
        self, mock_validate_url: MagicMock, mock_available: MagicMock, mock_run: MagicMock
    ) -> None:
        """Successful TorBot crawl with JSON output returns parsed results."""
        mock_validate_url.return_value = "http://example.onion"
        mock_available.return_value = True
        torbot_output = json.dumps({
            "links": ["http://example.onion/page1", "http://example.onion/page2"],
            "emails": ["admin@example.onion", "contact@example.onion"],
            "phone_numbers": ["+1-555-0123", "+1-555-0456"],
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=torbot_output, stderr="")

        result = research_torbot("http://example.onion", depth=2)

        assert result["url"] == "http://example.onion"
        assert result["depth_crawled"] == 2
        assert len(result["links_found"]) == 2
        assert "http://example.onion/page1" in result["links_found"]
        assert len(result["emails_found"]) == 2
        assert "admin@example.onion" in result["emails_found"]
        assert len(result["phone_numbers"]) == 2
        assert "+1-555-0123" in result["phone_numbers"]
        mock_run.assert_called_once_with(
            ["torbot", "-u", "http://example.onion", "--depth", "2", "--json"],
            capture_output=True,
            text=True,
            timeout=300,
        )

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    @patch("loom.tools.dark_recon.validate_url")
    def test_torbot_success_text_fallback(
        self, mock_validate_url: MagicMock, mock_available: MagicMock, mock_run: MagicMock
    ) -> None:
        """TorBot with non-JSON output falls back to regex parsing."""
        mock_validate_url.return_value = "http://example.onion"
        mock_available.return_value = True
        torbot_output = """
        Found: http://example.onion/page1
        Found: http://example.onion/page2
        Email: admin@example.onion
        Phone: +1-555-0123
        """
        mock_run.return_value = MagicMock(returncode=0, stdout=torbot_output, stderr="")

        result = research_torbot("http://example.onion", depth=1)

        assert result["url"] == "http://example.onion"
        assert len(result["links_found"]) >= 2
        assert len(result["emails_found"]) >= 1
        assert len(result["phone_numbers"]) >= 1

    @patch("loom.tools.dark_recon._is_tool_available")
    @patch("loom.tools.dark_recon.validate_url")
    def test_torbot_not_installed(
        self, mock_validate_url: MagicMock, mock_available: MagicMock
    ) -> None:
        """TorBot not installed returns graceful warning."""
        mock_validate_url.return_value = "http://example.onion"
        mock_available.return_value = False

        result = research_torbot("http://example.onion")

        assert result["url"] == "http://example.onion"
        assert "warning" in result
        assert "TorBot is not installed" in result["warning"]
        assert result["links_found"] == []
        assert result["emails_found"] == []
        assert result["phone_numbers"] == []
        assert result["depth_crawled"] == 0

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    @patch("loom.tools.dark_recon.validate_url")
    def test_torbot_command_failed(
        self, mock_validate_url: MagicMock, mock_available: MagicMock, mock_run: MagicMock
    ) -> None:
        """TorBot command failure returns error."""
        mock_validate_url.return_value = "http://example.onion"
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Connection refused")

        result = research_torbot("http://example.onion")

        assert result["url"] == "http://example.onion"
        assert "error" in result
        assert "torbot command failed" in result["error"]
        assert result["links_found"] == []

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    @patch("loom.tools.dark_recon.validate_url")
    def test_torbot_timeout(
        self, mock_validate_url: MagicMock, mock_available: MagicMock, mock_run: MagicMock
    ) -> None:
        """TorBot timeout returns error."""
        mock_validate_url.return_value = "http://example.onion"
        mock_available.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("torbot", timeout=300)

        result = research_torbot("http://example.onion", depth=3)

        assert result["url"] == "http://example.onion"
        assert "error" in result
        assert "timed out" in result["error"]
        assert result["depth_crawled"] == 0

    def test_torbot_invalid_url(self) -> None:
        """Invalid URL returns error."""
        from loom.validators import UrlSafetyError

        with patch("loom.tools.dark_recon.validate_url", side_effect=UrlSafetyError("Invalid URL")):
            result = research_torbot("not a valid url")
            assert "error" in result

    def test_torbot_invalid_depth_type(self) -> None:
        """Non-integer depth returns error."""
        with patch("loom.tools.dark_recon.validate_url", return_value="http://example.onion"):
            result = research_torbot("http://example.onion", depth="invalid")  # type: ignore
            assert "error" in result
            assert "depth must be an integer" in result["error"]

    @patch("loom.tools.dark_recon._is_tool_available")
    @patch("loom.tools.dark_recon.validate_url")
    def test_torbot_invalid_depth_range(
        self, mock_validate_url: MagicMock, mock_available: MagicMock
    ) -> None:
        """Depth out of range returns error."""
        mock_validate_url.return_value = "http://example.onion"
        mock_available.return_value = True

        result = research_torbot("http://example.onion", depth=0)
        assert "error" in result

        result = research_torbot("http://example.onion", depth=6)
        assert "error" in result


class TestAmassEnum:
    """research_amass_enum command execution and output parsing."""

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_success(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Successful Amass enum returns parsed subdomains, ASNs, and IPs."""
        mock_available.return_value = True
        amass_output = "\n".join([
            json.dumps({"name": "sub1.example.com", "addresses": [{"ip": "192.168.1.1"}], "asn": {"asnum": 12345}, "sources": ["source1"]}),
            json.dumps({"name": "sub2.example.com", "addresses": [{"ip": "192.168.1.2"}], "asn": {"asnum": 12346}, "sources": ["source2"]}),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=amass_output, stderr="")

        result = research_amass_enum("example.com", passive=True, timeout=120)

        assert result["domain"] == "example.com"
        assert len(result["subdomains"]) >= 2
        assert "sub1.example.com" in result["subdomains"]
        assert len(result["ip_addresses"]) >= 2
        assert "192.168.1.1" in result["ip_addresses"]
        assert len(result["asns"]) >= 2
        assert "12345" in result["asns"]
        assert result["count"] > 0

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_with_passive_flag(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass enum respects passive flag."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        research_amass_enum("example.com", passive=True)
        call_args = mock_run.call_args[0][0]
        assert "-passive" in call_args

        research_amass_enum("example.com", passive=False)
        call_args = mock_run.call_args[0][0]
        assert "-passive" not in call_args

    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_not_installed(self, mock_available: MagicMock) -> None:
        """Amass not installed returns graceful warning."""
        mock_available.return_value = False

        result = research_amass_enum("example.com")

        assert result["domain"] == "example.com"
        assert "warning" in result
        assert "Amass is not installed" in result["warning"]
        assert result["subdomains"] == []
        assert result["ip_addresses"] == []
        assert result["asns"] == []
        assert result["count"] == 0

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_command_failed(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass enum command failure returns error."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Invalid domain")

        result = research_amass_enum("invalid..domain")

        assert "error" in result

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_timeout(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass enum timeout returns error."""
        import subprocess

        mock_available.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("amass", timeout=60)

        result = research_amass_enum("example.com", timeout=60)

        assert "error" in result
        assert "timed out" in result["error"]
        assert result["count"] == 0

    def test_amass_enum_invalid_domain(self) -> None:
        """Invalid domain returns error."""
        result = research_amass_enum("invalid@domain")

        assert "error" in result
        assert "disallowed characters" in result["error"]

    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_invalid_timeout(self, mock_available: MagicMock) -> None:
        """Timeout out of range returns error."""
        mock_available.return_value = True

        result = research_amass_enum("example.com", timeout=0)
        assert "error" in result

        result = research_amass_enum("example.com", timeout=601)
        assert "error" in result

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_enum_malformed_json(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass enum with malformed JSON lines skips them gracefully."""
        mock_available.return_value = True
        amass_output = "\n".join([
            json.dumps({"name": "valid.example.com"}),
            "invalid json line",
            json.dumps({"name": "also-valid.example.com"}),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=amass_output, stderr="")

        result = research_amass_enum("example.com")

        assert len(result["subdomains"]) == 2
        assert "valid.example.com" in result["subdomains"]


class TestAmassIntel:
    """research_amass_intel command execution and output parsing."""

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_success(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Successful Amass intel returns organizations, emails, and related domains."""
        mock_available.return_value = True
        amass_output = "\n".join([
            json.dumps({"org": "Example Corp", "email": "admin@example.com", "domain": "related.com"}),
            json.dumps({"org": "Another Corp", "email": "info@example.com", "domain": "another-related.com"}),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=amass_output, stderr="")

        result = research_amass_intel("example.com")

        assert result["domain"] == "example.com"
        assert len(result["organizations"]) >= 2
        assert "Example Corp" in result["organizations"]
        assert len(result["emails"]) >= 2
        assert "admin@example.com" in result["emails"]
        assert len(result["related_domains"]) >= 2
        assert "related.com" in result["related_domains"]

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_name_field_as_domain(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass intel extracts domains from 'name' field as fallback."""
        mock_available.return_value = True
        amass_output = json.dumps({"name": "fallback-domain.com"})
        mock_run.return_value = MagicMock(returncode=0, stdout=amass_output, stderr="")

        result = research_amass_intel("example.com")

        assert "fallback-domain.com" in result["related_domains"]

    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_not_installed(self, mock_available: MagicMock) -> None:
        """Amass not installed returns graceful warning."""
        mock_available.return_value = False

        result = research_amass_intel("example.com")

        assert result["domain"] == "example.com"
        assert "warning" in result
        assert "Amass is not installed" in result["warning"]
        assert result["organizations"] == []
        assert result["emails"] == []
        assert result["related_domains"] == []

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_command_failed(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass intel command failure returns error."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Domain not found")

        result = research_amass_intel("invalid..domain")

        assert "error" in result

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_timeout(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass intel timeout returns error."""
        import subprocess

        mock_available.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("amass", timeout=120)

        result = research_amass_intel("example.com")

        assert "error" in result
        assert "timed out" in result["error"]

    def test_amass_intel_invalid_domain(self) -> None:
        """Invalid domain returns error."""
        result = research_amass_intel("invalid@domain")

        assert "error" in result
        assert "disallowed characters" in result["error"]

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_malformed_json(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass intel with malformed JSON lines skips them gracefully."""
        mock_available.return_value = True
        amass_output = "\n".join([
            json.dumps({"org": "Valid Corp"}),
            "invalid json",
            json.dumps({"org": "Also Valid"}),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=amass_output, stderr="")

        result = research_amass_intel("example.com")

        assert len(result["organizations"]) == 2
        assert "Valid Corp" in result["organizations"]

    @patch("loom.tools.dark_recon.subprocess.run")
    @patch("loom.tools.dark_recon._is_tool_available")
    def test_amass_intel_empty_output(self, mock_available: MagicMock, mock_run: MagicMock) -> None:
        """Amass intel with empty output returns empty lists."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = research_amass_intel("example.com")

        assert result["domain"] == "example.com"
        assert result["organizations"] == []
        assert result["emails"] == []
        assert result["related_domains"] == []
