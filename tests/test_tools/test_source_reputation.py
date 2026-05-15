"""Tests for source reputation scoring."""
from __future__ import annotations

import pytest

from loom.tools.research.source_reputation import (
    BLOCKLIST,
    HIGH_QUALITY,
    TLD_SCORES,
    filter_by_reputation,
    research_source_reputation,
    score_source,
)


class TestScoreSource:
    """Tests for score_source function."""

    def test_blocked_domain(self):
        """Blocklisted domains get score 0."""
        assert score_source("https://spam-site.com/page") == 0
        assert score_source("https://malware-domain.xyz") == 0
        assert score_source("https://phishing-example.tk") == 0

    def test_high_quality_domains(self):
        """High-quality domains get score 95."""
        assert score_source("https://arxiv.org/paper") == 95
        assert score_source("https://github.com/repo") == 95
        assert score_source("https://wikipedia.org/article") == 95
        assert score_source("https://scholar.google.com/search") == 95

    def test_high_quality_subdomains(self):
        """Subdomains of high-quality domains get score 95."""
        assert score_source("https://example.mit.edu/research") == 95
        assert score_source("https://pages.stanford.edu/course") == 95

    def test_tld_scoring(self):
        """TLD-based scoring works correctly."""
        # .edu gets 85
        assert score_source("https://university.edu/page") == 85
        # .gov gets 90
        assert score_source("https://agency.gov/page") == 90
        # .org gets 70
        assert score_source("https://nonprofit.org/page") == 70
        # .com gets 50
        assert score_source("https://example.com/page") == 50

    def test_unknown_tld_default(self):
        """Unknown TLDs get default score of 50."""
        assert score_source("https://example.unknown/page") == 50

    def test_invalid_url_default(self):
        """Invalid URLs get default score of 30."""
        assert score_source("not a valid url") == 30
        assert score_source("") == 30

    def test_www_prefix_stripped(self):
        """www prefix is stripped for domain comparison."""
        assert score_source("https://www.arxiv.org/paper") == 95
        assert score_source("https://www.github.com/repo") == 95

    def test_case_insensitivity(self):
        """Domain comparison is case-insensitive."""
        assert score_source("https://ARXIV.ORG/paper") == 95
        assert score_source("https://SPAM-SITE.COM/page") == 0


class TestFilterByReputation:
    """Tests for filter_by_reputation function."""

    def test_filter_empty_list(self):
        """Empty result list returns empty."""
        assert filter_by_reputation([]) == []

    def test_filter_adds_reputation_score(self):
        """Each result gets a reputation_score field."""
        results = [{"url": "https://arxiv.org/paper"}]
        filtered = filter_by_reputation(results)
        assert len(filtered) == 1
        assert "reputation_score" in filtered[0]
        assert filtered[0]["reputation_score"] == 95

    def test_filter_removes_low_scores(self):
        """Results below min_score are filtered out."""
        results = [
            {"url": "https://arxiv.org/paper"},  # 95
            {"url": "https://spam-site.com/junk"},  # 0
            {"url": "https://example.tk/page"},  # 10
        ]
        filtered = filter_by_reputation(results, min_score=30)
        assert len(filtered) == 1
        assert filtered[0]["url"] == "https://arxiv.org/paper"

    def test_filter_keeps_threshold_match(self):
        """Results at min_score are kept."""
        results = [{"url": "https://example.gov/page"}]  # 90
        filtered = filter_by_reputation(results, min_score=90)
        assert len(filtered) == 1
        assert filtered[0]["reputation_score"] == 90

    def test_filter_with_link_field(self):
        """filter_by_reputation works with 'link' field as fallback."""
        results = [{"link": "https://arxiv.org/paper", "title": "Paper"}]
        filtered = filter_by_reputation(results)
        assert len(filtered) == 1
        assert "reputation_score" in filtered[0]

    def test_filter_preserves_other_fields(self):
        """Filtering preserves existing fields in results."""
        results = [
            {"url": "https://arxiv.org/paper", "title": "Paper", "source": "test"}
        ]
        filtered = filter_by_reputation(results)
        assert filtered[0]["title"] == "Paper"
        assert filtered[0]["source"] == "test"

    def test_filter_mixed_scores(self):
        """Filters correctly with mixed result scores."""
        results = [
            {"url": "https://arxiv.org/paper", "title": "A"},  # 95
            {"url": "https://example.com/page", "title": "B"},  # 50
            {"url": "https://example.gov/page", "title": "C"},  # 90
            {"url": "https://spam-site.com", "title": "D"},  # 0
        ]
        filtered = filter_by_reputation(results, min_score=60)
        assert len(filtered) == 2
        assert filtered[0]["title"] == "A"
        assert filtered[1]["title"] == "C"


class TestResearchSourceReputation:
    """Tests for research_source_reputation async function."""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """research_source_reputation returns dict with expected fields."""
        result = await research_source_reputation("https://arxiv.org/paper")
        assert isinstance(result, dict)
        assert "url" in result
        assert "domain" in result
        assert "reputation_score" in result
        assert "blocked" in result
        assert "high_quality" in result

    @pytest.mark.asyncio
    async def test_high_quality_detection(self):
        """High-quality domains are flagged correctly."""
        result = await research_source_reputation("https://arxiv.org/paper")
        assert result["reputation_score"] == 95
        assert result["high_quality"] is True
        assert result["blocked"] is False

    @pytest.mark.asyncio
    async def test_blocked_detection(self):
        """Blocked domains are flagged correctly."""
        result = await research_source_reputation("https://spam-site.com/page")
        assert result["reputation_score"] == 0
        assert result["blocked"] is True
        assert result["high_quality"] is False

    @pytest.mark.asyncio
    async def test_domain_extraction(self):
        """Domain is correctly extracted from URL."""
        result = await research_source_reputation("https://www.example.org/path")
        assert result["domain"] == "example.org"
        assert result["url"] == "https://www.example.org/path"

    @pytest.mark.asyncio
    async def test_score_threshold_for_high_quality_flag(self):
        """high_quality flag is True for scores >= 80."""
        # .gov gets 90
        result = await research_source_reputation("https://example.gov/page")
        assert result["reputation_score"] == 90
        assert result["high_quality"] is True

        # .com gets 50
        result = await research_source_reputation("https://example.com/page")
        assert result["reputation_score"] == 50
        assert result["high_quality"] is False


class TestConstants:
    """Tests for module constants."""

    def test_blocklist_is_frozen_set(self):
        """BLOCKLIST is immutable."""
        assert isinstance(BLOCKLIST, frozenset)
        assert "spam-site.com" in BLOCKLIST

    def test_high_quality_is_frozen_set(self):
        """HIGH_QUALITY is immutable."""
        assert isinstance(HIGH_QUALITY, frozenset)
        assert "arxiv.org" in HIGH_QUALITY

    def test_tld_scores_dict(self):
        """TLD_SCORES has expected entries."""
        assert TLD_SCORES[".edu"] == 85
        assert TLD_SCORES[".gov"] == 90
        assert TLD_SCORES[".com"] == 50
