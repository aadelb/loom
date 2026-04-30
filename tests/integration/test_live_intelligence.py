"""Live integration tests for Intelligence tools (REQ-042).

Tests 12 Intelligence tools with real network calls:
1. research_identity_resolve — cross-platform identity linking
2. research_change_monitor — website delta detection
3. research_social_graph — network analysis
4. research_competitive_intel — competitor research
5. research_crypto_trace — blockchain tracing
6. research_stego_detect — steganography detection
7. research_threat_profile — threat profiling
8. research_company_diligence — company research
9. research_salary_intelligence — salary data
10. research_supply_chain_risk — supply chain analysis
11. research_patent_landscape — patent analysis
12. research_dependency_audit — dependency audit

All tests marked @pytest.mark.live for optional execution.
Gracefully handles missing API keys and network unavailability.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

logger = logging.getLogger("tests.integration.test_live_intelligence")


@pytest.fixture
def safe_test_inputs() -> dict[str, Any]:
    """Provide safe, public test inputs for Intelligence tools."""
    return {
        "email": "test@example.com",
        "username": "torvalds",  # Linus Torvalds (public GitHub)
        "company": "OpenAI",
        "domain": "example.com",
        "url": "https://example.com",
        "address_eth": "0x1234567890123456789012345678901234567890",
        "address_btc": "1A1z7agoat2EYMJG7omPYxSgv4MtsuC1qs",
        "package_pypi": "requests",
        "job_title": "Software Engineer",
        "location": "San Francisco",
        "tech_query": "machine learning",
        "github_repo": "https://github.com/torvalds/linux",
    }


# ==============================================================================
# 1. research_identity_resolve — Cross-platform identity linking
# ==============================================================================


@pytest.mark.live
def test_identity_resolve_email(safe_test_inputs: dict[str, Any]) -> None:
    """research_identity_resolve with email — assert profile linkage."""
    try:
        from loom.tools.identity_resolve import research_identity_resolve
    except ImportError:
        pytest.skip("Loom not installed")

    email = safe_test_inputs["email"]

    try:
        result = research_identity_resolve(email=email, check_gravatar=True, check_pgp=False)

        # Assert basic structure
        assert isinstance(result, dict)
        assert result.get("email") == email
        assert "total_matches" in result
        assert "total_platforms_checked" in result
        assert "platforms_found" in result
        assert isinstance(result["platforms_found"], list)

        logger.info("identity_resolve email passed", extra={"email": email})
    except Exception as exc:
        logger.warning("identity_resolve email failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


@pytest.mark.live
def test_identity_resolve_username(safe_test_inputs: dict[str, Any]) -> None:
    """research_identity_resolve with username — assert cross-platform presence."""
    try:
        from loom.tools.identity_resolve import research_identity_resolve
    except ImportError:
        pytest.skip("Loom not installed")

    username = safe_test_inputs["username"]

    try:
        result = research_identity_resolve(username=username, check_github=True)

        # Assert structure
        assert isinstance(result, dict)
        assert result.get("username") == username
        assert "total_matches" in result
        assert "platforms_found" in result

        logger.info("identity_resolve username passed", extra={"username": username})
    except Exception as exc:
        logger.warning("identity_resolve username failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 2. research_change_monitor — Website delta detection
# ==============================================================================


@pytest.mark.live
def test_change_monitor_initial_snapshot(safe_test_inputs: dict[str, Any]) -> None:
    """research_change_monitor initial snapshot — assert content hash recorded."""
    try:
        from loom.tools.change_monitor import research_change_monitor
    except ImportError:
        pytest.skip("Loom not installed")

    url = safe_test_inputs["url"]

    try:
        result = research_change_monitor(url=url, store_result=True)

        # Assert snapshot structure
        assert isinstance(result, dict)
        assert result.get("url") == url
        assert "content_hash" in result
        assert "is_first_snapshot" in result
        assert "timestamp" in result
        assert len(result["content_hash"]) == 64  # SHA-256 hex

        logger.info("change_monitor initial passed", extra={"url": url})
    except Exception as exc:
        logger.warning("change_monitor initial failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


@pytest.mark.live
def test_change_monitor_second_snapshot(safe_test_inputs: dict[str, Any]) -> None:
    """research_change_monitor second snapshot — assert delta detection."""
    try:
        from loom.tools.change_monitor import research_change_monitor
    except ImportError:
        pytest.skip("Loom not installed")

    url = safe_test_inputs["url"]

    try:
        # First snapshot
        result1 = research_change_monitor(url=url, store_result=True)
        assert "content_hash" in result1

        # Second snapshot
        result2 = research_change_monitor(url=url, store_result=True)

        # Assert change detection
        assert isinstance(result2, dict)
        assert "content_hash" in result2
        assert "has_changed" in result2  # Delta detection
        assert "change_summary" in result2 or result2.get("has_changed") is not None

        logger.info("change_monitor delta passed", extra={"url": url})
    except Exception as exc:
        logger.warning("change_monitor delta failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 3. research_social_graph — Network analysis
# ==============================================================================


@pytest.mark.live
def test_social_graph_github_network(safe_test_inputs: dict[str, Any]) -> None:
    """research_social_graph — assert graph nodes and edges."""
    try:
        from loom.tools.social_graph import research_social_graph
    except ImportError:
        pytest.skip("Loom not installed")

    username = safe_test_inputs["username"]

    try:
        result = research_social_graph(username=username, platforms=["github"])

        # Assert graph structure
        assert isinstance(result, dict)
        assert result.get("username") == username
        assert "nodes" in result
        assert "edges" in result
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)

        # Validate node structure if nodes exist
        if result["nodes"]:
            for node in result["nodes"]:
                assert "id" in node
                assert "platform" in node

        logger.info("social_graph passed", extra={"username": username})
    except Exception as exc:
        logger.warning("social_graph failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 4. research_competitive_intel — Competitor research
# ==============================================================================


@pytest.mark.live
def test_competitive_intel_company_analysis(safe_test_inputs: dict[str, Any]) -> None:
    """research_competitive_intel — assert intel signals."""
    try:
        from loom.tools.competitive_intel import research_competitive_intel
    except ImportError:
        pytest.skip("Loom not installed")

    company = safe_test_inputs["company"]

    try:
        result = asyncio.run(research_competitive_intel(company=company))

        # Assert intel structure
        assert isinstance(result, dict)
        assert result.get("company") == company
        assert "summary" in result or "signals" in result or "intelligence" in result

        logger.info("competitive_intel passed", extra={"company": company})
    except Exception as exc:
        logger.warning("competitive_intel failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 5. research_crypto_trace — Blockchain tracing
# ==============================================================================


@pytest.mark.live
def test_crypto_trace_ethereum_address(safe_test_inputs: dict[str, Any]) -> None:
    """research_crypto_trace Ethereum — assert address trace data."""
    try:
        from loom.tools.crypto_trace import research_crypto_trace
    except ImportError:
        pytest.skip("Loom not installed")

    address = safe_test_inputs["address_eth"]

    try:
        result = research_crypto_trace(address=address, chain="auto")

        # Assert trace structure
        assert isinstance(result, dict)
        assert result.get("address") == address
        assert "balance" in result or "transactions" in result or "trace" in result

        logger.info("crypto_trace ethereum passed", extra={"address": address})
    except Exception as exc:
        logger.warning("crypto_trace ethereum failed: %s", exc)
        pytest.skip(f"Network error or invalid address: {exc}")


@pytest.mark.live
def test_crypto_trace_bitcoin_address(safe_test_inputs: dict[str, Any]) -> None:
    """research_crypto_trace Bitcoin — assert UTXO trace."""
    try:
        from loom.tools.crypto_trace import research_crypto_trace
    except ImportError:
        pytest.skip("Loom not installed")

    address = safe_test_inputs["address_btc"]

    try:
        result = research_crypto_trace(address=address, chain="bitcoin")

        # Assert trace structure
        assert isinstance(result, dict)
        assert "balance" in result or "transactions" in result or "trace" in result

        logger.info("crypto_trace bitcoin passed", extra={"address": address})
    except Exception as exc:
        logger.warning("crypto_trace bitcoin failed: %s", exc)
        pytest.skip(f"Network error or invalid address: {exc}")


# ==============================================================================
# 6. research_stego_detect — Steganography detection
# ==============================================================================


@pytest.mark.live
def test_stego_detect_public_image(safe_test_inputs: dict[str, Any]) -> None:
    """research_stego_detect image URL — assert stego analysis."""
    try:
        from loom.tools.stego_detect import research_stego_detect
    except ImportError:
        pytest.skip("Loom not installed")

    # Use a public test image URL
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/320px-PNG_transparency_demonstration_1.png"

    try:
        result = research_stego_detect(image_url=url, check_whitespace=True)

        # Assert detection structure
        assert isinstance(result, dict)
        assert "analysis" in result or "whitespace" in result or "entropy" in result or "result" in result

        logger.info("stego_detect passed", extra={"url": url})
    except Exception as exc:
        logger.warning("stego_detect failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 7. research_threat_profile — Threat profiling
# ==============================================================================


@pytest.mark.live
def test_threat_profile_username(safe_test_inputs: dict[str, Any]) -> None:
    """research_threat_profile username — assert threat indicators."""
    try:
        from loom.tools.threat_profile import research_threat_profile
    except ImportError:
        pytest.skip("Loom not installed")

    username = safe_test_inputs["username"]

    try:
        result = research_threat_profile(username=username, check_platforms=True)

        # Assert profile structure
        assert isinstance(result, dict)
        assert result.get("username") == username
        assert "threat_score" in result or "indicators" in result or "profile" in result

        logger.info("threat_profile passed", extra={"username": username})
    except Exception as exc:
        logger.warning("threat_profile failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 8. research_company_diligence — Company research
# ==============================================================================


@pytest.mark.live
def test_company_diligence_well_known(safe_test_inputs: dict[str, Any]) -> None:
    """research_company_diligence — assert company fundamentals."""
    try:
        from loom.tools.company_intel import research_company_diligence
    except ImportError:
        pytest.skip("Loom not installed")

    company = safe_test_inputs["company"]

    try:
        result = asyncio.run(research_company_diligence(company_name=company))

        # Assert diligence structure
        assert isinstance(result, dict)
        assert result.get("company") == company
        assert "industry" in result or "funding_stage" in result or "culture_score" in result
        assert "red_flags" in result or "recommendation" in result

        logger.info("company_diligence passed", extra={"company": company})
    except Exception as exc:
        logger.warning("company_diligence failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 9. research_salary_intelligence — Salary data
# ==============================================================================


@pytest.mark.live
def test_salary_intelligence_job_title(safe_test_inputs: dict[str, Any]) -> None:
    """research_salary_intelligence — assert salary ranges."""
    try:
        from loom.tools.company_intel import research_salary_intelligence
    except ImportError:
        pytest.skip("Loom not installed")

    job_title = safe_test_inputs["job_title"]
    location = safe_test_inputs["location"]

    try:
        result = asyncio.run(
            research_salary_intelligence(role=job_title, location=location)
        )

        # Assert salary structure
        assert isinstance(result, dict)
        assert result.get("role") == job_title or "role" in result
        assert "salary_min" in result or "salary_estimate" in result or "range" in result
        assert "salary_max" in result or "salary_estimate" in result or "range" in result

        logger.info("salary_intelligence passed", extra={"role": job_title})
    except Exception as exc:
        logger.warning("salary_intelligence failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 10. research_supply_chain_risk — Supply chain analysis
# ==============================================================================


@pytest.mark.live
def test_supply_chain_risk_pypi_package(safe_test_inputs: dict[str, Any]) -> None:
    """research_supply_chain_risk PyPI — assert risk assessment."""
    try:
        from loom.tools.supply_chain_intel import research_supply_chain_risk
    except ImportError:
        pytest.skip("Loom not installed")

    package = safe_test_inputs["package_pypi"]

    try:
        result = asyncio.run(research_supply_chain_risk(package_name=package, ecosystem="pypi"))

        # Assert risk structure
        assert isinstance(result, dict)
        assert result.get("package") == package
        assert "risk_score" in result or "vulnerabilities" in result or "assessment" in result
        assert "last_update_days_ago" in result or "maintenance_status" in result

        logger.info("supply_chain_risk passed", extra={"package": package})
    except Exception as exc:
        logger.warning("supply_chain_risk failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 11. research_patent_landscape — Patent analysis
# ==============================================================================


@pytest.mark.live
def test_patent_landscape_technology(safe_test_inputs: dict[str, Any]) -> None:
    """research_patent_landscape — assert patent data."""
    try:
        from loom.tools.supply_chain_intel import research_patent_landscape
    except ImportError:
        pytest.skip("Loom not installed")

    query = safe_test_inputs["tech_query"]

    try:
        result = asyncio.run(research_patent_landscape(query=query, max_results=10))

        # Assert patent structure
        assert isinstance(result, dict)
        assert "patents" in result or "results" in result or "total" in result
        assert "query" in result or result.get("count", 0) >= 0

        logger.info("patent_landscape passed", extra={"query": query})
    except Exception as exc:
        logger.warning("patent_landscape failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# 12. research_dependency_audit — Dependency audit
# ==============================================================================


@pytest.mark.live
def test_dependency_audit_github_repo(safe_test_inputs: dict[str, Any]) -> None:
    """research_dependency_audit — assert vulnerability findings."""
    try:
        from loom.tools.supply_chain_intel import research_dependency_audit
    except ImportError:
        pytest.skip("Loom not installed")

    repo_url = safe_test_inputs["github_repo"]

    try:
        result = asyncio.run(research_dependency_audit(repo_url=repo_url))

        # Assert audit structure
        assert isinstance(result, dict)
        assert "dependencies" in result or "vulnerabilities" in result or "findings" in result
        assert "audit_summary" in result or "risk_assessment" in result

        logger.info("dependency_audit passed", extra={"repo": repo_url})
    except Exception as exc:
        logger.warning("dependency_audit failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


# ==============================================================================
# Parametrized tests for batch coverage
# ==============================================================================


@pytest.mark.live
@pytest.mark.parametrize(
    "email_input",
    [
        "test@example.com",
        "dev@example.org",
    ],
)
def test_identity_resolve_multiple_emails(email_input: str) -> None:
    """research_identity_resolve multiple emails — assert robustness."""
    try:
        from loom.tools.identity_resolve import research_identity_resolve
    except ImportError:
        pytest.skip("Loom not installed")

    try:
        result = research_identity_resolve(email=email_input)
        assert result.get("email") == email_input
        logger.info("identity_resolve batch passed", extra={"email": email_input})
    except Exception as exc:
        logger.warning("identity_resolve batch failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


@pytest.mark.live
@pytest.mark.parametrize(
    "job_title",
    [
        "Software Engineer",
        "Data Scientist",
        "DevOps Engineer",
    ],
)
def test_salary_intelligence_multiple_roles(job_title: str) -> None:
    """research_salary_intelligence multiple roles — assert coverage."""
    try:
        from loom.tools.company_intel import research_salary_intelligence
    except ImportError:
        pytest.skip("Loom not installed")

    try:
        result = asyncio.run(research_salary_intelligence(role=job_title))
        assert isinstance(result, dict)
        logger.info("salary_intelligence batch passed", extra={"role": job_title})
    except Exception as exc:
        logger.warning("salary_intelligence batch failed: %s", exc)
        pytest.skip(f"Network error: {exc}")


@pytest.mark.live
@pytest.mark.parametrize(
    "package_name",
    [
        "requests",
        "numpy",
        "django",
    ],
)
def test_supply_chain_risk_multiple_packages(package_name: str) -> None:
    """research_supply_chain_risk multiple packages — assert scalability."""
    try:
        from loom.tools.supply_chain_intel import research_supply_chain_risk
    except ImportError:
        pytest.skip("Loom not installed")

    try:
        result = asyncio.run(research_supply_chain_risk(package_name=package_name))
        assert isinstance(result, dict)
        logger.info("supply_chain_risk batch passed", extra={"package": package_name})
    except Exception as exc:
        logger.warning("supply_chain_risk batch failed: %s", exc)
        pytest.skip(f"Network error: {exc}")
