"""Tests for CVE lookup tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest


class TestResearchCveLookup:
    def test_empty_query(self):
        """Test handling of empty query."""
        from loom.tools.cve_lookup import research_cve_lookup

        result = research_cve_lookup("", limit=10)

        assert result["query"] == ""
        assert result["total_results"] == 0
        assert result["cves"] == []
        assert result["error"] == "query required"

    def test_limit_validation(self):
        """Test that limit is clamped to 1-100."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"totalResults": 0, "vulnerabilities": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_lookup

            result = research_cve_lookup("openssl", limit=200)

            # Limit should be clamped to 100
            call_args = mock_client.get.call_args
            assert call_args[1]["params"]["resultsPerPage"] == 100

    def test_successful_lookup(self):
        """Test successful CVE lookup."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "totalResults": 2,
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-44228",
                        "descriptions": [
                            {"value": "Apache Log4j remote code execution"}
                        ],
                        "published": "2021-12-10",
                        "lastModified": "2022-01-15",
                        "references": [
                            {"url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"}
                        ],
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
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_lookup

            result = research_cve_lookup("log4j", limit=10)

            assert result["query"] == "log4j"
            assert result["total_results"] == 2
            assert len(result["cves"]) == 1
            assert result["cves"][0]["id"] == "CVE-2021-44228"
            assert result["cves"][0]["severity"] == "CRITICAL"
            assert result["cves"][0]["cvss"] == 10.0

    def test_cvss_v30_fallback(self):
        """Test fallback to CVSS v3.0 when v3.1 is unavailable."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "totalResults": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2020-1234",
                        "descriptions": [{"value": "Test vulnerability"}],
                        "published": "2020-01-01",
                        "lastModified": "2020-02-01",
                        "references": [],
                        "metrics": {
                            "cvssMetricV30": [
                                {
                                    "cvssData": {
                                        "baseScore": 7.5,
                                        "baseSeverity": "HIGH",
                                    }
                                }
                            ]
                        },
                    }
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_lookup

            result = research_cve_lookup("test", limit=10)

            assert result["cves"][0]["cvss"] == 7.5
            assert result["cves"][0]["severity"] == "HIGH"

    def test_timeout_exception(self):
        """Test handling of timeout."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_lookup

            result = research_cve_lookup("openssl", limit=10)

            assert result["cves"] == []
            assert "timed out" in result["error"].lower()

    def test_description_capped_at_500_chars(self):
        """Test that descriptions are capped at 500 characters."""
        long_description = "A" * 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "totalResults": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-1234",
                        "descriptions": [{"value": long_description}],
                        "published": "2021-01-01",
                        "lastModified": "2021-02-01",
                        "references": [],
                        "metrics": {"cvssMetricV2": [{"cvssData": {"baseScore": 5.0}}]},
                    }
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_lookup

            result = research_cve_lookup("test")

            assert len(result["cves"][0]["description"]) <= 500

    def test_references_capped_at_5(self):
        """Test that references are capped at 5."""
        refs = [{"url": f"https://example.com/{i}"} for i in range(10)]
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "totalResults": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-5678",
                        "descriptions": [{"value": "Test"}],
                        "published": "2021-01-01",
                        "lastModified": "2021-02-01",
                        "references": refs,
                        "metrics": {},
                    }
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_lookup

            result = research_cve_lookup("test")

            assert len(result["cves"][0]["references"]) <= 5


class TestResearchCveDetail:
    def test_invalid_cve_id_format(self):
        """Test rejection of invalid CVE ID format."""
        from loom.tools.cve_lookup import research_cve_detail

        result = research_cve_detail("INVALID-1234")

        assert result["cve_id"] == "INVALID-1234"
        assert "Invalid CVE ID format" in result["error"]

    def test_cve_not_found(self):
        """Test handling when CVE is not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"vulnerabilities": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_detail

            result = research_cve_detail("CVE-9999-99999")

            assert result["error"] == "CVE not found"

    def test_successful_cve_detail_lookup(self):
        """Test successful detailed CVE lookup."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-44228",
                        "descriptions": [
                            {"value": "Apache Log4j RCE vulnerability"}
                        ],
                        "published": "2021-12-10",
                        "lastModified": "2022-01-15",
                        "references": [{"url": "https://nvd.nist.gov/"}],
                        "configurations": [
                            {
                                "nodes": [
                                    {
                                        "cpeMatch": [
                                            {"criteria": "cpe:2.3:a:apache:log4j:*"}
                                        ]
                                    }
                                ]
                            }
                        ],
                        "weaknesses": [
                            {
                                "description": [
                                    {"value": "CWE-94"}
                                ]
                            }
                        ],
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
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_detail

            result = research_cve_detail("CVE-2021-44228")

            assert result["cve_id"] == "CVE-2021-44228"
            assert result["severity"] == "CRITICAL"
            assert result["cvss"] == 10.0
            assert len(result["affected_products"]) > 0
            assert len(result["weaknesses"]) > 0

    def test_affected_products_capped_at_10(self):
        """Test that affected products list is capped at 10."""
        cpe_matches = [
            {"criteria": f"cpe:2.3:a:vendor:{i}:*"}
            for i in range(15)
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2021-1111",
                        "descriptions": [{"value": "Test"}],
                        "published": "2021-01-01",
                        "lastModified": "2021-02-01",
                        "references": [],
                        "configurations": [
                            {"nodes": [{"cpeMatch": cpe_matches}]}
                        ],
                        "weaknesses": [],
                        "metrics": {},
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_detail

            result = research_cve_detail("CVE-2021-1111")

            assert len(result["affected_products"]) <= 10

    def test_timeout_on_detail_lookup(self):
        """Test timeout handling in detailed lookup."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client_cls.return_value = mock_client

            from loom.tools.cve_lookup import research_cve_detail

            result = research_cve_detail("CVE-2021-44228")

            assert "timed out" in result["error"].lower()
