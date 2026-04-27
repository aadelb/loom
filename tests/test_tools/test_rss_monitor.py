"""Tests for RSS monitoring tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestRssFetch:
    """Tests for research_rss_fetch tool."""

    def test_fetch_rss_2_feed(self):
        """Test fetching and parsing RSS 2.0 feed."""
        rss_content = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <description>A test RSS feed</description>
        <link>https://example.com</link>
        <language>en</language>
        <item>
            <title>Item 1</title>
            <link>https://example.com/item1</link>
            <description>&lt;p&gt;First item&lt;/p&gt;</description>
            <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
            <author>John Doe</author>
            <category>Tech</category>
        </item>
        <item>
            <title>Item 2</title>
            <link>https://example.com/item2</link>
            <description>Second item</description>
            <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>"""

        mock_resp = MagicMock()
        mock_resp.text = rss_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_fetch

            result = research_rss_fetch("https://example.com/feed.xml", max_items=10)

        assert result["format"] == "rss"
        assert result["feed"]["title"] == "Test Feed"
        assert result["feed"]["description"] == "A test RSS feed"
        assert result["feed"]["language"] == "en"
        assert result["item_count"] == 2
        assert len(result["items"]) == 2

        item1 = result["items"][0]
        assert item1["title"] == "Item 1"
        assert item1["link"] == "https://example.com/item1"
        assert item1["author"] == "John Doe"
        assert "First item" in item1["summary"]
        assert "Tech" in item1["categories"]

    def test_fetch_atom_feed(self):
        """Test fetching and parsing Atom feed."""
        atom_content = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">
    <title>Atom Test Feed</title>
    <subtitle>Testing Atom parsing</subtitle>
    <link href="https://example.com/"/>
    <entry>
        <title>Atom Entry 1</title>
        <link href="https://example.com/entry1"/>
        <summary>Entry summary</summary>
        <published>2024-01-01T00:00:00Z</published>
        <author><name>Jane Smith</name></author>
        <category term="Science"/>
    </entry>
</feed>"""

        mock_resp = MagicMock()
        mock_resp.text = atom_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_fetch

            result = research_rss_fetch("https://example.com/atom.xml")

        assert result["format"] == "atom"
        assert result["feed"]["title"] == "Atom Test Feed"
        assert result["item_count"] == 1
        assert result["items"][0]["title"] == "Atom Entry 1"

    def test_fetch_invalid_url(self):
        """Test with invalid URL."""
        from loom.tools.rss_monitor import research_rss_fetch

        result = research_rss_fetch("not a valid url")
        assert "error" in result
        assert result["item_count"] == 0

    def test_fetch_network_error(self):
        """Test handling network errors."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Network error")

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_fetch

            result = research_rss_fetch("https://example.com/feed.xml")

        assert "error" in result
        assert result["item_count"] == 0

    def test_max_items_limit(self):
        """Test max_items parameter limits results."""
        rss_content = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test</title>
        <item><title>1</title></item>
        <item><title>2</title></item>
        <item><title>3</title></item>
        <item><title>4</title></item>
        <item><title>5</title></item>
    </channel>
</rss>"""

        mock_resp = MagicMock()
        mock_resp.text = rss_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_fetch

            result = research_rss_fetch("https://example.com/feed.xml", max_items=2)

        assert result["item_count"] == 2
        assert len(result["items"]) == 2


class TestRssSearch:
    """Tests for research_rss_search tool."""

    def test_search_single_feed(self):
        """Test searching a single RSS feed."""
        rss_content = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Tech News</title>
        <item>
            <title>Python Tips</title>
            <description>Learn Python programming</description>
        </item>
        <item>
            <title>JavaScript Guide</title>
            <description>Master JavaScript basics</description>
        </item>
        <item>
            <title>Python Best Practices</title>
            <description>Advanced Python techniques</description>
        </item>
    </channel>
</rss>"""

        mock_resp = MagicMock()
        mock_resp.text = rss_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_search

            result = research_rss_search(
                ["https://example.com/feed.xml"],
                "Python",
                max_results=10,
            )

        assert result["query"] == "Python"
        assert result["feeds_searched"] == 1
        assert result["total_matches"] == 2
        assert len(result["results"]) == 2

        # Check that results are ranked by relevance
        for r in result["results"]:
            assert "Python" in r["title"] or "Python" in r["summary"]

    def test_search_multiple_feeds(self):
        """Test searching multiple RSS feeds."""
        rss1 = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Feed 1</title>
        <item>
            <title>AI News</title>
            <description>Latest AI developments</description>
        </item>
    </channel>
</rss>"""

        rss2 = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Feed 2</title>
        <item>
            <title>AI Ethics</title>
            <description>Discussing AI ethics and safety</description>
        </item>
    </channel>
</rss>"""

        mock_resp1 = MagicMock()
        mock_resp1.text = rss1
        mock_resp1.raise_for_status = MagicMock()

        mock_resp2 = MagicMock()
        mock_resp2.text = rss2
        mock_resp2.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [mock_resp1, mock_resp2]

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_search

            result = research_rss_search(
                ["https://example.com/feed1.xml", "https://example.com/feed2.xml"],
                "AI",
            )

        assert result["feeds_searched"] == 2
        assert result["total_matches"] == 2

    def test_search_empty_query(self):
        """Test search with empty query."""
        from loom.tools.rss_monitor import research_rss_search

        result = research_rss_search(["https://example.com/feed.xml"], "")
        assert "error" in result
        assert result["total_matches"] == 0

    def test_search_empty_urls(self):
        """Test search with empty URL list."""
        from loom.tools.rss_monitor import research_rss_search

        result = research_rss_search([], "Python")
        assert "error" in result
        assert result["feeds_searched"] == 0

    def test_search_relevance_scoring(self):
        """Test that relevance scoring works correctly."""
        rss_content = """<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test</title>
        <item>
            <title>Python Python Python</title>
            <description>About Python</description>
        </item>
        <item>
            <title>Web Development</title>
            <description>Python frameworks for web development</description>
        </item>
    </channel>
</rss>"""

        mock_resp = MagicMock()
        mock_resp.text = rss_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.rss_monitor import research_rss_search

            result = research_rss_search(
                ["https://example.com/feed.xml"],
                "Python",
            )

        # First result should have higher relevance due to multiple occurrences
        assert result["results"][0]["relevance"] > result["results"][1]["relevance"]
