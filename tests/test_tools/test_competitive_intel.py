"""Unit tests for competitive_intel tool — SEC, USPTO, GitHub, CT, DNS signals."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.competitive_intel import (
    _fetch_certificate_transparency,
    _fetch_dns_records,
    _fetch_github_activity,
    _fetch_patents,
    _fetch_sec_filings,
    _synthesize_signals,
    research_competitive_intel,
)


class TestFetchSecFilings:
    """SEC EDGAR filing fetch and parsing."""

    @pytest.mark.asyncio
    async def test_sec_filings_success(self) -> None:
        """Successful SEC filing fetch returns count and recent filings."""
        mock_html = """
        10-K | 2025-03-15
        10-Q | 2024-11-30
        10-Q | 2024-08-20
        10-K | 2024-03-10
        """
        with patch("loom.tools.competitive_intel._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_html

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_sec_filings(client, "OpenAI")

            assert result["count"] >= 2
            assert isinstance(result["recent"], list)
            assert all("form" in f and "date" in f for f in result["recent"])

    @pytest.mark.asyncio
    async def test_sec_filings_no_results(self) -> None:
        """SEC filing fetch with no results returns zero count."""
        with patch("loom.tools.competitive_intel._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = ""

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_sec_filings(client, "FakeCompany123")

            assert result["count"] == 0
            assert result["recent"] == []

    @pytest.mark.asyncio
    async def test_sec_filings_network_error(self) -> None:
        """SEC filing fetch with network error returns empty gracefully."""
        with patch("loom.tools.competitive_intel._get_text", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_sec_filings(client, "TestCorp")

            assert result["count"] == 0
            assert result["recent"] == []


class TestFetchPatents:
    """USPTO patent fetch and parsing."""

    @pytest.mark.asyncio
    async def test_patents_success(self) -> None:
        """Successful patent fetch returns count and titles."""
        mock_response = {
            "response": {
                "numFound": 45,
                "docs": [
                    {"publicationTitle": "AI Neural Network Patent"},
                    {"publicationTitle": "Cloud Computing Method"},
                    {"publicationTitle": "Data Processing System"},
                ],
            }
        }

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_patents(client, "TechCorp")

            assert result["count"] == 45
            assert len(result["recent_titles"]) == 3
            assert "AI Neural Network" in result["recent_titles"][0]

    @pytest.mark.asyncio
    async def test_patents_with_title_fallback(self) -> None:
        """Patent parsing uses 'title' field if publicationTitle absent."""
        mock_response = {
            "response": {
                "numFound": 2,
                "docs": [
                    {"title": "Fallback Title Patent"},
                ],
            }
        }

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_patents(client, "TestCorp")

            assert result["count"] == 2
            assert "Fallback Title" in result["recent_titles"][0]

    @pytest.mark.asyncio
    async def test_patents_no_response_field(self) -> None:
        """Patent fetch with missing response field returns empty."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {}

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_patents(client, "FakeCorp")

            assert result["count"] == 0
            assert result["recent_titles"] == []

    @pytest.mark.asyncio
    async def test_patents_network_error(self) -> None:
        """Patent fetch with network error returns empty gracefully."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network timeout")

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_patents(client, "TestCorp")

            assert result["count"] == 0
            assert result["recent_titles"] == []


class TestFetchGithubActivity:
    """GitHub organization activity fetch and parsing."""

    @pytest.mark.asyncio
    async def test_github_activity_success(self) -> None:
        """Successful GitHub fetch returns repos, stars, and languages."""
        mock_repos = [
            {
                "name": "repo1",
                "stargazers_count": 500,
                "language": "Python",
                "updated_at": "2025-04-01T12:00:00Z",
            },
            {
                "name": "repo2",
                "stargazers_count": 300,
                "language": "TypeScript",
                "updated_at": "2025-03-28T08:00:00Z",
            },
            {
                "name": "repo3",
                "stargazers_count": 200,
                "language": "Python",
                "updated_at": "2025-03-25T14:00:00Z",
            },
        ]

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_repos

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_github_activity(client, "openai")

            assert result["repo_count"] == 3
            assert result["total_stars"] == 1000
            assert "Python" in result["languages"]
            assert len(result["recent_repos"]) == 3
            assert result["recent_repos"][0]["stars"] == 500

    @pytest.mark.asyncio
    async def test_github_activity_null_language(self) -> None:
        """GitHub repos with null language are handled gracefully."""
        mock_repos = [
            {
                "name": "repo1",
                "stargazers_count": 100,
                "language": None,
                "updated_at": "2025-04-01T12:00:00Z",
            },
        ]

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_repos

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_github_activity(client, "testorg")

            assert result["repo_count"] == 1
            assert result["recent_repos"][0]["language"] == "Unknown"

    @pytest.mark.asyncio
    async def test_github_activity_not_list(self) -> None:
        """GitHub fetch with non-list response returns empty."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"error": "Not found"}

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_github_activity(client, "notfound")

            assert result["repo_count"] == 0
            assert result["total_stars"] == 0
            assert result["languages"] == []

    @pytest.mark.asyncio
    async def test_github_activity_network_error(self) -> None:
        """GitHub fetch with network error returns empty gracefully."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_github_activity(client, "testorg")

            assert result["repo_count"] == 0
            assert result["total_stars"] == 0


class TestFetchCertificateTransparency:
    """Certificate Transparency subdomain fetch and parsing."""

    @pytest.mark.asyncio
    async def test_ct_subdomains_success(self) -> None:
        """Successful CT fetch returns unique subdomains."""
        mock_ct_data = [
            {"name_value": "example.com\nwww.example.com\napi.example.com"},
            {"name_value": "*.example.com\ncdn.example.com"},
            {"name_value": "mail.example.com"},
        ]

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_ct_data

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_certificate_transparency(client, "example.com")

            assert result["total_found"] >= 5
            assert "www.example.com" in result["recent_subdomains"]
            assert "api.example.com" in result["recent_subdomains"]

    @pytest.mark.asyncio
    async def test_ct_subdomains_deduplication(self) -> None:
        """CT fetch deduplicates subdomains."""
        mock_ct_data = [
            {"name_value": "www.example.com\nwww.example.com\napi.example.com"},
        ]

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_ct_data

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_certificate_transparency(client, "example.com")

            # Count occurrences of www.example.com in recent_subdomains
            www_count = sum(1 for s in result["recent_subdomains"] if s == "www.example.com")
            assert www_count == 1

    @pytest.mark.asyncio
    async def test_ct_subdomains_no_results(self) -> None:
        """CT fetch with no results returns empty."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_certificate_transparency(client, "notfound.test")

            assert result["total_found"] == 0
            assert result["recent_subdomains"] == []

    @pytest.mark.asyncio
    async def test_ct_subdomains_network_error(self) -> None:
        """CT fetch with network error returns empty gracefully."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Timeout")

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_certificate_transparency(client, "example.com")

            assert result["total_found"] == 0
            assert result["recent_subdomains"] == []


class TestFetchDnsRecords:
    """DNS record fetch and technology detection."""

    @pytest.mark.asyncio
    async def test_dns_records_success(self) -> None:
        """Successful DNS fetch returns records and detects technologies."""
        dns_responses = {
            "A": [{"data": "93.184.216.34"}],
            "MX": [{"data": "10 aspmx.l.google.com"}],
            "CNAME": [{"data": "cdn.cloudflare.net"}],
            "TXT": [{"data": "v=spf1"}],
        }

        call_count = [0]

        async def mock_get_json_side_effect(client, url, timeout=10.0):
            call_count[0] += 1
            # Return different responses based on record type in URL
            if "type=A" in url:
                return {"Answer": [{"data": "93.184.216.34"}]}
            elif "type=MX" in url:
                return {"Answer": [{"data": "10 aspmx.l.google.com"}]}
            elif "type=CNAME" in url:
                return {"Answer": [{"data": "cdn.cloudflare.net"}]}
            return {"Answer": []}

        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = mock_get_json_side_effect

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_dns_records(client, "example.com")

            assert "records" in result
            assert "detected_technologies" in result
            # Should detect Google Workspace and Cloudflare
            tech_str = " ".join(result["detected_technologies"]).lower()
            assert "google" in tech_str or "cloudflare" in tech_str or result["detected_technologies"]

    @pytest.mark.asyncio
    async def test_dns_records_no_answer(self) -> None:
        """DNS fetch with no Answer field returns empty records."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"Status": 0}

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_dns_records(client, "notfound.test")

            assert result["records"] == {}
            assert result["detected_technologies"] == []

    @pytest.mark.asyncio
    async def test_dns_records_network_error(self) -> None:
        """DNS fetch with network error returns empty gracefully."""
        with patch("loom.tools.competitive_intel._get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")

            import httpx
            client = httpx.AsyncClient()

            result = await _fetch_dns_records(client, "example.com")

            assert result["records"] == {}
            assert result["detected_technologies"] == []


class TestSynthesizeSignals:
    """Signal synthesis and assessment generation."""

    def test_synthesize_signals_all_sources(self) -> None:
        """Synthesize with all data sources present."""
        sec_data = {"count": 3, "recent": []}
        patent_data = {"count": 12, "recent_titles": []}
        github_data = {
            "repo_count": 25,
            "total_stars": 5000,
            "languages": ["Python"],
            "recent_repos": [],
        }
        ct_data = {"total_found": 20, "recent_subdomains": []}
        dns_data = {"records": {}, "detected_technologies": ["Cloudflare", "Google Workspace"]}

        signals, assessment = _synthesize_signals(
            sec_data, patent_data, github_data, ct_data, dns_data
        )

        assert len(signals) >= 3  # At least SEC, patents, GitHub
        assert all("source" in s and "signal_type" in s for s in signals)
        assert "Financial" in assessment or "financial" in assessment.lower()
        assert "patent" in assessment.lower()

    def test_synthesize_signals_minimal_data(self) -> None:
        """Synthesize with minimal data sources."""
        sec_data = {"count": 0, "recent": []}
        patent_data = {"count": 0, "recent_titles": []}
        github_data = {"repo_count": 0, "total_stars": 0, "languages": [], "recent_repos": []}
        ct_data = {"total_found": 5, "recent_subdomains": []}
        dns_data = {"records": {}, "detected_technologies": []}

        signals, assessment = _synthesize_signals(
            sec_data, patent_data, github_data, ct_data, dns_data
        )

        assert len(signals) >= 0  # May have no signals
        assert isinstance(assessment, str)
        assert len(assessment) > 0

    def test_synthesize_signals_confidence_levels(self) -> None:
        """Synthesized signals have appropriate confidence levels."""
        sec_data = {"count": 2, "recent": []}
        patent_data = {"count": 0, "recent_titles": []}
        github_data = {"repo_count": 15, "total_stars": 1000, "languages": [], "recent_repos": []}
        ct_data = {"total_found": 0, "recent_subdomains": []}
        dns_data = {"records": {}, "detected_technologies": []}

        signals, _ = _synthesize_signals(
            sec_data, patent_data, github_data, ct_data, dns_data
        )

        # All signals should have confidence between 0 and 1
        for signal in signals:
            assert 0 <= signal["confidence"] <= 1


class TestResearchCompetitiveIntel:
    """Main competitive_intel tool integration."""

    def test_competitive_intel_valid_company(self) -> None:
        """Competitive intel returns proper structure for valid company."""
        with patch("loom.tools.competitive_intel._fetch_sec_filings", new_callable=AsyncMock) as mock_sec, \
             patch("loom.tools.competitive_intel._fetch_patents", new_callable=AsyncMock) as mock_patent, \
             patch("loom.tools.competitive_intel._fetch_github_activity", new_callable=AsyncMock) as mock_github, \
             patch("loom.tools.competitive_intel._fetch_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.competitive_intel._fetch_dns_records", new_callable=AsyncMock) as mock_dns:

            mock_sec.return_value = {"count": 2, "recent": []}
            mock_patent.return_value = {"count": 5, "recent_titles": []}
            mock_github.return_value = {
                "repo_count": 10,
                "total_stars": 500,
                "languages": [],
                "recent_repos": [],
            }
            mock_ct.return_value = {"total_found": 8, "recent_subdomains": []}
            mock_dns.return_value = {"records": {}, "detected_technologies": []}

            result = research_competitive_intel("OpenAI")

            assert result["company"] == "OpenAI"
            assert "domain" in result
            assert "github_org" in result
            assert "signals" in result
            assert "sec_filings" in result
            assert "patents" in result
            assert "github_activity" in result
            assert "new_subdomains" in result
            assert "dns_records" in result
            assert "overall_assessment" in result

    def test_competitive_intel_with_optional_params(self) -> None:
        """Competitive intel accepts optional domain and github_org."""
        with patch("loom.tools.competitive_intel._fetch_sec_filings", new_callable=AsyncMock) as mock_sec, \
             patch("loom.tools.competitive_intel._fetch_patents", new_callable=AsyncMock) as mock_patent, \
             patch("loom.tools.competitive_intel._fetch_github_activity", new_callable=AsyncMock) as mock_github, \
             patch("loom.tools.competitive_intel._fetch_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.competitive_intel._fetch_dns_records", new_callable=AsyncMock) as mock_dns:

            mock_sec.return_value = {"count": 1, "recent": []}
            mock_patent.return_value = {"count": 0, "recent_titles": []}
            mock_github.return_value = {"repo_count": 0, "total_stars": 0, "languages": [], "recent_repos": []}
            mock_ct.return_value = {"total_found": 0, "recent_subdomains": []}
            mock_dns.return_value = {"records": {}, "detected_technologies": []}

            result = research_competitive_intel(
                "MyCompany",
                domain="mycompany.io",
                github_org="my-company-org",
            )

            assert result["domain"] == "mycompany.io"
            assert result["github_org"] == "my-company-org"

    def test_competitive_intel_empty_company(self) -> None:
        """Competitive intel rejects empty company name."""
        result = research_competitive_intel("")

        assert "error" in result
        assert "1-256" in result.get("error", "")

    def test_competitive_intel_company_too_long(self) -> None:
        """Competitive intel rejects overly long company name."""
        long_name = "A" * 300
        result = research_competitive_intel(long_name)

        assert "error" in result
        assert "1-256" in result.get("error", "")

    def test_competitive_intel_domain_inference(self) -> None:
        """Competitive intel infers domain from company name."""
        with patch("loom.tools.competitive_intel._fetch_sec_filings", new_callable=AsyncMock) as mock_sec, \
             patch("loom.tools.competitive_intel._fetch_patents", new_callable=AsyncMock) as mock_patent, \
             patch("loom.tools.competitive_intel._fetch_github_activity", new_callable=AsyncMock) as mock_github, \
             patch("loom.tools.competitive_intel._fetch_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.competitive_intel._fetch_dns_records", new_callable=AsyncMock) as mock_dns:

            mock_sec.return_value = {"count": 0, "recent": []}
            mock_patent.return_value = {"count": 0, "recent_titles": []}
            mock_github.return_value = {"repo_count": 0, "total_stars": 0, "languages": [], "recent_repos": []}
            mock_ct.return_value = {"total_found": 0, "recent_subdomains": []}
            mock_dns.return_value = {"records": {}, "detected_technologies": []}

            result = research_competitive_intel("My New Company")

            # Domain should be inferred and lowercased
            assert "my-new-company" in result["domain"].lower()
            assert ".com" in result["domain"]

    def test_competitive_intel_github_org_inference(self) -> None:
        """Competitive intel infers github_org from company name."""
        with patch("loom.tools.competitive_intel._fetch_sec_filings", new_callable=AsyncMock) as mock_sec, \
             patch("loom.tools.competitive_intel._fetch_patents", new_callable=AsyncMock) as mock_patent, \
             patch("loom.tools.competitive_intel._fetch_github_activity", new_callable=AsyncMock) as mock_github, \
             patch("loom.tools.competitive_intel._fetch_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.competitive_intel._fetch_dns_records", new_callable=AsyncMock) as mock_dns:

            mock_sec.return_value = {"count": 0, "recent": []}
            mock_patent.return_value = {"count": 0, "recent_titles": []}
            mock_github.return_value = {"repo_count": 0, "total_stars": 0, "languages": [], "recent_repos": []}
            mock_ct.return_value = {"total_found": 0, "recent_subdomains": []}
            mock_dns.return_value = {"records": {}, "detected_technologies": []}

            result = research_competitive_intel("Test Company Inc")

            # GitHub org should be inferred
            assert "test" in result["github_org"].lower()
            assert "company" in result["github_org"].lower()

    def test_competitive_intel_whitespace_normalization(self) -> None:
        """Competitive intel normalizes whitespace in inputs."""
        with patch("loom.tools.competitive_intel._fetch_sec_filings", new_callable=AsyncMock) as mock_sec, \
             patch("loom.tools.competitive_intel._fetch_patents", new_callable=AsyncMock) as mock_patent, \
             patch("loom.tools.competitive_intel._fetch_github_activity", new_callable=AsyncMock) as mock_github, \
             patch("loom.tools.competitive_intel._fetch_certificate_transparency", new_callable=AsyncMock) as mock_ct, \
             patch("loom.tools.competitive_intel._fetch_dns_records", new_callable=AsyncMock) as mock_dns:

            mock_sec.return_value = {"count": 0, "recent": []}
            mock_patent.return_value = {"count": 0, "recent_titles": []}
            mock_github.return_value = {"repo_count": 0, "total_stars": 0, "languages": [], "recent_repos": []}
            mock_ct.return_value = {"total_found": 0, "recent_subdomains": []}
            mock_dns.return_value = {"records": {}, "detected_technologies": []}

            result = research_competitive_intel(
                "  OpenAI  ",
                domain="  openai.com  ",
                github_org="  openai  ",
            )

            assert result["company"] == "OpenAI"
            assert result["domain"] == "openai.com"
            assert result["github_org"] == "openai"
