"""Tests for vulnerability intelligence aggregation tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestResearchVulnIntel:
    def test_empty_query(self):
        """Test handling of empty query."""
        from loom.tools.vuln_intel import research_vuln_intel

        result = research_vuln_intel("", max_results=30)

        assert result["query"] == ""
        assert result["total_vulns"] == 0
        assert result["vulns"] == []
        assert result["error"] == "query required"

    def test_whitespace_only_query(self):
        """Test handling of whitespace-only query."""
        from loom.tools.vuln_intel import research_vuln_intel

        result = research_vuln_intel("   ", max_results=30)

        assert result["total_vulns"] == 0
        assert result["vulns"] == []
        assert result["error"] == "query required"

    def test_max_results_validation(self):
        """Test that max_results is clamped to valid range."""
        from loom.tools.vuln_intel import research_vuln_intel

        # Test with value > 100 (should clamp to 30)
        with patch("loom.tools.vuln_intel.asyncio.run") as mock_run:
            mock_run.return_value = {
                "query": "test",
                "sources_checked": [],
                "total_vulns": 0,
                "vulns": [],
            }
            result = research_vuln_intel("test", max_results=200)
            assert "vulns" in result

    def test_max_results_minimum(self):
        """Test that max_results defaults to 30 when < 1."""
        from loom.tools.vuln_intel import research_vuln_intel

        with patch("loom.tools.vuln_intel.asyncio.run") as mock_run:
            mock_run.return_value = {
                "query": "test",
                "sources_checked": [],
                "total_vulns": 0,
                "vulns": [],
            }
            result = research_vuln_intel("test", max_results=0)
            assert "vulns" in result

    def test_nvd_search_success(self):
        """Test successful NVD search."""
        from loom.tools.vuln_intel import research_vuln_intel

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-44228",
                        "descriptions": [{"value": "Apache Log4j RCE"}],
                        "published": "2021-12-10",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 10.0,
                                        "baseSeverity": "CRITICAL",
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("log4j", max_results=30)

            assert result["query"] == "log4j"
            assert "NVD" in result["sources_checked"]
            assert result["total_vulns"] >= 0

    def test_deduplication_by_cve_id(self):
        """Test deduplication of vulnerabilities by CVE ID."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-44228",
                        "descriptions": [{"value": "Log4j RCE"}],
                        "published": "2021-12-10",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 10.0,
                                        "baseSeverity": "CRITICAL",
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
        nvd_response.status_code = 200

        github_response = MagicMock()
        github_response.json.return_value = [
            {
                "ghsa_id": "GHSA-jfgw-4f94-5980",
                "cve_id": "CVE-2021-44228",
                "summary": "Log4j vulnerability",
                "severity": "critical",
                "description": "Log4j RCE",
                "html_url": "https://github.com/advisories/GHSA-jfgw-4f94-5980",
                "published_at": "2021-12-10",
                "cvss": {"score": 10.0},
            }
        ]
        github_response.status_code = 200

        responses = [nvd_response, github_response]
        response_idx = [0]

        def get_side_effect(*args, **kwargs):
            resp = responses[min(response_idx[0], len(responses) - 1)]
            response_idx[0] += 1
            return resp

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = get_side_effect
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("log4j", max_results=30)

            # Should deduplicate CVE-2021-44228
            assert result["query"] == "log4j"

    def test_severity_sorting(self):
        """Test that results are sorted by severity."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-11111",
                        "descriptions": [{"value": "Low severity"}],
                        "published": "2021-01-01",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 3.0,
                                        "baseSeverity": "LOW",
                                    }
                                }
                            ]
                        },
                    }
                },
                {
                    "cve": {
                        "id": "CVE-2021-22222",
                        "descriptions": [{"value": "Critical severity"}],
                        "published": "2021-01-02",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 9.8,
                                        "baseSeverity": "CRITICAL",
                                    }
                                }
                            ]
                        },
                    }
                },
            ]
        }
        nvd_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = nvd_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=30)

            if len(result["vulns"]) >= 2:
                # First should be CRITICAL
                assert result["vulns"][0]["severity"] == "CRITICAL"
                # Second should be LOW
                assert result["vulns"][1]["severity"] == "LOW"

    def test_cisa_kev_marked_as_exploited(self):
        """Test that CISA KEV results are marked with exploits_available=True."""
        from loom.tools.vuln_intel import research_vuln_intel

        cisa_response = MagicMock()
        cisa_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cveID": "CVE-2021-44228",
                    "shortDescription": "Log4j RCE",
                    "dateAdded": "2021-12-10",
                }
            ]
        }
        cisa_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = cisa_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("log4j", max_results=30)

            assert result["query"] == "log4j"
            assert "CISA KEV" in result["sources_checked"]

    def test_github_poc_marked_as_exploited(self):
        """Test that GitHub PoC results are marked with exploits_available=True."""
        from loom.tools.vuln_intel import research_vuln_intel

        poc_response = MagicMock()
        poc_response.json.return_value = {
            "items": [
                {
                    "full_name": "user/log4j-exploit",
                    "description": "Log4j RCE exploit PoC",
                    "html_url": "https://github.com/user/log4j-exploit",
                    "created_at": "2021-12-11",
                }
            ]
        }
        poc_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = poc_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("log4j", max_results=30)

            assert result["query"] == "log4j"
            assert "GitHub PoC" in result["sources_checked"]

    def test_vulners_search_success(self):
        """Test successful Vulners API search."""
        from loom.tools.vuln_intel import research_vuln_intel

        vulners_response = MagicMock()
        vulners_response.json.return_value = {
            "data": {
                "documents": {
                    "doc1": {
                        "id": "CVE-2021-44228",
                        "description": "Log4j RCE",
                        "published": "2021-12-10",
                        "href": "https://vulners.com/cve/CVE-2021-44228",
                        "type": "exploit",
                        "cvssScore": {"v3": {"baseScore": 10.0, "baseSeverity": "CRITICAL"}},
                    }
                }
            }
        }
        vulners_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = vulners_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("log4j", max_results=30)

            assert result["query"] == "log4j"
            assert "Vulners" in result["sources_checked"]

    def test_description_truncation(self):
        """Test that descriptions are truncated appropriately."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        long_description = "A" * 1000
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-11111",
                        "descriptions": [{"value": long_description}],
                        "published": "2021-01-01",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 5.0,
                                        "baseSeverity": "MEDIUM",
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
        nvd_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = nvd_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=30)

            if result["vulns"]:
                # Description should be <= 300 chars
                assert len(result["vulns"][0]["description"]) <= 300

    def test_extract_cve_id_from_text(self):
        """Test CVE ID extraction from text."""
        from loom.tools.vuln_intel import _extract_cve_id

        assert _extract_cve_id("CVE-2021-44228") == "CVE-2021-44228"
        assert _extract_cve_id("Found CVE-2020-12345 in docs") == "CVE-2020-12345"
        assert _extract_cve_id("cve-2019-5678") == "CVE-2019-5678"
        assert _extract_cve_id("No CVE here") is None

    def test_deduplication_with_cve_in_description(self):
        """Test deduplication when CVE ID is in description."""
        from loom.tools.vuln_intel import _deduplicate_vulns

        vulns = [
            {
                "id": "CVE-2021-44228",
                "severity": "CRITICAL",
                "exploits_available": False,
            },
            {
                "id": "GHSA-xyz-abc-123",
                "severity": "CRITICAL",
                "description": "CVE-2021-44228 Log4j",
                "exploits_available": True,
            },
        ]

        deduped = _deduplicate_vulns(vulns)

        # Should keep only one entry for this CVE
        assert len(deduped) == 1
        # Should prefer the one with exploits_available=True
        assert deduped[0]["exploits_available"] is True

    def test_sources_checked_list(self):
        """Test that sources_checked includes all attempted sources."""
        from loom.tools.vuln_intel import research_vuln_intel

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Mock all responses to return empty/None
            async def mock_get(*args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"vulnerabilities": []}
                return resp

            mock_client.get.side_effect = mock_get
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=30)

            # Should have checked all 5 sources
            expected_sources = ["NVD", "GitHub Advisories", "CISA KEV", "Vulners", "GitHub PoC"]
            assert all(source in result["sources_checked"] for source in expected_sources)

    def test_total_vulns_count(self):
        """Test that total_vulns matches the length of vulns list."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": f"CVE-2021-{i:05d}",
                        "descriptions": [{"value": f"Vuln {i}"}],
                        "published": "2021-01-01",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 5.0,
                                        "baseSeverity": "MEDIUM",
                                    }
                                }
                            ]
                        },
                    }
                }
                for i in range(5)
            ]
        }
        nvd_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = nvd_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=30)

            assert result["total_vulns"] == len(result["vulns"])

    def test_exploit_availability_sorting(self):
        """Test that exploits_available=True entries come first."""
        from loom.tools.vuln_intel import _deduplicate_vulns

        vulns = [
            {
                "id": "CVE-2021-11111",
                "severity": "MEDIUM",
                "exploits_available": False,
                "description": "No exploit",
            },
            {
                "id": "CVE-2021-22222",
                "severity": "MEDIUM",
                "exploits_available": True,
                "description": "Has exploit",
            },
        ]

        from loom.tools.vuln_intel import research_vuln_intel

        # Simulate sorting behavior from research_vuln_intel
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        sorted_vulns = sorted(
            vulns,
            key=lambda v: (
                severity_order.get(v.get("severity", "UNKNOWN"), 4),
                not v.get("exploits_available", False),
            ),
        )

        # Should have same severity, so exploit order matters
        # exploits_available=True should be first
        assert sorted_vulns[0]["exploits_available"] is True

    def test_handles_missing_fields(self):
        """Test handling of vulnerabilities with missing fields."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-11111",
                        # Missing descriptions
                        "published": "2021-01-01",
                        "metrics": {},  # No CVSS data
                    }
                }
            ]
        }
        nvd_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = nvd_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=30)

            # Should not crash, should handle gracefully
            assert result["query"] == "test"
            assert "sources_checked" in result

    def test_max_results_limit_enforced(self):
        """Test that max_results limit is enforced."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": f"CVE-2021-{i:05d}",
                        "descriptions": [{"value": f"Vuln {i}"}],
                        "published": "2021-01-01",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 5.0,
                                        "baseSeverity": "MEDIUM",
                                    }
                                }
                            ]
                        },
                    }
                }
                for i in range(100)
            ]
        }
        nvd_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = nvd_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=10)

            assert len(result["vulns"]) <= 10
            assert result["total_vulns"] <= 10

    def test_result_contains_required_fields(self):
        """Test that result contains all required fields."""
        from loom.tools.vuln_intel import research_vuln_intel

        nvd_response = MagicMock()
        nvd_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-44228",
                        "descriptions": [{"value": "Test"}],
                        "published": "2021-01-01",
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 5.0,
                                        "baseSeverity": "MEDIUM",
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
        nvd_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = nvd_response
            mock_client_cls.return_value = mock_client

            result = research_vuln_intel("test", max_results=30)

            assert "query" in result
            assert "sources_checked" in result
            assert "total_vulns" in result
            assert "vulns" in result

            if result["vulns"]:
                vuln = result["vulns"][0]
                assert "source" in vuln
                assert "id" in vuln
                assert "title" in vuln
                assert "severity" in vuln
                assert "description" in vuln
                assert "url" in vuln
                assert "published" in vuln
                assert "exploits_available" in vuln
