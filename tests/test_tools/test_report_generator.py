"""Unit tests for report_generator tool — automated research report generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.tools.report_generator import (
    _arxiv_recent,
    _generate_markdown_report,
    _hackernews_discussion,
    _semantic_scholar_papers,
    _wikipedia_overview,
    research_generate_report,
)


class TestWikipediaOverview:
    """_wikipedia_overview extracts topic overview."""

    def test_valid_wikipedia_response(self) -> None:
        """Parse Wikipedia response and extract overview."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            wiki_data = {
                "query": {
                    "pages": {
                        "123": {
                            "title": "Transformers",
                            "extract": "Transformers are a type of neural network architecture introduced in 2017. They are based on self-attention mechanisms and have become the foundation for many modern language models.",
                        }
                    }
                }
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = wiki_data
            mock_client.get.return_value = mock_response

            result = await _wikipedia_overview(mock_client, "Transformers")
            assert result["title"] == "Transformers"
            assert "Transformers" in result["overview"]
            assert result["source"] == "wikipedia"

        asyncio.run(test())

    def test_empty_wikipedia_response(self) -> None:
        """Handle missing Wikipedia page gracefully."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            wiki_data = {"query": {"pages": {}}}

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = wiki_data
            mock_client.get.return_value = mock_response

            result = await _wikipedia_overview(mock_client, "XYZTopic")
            assert result["overview"] == ""
            assert result["source"] == "wikipedia"

        asyncio.run(test())


class TestSemanticScholarPapers:
    """_semantic_scholar_papers extracts key papers."""

    def test_valid_scholar_response(self) -> None:
        """Parse Semantic Scholar response with papers."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            scholar_data = {
                "data": [
                    {
                        "title": "Attention is All You Need",
                        "year": 2017,
                        "citationCount": 50000,
                        "authors": [
                            {"name": "Vaswani"},
                            {"name": "Shazeer"},
                        ],
                        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks",
                    },
                    {
                        "title": "BERT: Pre-training",
                        "year": 2018,
                        "citationCount": 30000,
                        "authors": [
                            {"name": "Devlin"},
                        ],
                        "abstract": "We introduce BERT a new method of pre-training language models",
                    },
                ]
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = scholar_data
            mock_client.get.return_value = mock_response

            result = await _semantic_scholar_papers(mock_client, "transformers")
            assert len(result["papers"]) == 2
            assert result["papers"][0]["title"] == "Attention is All You Need"
            assert result["papers"][0]["citations"] == 50000
            assert result["source"] == "semantic_scholar"

        asyncio.run(test())

    def test_empty_scholar_response(self) -> None:
        """Handle empty Semantic Scholar response."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            scholar_data = {"data": []}

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = scholar_data
            mock_client.get.return_value = mock_response

            result = await _semantic_scholar_papers(mock_client, "xyz")
            assert result["papers"] == []
            assert result["source"] == "semantic_scholar"

        asyncio.run(test())


class TestArxivRecent:
    """_arxiv_recent extracts recent papers from arXiv."""

    def test_valid_arxiv_response(self) -> None:
        """Parse arXiv XML and extract recent papers."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <title>Neural Networks and Deep Learning</title>
        <summary>A comprehensive overview of neural network architectures</summary>
        <updated>2026-06-15T10:30:00Z</updated>
        <author>
            <name>John Doe</name>
        </author>
        <author>
            <name>Jane Smith</name>
        </author>
    </entry>
</feed>"""

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = arxiv_xml
            mock_client.get.return_value = mock_response

            result = await _arxiv_recent(mock_client, "neural networks")
            assert len(result["papers"]) == 1
            assert "Neural Networks" in result["papers"][0]["title"]
            assert result["papers"][0]["date"] == "2026-06-15"
            assert "John Doe" in result["papers"][0]["authors"]
            assert result["source"] == "arxiv"

        asyncio.run(test())

    def test_empty_arxiv_response(self) -> None:
        """Handle empty arXiv response."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = arxiv_xml
            mock_client.get.return_value = mock_response

            result = await _arxiv_recent(mock_client, "xyz")
            assert result["papers"] == []
            assert result["source"] == "arxiv"

        asyncio.run(test())


class TestHackernewsDiscussion:
    """_hackernews_discussion extracts community discussions."""

    def test_valid_hn_response(self) -> None:
        """Parse HackerNews response with discussions."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            hn_data = {
                "hits": [
                    {
                        "title": "New AI breakthrough announced",
                        "points": 500,
                        "num_comments": 150,
                        "url": "https://example.com/ai-breakthrough",
                        "author": "user1",
                    },
                    {
                        "title": "Machine Learning best practices",
                        "points": 350,
                        "num_comments": 80,
                        "url": "https://example.com/ml-practices",
                        "author": "user2",
                    },
                ]
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = hn_data
            mock_client.get.return_value = mock_response

            result = await _hackernews_discussion(mock_client, "ai")
            assert len(result["discussions"]) == 2
            assert result["discussions"][0]["points"] == 500
            assert "AI breakthrough" in result["discussions"][0]["title"]
            assert result["source"] == "hackernews"

        asyncio.run(test())

    def test_empty_hn_response(self) -> None:
        """Handle empty HackerNews response."""
        import asyncio
        from unittest.mock import AsyncMock

        import httpx

        async def test():
            mock_client = AsyncMock(spec=httpx.AsyncClient)

            hn_data = {"hits": []}

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = hn_data
            mock_client.get.return_value = mock_response

            result = await _hackernews_discussion(mock_client, "xyz")
            assert result["discussions"] == []
            assert result["source"] == "hackernews"

        asyncio.run(test())


class TestGenerateMarkdownReport:
    """_generate_markdown_report creates formatted markdown."""

    def test_generates_valid_markdown(self) -> None:
        """Generate markdown with all sections."""
        sections_data = {
            "overview": {
                "title": "Transformers",
                "overview": "Transformers are neural network architectures.",
                "source": "wikipedia",
            },
            "key_papers": {
                "papers": [
                    {
                        "title": "Attention is All You Need",
                        "year": 2017,
                        "citations": 50000,
                        "authors": ["Vaswani", "Shazeer"],
                        "summary": "The transformer architecture",
                    }
                ],
                "source": "semantic_scholar",
            },
            "recent_developments": {
                "papers": [
                    {
                        "title": "New Transformer Variant",
                        "date": "2026-06-15",
                        "authors": ["Smith"],
                        "summary": "A new approach",
                    }
                ],
                "source": "arxiv",
            },
            "community_discussion": {
                "discussions": [
                    {
                        "title": "Transformers discussion",
                        "points": 200,
                        "comments": 50,
                        "url": "https://example.com",
                    }
                ],
                "source": "hackernews",
            },
        }

        markdown = _generate_markdown_report("Transformers", "standard", sections_data)

        assert "# Research Report: Transformers" in markdown
        assert "## Overview" in markdown
        assert "## Key Papers" in markdown
        assert "## Recent Developments" in markdown
        assert "## Community Discussion" in markdown
        assert "Transformers are neural network architectures" in markdown

    def test_markdown_with_empty_sections(self) -> None:
        """Generate markdown gracefully with empty sections."""
        sections_data = {
            "overview": {"title": "Test", "overview": "", "source": "wikipedia"},
            "key_papers": {"papers": [], "source": "semantic_scholar"},
            "recent_developments": {"papers": [], "source": "arxiv"},
            "community_discussion": {"discussions": [], "source": "hackernews"},
        }

        markdown = _generate_markdown_report("Test", "brief", sections_data)

        assert "# Research Report: Test" in markdown
        assert "# Research Report: Test" in markdown  # Main header always exists


@pytest.mark.asyncio
class TestResearchGenerateReport:
    """research_generate_report main function."""

    async def test_full_report_generation(self) -> None:
        """Generate complete research report with all sources."""
        with patch("loom.tools.report_generator._wikipedia_overview") as mock_wiki:
            with patch(
                "loom.tools.report_generator._semantic_scholar_papers"
            ) as mock_scholar:
                with patch(
                    "loom.tools.report_generator._arxiv_recent"
                ) as mock_arxiv:
                    with patch(
                        "loom.tools.report_generator._hackernews_discussion"
                    ) as mock_hn:
                        mock_wiki.return_value = {
                            "title": "Transformers",
                            "overview": "Transformer networks are the foundation of modern AI.",
                            "source": "wikipedia",
                        }
                        mock_scholar.return_value = {
                            "papers": [
                                {
                                    "title": "Attention is All You Need",
                                    "year": 2017,
                                    "citations": 50000,
                                    "authors": ["Vaswani"],
                                    "summary": "The transformer architecture",
                                }
                            ],
                            "source": "semantic_scholar",
                        }
                        mock_arxiv.return_value = {
                            "papers": [
                                {
                                    "title": "New Transformer",
                                    "date": "2026-06-15",
                                    "authors": ["Smith"],
                                    "summary": "Recent work",
                                }
                            ],
                            "source": "arxiv",
                        }
                        mock_hn.return_value = {
                            "discussions": [
                                {
                                    "title": "Transformers discussion",
                                    "points": 200,
                                    "comments": 50,
                                    "url": "https://example.com",
                                    "author": "user1",
                                }
                            ],
                            "source": "hackernews",
                        }

                        result = await research_generate_report("transformers")

                        assert result["topic"] == "transformers"
                        assert "sections" in result
                        assert len(result["sections"]) > 0
                        assert "markdown_report" in result
                        assert "generated_at" in result
                        assert "total_sources" in result
                        assert result["total_sources"] >= 1
                        assert "word_count" in result
                        assert result["word_count"] > 0

    async def test_report_with_deep_depth(self) -> None:
        """Generate report with deep depth level."""
        with patch("loom.tools.report_generator._wikipedia_overview") as mock_wiki:
            with patch(
                "loom.tools.report_generator._semantic_scholar_papers"
            ) as mock_scholar:
                with patch(
                    "loom.tools.report_generator._arxiv_recent"
                ) as mock_arxiv:
                    with patch(
                        "loom.tools.report_generator._hackernews_discussion"
                    ) as mock_hn:
                        mock_wiki.return_value = {
                            "title": "AI",
                            "overview": "Artificial intelligence overview",
                            "source": "wikipedia",
                        }
                        mock_scholar.return_value = {
                            "papers": [],
                            "source": "semantic_scholar",
                        }
                        mock_arxiv.return_value = {
                            "papers": [],
                            "source": "arxiv",
                        }
                        mock_hn.return_value = {
                            "discussions": [],
                            "source": "hackernews",
                        }

                        result = await research_generate_report("ai", depth="deep")

                        assert result["depth"] == "deep"
                        assert "Open Questions" in result["markdown_report"]

    async def test_report_with_brief_depth(self) -> None:
        """Generate brief report with minimal content."""
        with patch("loom.tools.report_generator._wikipedia_overview") as mock_wiki:
            with patch(
                "loom.tools.report_generator._semantic_scholar_papers"
            ) as mock_scholar:
                with patch(
                    "loom.tools.report_generator._arxiv_recent"
                ) as mock_arxiv:
                    with patch(
                        "loom.tools.report_generator._hackernews_discussion"
                    ) as mock_hn:
                        mock_wiki.return_value = {
                            "title": "Topic",
                            "overview": "Brief overview",
                            "source": "wikipedia",
                        }
                        mock_scholar.return_value = {
                            "papers": [],
                            "source": "semantic_scholar",
                        }
                        mock_arxiv.return_value = {
                            "papers": [],
                            "source": "arxiv",
                        }
                        mock_hn.return_value = {
                            "discussions": [],
                            "source": "hackernews",
                        }

                        result = await research_generate_report("topic", depth="brief")

                        assert result["depth"] == "brief"
                        assert "# Research Report: topic" in result["markdown_report"]

    async def test_report_sources_used_tracked(self) -> None:
        """Track which sources were used in report."""
        with patch("loom.tools.report_generator._wikipedia_overview") as mock_wiki:
            with patch(
                "loom.tools.report_generator._semantic_scholar_papers"
            ) as mock_scholar:
                with patch(
                    "loom.tools.report_generator._arxiv_recent"
                ) as mock_arxiv:
                    with patch(
                        "loom.tools.report_generator._hackernews_discussion"
                    ) as mock_hn:
                        mock_wiki.return_value = {
                            "title": "Test",
                            "overview": "Test overview",
                            "source": "wikipedia",
                        }
                        mock_scholar.return_value = {
                            "papers": [{"title": "Paper", "year": 2020, "citations": 10, "authors": [], "summary": ""}],
                            "source": "semantic_scholar",
                        }
                        mock_arxiv.return_value = {
                            "papers": [],
                            "source": "arxiv",
                        }
                        mock_hn.return_value = {
                            "discussions": [],
                            "source": "hackernews",
                        }

                        result = await research_generate_report("test")

                        assert "sources_used" in result
                        assert "wikipedia" in result["sources_used"]
                        assert "semantic_scholar" in result["sources_used"]
