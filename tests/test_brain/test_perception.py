"""Tests for Brain Perception Layer — Intent parsing and query understanding."""

from __future__ import annotations

import pytest

from loom.brain.perception import parse_intent


class TestParseIntent:
    """Test intent parsing functionality."""

    def test_parse_intent_security_domain(self) -> None:
        """Test security domain detection."""
        result = parse_intent("search for CVE-2024-1234 vulnerability")
        assert "security" in result["domains"]
        assert result["query"] == "search for CVE-2024-1234 vulnerability"

    def test_parse_intent_fetch_domain(self) -> None:
        """Test fetch domain detection."""
        result = parse_intent("fetch the content from https://example.com")
        assert "fetch" in result["domains"]

    def test_parse_intent_url_extraction(self) -> None:
        """Test URL extraction from query."""
        result = parse_intent("analyze https://example.com and https://test.org")
        assert "urls" in result["entities"]
        assert len(result["entities"]["urls"]) == 2

    def test_parse_intent_empty_query(self) -> None:
        """Test empty query handling."""
        result = parse_intent("")
        assert result["query"] == ""
        assert result["domains"] == ["general"]  # Default domain
        assert isinstance(result["keywords"], list)

    def test_parse_intent_whitespace_only(self) -> None:
        """Test whitespace-only query handling."""
        result = parse_intent("   \t\n   ")
        assert result["domains"] == ["general"]

    def test_parse_intent_keyword_extraction(self) -> None:
        """Test keyword extraction for tool matching."""
        result = parse_intent("search for python programming tutorials")
        assert "python" in result["keywords"]
        assert "programming" in result["keywords"]
        assert "tutorials" in result["keywords"]

    def test_parse_intent_stop_words_filtered(self) -> None:
        """Test that stop words are filtered out."""
        result = parse_intent("find the best paper about machine learning")
        # "the" and "about" should be filtered out
        assert "the" not in result["keywords"]
        assert "about" not in result["keywords"]

    def test_parse_intent_multi_step_detection(self) -> None:
        """Test multi-step intent type detection."""
        result = parse_intent("search for papers and then fetch the full text")
        assert result["intent_type"] == "multi_step"

    def test_parse_intent_comparison_detection(self) -> None:
        """Test comparison intent detection."""
        result = parse_intent("compare python vs javascript performance")
        assert result["intent_type"] == "comparison"

    def test_parse_intent_explanation_detection(self) -> None:
        """Test explanation intent detection."""
        result = parse_intent("explain how blockchain works")
        assert result["intent_type"] == "explanation"

    def test_parse_intent_monitoring_detection(self) -> None:
        """Test monitoring intent detection."""
        result = parse_intent("monitor these domains for changes")
        assert result["intent_type"] == "monitoring"

    def test_parse_intent_email_extraction(self) -> None:
        """Test email extraction."""
        result = parse_intent("contact admin@example.com and user@test.org")
        assert "emails" in result["entities"]
        assert len(result["entities"]["emails"]) == 2

    def test_parse_intent_ip_extraction(self) -> None:
        """Test IP address extraction."""
        result = parse_intent("scan 192.168.1.1 and 10.0.0.1")
        assert "ips" in result["entities"]
        assert len(result["entities"]["ips"]) == 2

    def test_parse_intent_domain_extraction(self) -> None:
        """Test domain name extraction."""
        result = parse_intent("check example.com and github.io")
        assert "domains" in result["entities"]
        assert "example.com" in result["entities"]["domains"]

    def test_parse_intent_academic_domain(self) -> None:
        """Test academic domain detection."""
        result = parse_intent("find papers on arxiv about citation networks")
        assert "academic" in result["domains"]

    def test_parse_intent_crypto_domain(self) -> None:
        """Test crypto domain detection."""
        result = parse_intent("trace bitcoin wallet address")
        assert "crypto" in result["domains"]

    def test_parse_intent_privacy_domain(self) -> None:
        """Test privacy domain detection."""
        result = parse_intent("check fingerprinting and tracking techniques")
        assert "privacy" in result["domains"]

    def test_parse_intent_multiple_domains(self) -> None:
        """Test detection of multiple domains in single query."""
        result = parse_intent("find paper about blockchain security")
        assert "academic" in result["domains"]
        assert "crypto" in result["domains"]

    def test_parse_intent_case_insensitive(self) -> None:
        """Test case-insensitive processing."""
        result1 = parse_intent("SEARCH FOR CVE VULNERABILITIES")
        result2 = parse_intent("search for cve vulnerabilities")
        assert "security" in result1["domains"]
        assert "security" in result2["domains"]

    def test_parse_intent_short_words_filtered(self) -> None:
        """Test that short words (len <= 2) are filtered from keywords."""
        result = parse_intent("find it by searching")
        # "it" and "by" are short, should be filtered
        assert all(len(kw) > 2 for kw in result["keywords"])

    def test_parse_intent_single_tool_default(self) -> None:
        """Test that single_tool is default intent type."""
        result = parse_intent("fetch example.com")
        assert result["intent_type"] == "single_tool"
