"""Live integration tests for Domain Intel + Security tools (REQ-047)."""
import pytest

pytestmark = [pytest.mark.live, pytest.mark.timeout(60)]


class TestDomainIntelTools:
    @pytest.mark.asyncio
    async def test_whois(self):
        from loom.tools.intelligence.domain_intel import research_whois
        result = await research_whois(domain="example.com")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dns_lookup(self):
        from loom.tools.intelligence.domain_intel import research_dns_lookup
        result = await research_dns_lookup(domain="example.com")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_nmap_scan(self):
        try:
            from loom.tools.intelligence.domain_intel import research_nmap_scan
            result = await research_nmap_scan(target="example.com", ports="80,443")
            assert isinstance(result, dict)
        except (ImportError, FileNotFoundError):
            pytest.skip("nmap not installed")


class TestSecurityTools:
    @pytest.mark.asyncio
    async def test_cert_analyze(self):
        from loom.tools.security.cert_analyzer import research_cert_analyze
        result = await research_cert_analyze(domain="example.com")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_security_headers(self):
        from loom.tools.security.security_headers import research_security_headers
        result = await research_security_headers(url="https://example.com")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_ip_reputation(self):
        from loom.tools.intelligence.ip_intel import research_ip_reputation
        result = await research_ip_reputation(ip="8.8.8.8")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cve_lookup(self):
        from loom.tools.security.cve_lookup import research_cve_lookup
        result = await research_cve_lookup(query="log4j")
        assert isinstance(result, dict)
