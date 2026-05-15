"""Tests for supply chain intelligence tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.intelligence.supply_chain_intel import (
    research_supply_chain_risk,
    research_patent_landscape,
    research_dependency_audit,
    _calculate_bus_factor,
    _calculate_risk_level,
    _calculate_staleness_days,
)


class TestCalculateBusFactor:
    """Tests for _calculate_bus_factor helper."""

    def test_no_maintainers_returns_critical(self) -> None:
        """No maintainers = 1.0 (critical risk)."""
        assert _calculate_bus_factor([]) == 1.0

    def test_single_maintainer_returns_critical(self) -> None:
        """Single maintainer = 1.0 (critical risk)."""
        maintainers = [{"name": "Alice", "email": "alice@example.com"}]
        assert _calculate_bus_factor(maintainers) == 1.0

    def test_two_three_maintainers_returns_high(self) -> None:
        """2-3 maintainers = 0.66 (high risk)."""
        maintainers = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
        assert _calculate_bus_factor(maintainers) == 0.66

        maintainers = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
        ]
        assert _calculate_bus_factor(maintainers) == 0.66

    def test_four_plus_maintainers_returns_medium(self) -> None:
        """4+ maintainers = 0.33 (medium risk)."""
        maintainers = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
            {"name": "David", "email": "david@example.com"},
        ]
        assert _calculate_bus_factor(maintainers) == 0.33


class TestCalculateStaleness:
    """Tests for _calculate_staleness_days helper."""

    def test_empty_string_returns_negative_one(self) -> None:
        """Empty string returns -1."""
        assert _calculate_staleness_days("") == -1

    def test_invalid_format_returns_negative_one(self) -> None:
        """Invalid format returns -1."""
        assert _calculate_staleness_days("invalid-date") == -1

    def test_iso_format_parsing(self) -> None:
        """ISO format date is parsed correctly."""
        # This is somewhat hard to test without freezing time
        # Just verify it doesn't crash on valid ISO format
        result = _calculate_staleness_days("2020-01-01T00:00:00Z")
        assert isinstance(result, int)
        assert result > 0


class TestCalculateRiskLevel:
    """Tests for _calculate_risk_level helper."""

    def test_high_bus_factor_contributes_to_risk(self) -> None:
        """High bus factor alone = medium risk (30% of score)."""
        result = _calculate_risk_level(1.0, 0, 1, 0)
        assert result == "medium"

    def test_very_old_package_is_medium_risk(self) -> None:
        """Package not updated in 2+ years adds 30% risk (total ~40%)."""
        result = _calculate_risk_level(0.33, 731, 1, 0)
        assert result in ["medium", "high"]

    def test_many_vulnerabilities_contributes_to_risk(self) -> None:
        """Many known vulnerabilities adds 20% risk (total ~30%)."""
        result = _calculate_risk_level(0.33, 0, 1, 10)
        assert result in ["low", "medium"]

    def test_low_risk_all_factors_good(self) -> None:
        """All good factors = low to medium risk."""
        result = _calculate_risk_level(0.33, 30, 3, 0)
        assert result in ["low", "medium"]

    def test_critical_risk_when_bus_and_staleness_combined(self) -> None:
        """Bus factor 1.0 + old staleness (0.3+0.3) = 0.6 = high risk."""
        result = _calculate_risk_level(1.0, 731, 10, 0)
        assert result in ["high", "critical"]


@pytest.mark.asyncio
class TestSupplyChainRisk:
    """Tests for research_supply_chain_risk tool."""

    async def test_invalid_package_name_empty(self) -> None:
        """Empty package name returns error."""
        result = await research_supply_chain_risk("")
        assert "error" in result
        assert "must be 1-200 characters" in result["error"]

    async def test_invalid_package_name_too_long(self) -> None:
        """Package name > 200 chars returns error."""
        long_name = "A" * 201
        result = await research_supply_chain_risk(long_name)
        assert "error" in result

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_supply_chain_risk("unknown-package-xyz")

            required_fields = [
                "package_name",
                "ecosystem",
                "maintainers",
                "last_update",
                "stars",
                "bus_factor_score",
                "staleness_days",
                "dependency_depth",
                "known_vulns",
                "risk_level",
            ]
            for field in required_fields:
                assert field in result

    async def test_package_name_trimmed(self) -> None:
        """Package name is trimmed."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_supply_chain_risk("  test-package  ")
            assert result["package_name"] == "test-package"

    async def test_supports_multiple_ecosystems(self) -> None:
        """Supports pypi, npm, and cargo ecosystems."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            for ecosystem in ["pypi", "npm", "cargo"]:
                result = await research_supply_chain_risk("test-package", ecosystem=ecosystem)
                assert result["ecosystem"] == ecosystem

    async def test_bus_factor_score_in_valid_range(self) -> None:
        """Bus factor score is 0-1."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_supply_chain_risk("test-package")
            assert 0.0 <= result["bus_factor_score"] <= 1.0

    async def test_risk_level_valid_values(self) -> None:
        """Risk level is one of valid values."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_supply_chain_risk("test-package")
            assert result["risk_level"] in ["critical", "high", "medium", "low", "unknown"]


@pytest.mark.asyncio
class TestPatentLandscape:
    """Tests for research_patent_landscape tool."""

    async def test_invalid_query_empty(self) -> None:
        """Empty query returns error."""
        result = await research_patent_landscape("")
        assert "error" in result
        assert "must be 1-500 characters" in result["error"]

    async def test_invalid_query_too_long(self) -> None:
        """Query > 500 chars returns error."""
        long_query = "A" * 501
        result = await research_patent_landscape(long_query)
        assert "error" in result

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_patent_landscape("blockchain")

            required_fields = [
                "query",
                "total_patents",
                "recent_patents",
                "top_assignees",
                "filing_trend",
            ]
            for field in required_fields:
                assert field in result

    async def test_query_trimmed(self) -> None:
        """Query is trimmed."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_patent_landscape("  blockchain  ")
            assert result["query"] == "blockchain"

    async def test_max_results_capped(self) -> None:
        """max_results is capped at 100."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, json=lambda: {}))

            result = await research_patent_landscape("blockchain", max_results=200)
            # Should not raise, max_results is capped internally
            assert "query" in result

    async def test_recent_patents_is_list(self) -> None:
        """recent_patents is always a list."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_patent_landscape("blockchain")
            assert isinstance(result["recent_patents"], list)

    async def test_top_assignees_is_dict(self) -> None:
        """top_assignees is always a dict."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_patent_landscape("blockchain")
            assert isinstance(result["top_assignees"], dict)

    async def test_filing_trend_valid_values(self) -> None:
        """filing_trend is one of valid values."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

            result = await research_patent_landscape("blockchain")
            assert result["filing_trend"] in ["increasing", "stable", "decreasing", "unknown"]


@pytest.mark.asyncio
class TestDependencyAudit:
    """Tests for research_dependency_audit tool."""

    async def test_invalid_repo_url_not_github(self) -> None:
        """Non-GitHub URL returns error."""
        result = await research_dependency_audit("https://gitlab.com/owner/repo")
        assert "error" in result
        assert "GitHub" in result["error"]

    async def test_invalid_repo_url_empty(self) -> None:
        """Empty URL returns error."""
        result = await research_dependency_audit("")
        assert "error" in result

    async def test_returns_required_fields(self) -> None:
        """Result contains all required fields."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))

            result = await research_dependency_audit("https://github.com/owner/repo")

            required_fields = [
                "repo_url",
                "dependencies_found",
                "audited",
                "vulnerabilities",
                "outdated",
                "risk_summary",
            ]
            for field in required_fields:
                assert field in result

    async def test_repo_url_normalized(self) -> None:
        """Repo URL is normalized (trailing slash removed)."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))

            result = await research_dependency_audit("https://github.com/owner/repo/")
            assert result["repo_url"] == "https://github.com/owner/repo"

    async def test_vulnerabilities_is_list(self) -> None:
        """vulnerabilities is always a list."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))

            result = await research_dependency_audit("https://github.com/owner/repo")
            assert isinstance(result["vulnerabilities"], list)

    async def test_outdated_is_list(self) -> None:
        """outdated is always a list."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))

            result = await research_dependency_audit("https://github.com/owner/repo")
            assert isinstance(result["outdated"], list)

    async def test_risk_summary_valid_values(self) -> None:
        """risk_summary is one of valid values."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text=""))

            result = await research_dependency_audit("https://github.com/owner/repo")
            assert result["risk_summary"] in ["critical", "high", "medium", "low", "unknown"]

    async def test_parses_requirements_txt(self) -> None:
        """Parses requirements.txt dependencies."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    text="requests==2.25.1\nnumpy>=1.19.0",
                )
            )

            result = await research_dependency_audit("https://github.com/owner/repo")
            assert result["dependencies_found"] > 0
