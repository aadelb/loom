"""Tests for Brain Tool Chains — Pre-defined tool composition patterns."""

from __future__ import annotations

import pytest

from loom.brain.chains import get_chain_tools, match_chain


class TestMatchChain:
    """Test predefined chain matching."""

    def test_match_chain_deep_research(self) -> None:
        """Test matching deep research chain."""
        result = match_chain("deep research on machine learning")
        assert result is not None
        assert result["chain_name"] == "deep_research"
        assert "research_search" in result["tools"]
        assert "research_fetch" in result["tools"]

    def test_match_chain_thorough_investigation(self) -> None:
        """Test matching deep research with alternative trigger."""
        result = match_chain("thorough investigation of blockchain")
        assert result is not None
        assert result["chain_name"] == "deep_research"

    def test_match_chain_security_audit(self) -> None:
        """Test matching security audit chain."""
        result = match_chain("full security scan of example.com")
        assert result is not None
        assert result["chain_name"] == "security_audit"
        assert "research_nuclei_scan" in result["tools"]

    def test_match_chain_comprehensive_scan(self) -> None:
        """Test matching security audit with alternative trigger."""
        result = match_chain("comprehensive scan required")
        assert result is not None
        assert result["chain_name"] == "security_audit"

    def test_match_chain_person_investigation(self) -> None:
        """Test matching person investigation chain."""
        result = match_chain("investigate person John Doe")
        assert result is not None
        assert result["chain_name"] == "person_investigation"
        assert "research_social_graph" in result["tools"]

    def test_match_chain_background_check(self) -> None:
        """Test matching background check variant."""
        result = match_chain("background check on someone")
        assert result is not None
        assert result["chain_name"] == "person_investigation"

    def test_match_chain_domain_recon(self) -> None:
        """Test matching domain reconnaissance chain."""
        result = match_chain("domain intelligence for example.com")
        assert result is not None
        assert result["chain_name"] == "domain_recon"

    def test_match_chain_academic_review(self) -> None:
        """Test matching academic review chain."""
        result = match_chain("review paper quality")
        assert result is not None
        assert result["chain_name"] == "academic_review"

    def test_match_chain_academic_integrity(self) -> None:
        """Test matching academic integrity variant."""
        result = match_chain("check academic integrity")
        assert result is not None
        assert result["chain_name"] == "academic_review"

    def test_match_chain_darkweb_monitoring(self) -> None:
        """Test matching darkweb monitoring chain."""
        result = match_chain("dark web monitor for mentions")
        assert result is not None
        assert result["chain_name"] == "darkweb_monitoring"

    def test_match_chain_content_analysis(self) -> None:
        """Test matching content analysis chain."""
        result = match_chain("analyze this url")
        assert result is not None
        assert result["chain_name"] == "content_analysis"

    def test_match_chain_full_page_analysis(self) -> None:
        """Test matching full page analysis variant."""
        result = match_chain("full page analysis required")
        assert result is not None
        assert result["chain_name"] == "content_analysis"

    def test_match_chain_crypto_investigation(self) -> None:
        """Test matching cryptocurrency investigation chain."""
        result = match_chain("blockchain trace of suspicious activity")
        assert result is not None
        assert result["chain_name"] == "crypto_investigation"

    def test_match_chain_blockchain_trace(self) -> None:
        """Test matching blockchain trace variant."""
        result = match_chain("blockchain trace analysis")
        assert result is not None
        assert result["chain_name"] == "crypto_investigation"

    def test_match_chain_no_match_returns_none(self) -> None:
        """Test that unmatched query returns None."""
        result = match_chain("random query about something else")
        assert result is None

    def test_match_chain_empty_query(self) -> None:
        """Test matching empty query."""
        result = match_chain("")
        assert result is None

    def test_match_chain_case_insensitive(self) -> None:
        """Test case-insensitive matching."""
        result_lower = match_chain("deep research on topic")
        result_upper = match_chain("DEEP RESEARCH ON TOPIC")
        assert (result_lower is None) == (result_upper is None)

    def test_match_chain_partial_trigger(self) -> None:
        """Test that trigger must be contained in query."""
        result = match_chain("please do deep research")
        assert result is not None

    def test_match_chain_returns_structure(self) -> None:
        """Test that matched chain has required structure."""
        result = match_chain("deep research on something")
        assert "chain_name" in result
        assert "tools" in result
        assert "description" in result
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0

    def test_match_chain_priority_first_match(self) -> None:
        """Test that first matching chain is returned."""
        result = match_chain("domain recon for target")
        assert result is not None
        assert result["chain_name"] == "domain_recon"


class TestGetChainTools:
    """Test getting tools from named chains."""

    def test_get_chain_tools_deep_research(self) -> None:
        """Test getting tools for deep_research chain."""
        tools = get_chain_tools("deep_research")
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert "research_search" in tools
        assert "research_fetch" in tools

    def test_get_chain_tools_security_audit(self) -> None:
        """Test getting tools for security_audit chain."""
        tools = get_chain_tools("security_audit")
        assert isinstance(tools, list)
        assert "research_nuclei_scan" in tools
        assert "research_security_headers" in tools
        assert "research_cert_analyze" in tools

    def test_get_chain_tools_person_investigation(self) -> None:
        """Test getting tools for person_investigation chain."""
        tools = get_chain_tools("person_investigation")
        assert isinstance(tools, list)
        assert "research_social_graph" in tools
        assert "research_career_trajectory" in tools
        assert "research_breach_check" in tools

    def test_get_chain_tools_domain_recon(self) -> None:
        """Test getting tools for domain_recon chain."""
        tools = get_chain_tools("domain_recon")
        assert isinstance(tools, list)
        assert len(tools) >= 3

    def test_get_chain_tools_academic_review(self) -> None:
        """Test getting tools for academic_review chain."""
        tools = get_chain_tools("academic_review")
        assert isinstance(tools, list)
        assert "research_citation_analysis" in tools
        assert "research_retraction_check" in tools

    def test_get_chain_tools_darkweb_monitoring(self) -> None:
        """Test getting tools for darkweb_monitoring chain."""
        tools = get_chain_tools("darkweb_monitoring")
        assert isinstance(tools, list)
        assert "research_dark_forum" in tools
        assert "research_leak_scan" in tools

    def test_get_chain_tools_content_analysis(self) -> None:
        """Test getting tools for content_analysis chain."""
        tools = get_chain_tools("content_analysis")
        assert isinstance(tools, list)
        assert "research_fetch" in tools
        assert "research_markdown" in tools

    def test_get_chain_tools_crypto_investigation(self) -> None:
        """Test getting tools for crypto_investigation chain."""
        tools = get_chain_tools("crypto_investigation")
        assert isinstance(tools, list)
        assert "research_crypto_trace" in tools

    def test_get_chain_tools_nonexistent(self) -> None:
        """Test getting tools for nonexistent chain."""
        tools = get_chain_tools("nonexistent_chain")
        assert tools == []

    def test_get_chain_tools_empty_name(self) -> None:
        """Test getting tools with empty chain name."""
        tools = get_chain_tools("")
        assert tools == []

    def test_get_chain_tools_returns_list(self) -> None:
        """Test that result is always a list."""
        tools = get_chain_tools("deep_research")
        assert isinstance(tools, list)

        tools_none = get_chain_tools("nonexistent")
        assert isinstance(tools_none, list)

    def test_get_chain_tools_all_are_strings(self) -> None:
        """Test that all returned tools are strings."""
        tools = get_chain_tools("security_audit")
        assert all(isinstance(t, str) for t in tools)

    def test_match_then_get_chain_tools_consistency(self) -> None:
        """Test consistency between match_chain and get_chain_tools."""
        matched = match_chain("deep research on topic")
        if matched:
            chain_name = matched["chain_name"]
            match_tools = matched["tools"]
            get_tools = get_chain_tools(chain_name)

            # Both should return same tools
            assert match_tools == get_tools
