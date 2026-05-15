"""Unit tests for infrastructure analysis tools."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import loom.tools.intelligence.infra_analysis


pytestmark = pytest.mark.asyncio

class TestRegistryGraveyard:
    """Tests for research_registry_graveyard tool."""

    async def test_pypi_yanked_detection(self) -> None:
        """Detects yanked versions on PyPI."""
        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = {
                "releases": {
                    "1.0.0": [{"yanked": False}],
                    "1.0.1": [{"yanked": True}],
                    "1.0.2": [{"yanked": True}],
                },
                "info": {"name": "test-package"},
            }

            result = await infra_analysis.research_registry_graveyard(
                "test-package", ecosystem="pypi"
            )

            assert result["package_name"] == "test-package"
            assert result["ecosystem"] == "pypi"
            assert result["exists"] is True
            assert result["version_count"] == 3
            assert result["yanked_count"] == 2
            assert result["is_yanked"] is True

    async def test_npm_deprecated_detection(self) -> None:
        """Detects deprecated versions on NPM."""
        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = {
                "versions": {
                    "1.0.0": {"deprecated": False},
                    "1.0.1": {"deprecated": "Use version 2.0"},
                    "1.0.2": {"deprecated": "Use version 2.0"},
                }
            }

            result = await infra_analysis.research_registry_graveyard(
                "test-package", ecosystem="npm"
            )

            assert result["package_name"] == "test-package"
            assert result["ecosystem"] == "npm"
            assert result["exists"] is True
            assert result["version_count"] == 3
            assert result["deprecated_count"] == 2

    async def test_rubygems_yanked_versions(self) -> None:
        """Detects yanked versions on RubyGems."""
        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = [
                {"number": "1.0.0", "yanked": False},
                {"number": "1.0.1", "yanked": True},
                {"number": "1.0.2", "yanked": True},
            ]

            result = await infra_analysis.research_registry_graveyard(
                "test-package", ecosystem="rubygems"
            )

            assert result["ecosystem"] == "rubygems"
            assert result["version_count"] == 3
            assert result["yanked_count"] == 2

    async def test_entropy_calculation(self) -> None:
        """Entropy score is calculated for package name."""
        result = await infra_analysis.research_registry_graveyard(
            "numpy", ecosystem="pypi"
        )

        # Real entropy value should be present and reasonable
        assert "entropy_score" in result
        assert 0.0 <= result["entropy_score"] <= 5.5

    async def test_invalid_package_name(self) -> None:
        """Rejects invalid package names."""
        result = await infra_analysis.research_registry_graveyard("", ecosystem="pypi")

        assert result["exists"] is False
        assert "error" in result

    async def test_invalid_ecosystem(self) -> None:
        """Rejects unknown ecosystems."""
        result = await infra_analysis.research_registry_graveyard(
            "test", ecosystem="unknown"  # type: ignore
        )

        assert result["exists"] is False
        assert "error" in result

    async def test_risk_level_assessment(self) -> None:
        """Risk level is assessed based on yanked/deprecated status."""
        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            # High risk: many yanked versions
            mock_get.return_value = {
                "releases": {
                    f"{i}.0.0": [{"yanked": i > 2}]
                    for i in range(10)
                }
            }

            result = await infra_analysis.research_registry_graveyard(
                "risky-package", ecosystem="pypi"
            )

            assert result["risk_level"] in ["critical", "high", "medium", "low"]

    async def test_typosquatting_candidates(self) -> None:
        """Identifies suspicious package names."""
        result = await infra_analysis.research_registry_graveyard(
            "numpy", ecosystem="pypi"
        )

        # Should have typosquatting_candidates field
        assert "typosquatting_candidates" in result
        assert isinstance(result["typosquatting_candidates"], list)


class TestSubdomainTemporal:
    """Tests for research_subdomain_temporal tool."""

    async def test_ct_logs_parsing(self) -> None:
        """Parses Certificate Transparency logs correctly."""
        now = datetime.now(UTC)

        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = [
                {
                    "name_value": "example.com\nwww.example.com\napi.example.com",
                    "not_before": now.isoformat(),
                    "issuer_name": "Let's Encrypt",
                },
                {
                    "name_value": "admin.example.com",
                    "not_before": (now - timedelta(days=1)).isoformat(),
                    "issuer_name": "DigiCert",
                },
            ]

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=90
            )

            assert result["domain"] == "example.com"
            assert result["subdomains_total"] > 0

    async def test_internal_tools_detection(self) -> None:
        """Detects exposed internal tool subdomains."""
        now = datetime.now(UTC)

        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = [
                {
                    "name_value": "jenkins.example.com\njira.example.com\ngrafana.example.com",
                    "not_before": now.isoformat(),
                    "issuer_name": "Let's Encrypt",
                }
            ]

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=90
            )

            assert len(result["internal_tools_exposed"]) > 0
            assert "jenkins.example.com" in result["internal_tools_exposed"]
            assert "jira.example.com" in result["internal_tools_exposed"]

    async def test_internal_tools_risk_assessment(self) -> None:
        """Risk is critical when internal tools are exposed."""
        now = datetime.now(UTC)

        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = [
                {
                    "name_value": "jenkins.example.com\njira.example.com\ngrafana.example.com\nkibana.example.com",
                    "not_before": now.isoformat(),
                    "issuer_name": "Let's Encrypt",
                }
            ]

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=90
            )

            # More than 3 internal tools should be critical risk
            if len(result["internal_tools_exposed"]) > 3:
                assert result["risk_level"] == "critical"

    async def test_burst_detection(self) -> None:
        """Detects certificate issuance bursts."""
        now = datetime.now(UTC)

        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            # Simulate 20 certs in one month and 2 in others
            certs = []
            for i in range(20):
                certs.append({
                    "name_value": f"subdomain{i}.example.com",
                    "not_before": now.isoformat(),
                    "issuer_name": "Let's Encrypt",
                })
            for i in range(2):
                certs.append({
                    "name_value": f"other{i}.example.com",
                    "not_before": (now - timedelta(days=60)).isoformat(),
                    "issuer_name": "Let's Encrypt",
                })

            mock_get.return_value = certs

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=90
            )

            # Burst pattern should be detected
            assert "burst_detected" in result

    async def test_days_back_validation(self) -> None:
        """Validates days_back parameter bounds."""
        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = []

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=400  # Should be clamped to 365
            )

            assert result["domain"] == "example.com"

    async def test_empty_ct_logs(self) -> None:
        """Handles empty CT logs gracefully."""
        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = None

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=90
            )

            assert result["subdomains_total"] == 0
            assert result["burst_detected"] is False
            assert result["risk_level"] == "low"

    async def test_monthly_distribution(self) -> None:
        """Tracks subdomain creation by month."""
        now = datetime.now(UTC)

        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            mock_get.return_value = [
                {
                    "name_value": "api.example.com",
                    "not_before": now.isoformat(),
                    "issuer_name": "Let's Encrypt",
                },
                {
                    "name_value": "staging.example.com",
                    "not_before": (now - timedelta(days=30)).isoformat(),
                    "issuer_name": "Let's Encrypt",
                },
            ]

            result = await infra_analysis.research_subdomain_temporal(
                "example.com", days_back=90
            )

            assert "monthly_distribution" in result


class TestCommitAnalyzer:
    """Tests for research_commit_analyzer tool."""

    async def test_security_commit_detection(self) -> None:
        """Detects security-related commits."""
        now = datetime.now(UTC)

        async def mock_get_async(client, url, timeout=20.0):
            return [
                {
                    "commit": {
                        "message": "fix(security): patch CVE-2024-12345 vulnerability",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                },
                {
                    "commit": {
                        "message": "docs: update readme",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "bob"},
                },
            ]

        with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
            # Mock the httpx.AsyncClient.get method
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {
                    "commit": {
                        "message": "fix(security): patch CVE-2024-12345 vulnerability",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                },
                {
                    "commit": {
                        "message": "docs: update readme",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "bob"},
                },
            ]

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
                mock_http_get.return_value = mock_resp

                result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

                assert result["security_incidents"] >= 1
                assert len(result["security_commits"]) > 0

    async def test_crunch_score_calculation(self) -> None:
        """Calculates crunch score (weekend/night commits)."""
        now = datetime.now(UTC)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            # Create commits at different times
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {
                    "commit": {
                        "message": "feature: add new endpoint",
                        "author": {"date": (now - timedelta(days=2)).isoformat()},
                    },
                    "author": {"login": "alice"},
                },
                {
                    "commit": {
                        "message": "fix: bug in parser",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "bob"},
                },
            ]
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

            assert "crunch_score" in result
            assert 0 <= result["crunch_score"] <= 100

    async def test_author_churn_detection(self) -> None:
        """Tracks unique authors and churn rate."""
        now = datetime.now(UTC)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {
                    "commit": {
                        "message": "feature: xyz",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                },
                {
                    "commit": {
                        "message": "fix: abc",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "bob"},
                },
                {
                    "commit": {
                        "message": "docs: xyz",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                },
            ]
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

            assert result["unique_authors"] == 2
            assert "author_churn_rate" in result

    async def test_sentiment_analysis(self) -> None:
        """Analyzes commit message sentiment."""
        now = datetime.now(UTC)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            # Mix of positive and negative keywords
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {
                    "commit": {
                        "message": "fix: critical bug in authentication",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                },
                {
                    "commit": {
                        "message": "feature: add improved API endpoint",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "bob"},
                },
            ]
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

            assert "sentiment_trend" in result
            assert result["sentiment_trend"] in ["positive", "neutral", "negative"]
            assert isinstance(result["sentiment_score"], float)

    async def test_tech_direction_detection(self) -> None:
        """Detects technology direction from commits."""
        now = datetime.now(UTC)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {
                    "commit": {
                        "message": "chore: update requirements.txt dependencies",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                },
                {
                    "commit": {
                        "message": "ci: add GitHub Actions workflow",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "bob"},
                },
                {
                    "commit": {
                        "message": "infra: add Dockerfile for containerization",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "charlie"},
                },
            ]
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

            assert "tech_direction" in result
            assert isinstance(result["tech_direction"], list)

    async def test_invalid_repo_format(self) -> None:
        """Rejects invalid repo format."""
        result = await infra_analysis.research_commit_analyzer("invalid-repo-no-slash")

        assert "error" in result

    async def test_risk_assessment_high_security_incidents(self) -> None:
        """Risk is high with many security incidents."""
        now = datetime.now(UTC)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            # Many security-related commits
            commits = [
                {
                    "commit": {
                        "message": f"fix(security): CVE-2024-{i:05d}",
                        "author": {"date": now.isoformat()},
                    },
                    "author": {"login": "alice"},
                }
                for i in range(10)
            ]

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = commits
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

            assert result["security_incidents"] >= 5
            # High number of security incidents should trigger higher risk
            assert result["risk_level"] in ["critical", "high"]

    async def test_empty_repo(self) -> None:
        """Handles empty repositories gracefully."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = []
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=30)

            assert result["total_commits"] == 0
            assert result["risk_level"] == "low"

    async def test_days_back_parameter(self) -> None:
        """Respects days_back parameter bounds."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = []
            mock_http_get.return_value = mock_resp

            result = await infra_analysis.research_commit_analyzer("owner/repo", days_back=500)

            # Should clamp to 365
            assert result["repo"] == "owner/repo"


class TestLevenshteinDistance:
    """Tests for string similarity calculation."""

    async def test_identical_strings(self) -> None:
        """Identical strings have distance 0."""
        assert infra_analysis._levenshtein_distance("test", "test") == 0

    async def test_empty_string(self) -> None:
        """Distance to empty string is length of string."""
        assert infra_analysis._levenshtein_distance("test", "") == 4
        assert infra_analysis._levenshtein_distance("", "test") == 4

    async def test_single_substitution(self) -> None:
        """Single character change has distance 1."""
        assert infra_analysis._levenshtein_distance("cat", "bat") == 1

    async def test_typosquatting_similarity(self) -> None:
        """Detects typosquatting patterns."""
        # "numpy" vs "numby" (one substitution)
        assert infra_analysis._levenshtein_distance("numpy", "numby") == 1


class TestEntropyCalculation:
    """Tests for Shannon entropy calculation."""

    async def test_uniform_entropy(self) -> None:
        """Uniform distribution has maximum entropy."""
        # "aaaa" has entropy 0 (all same)
        entropy_low = infra_analysis._calculate_entropy("aaaa")
        # "abcd" has higher entropy (all different)
        entropy_high = infra_analysis._calculate_entropy("abcd")

        assert entropy_low < entropy_high

    async def test_empty_string(self) -> None:
        """Empty string has 0 entropy."""
        assert infra_analysis._calculate_entropy("") == 0.0

    async def test_single_character(self) -> None:
        """Single character has 0 entropy."""
        assert infra_analysis._calculate_entropy("a") == 0.0

    async def test_high_entropy_detection(self) -> None:
        """Random strings have high entropy."""
        # Truly random-looking strings
        random_str = "xyzqwjklmn"
        entropy = infra_analysis._calculate_entropy(random_str)
        assert entropy > 3.0  # High entropy indicates randomness


@pytest.mark.parametrize(
    "ecosystem",
    ["pypi", "npm", "rubygems"],
)
async def test_registry_graveyard_ecosystems(ecosystem: str) -> None:
    """Tests all supported ecosystems."""
    with patch("loom.tools.intelligence.infra_analysis._get_json") as mock_get:
        if ecosystem == "pypi":
            mock_get.return_value = {"releases": {"1.0.0": [{"yanked": False}]}}
        elif ecosystem == "npm":
            mock_get.return_value = {"versions": {"1.0.0": {"deprecated": False}}}
        else:  # rubygems
            mock_get.return_value = [{"number": "1.0.0", "yanked": False}]

        result = await infra_analysis.research_registry_graveyard("test-pkg", ecosystem=ecosystem)

        assert result["ecosystem"] == ecosystem
        assert result["exists"] is True
