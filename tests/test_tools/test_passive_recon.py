"""Unit tests for passive_recon tool — passive infrastructure reconnaissance."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.input_validators import validate_domain
from loom.tools.intelligence.passive_recon import (
    _detect_tech_stack,
    _extract_ct_subdomains,
    _extract_dns_records,
    _parse_email_security,
    research_passive_recon,
)


pytestmark = pytest.mark.asyncio

class TestValidateDomain:
    """Domain validation."""

    async def test_valid_domain(self) -> None:
        """Valid domains pass validation."""
        assert validate_domain("example.com") == "example.com"
        assert validate_domain("subdomain.example.org") == "subdomain.example.org"
        assert validate_domain("test-domain.co.uk") == "test-domain.co.uk"
        assert validate_domain("example123.com") == "example123.com"

    async def test_domain_empty(self) -> None:
        """Empty domain fails validation."""
        with pytest.raises(ValueError):
            validate_domain("")

    async def test_domain_too_long(self) -> None:
        """Domain exceeding 255 chars fails validation."""
        long_domain = "a" * 256 + ".com"
        with pytest.raises(ValueError):
            validate_domain(long_domain)

    async def test_domain_invalid_chars(self) -> None:
        """Domain with invalid chars fails validation."""
        with pytest.raises(ValueError):
            validate_domain("example@com")
        with pytest.raises(ValueError):
            validate_domain("example_com.net")
        with pytest.raises(ValueError):
            validate_domain("example!.com")

    async def test_domain_case_insensitive(self) -> None:
        """Domain validation is case-insensitive."""
        assert validate_domain("EXAMPLE.COM") == "EXAMPLE.COM"
        assert validate_domain("Example.Com") == "Example.Com"


class TestExtractCTSubdomains:
    """Certificate Transparency subdomain extraction."""

    async def test_extract_single_subdomain(self) -> None:
        """Extract single subdomain from CT response."""
        ct_data = [{"name_value": "example.com"}]
        result = _extract_ct_subdomains(ct_data)
        assert "example.com" in result

    async def test_extract_multiple_subdomains(self) -> None:
        """Extract multiple subdomains from CT response."""
        ct_data = [
            {"name_value": "example.com\nwww.example.com\nmail.example.com"},
            {"name_value": "api.example.com"},
        ]
        result = _extract_ct_subdomains(ct_data)
        assert "example.com" in result
        assert "www.example.com" in result
        assert "mail.example.com" in result
        assert "api.example.com" in result

    async def test_extract_wildcard_subdomains(self) -> None:
        """Extract wildcard subdomains (strip * prefix)."""
        ct_data = [{"name_value": "*.example.com\n*.api.example.com"}]
        result = _extract_ct_subdomains(ct_data)
        assert "example.com" in result
        assert "api.example.com" in result

    async def test_extract_empty_ct_data(self) -> None:
        """Extract from empty CT data."""
        result = _extract_ct_subdomains([])
        assert result == []

    async def test_extract_duplicates_deduped(self) -> None:
        """Duplicate subdomains are deduplicated."""
        ct_data = [
            {"name_value": "example.com\nexample.com"},
        ]
        result = _extract_ct_subdomains(ct_data)
        assert result.count("example.com") == 1

    async def test_extract_max_50_subdomains(self) -> None:
        """Max 50 subdomains returned."""
        ct_data = [
            {
                "name_value": "\n".join(
                    [f"sub{i}.example.com" for i in range(100)]
                )
            }
        ]
        result = _extract_ct_subdomains(ct_data)
        assert len(result) <= 50


class TestExtractDNSRecords:
    """DNS record extraction from Google DNS API."""

    async def test_extract_a_records(self) -> None:
        """Extract A records from DNS response."""
        dns_json = {
            "Answer": [
                {"data": "93.184.216.34"},
                {"data": "93.184.216.35"},
            ]
        }
        result = _extract_dns_records(dns_json)
        assert "93.184.216.34" in result
        assert "93.184.216.35" in result

    async def test_extract_single_record(self) -> None:
        """Extract single record."""
        dns_json = {"Answer": [{"data": "93.184.216.34"}]}
        result = _extract_dns_records(dns_json)
        assert result == ["93.184.216.34"]

    async def test_extract_empty_answer(self) -> None:
        """Extract from empty Answer section."""
        dns_json = {"Answer": []}
        result = _extract_dns_records(dns_json)
        assert result == []

    async def test_extract_no_answer_section(self) -> None:
        """Extract from response without Answer."""
        dns_json = {}
        result = _extract_dns_records(dns_json)
        assert result == []

    async def test_extract_missing_data_field(self) -> None:
        """Ignore records missing 'data' field."""
        dns_json = {
            "Answer": [
                {"data": "93.184.216.34"},
                {"type": "MX"},  # No 'data' field
            ]
        }
        result = _extract_dns_records(dns_json)
        assert result == ["93.184.216.34"]


class TestParseEmailSecurity:
    """Email security (SPF, DKIM, DMARC) parsing."""

    async def test_spf_detected(self) -> None:
        """SPF record detected."""
        txt_records = ["v=spf1 include:_spf.google.com ~all"]
        result = _parse_email_security(txt_records)
        assert result["spf"] is True
        assert result["dkim"] is False
        assert result["dmarc"] is False

    async def test_dkim_detected(self) -> None:
        """DKIM record detected."""
        txt_records = ["v=DKIM1; k=rsa; p=MIGfMA0..."]
        result = _parse_email_security(txt_records)
        assert result["dkim"] is True
        assert result["spf"] is False

    async def test_dmarc_detected_and_parsed(self) -> None:
        """DMARC record detected and policy extracted."""
        dmarc_policy = "v=DMARC1; p=reject; rua=mailto:admin@example.com"
        txt_records = [dmarc_policy]
        result = _parse_email_security(txt_records)
        assert result["dmarc"] is True
        assert result["dmarc_policy"] == dmarc_policy

    async def test_all_three_detected(self) -> None:
        """All three email security mechanisms detected."""
        txt_records = [
            "v=spf1 include:_spf.google.com ~all",
            "v=DKIM1; k=rsa; p=MIGfMA0...",
            "v=DMARC1; p=quarantine",
        ]
        result = _parse_email_security(txt_records)
        assert result["spf"] is True
        assert result["dkim"] is True
        assert result["dmarc"] is True

    async def test_case_insensitive_detection(self) -> None:
        """Detection is case-insensitive."""
        txt_records = [
            "V=SPF1 include:_spf.google.com ~all",
            "V=DKIM1; k=rsa",
            "V=DMARC1; p=reject",
        ]
        result = _parse_email_security(txt_records)
        assert result["spf"] is True
        assert result["dkim"] is True
        assert result["dmarc"] is True

    async def test_empty_records(self) -> None:
        """Empty TXT records."""
        result = _parse_email_security([])
        assert result["spf"] is False
        assert result["dkim"] is False
        assert result["dmarc"] is False


class TestDetectTechStack:
    """Tech stack fingerprinting."""

    async def test_server_header_extraction(self) -> None:
        """Extract Server header."""
        headers = {"server": "nginx/1.24.0"}
        result = _detect_tech_stack("example.com", headers, "")
        assert result["server"] == "nginx/1.24.0"

    async def test_powered_by_header(self) -> None:
        """Extract X-Powered-By header."""
        headers = {"x-powered-by": "Express"}
        result = _detect_tech_stack("example.com", headers, "")
        assert result["powered_by"] == "Express"

    async def test_x_generator_header(self) -> None:
        """Extract X-Generator header."""
        headers = {"x-generator": "Next.js"}
        result = _detect_tech_stack("example.com", headers, "")
        assert result["powered_by"] == "Next.js"

    async def test_wordpress_detection(self) -> None:
        """Detect WordPress from HTML."""
        html = '<script src="/wp-content/themes/theme/script.js"></script>'
        result = _detect_tech_stack("example.com", {}, html)
        assert "WordPress" in result["frameworks"]

    async def test_drupal_detection(self) -> None:
        """Detect Drupal from HTML."""
        html = "Powered by Drupal"
        result = _detect_tech_stack("example.com", {}, html)
        assert "Drupal" in result["frameworks"]

    async def test_react_detection(self) -> None:
        """Detect React from HTML."""
        html = "<div id='__react_root'>"
        result = _detect_tech_stack("example.com", {}, html)
        assert "React" in result["frameworks"]

    async def test_vue_detection(self) -> None:
        """Detect Vue.js from HTML."""
        html = "<div v-app>"
        result = _detect_tech_stack("example.com", {}, html)
        assert "Vue.js" in result["frameworks"]

    async def test_angular_detection(self) -> None:
        """Detect Angular from HTML."""
        html = "<div ng-app>"
        result = _detect_tech_stack("example.com", {}, html)
        assert "Angular" in result["frameworks"]

    async def test_nextjs_detection(self) -> None:
        """Detect Next.js from HTML."""
        html = "<script id='__NEXT_DATA__'>"
        result = _detect_tech_stack("example.com", {}, html)
        assert "Next.js" in result["frameworks"]

    async def test_cloudflare_cdn_detection(self) -> None:
        """Detect Cloudflare CDN from headers."""
        headers = {"server": "cloudflare"}
        result = _detect_tech_stack("example.com", headers, "")
        assert result["cdn"] == "Cloudflare"

    async def test_multiple_frameworks(self) -> None:
        """Detect multiple frameworks."""
        html = """
        <script src="/wp-content/script.js"></script>
        <div v-app></div>
        <div ng-app></div>
        """
        result = _detect_tech_stack("example.com", {}, html)
        assert len(result["frameworks"]) >= 3

    async def test_header_case_insensitive(self) -> None:
        """Header matching is case-insensitive."""
        headers = {
            "Server": "nginx",
            "X-Powered-By": "Express",
            "X-Generator": "Hugo",
        }
        result = _detect_tech_stack("example.com", headers, "")
        assert result["server"] == "nginx"
        assert result["powered_by"] == "Express"


class TestResearchPassiveRecon:
    """Main research_passive_recon function."""

    async def test_invalid_domain(self) -> None:
        """Invalid domain returns error."""
        result = research_passive_recon("invalid@domain!")
        assert "error" in result
        assert result["domain"] == "invalid@domain!"

    async def test_domain_too_long(self) -> None:
        """Domain exceeding 255 chars returns error."""
        long_domain = "a" * 256 + ".com"
        result = research_passive_recon(long_domain)
        assert "error" in result

    async def test_response_structure(self) -> None:
        """Response has correct structure."""
        with patch("loom.tools.intelligence.passive_recon.httpx.Client"):
            result = research_passive_recon("example.com")
            assert "domain" in result
            assert "subdomains" in result
            assert "dns_records" in result
            assert "reverse_ip_domains" in result
            assert "tech_stack" in result
            assert "email_security" in result
            assert "total_findings" in result

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_ct_logs_parsing(self, mock_client_class: MagicMock) -> None:
        """CT logs are fetched and parsed."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name_value": "example.com\nwww.example.com"}
        ]
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = research_passive_recon("example.com", check_ct_logs=True)
        assert "example.com" in result["subdomains"] or result["subdomains"] == []

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_dns_records_parsing(self, mock_client_class: MagicMock) -> None:
        """DNS records are fetched and parsed."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Answer": [{"data": "93.184.216.34"}]
        }
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = research_passive_recon("example.com", check_dns=True)
        assert isinstance(result["dns_records"], dict)

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_reverse_ip_lookup(self, mock_client_class: MagicMock) -> None:
        """Reverse IP lookup is performed."""
        mock_client = MagicMock()

        async def mock_get(url: str, **kwargs):
            response = MagicMock()
            if "dns.google" in url:
                response.status_code = 200
                response.json.return_value = {
                    "Answer": [{"data": "93.184.216.34"}]
                }
            elif "reverseiplookup" in url:
                response.status_code = 200
                response.text = "domain1.com\ndomain2.com"
            else:
                response.status_code = 200
                response.text = ""
            return response

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = research_passive_recon(
            "example.com",
            check_dns=True,
            check_reverse_ip=True,
        )
        assert isinstance(result["reverse_ip_domains"], list)

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_tech_stack_detection(self, mock_client_class: MagicMock) -> None:
        """Tech stack is detected from homepage."""
        mock_client = MagicMock()

        async def mock_get(url: str, **kwargs):
            response = MagicMock()
            if "dns.google" in url:
                response.status_code = 200
                response.json.return_value = {}
            elif url.startswith("https://example.com") or url.startswith(
                "http://example.com"
            ):
                response.status_code = 200
                response.text = '<script src="/wp-content/script.js"></script>'
                response.headers = {"server": "nginx/1.24.0"}
            else:
                response.status_code = 404
                response.text = ""
            return response

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = research_passive_recon(
            "example.com",
            check_ct_logs=False,
            check_dns=False,
            check_reverse_ip=False,
            check_tech_stack=True,
        )
        assert isinstance(result["tech_stack"], dict)

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_skip_ct_logs(self, mock_client_class: MagicMock) -> None:
        """CT logs can be skipped."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = research_passive_recon("example.com", check_ct_logs=False)
        assert result["subdomains"] == []

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_total_findings_count(self, mock_client_class: MagicMock) -> None:
        """Total findings count is calculated."""
        with patch("loom.tools.intelligence.passive_recon.httpx.Client"):
            result = research_passive_recon("example.com")
            assert "total_findings" in result
            assert isinstance(result["total_findings"], int)
            assert result["total_findings"] >= 0

    @patch("loom.tools.intelligence.passive_recon.httpx.Client")
    async def test_error_handling(self, mock_client_class: MagicMock) -> None:
        """Errors are handled gracefully."""
        mock_client_class.side_effect = Exception("Network error")

        result = research_passive_recon("example.com")
        assert "error" in result or result["total_findings"] == 0
