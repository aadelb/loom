"""Unit tests for deep research query type detection, especially darkweb queries.

Tests cover:
  - Darkweb query detection (tor, onion, hidden service keywords)
  - Finance query detection (crypto, stock keywords)
  - News query detection
  - Code query detection
  - No overlap between query types (specificity)
"""

from __future__ import annotations

from loom.tools.deep import _detect_query_type


class TestQueryTypeDetection:
    """Tests for _detect_query_type function."""

    def test_detect_darkweb_query_tor(self) -> None:
        """Test detection of Tor-related queries."""
        query = "how to access tor hidden service safely"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_darkweb_query_onion(self) -> None:
        """Test detection of .onion domain queries."""
        query = "find onion sites for privacy"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_darkweb_query_darknet(self) -> None:
        """Test detection of darknet queries."""
        query = "darknet marketplace comparison"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_darkweb_query_hidden_service(self) -> None:
        """Test detection of hidden service queries."""
        query = "what are hidden services on the dark web"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_finance_query_bitcoin(self) -> None:
        """Test detection of Bitcoin/crypto queries."""
        query = "bitcoin price today"
        types = _detect_query_type(query)

        assert "finance" in types

    def test_detect_finance_query_ethereum(self) -> None:
        """Test detection of Ethereum queries."""
        query = "ethereum smart contracts explained"
        types = _detect_query_type(query)

        assert "finance" in types

    def test_detect_finance_query_stocks(self) -> None:
        """Test detection of stock market queries."""
        query = "S&P 500 index performance"
        types = _detect_query_type(query)

        assert "finance" in types

    def test_detect_finance_query_crypto_general(self) -> None:
        """Test detection of general cryptocurrency queries."""
        query = "cryptocurrency trading strategies"
        types = _detect_query_type(query)

        assert "finance" in types

    def test_detect_news_query_breaking(self) -> None:
        """Test detection of breaking news queries."""
        query = "breaking news today"
        types = _detect_query_type(query)

        assert "news" in types

    def test_detect_news_query_latest(self) -> None:
        """Test detection of latest news queries."""
        query = "latest technology updates"
        types = _detect_query_type(query)

        assert "news" in types

    def test_detect_news_query_announcement(self) -> None:
        """Test detection of announcement queries."""
        query = "recent company announcements"
        types = _detect_query_type(query)

        assert "news" in types

    def test_detect_code_query_github(self) -> None:
        """Test detection of code/GitHub queries."""
        query = "github open source libraries"
        types = _detect_query_type(query)

        assert "code" in types

    def test_detect_code_query_framework(self) -> None:
        """Test detection of framework queries."""
        query = "react framework documentation"
        types = _detect_query_type(query)

        assert "code" in types

    def test_detect_code_query_package(self) -> None:
        """Test detection of package/module queries."""
        query = "npm package for data visualization"
        types = _detect_query_type(query)

        assert "code" in types

    def test_detect_knowledge_query(self) -> None:
        """Test detection of knowledge queries."""
        query = "what is machine learning"
        types = _detect_query_type(query)

        assert "knowledge" in types

    def test_detect_academic_query_paper(self) -> None:
        """Test detection of academic paper queries."""
        query = "research paper on deep learning"
        types = _detect_query_type(query)

        assert "academic" in types

    def test_detect_academic_query_arxiv(self) -> None:
        """Test detection of arXiv queries."""
        query = "arxiv papers on neural networks"
        types = _detect_query_type(query)

        assert "academic" in types

    def test_detect_multiple_types_darkweb_finance(self) -> None:
        """Test that query can have multiple types (darkweb + finance)."""
        query = "bitcoin transactions on darkweb"
        types = _detect_query_type(query)

        assert "darkweb" in types
        assert "finance" in types

    def test_detect_multiple_types_darkweb_news(self) -> None:
        """Test that query can have darkweb + news types."""
        query = "latest news about tor network"
        types = _detect_query_type(query)

        assert "darkweb" in types
        assert "news" in types

    def test_detect_no_overlap_code_only(self) -> None:
        """Test that code query doesn't overlap with darkweb."""
        query = "github repositories library"
        types = _detect_query_type(query)

        assert "code" in types
        assert "darkweb" not in types

    def test_detect_no_overlap_market_research(self) -> None:
        """Test that 'market' in context doesn't trigger finance for general queries."""
        query = "ancient marketplace architecture"
        types = _detect_query_type(query)

        # Should not have finance because 'market' alone doesn't imply financial context
        # (only 'cryptocurrency', 'stock', 'trading' etc. do)
        assert "finance" not in types

    def test_detect_empty_query(self) -> None:
        """Test detection on empty query."""
        query = ""
        types = _detect_query_type(query)

        assert isinstance(types, set)
        assert len(types) == 0

    def test_detect_case_insensitive_darkweb(self) -> None:
        """Test that darkweb detection is case-insensitive."""
        query = "DARKWEB HIDDEN SERVICES TOR"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_case_insensitive_finance(self) -> None:
        """Test that finance detection is case-insensitive."""
        query = "BITCOIN ETHEREUM CRYPTOCURRENCY"
        types = _detect_query_type(query)

        assert "finance" in types

    def test_detect_onion_extension_detection(self) -> None:
        """Test detection of .onion in query."""
        query = "what domains use .onion"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_deep_web_phrase(self) -> None:
        """Test detection of 'deep web' phrase."""
        query = "deep web vs darkweb explained"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_i2p_query(self) -> None:
        """Test detection of I2P protocol queries."""
        query = "i2p network privacy"
        types = _detect_query_type(query)

        assert "darkweb" in types

    def test_detect_tails_os_query(self) -> None:
        """Test detection of Tails OS queries."""
        query = "tails operating system security"
        types = _detect_query_type(query)

        assert "darkweb" in types
