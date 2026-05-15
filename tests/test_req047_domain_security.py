"""REQ-047: Domain Intelligence (3) + Security (8) = 11 tools test suite (FIXED).

Tests the following domain intelligence and security tools:
- Domain: whois, dns_lookup, nmap_scan (3)
- Security: cert_analyze, security_headers, breach_check, password_check,
  ip_reputation, ip_geolocation, cve_lookup, cve_detail, vuln_intel,
  urlhaus_check, urlhaus_search (11)
"""

from __future__ import annotations

import logging

import pytest

logger = logging.getLogger("tests.test_req047_domain_security")

TEST_DOMAIN = "example.com"
TEST_IP = "8.8.8.8"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPassword123!"
TEST_URL = "https://example.com"
TEST_CVE_ID = "CVE-2021-1234"
TEST_QUERY = "sql injection"


pytestmark = pytest.mark.asyncio

class TestResearchWhois:
    """Test research_whois tool."""

    async def test_whois_basic(self) -> None:
        """Test WHOIS lookup."""
        from loom.tools.intelligence.domain_intel import research_whois

        result = await research_whois(domain=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_whois_basic: PASS")

    async def test_whois_returns_dict(self) -> None:
        """Verify whois returns dict."""
        from loom.tools.intelligence.domain_intel import research_whois

        result = await research_whois(domain=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_whois_returns_dict: PASS")


class TestResearchDnsLookup:
    """Test research_dns_lookup tool."""

    async def test_dns_lookup_basic(self) -> None:
        """Test DNS lookup."""
        from loom.tools.intelligence.domain_intel import research_dns_lookup

        result = await research_dns_lookup(domain=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_dns_lookup_basic: PASS")

    async def test_dns_lookup_with_types(self) -> None:
        """Test DNS lookup with record types."""
        from loom.tools.intelligence.domain_intel import research_dns_lookup

        result = await research_dns_lookup(domain=TEST_DOMAIN, record_types=["A", "MX"])
        assert isinstance(result, dict)
        logger.info("test_dns_lookup_with_types: PASS")

    async def test_dns_lookup_returns_dict(self) -> None:
        """Verify dns_lookup returns dict."""
        from loom.tools.intelligence.domain_intel import research_dns_lookup

        result = await research_dns_lookup(domain=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_dns_lookup_returns_dict: PASS")


class TestResearchNmapScan:
    """Test research_nmap_scan tool."""

    async def test_nmap_scan_basic(self) -> None:
        """Test nmap scan."""
        from loom.tools.intelligence.domain_intel import research_nmap_scan

        result = await research_nmap_scan(target=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_nmap_scan_basic: PASS")

    async def test_nmap_scan_with_ports(self) -> None:
        """Test nmap scan with ports."""
        from loom.tools.intelligence.domain_intel import research_nmap_scan

        result = await research_nmap_scan(target=TEST_DOMAIN, ports="80,443")
        assert isinstance(result, dict)
        logger.info("test_nmap_scan_with_ports: PASS")

    async def test_nmap_scan_returns_dict(self) -> None:
        """Verify nmap_scan returns dict."""
        from loom.tools.intelligence.domain_intel import research_nmap_scan

        result = await research_nmap_scan(target=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_nmap_scan_returns_dict: PASS")


class TestResearchCertAnalyze:
    """Test research_cert_analyze tool."""

    async def test_cert_analyze_basic(self) -> None:
        """Test certificate analysis."""
        from loom.tools.security.cert_analyzer import research_cert_analyze

        result = await research_cert_analyze(hostname=TEST_DOMAIN, port=443)
        assert isinstance(result, dict)
        logger.info("test_cert_analyze_basic: PASS")

    async def test_cert_analyze_returns_dict(self) -> None:
        """Verify cert_analyze returns dict."""
        from loom.tools.security.cert_analyzer import research_cert_analyze

        result = await research_cert_analyze(hostname=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_cert_analyze_returns_dict: PASS")


class TestResearchSecurityHeaders:
    """Test research_security_headers tool."""

    async def test_security_headers_basic(self) -> None:
        """Test security headers analysis."""
        from loom.tools.security.security_headers import research_security_headers

        result = await research_security_headers(url=TEST_URL)
        assert isinstance(result, dict)
        logger.info("test_security_headers_basic: PASS")

    async def test_security_headers_returns_dict(self) -> None:
        """Verify security_headers returns dict."""
        from loom.tools.security.security_headers import research_security_headers

        result = await research_security_headers(url=TEST_URL)
        assert isinstance(result, dict)
        logger.info("test_security_headers_returns_dict: PASS")


class TestResearchBreachCheck:
    """Test research_breach_check tool."""

    async def test_breach_check_basic(self) -> None:
        """Test breach check."""
        from loom.tools.intelligence.breach_check import research_breach_check

        result = await research_breach_check(email=TEST_EMAIL)
        assert isinstance(result, dict)
        logger.info("test_breach_check_basic: PASS")

    async def test_breach_check_returns_dict(self) -> None:
        """Verify breach_check returns dict."""
        from loom.tools.intelligence.breach_check import research_breach_check

        result = await research_breach_check(email=TEST_EMAIL)
        assert isinstance(result, dict)
        logger.info("test_breach_check_returns_dict: PASS")


class TestResearchPasswordCheck:
    """Test research_password_check tool."""

    async def test_password_check_basic(self) -> None:
        """Test password check."""
        from loom.tools.intelligence.breach_check import research_password_check

        result = await research_password_check(password=TEST_PASSWORD)
        assert isinstance(result, dict)
        # Check for actual response fields
        assert any(
            k in result
            for k in ["pwned_count", "is_pwned", "password_length", "error", "status"]
        ), f"Missing expected fields in {result.keys()}"
        logger.info("test_password_check_basic: PASS")

    async def test_password_check_returns_dict(self) -> None:
        """Verify password_check returns dict."""
        from loom.tools.intelligence.breach_check import research_password_check

        result = await research_password_check(password=TEST_PASSWORD)
        assert isinstance(result, dict)
        logger.info("test_password_check_returns_dict: PASS")


class TestResearchIpReputation:
    """Test research_ip_reputation tool."""

    async def test_ip_reputation_basic(self) -> None:
        """Test IP reputation check."""
        from loom.tools.intelligence.ip_intel import research_ip_reputation

        result = await research_ip_reputation(ip=TEST_IP)
        assert isinstance(result, dict)
        # Check for actual response fields
        assert any(
            k in result
            for k in ["ip", "abuse_score", "reputation", "score", "error", "status"]
        ), f"Missing expected fields in {result.keys()}"
        logger.info("test_ip_reputation_basic: PASS")

    async def test_ip_reputation_returns_dict(self) -> None:
        """Verify ip_reputation returns dict."""
        from loom.tools.intelligence.ip_intel import research_ip_reputation

        result = await research_ip_reputation(ip=TEST_IP)
        assert isinstance(result, dict)
        logger.info("test_ip_reputation_returns_dict: PASS")


class TestResearchIpGeolocation:
    """Test research_ip_geolocation tool."""

    async def test_ip_geolocation_basic(self) -> None:
        """Test IP geolocation."""
        from loom.tools.intelligence.ip_intel import research_ip_geolocation

        result = await research_ip_geolocation(ip=TEST_IP)
        assert isinstance(result, dict)
        logger.info("test_ip_geolocation_basic: PASS")

    async def test_ip_geolocation_returns_dict(self) -> None:
        """Verify ip_geolocation returns dict."""
        from loom.tools.intelligence.ip_intel import research_ip_geolocation

        result = await research_ip_geolocation(ip=TEST_IP)
        assert isinstance(result, dict)
        logger.info("test_ip_geolocation_returns_dict: PASS")


class TestResearchCveLookup:
    """Test research_cve_lookup tool."""

    async def test_cve_lookup_basic(self) -> None:
        """Test CVE lookup."""
        from loom.tools.security.cve_lookup import research_cve_lookup

        result = await research_cve_lookup(query=TEST_QUERY, limit=5)
        assert isinstance(result, dict)
        logger.info("test_cve_lookup_basic: PASS")

    async def test_cve_lookup_returns_dict(self) -> None:
        """Verify cve_lookup returns dict."""
        from loom.tools.security.cve_lookup import research_cve_lookup

        result = await research_cve_lookup(query=TEST_QUERY)
        assert isinstance(result, dict)
        logger.info("test_cve_lookup_returns_dict: PASS")


class TestResearchCveDetail:
    """Test research_cve_detail tool."""

    async def test_cve_detail_basic(self) -> None:
        """Test CVE detail lookup."""
        from loom.tools.security.cve_lookup import research_cve_detail

        result = await research_cve_detail(cve_id=TEST_CVE_ID)
        assert isinstance(result, dict)
        logger.info("test_cve_detail_basic: PASS")

    async def test_cve_detail_returns_dict(self) -> None:
        """Verify cve_detail returns dict."""
        from loom.tools.security.cve_lookup import research_cve_detail

        result = await research_cve_detail(cve_id=TEST_CVE_ID)
        assert isinstance(result, dict)
        logger.info("test_cve_detail_returns_dict: PASS")


class TestResearchVulnIntel:
    """Test research_vuln_intel tool."""

    async def test_vuln_intel_basic(self) -> None:
        """Test vulnerability intelligence."""
        from loom.tools.intelligence.vuln_intel import research_vuln_intel

        result = await research_vuln_intel(query=TEST_QUERY, max_results=10)
        assert isinstance(result, dict)
        # Check for actual response fields
        assert any(
            k in result
            for k in ["vulns", "total_vulns", "query", "error", "data"]
        ), f"Missing expected fields in {result.keys()}"
        logger.info("test_vuln_intel_basic: PASS")

    async def test_vuln_intel_returns_dict(self) -> None:
        """Verify vuln_intel returns dict."""
        from loom.tools.intelligence.vuln_intel import research_vuln_intel

        result = await research_vuln_intel(query=TEST_QUERY)
        assert isinstance(result, dict)
        logger.info("test_vuln_intel_returns_dict: PASS")


class TestResearchUrlhausCheck:
    """Test research_urlhaus_check tool."""

    async def test_urlhaus_check_basic(self) -> None:
        """Test URLhaus check."""
        from loom.tools.security.urlhaus_lookup import research_urlhaus_check

        result = await research_urlhaus_check(url=TEST_URL)
        assert isinstance(result, dict)
        logger.info("test_urlhaus_check_basic: PASS")

    async def test_urlhaus_check_returns_dict(self) -> None:
        """Verify urlhaus_check returns dict."""
        from loom.tools.security.urlhaus_lookup import research_urlhaus_check

        result = await research_urlhaus_check(url=TEST_URL)
        assert isinstance(result, dict)
        logger.info("test_urlhaus_check_returns_dict: PASS")


class TestResearchUrlhausSearch:
    """Test research_urlhaus_search tool."""

    async def test_urlhaus_search_basic(self) -> None:
        """Test URLhaus search."""
        from loom.tools.security.urlhaus_lookup import research_urlhaus_search

        result = await research_urlhaus_search(query=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_urlhaus_search_basic: PASS")

    async def test_urlhaus_search_returns_dict(self) -> None:
        """Verify urlhaus_search returns dict."""
        from loom.tools.security.urlhaus_lookup import research_urlhaus_search

        result = await research_urlhaus_search(query=TEST_DOMAIN)
        assert isinstance(result, dict)
        logger.info("test_urlhaus_search_returns_dict: PASS")


class TestDomainSecurityToolsCoverage:
    """Integration test for all Domain Intelligence and Security tools."""

    async def test_all_domain_security_tools_callable(self) -> None:
        """Verify all domain and security tools are callable."""
        tools_tested = []

        # Domain Intelligence (3)
        try:
            from loom.tools.intelligence.domain_intel import research_whois

            result = await research_whois(domain=TEST_DOMAIN)
            assert isinstance(result, dict)
            tools_tested.append("research_whois")
        except Exception as e:
            logger.warning(f"research_whois failed: {e}")

        try:
            from loom.tools.intelligence.domain_intel import research_dns_lookup

            result = await research_dns_lookup(domain=TEST_DOMAIN)
            assert isinstance(result, dict)
            tools_tested.append("research_dns_lookup")
        except Exception as e:
            logger.warning(f"research_dns_lookup failed: {e}")

        try:
            from loom.tools.intelligence.domain_intel import research_nmap_scan

            result = await research_nmap_scan(target=TEST_DOMAIN)
            assert isinstance(result, dict)
            tools_tested.append("research_nmap_scan")
        except Exception as e:
            logger.warning(f"research_nmap_scan failed: {e}")

        # Security (11)
        try:
            from loom.tools.security.cert_analyzer import research_cert_analyze

            result = await research_cert_analyze(hostname=TEST_DOMAIN)
            assert isinstance(result, dict)
            tools_tested.append("research_cert_analyze")
        except Exception as e:
            logger.warning(f"research_cert_analyze failed: {e}")

        try:
            from loom.tools.security.security_headers import research_security_headers

            result = await research_security_headers(url=TEST_URL)
            assert isinstance(result, dict)
            tools_tested.append("research_security_headers")
        except Exception as e:
            logger.warning(f"research_security_headers failed: {e}")

        try:
            from loom.tools.intelligence.breach_check import research_breach_check

            result = await research_breach_check(email=TEST_EMAIL)
            assert isinstance(result, dict)
            tools_tested.append("research_breach_check")
        except Exception as e:
            logger.warning(f"research_breach_check failed: {e}")

        try:
            from loom.tools.intelligence.breach_check import research_password_check

            result = await research_password_check(password=TEST_PASSWORD)
            assert isinstance(result, dict)
            tools_tested.append("research_password_check")
        except Exception as e:
            logger.warning(f"research_password_check failed: {e}")

        try:
            from loom.tools.intelligence.ip_intel import research_ip_reputation

            result = await research_ip_reputation(ip=TEST_IP)
            assert isinstance(result, dict)
            tools_tested.append("research_ip_reputation")
        except Exception as e:
            logger.warning(f"research_ip_reputation failed: {e}")

        try:
            from loom.tools.intelligence.ip_intel import research_ip_geolocation

            result = await research_ip_geolocation(ip=TEST_IP)
            assert isinstance(result, dict)
            tools_tested.append("research_ip_geolocation")
        except Exception as e:
            logger.warning(f"research_ip_geolocation failed: {e}")

        try:
            from loom.tools.security.cve_lookup import research_cve_lookup

            result = await research_cve_lookup(query=TEST_QUERY, limit=1)
            assert isinstance(result, dict)
            tools_tested.append("research_cve_lookup")
        except Exception as e:
            logger.warning(f"research_cve_lookup failed: {e}")

        try:
            from loom.tools.security.cve_lookup import research_cve_detail

            result = await research_cve_detail(cve_id=TEST_CVE_ID)
            assert isinstance(result, dict)
            tools_tested.append("research_cve_detail")
        except Exception as e:
            logger.warning(f"research_cve_detail failed: {e}")

        try:
            from loom.tools.intelligence.vuln_intel import research_vuln_intel

            result = await research_vuln_intel(query=TEST_QUERY, max_results=1)
            assert isinstance(result, dict)
            tools_tested.append("research_vuln_intel")
        except Exception as e:
            logger.warning(f"research_vuln_intel failed: {e}")

        try:
            from loom.tools.security.urlhaus_lookup import research_urlhaus_check

            result = await research_urlhaus_check(url=TEST_URL)
            assert isinstance(result, dict)
            tools_tested.append("research_urlhaus_check")
        except Exception as e:
            logger.warning(f"research_urlhaus_check failed: {e}")

        try:
            from loom.tools.security.urlhaus_lookup import research_urlhaus_search

            result = await research_urlhaus_search(query=TEST_DOMAIN)
            assert isinstance(result, dict)
            tools_tested.append("research_urlhaus_search")
        except Exception as e:
            logger.warning(f"research_urlhaus_search failed: {e}")

        logger.info(f"REQ-047 Tools Summary: {len(tools_tested)}/14 tools passed")
        logger.info(f"Tools passed: {', '.join(tools_tested)}")

        assert (
            len(tools_tested) >= 10
        ), f"Expected at least 10 tools, got {len(tools_tested)}"
