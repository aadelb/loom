"""Unit tests for ProjectDiscovery tools — nuclei, katana, subfinder, httpx."""

from __future__ import annotations

import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from loom.input_validators import validate_domain
from loom.tools.infrastructure.projectdiscovery import (
    _check_binary_exists,
    research_httpx_probe,
    research_katana_crawl,
    research_nuclei_scan,
    research_subfinder,
)


class TestValidateDomain:
    """Domain validation for subfinder."""

    def test_valid_domain(self) -> None:
        """Valid domains pass validation."""
        assert validate_domain("example.com") == "example.com"
        assert validate_domain("sub.example.org") == "sub.example.org"
        assert validate_domain("test-domain.co.uk") == "test-domain.co.uk"
        assert validate_domain("my_domain.net") == "my_domain.net"

    def test_domain_too_long(self) -> None:
        """Domain exceeding 255 chars raises error."""
        long_domain = "a" * 256 + ".com"
        with pytest.raises(ValueError, match="1-255 characters"):
            validate_domain(long_domain)

    def test_domain_empty(self) -> None:
        """Empty domain raises error."""
        with pytest.raises(ValueError):
            validate_domain("")

    def test_domain_disallowed_chars(self) -> None:
        """Domain with spaces or special chars raises error."""
        with pytest.raises(ValueError, match="disallowed characters"):
            validate_domain("example .com")
        with pytest.raises(ValueError, match="disallowed characters"):
            validate_domain("example@com")
        with pytest.raises(ValueError, match="disallowed characters"):
            validate_domain("example/com")


class TestCheckBinaryExists:
    """Binary existence checking."""

    @patch("loom.tools.infrastructure.projectdiscovery.shutil.which")
    def test_binary_exists(self, mock_which: MagicMock) -> None:
        """Binary in PATH returns True and path."""
        mock_which.return_value = "/usr/local/bin/subfinder"
        exists, path = _check_binary_exists("subfinder")
        assert exists is True
        assert path == "/usr/local/bin/subfinder"

    @patch("loom.tools.infrastructure.projectdiscovery.shutil.which")
    def test_binary_not_exists(self, mock_which: MagicMock) -> None:
        """Binary not in PATH returns False and None."""
        mock_which.return_value = None
        exists, path = _check_binary_exists("subfinder")
        assert exists is False
        assert path is None


class TestSubfinder:
    """research_subfinder command execution and output parsing."""

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_subfinder_success(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Successful subfinder execution returns subdomains."""
        mock_check.return_value = (True, "/usr/local/bin/subfinder")
        # NDJSON format - one JSON object per line
        subfinder_output = (
            '{"domain": "example.com", "subdomain": "mail.example.com", "source": "certspotter"}\n'
            '{"domain": "example.com", "subdomain": "www.example.com", "source": "crtsh"}\n'
            '{"domain": "example.com", "subdomain": "api.example.com", "source": "dns"}\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=subfinder_output, stderr="")

        result = research_subfinder("example.com")

        assert result["domain"] == "example.com"
        assert len(result["subdomains"]) == 3
        assert "mail.example.com" in result["subdomains"]
        assert "www.example.com" in result["subdomains"]
        assert "api.example.com" in result["subdomains"]
        assert result["count"] == 3
        assert "certspotter" in result["sources_used"]
        assert "crtsh" in result["sources_used"]

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_subfinder_binary_not_found(self, mock_check: MagicMock) -> None:
        """Missing binary returns error."""
        mock_check.return_value = (False, None)
        result = research_subfinder("example.com")
        assert "error" in result
        assert "not installed" in result["error"]
        assert result["count"] == 0
        assert result["subdomains"] == []

    def test_subfinder_invalid_domain(self) -> None:
        """Invalid domain returns error."""
        result = research_subfinder("example@invalid")
        assert "error" in result
        assert result["count"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_subfinder_timeout(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Subfinder timeout returns error."""
        mock_check.return_value = (True, "/usr/local/bin/subfinder")
        mock_run.side_effect = TimeoutError()
        result = research_subfinder("example.com", timeout=5)
        assert "error" in result
        assert result["count"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_subfinder_deduplication(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Duplicate subdomains are deduplicated."""
        mock_check.return_value = (True, "/usr/local/bin/subfinder")
        subfinder_output = (
            '{"domain": "example.com", "subdomain": "www.example.com", "source": "certspotter"}\n'
            '{"domain": "example.com", "subdomain": "www.example.com", "source": "crtsh"}\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=subfinder_output, stderr="")

        result = research_subfinder("example.com")

        assert result["count"] == 1
        assert len(result["subdomains"]) == 1

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_subfinder_empty_output(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """No subdomains found returns empty list."""
        mock_check.return_value = (True, "/usr/local/bin/subfinder")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = research_subfinder("example.com")

        assert result["domain"] == "example.com"
        assert result["count"] == 0
        assert result["subdomains"] == []


class TestKatanaCrawl:
    """research_katana_crawl command execution and output parsing."""

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_katana_success(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Successful katana execution returns crawled URLs."""
        mock_check.return_value = (True, "/usr/local/bin/katana")
        # NDJSON format
        katana_output = (
            '{"url": "https://example.com", "depth": 0, "status": 200}\n'
            '{"url": "https://example.com/about", "depth": 1, "status": 200}\n'
            '{"url": "https://example.com/contact", "depth": 1, "status": 200}\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=katana_output, stderr="")

        result = research_katana_crawl("https://example.com")

        assert result["url"] == "https://example.com"
        assert result["pages_crawled"] == 3
        assert "https://example.com" in result["urls_found"]
        assert "https://example.com/about" in result["urls_found"]
        assert "https://example.com/contact" in result["urls_found"]
        assert result["depth_reached"] == 1

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_katana_binary_not_found(self, mock_check: MagicMock) -> None:
        """Missing binary returns error."""
        mock_check.return_value = (False, None)
        result = research_katana_crawl("https://example.com")
        assert "error" in result
        assert "not installed" in result["error"]
        assert result["pages_crawled"] == 0

    def test_katana_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_katana_crawl("not a url")
        assert "error" in result
        assert result["pages_crawled"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_katana_invalid_depth(self, mock_check: MagicMock) -> None:
        """Invalid depth returns error."""
        mock_check.return_value = (True, "/usr/local/bin/katana")
        result = research_katana_crawl("https://example.com", depth=10)
        assert "error" in result

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_katana_invalid_max_pages(self, mock_check: MagicMock) -> None:
        """Invalid max_pages returns error."""
        mock_check.return_value = (True, "/usr/local/bin/katana")
        result = research_katana_crawl("https://example.com", max_pages=2000)
        assert "error" in result

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_katana_timeout(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Katana timeout returns error."""
        mock_check.return_value = (True, "/usr/local/bin/katana")
        mock_run.side_effect = TimeoutError()
        result = research_katana_crawl("https://example.com", timeout=5)
        assert "error" in result
        assert result["pages_crawled"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_katana_deduplication(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Duplicate URLs are deduplicated."""
        mock_check.return_value = (True, "/usr/local/bin/katana")
        katana_output = (
            '{"url": "https://example.com/page", "depth": 0}\n'
            '{"url": "https://example.com/page", "depth": 1}\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=katana_output, stderr="")

        result = research_katana_crawl("https://example.com")

        assert result["pages_crawled"] == 1
        assert len(result["urls_found"]) == 1


class TestHttpxProbe:
    """research_httpx_probe command execution and output parsing."""

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_httpx_success(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Successful httpx execution returns live hosts."""
        mock_check.return_value = (True, "/usr/local/bin/httpx")
        # NDJSON format
        httpx_output = (
            '{"url": "https://example.com", "status-code": 200, "title": "Example Domain", "server": "Apache/2.4.41", "technology": ["Apache", "HTTP/1.1"]}\n'
            '{"url": "https://example.com:8443", "status-code": 200, "title": "Admin Panel", "server": "nginx/1.18.0", "technology": ["nginx"]}\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=httpx_output, stderr="")

        result = research_httpx_probe(["example.com", "example.com:8443"])

        assert result["targets_checked"] == 2
        assert result["count"] == 2
        assert len(result["alive"]) == 2
        assert result["alive"][0]["status_code"] == 200
        assert result["alive"][0]["title"] == "Example Domain"

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_httpx_binary_not_found(self, mock_check: MagicMock) -> None:
        """Missing binary returns error."""
        mock_check.return_value = (False, None)
        result = research_httpx_probe(["example.com"])
        assert "error" in result
        assert "not installed" in result["error"]
        assert result["count"] == 0

    def test_httpx_empty_targets(self) -> None:
        """Empty targets list returns error."""
        result = research_httpx_probe([])
        assert "error" in result
        assert result["count"] == 0

    def test_httpx_too_many_targets(self) -> None:
        """Too many targets returns error."""
        targets = [f"example{i}.com" for i in range(150)]
        result = research_httpx_probe(targets)
        assert "error" in result

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_httpx_invalid_ports(self, mock_check: MagicMock) -> None:
        """Invalid ports return error."""
        mock_check.return_value = (True, "/usr/local/bin/httpx")
        result = research_httpx_probe(["example.com"], ports="99999")
        assert "error" in result

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_httpx_timeout(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Httpx timeout returns error."""
        mock_check.return_value = (True, "/usr/local/bin/httpx")
        mock_run.side_effect = TimeoutError()
        result = research_httpx_probe(["example.com"], timeout=5)
        assert "error" in result
        assert result["count"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_httpx_mixed_targets(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Mixed URLs and domains are handled."""
        mock_check.return_value = (True, "/usr/local/bin/httpx")
        httpx_output = '{"url": "http://example.com", "status-code": 200}\n'
        mock_run.return_value = MagicMock(returncode=0, stdout=httpx_output, stderr="")

        result = research_httpx_probe(["https://example.com", "test.org"])

        assert result["targets_checked"] == 2
        assert result["count"] == 1


class TestNucleiScan:
    """research_nuclei_scan command execution and output parsing."""

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_success(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Successful nuclei execution returns vulnerabilities."""
        mock_check.return_value = (True, "/usr/local/bin/nuclei")
        # NDJSON format
        nuclei_output = (
            '{"template-id": "cves/CVE-2021-1234", "severity": "high", "matched-at": "https://example.com/vulnerable-endpoint", "matcher-name": "sql-injection", "type": "vulnerability"}\n'
            '{"template-id": "exposures/exposed-keys", "severity": "critical", "matched-at": "https://example.com/.env", "matcher-name": "env-file", "type": "misconfiguration"}\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=nuclei_output, stderr="")

        result = research_nuclei_scan("https://example.com")

        assert result["target"] == "https://example.com"
        assert result["count"] == 2
        assert len(result["vulnerabilities"]) == 2
        assert result["vulnerabilities"][0]["severity"] == "high"
        assert result["vulnerabilities"][1]["severity"] == "critical"

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_binary_not_found(self, mock_check: MagicMock) -> None:
        """Missing binary returns error."""
        mock_check.return_value = (False, None)
        result = research_nuclei_scan("https://example.com")
        assert "error" in result
        assert "not installed" in result["error"]
        assert result["count"] == 0

    def test_nuclei_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_nuclei_scan("not a url")
        assert "error" in result
        assert result["count"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_invalid_templates(self, mock_check: MagicMock) -> None:
        """Invalid templates return error."""
        mock_check.return_value = (True, "/usr/local/bin/nuclei")
        result = research_nuclei_scan("https://example.com", templates="cves;DROP")
        assert "error" in result

    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_invalid_severity(self, mock_check: MagicMock) -> None:
        """Invalid severity returns error."""
        mock_check.return_value = (True, "/usr/local/bin/nuclei")
        result = research_nuclei_scan("https://example.com", severity="medium;DROP")
        assert "error" in result

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_timeout(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Nuclei timeout returns error."""
        mock_check.return_value = (True, "/usr/local/bin/nuclei")
        mock_run.side_effect = TimeoutError()
        result = research_nuclei_scan("https://example.com", timeout=10)
        assert "error" in result
        assert result["count"] == 0

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_empty_output(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """No vulnerabilities found returns empty list."""
        mock_check.return_value = (True, "/usr/local/bin/nuclei")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = research_nuclei_scan("https://example.com")

        assert result["target"] == "https://example.com"
        assert result["count"] == 0
        assert result["vulnerabilities"] == []

    @patch("loom.tools.infrastructure.projectdiscovery.subprocess.run")
    @patch("loom.tools.infrastructure.projectdiscovery._check_binary_exists")
    def test_nuclei_custom_severity(
        self,
        mock_check: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Custom severity filters are applied."""
        mock_check.return_value = (True, "/usr/local/bin/nuclei")
        nuclei_output = '{"template-id": "test/low-severity", "severity": "low", "matched-at": "https://example.com", "matcher-name": "test"}\n'
        mock_run.return_value = MagicMock(returncode=0, stdout=nuclei_output, stderr="")

        result = research_nuclei_scan("https://example.com", severity="low")

        assert result["count"] == 1
        mock_run.assert_called_once()
        # Verify the severity was passed correctly
        call_args = mock_run.call_args[0][0]
        assert "-s" in call_args
        assert "low" in call_args
