"""Tests for creative research tools."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_module_cache():
    """Ensure clean import state for each test."""
    sys.modules.pop("loom.tools.creative", None)
    yield
    sys.modules.pop("loom.tools.creative", None)


@pytest.mark.asyncio
class TestCreativeTools:
    async def test_research_red_team_basic(self):
        mock_llm_result = {"text": '["Counter claim 1", "Counter claim 2"]', "cost_usd": 0.01}
        mock_search_result = {
            "results": [
                {"title": "Source 1", "url": "http://source1.com"},
                {"title": "Source 2", "url": "http://source2.com"},
            ]
        }

        with (
            patch("loom.tools.llm.research_llm_chat", return_value=mock_llm_result),
            patch("loom.tools.search.research_search", return_value=mock_search_result),
        ):
            from loom.tools.creative import research_red_team

            result = await research_red_team("Test claim")

        assert "claim" in result
        assert "counter_arguments" in result
        assert "total_cost_usd" in result
        assert len(result["counter_arguments"]) == 2
        assert result["counter_arguments"][0]["evidence_found"] == 2
        assert len(result["counter_arguments"][0]["sources"]) == 2

    async def test_research_red_team_llm_not_available(self):
        with patch.dict("sys.modules", {"loom.tools.llm": None}):
            from loom.tools.creative import research_red_team

            result = await research_red_team("Test claim")
            assert "error" in result

    async def test_research_multilingual_basic(self):
        mock_search_result = {"results": [{"title": "Res 1", "url": "http://res1.com"}]}

        with patch("loom.tools.search.research_search", return_value=mock_search_result):
            from loom.tools.creative import research_multilingual

            result = await research_multilingual("test query", languages=["ar", "es"])

        assert "query" in result
        assert "languages_searched" in result
        assert "results_per_language" in result
        assert "unique_per_language" in result
        assert "total_unique_urls" in result
        assert len(result["results_per_language"]["ar"]) == 1

    async def test_research_consensus_basic(self):
        mock_search_result = {
            "results": [
                {"title": "Consensus Res", "url": "http://consensus.com", "snippet": "snip"}
            ]
        }

        with patch("loom.tools.search.research_search", return_value=mock_search_result):
            from loom.tools.creative import research_consensus

            result = await research_consensus("test query", providers=["exa", "ddgs"])

        assert "query" in result
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["consensus_score"] == 1.0
        assert result["results"][0]["is_singular"] is False

    async def test_research_misinfo_check_basic(self):
        mock_llm_result = {"text": '["False claim 1"]'}
        mock_search_result = {"results": [{"title": "Bad Source", "url": "http://bad.com"}]}

        with (
            patch("loom.tools.llm.research_llm_chat", return_value=mock_llm_result),
            patch("loom.tools.search.research_search", return_value=mock_search_result),
        ):
            from loom.tools.creative import research_misinfo_check

            result = await research_misinfo_check("True claim")

        assert "stress_score" in result
        assert "verdict" in result
        assert result["false_variants_tested"] == 1

    async def test_research_temporal_diff_basic(self):
        mock_wayback = {
            "snapshots": [{"archive_url": "http://archive.com", "timestamp": "20240101"}]
        }
        mock_extract = {"text": "some text content"}
        mock_llm = {"text": "Summary of changes"}

        with (
            patch("loom.tools.enrich.research_wayback", return_value=mock_wayback),
            patch(
                "loom.providers.trafilatura_extract.extract_with_trafilatura",
                return_value=mock_extract,
            ),
            patch("loom.tools.llm.research_llm_chat", return_value=mock_llm),
        ):
            from loom.tools.creative import research_temporal_diff

            result = await research_temporal_diff("http://example.com")

        assert "url" in result
        assert "changes_summary" in result
        assert result["changes_summary"] == "Summary of changes"

    async def test_research_temporal_diff_no_archive(self):
        with patch("loom.tools.enrich.research_wayback", return_value={"snapshots": []}):
            from loom.tools.creative import research_temporal_diff

            result = await research_temporal_diff("http://example.com")

        assert "error" in result

    async def test_research_citation_graph_basic(self):
        mock_search_resp = MagicMock()
        mock_search_resp.json.return_value = {
            "data": [
                {
                    "paperId": "seed1",
                    "title": "Seed Paper",
                    "authors": [{"name": "A1"}],
                    "year": 2024,
                    "citationCount": 10,
                    "url": "url1",
                }
            ]
        }
        mock_search_resp.raise_for_status = MagicMock()
        mock_search_resp.status_code = 200

        mock_cit_resp = MagicMock()
        mock_cit_resp.json.return_value = {
            "data": [
                {
                    "citingPaper": {
                        "paperId": "cit1",
                        "title": "Citing Paper",
                        "authors": [{"name": "A2"}],
                        "year": 2024,
                        "citationCount": 5,
                        "url": "url2",
                    }
                }
            ]
        }
        mock_cit_resp.status_code = 200

        mock_ref_resp = MagicMock()
        mock_ref_resp.json.return_value = {"data": []}
        mock_ref_resp.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def mock_get(url, *args, **kwargs):
            if "/paper/search" in url:
                return mock_search_resp
            if "/citations" in url:
                return mock_cit_resp
            if "/references" in url:
                return mock_ref_resp
            return MagicMock(status_code=404)

        mock_client.get.side_effect = mock_get

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.creative import research_citation_graph

            result = await research_citation_graph("Seed Paper")

        assert "papers" in result
        assert "edges" in result
        assert len(result["papers"]) == 2
        assert len(result["edges"]) == 1

    async def test_research_citation_graph_no_papers(self):
        mock_search_resp = MagicMock()
        mock_search_resp.json.return_value = {"data": []}
        mock_search_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_search_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.creative import research_citation_graph

            result = await research_citation_graph("Unknown Paper")

        assert "error" in result
        assert result["papers"] == []

    async def test_research_ai_detect_basic(self):
        mock_llm = {
            "text": '{"ai_probability": 85, "indicators": ["generic"], "reasoning": "reads like AI"}'
        }

        with patch("loom.tools.llm.research_llm_chat", return_value=mock_llm):
            from loom.tools.creative import research_ai_detect

            result = await research_ai_detect("x" * 150)

        assert "ai_probability" in result
        assert "verdict" in result
        assert result["ai_probability"] == 0.85
        assert result["verdict"] == "likely_ai"

    async def test_research_ai_detect_short_text(self):
        from loom.tools.creative import research_ai_detect

        result = await research_ai_detect("short")
        assert "error" in result

    async def test_research_curriculum_basic(self):
        mock_search = {
            "results": [{"title": "Tutorial", "url": "http://tut.com", "snippet": "abc"}]
        }
        mock_arxiv = {
            "results": [
                {"title": "Paper", "url": "http://arxiv.org/1", "snippet": "xyz", "authors": ["A1"]}
            ]
        }

        with (
            patch("loom.tools.search.research_search", return_value=mock_search),
            patch("loom.providers.arxiv_search.search_arxiv", return_value=mock_arxiv),
        ):
            from loom.tools.creative import research_curriculum

            result = await research_curriculum("Python")

        assert "levels" in result
        assert "beginner" in result["levels"]
        assert "advanced" in result["levels"]

    async def test_research_community_sentiment_basic(self):
        mock_hn = {"results": [{"title": "HN Post", "points": 100}]}
        mock_reddit = {"results": [{"title": "Reddit Post", "score": 200}]}

        with (
            patch("loom.providers.hn_reddit.search_hackernews", return_value=mock_hn),
            patch("loom.providers.hn_reddit.search_reddit", return_value=mock_reddit),
        ):
            from loom.tools.creative import research_community_sentiment

            result = await research_community_sentiment("Rust")

        assert "hackernews" in result
        assert "reddit" in result
        assert "combined_engagement" in result

    async def test_research_wiki_ghost_basic(self):
        mock_search_resp = MagicMock()
        mock_search_resp.json.return_value = ["Topic", ["Article Title"]]
        mock_search_resp.raise_for_status = MagicMock()
        mock_search_resp.status_code = 200

        mock_talk_resp = MagicMock()
        mock_talk_resp.json.return_value = {
            "parse": {"wikitext": {"*": "== Topic 1 ==\nDiscussion here."}}
        }
        mock_talk_resp.status_code = 200

        mock_rev_resp = MagicMock()
        mock_rev_resp.json.return_value = {
            "query": {
                "pages": {
                    "1": {
                        "revisions": [
                            {"timestamp": "2024", "user": "A", "comment": "fix", "size": 10}
                        ]
                    }
                }
            }
        }
        mock_rev_resp.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def mock_get(url, *args, **kwargs):
            params = kwargs.get("params", {})
            action = params.get("action")
            if action == "opensearch":
                return mock_search_resp
            if action == "parse":
                return mock_talk_resp
            if action == "query":
                return mock_rev_resp
            return MagicMock(status_code=404)

        mock_client.get.side_effect = mock_get

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.creative import research_wiki_ghost

            result = await research_wiki_ghost("Test Topic")

        assert "article_title" in result
        assert "talk_sections" in result
        assert "recent_edits" in result
        assert len(result["talk_sections"]) == 1
        assert len(result["recent_edits"]) == 1

    async def test_research_wiki_ghost_not_found(self):
        mock_search_resp = MagicMock()
        mock_search_resp.json.return_value = ["Topic", []]
        mock_search_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_search_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.creative import research_wiki_ghost

            result = await research_wiki_ghost("Unknown Topic")

        assert "error" in result

    async def test_research_semantic_sitemap_basic(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/xml"}
        mock_resp.text = (
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>http://example.com/page1</loc></url>"
            "<url><loc>http://example.com/page2</loc></url>"
            "</urlset>"
        )

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        mock_extract = {"title": "Test Page", "text": "Content"}
        mock_embed = {"embeddings": [[1.0, 0.0], [0.9, 0.1]]}

        with (
            patch("httpx.Client", return_value=mock_client),
            patch(
                "loom.providers.trafilatura_extract.extract_with_trafilatura",
                return_value=mock_extract,
            ),
            patch("loom.tools.llm.research_llm_embed", return_value=mock_embed),
        ):
            from loom.tools.creative import research_semantic_sitemap

            result = await research_semantic_sitemap("example.com", cluster_threshold=0.5)

        assert "clusters" in result
        assert len(result["clusters"]) == 1  # High similarity should cluster them

    async def test_research_semantic_sitemap_no_sitemap(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.tools.creative import research_semantic_sitemap

            result = await research_semantic_sitemap("example.com")

        assert "error" in result
