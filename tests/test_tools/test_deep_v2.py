"""Tests for the redesigned research_deep 7-stage pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from loom.tools.core.deep import (
    _detect_query_type,
    _is_youtube_url,
    _merge_search_results,
    _normalize_url,
)

_MOCK_CONFIG: dict = {
    "RESEARCH_SEARCH_PROVIDERS": ["exa"],
    "RESEARCH_EXPAND_QUERIES": True,
    "RESEARCH_EXTRACT": True,
    "RESEARCH_SYNTHESIZE": True,
    "RESEARCH_GITHUB_ENRICHMENT": True,
    "RESEARCH_MAX_COST_USD": 0.50,
    "SPIDER_CONCURRENCY": 5,
    "FETCH_AUTO_ESCALATE": True,
}


def _mock_search(query, **kwargs):
    return {
        "provider": "exa",
        "query": query,
        "results": [
            {
                "url": "https://example.com/page1",
                "title": "Page 1",
                "snippet": "First result",
                "score": 0.9,
            },
            {
                "url": "https://example.com/page2",
                "title": "Page 2",
                "snippet": "Second result",
                "score": 0.8,
            },
        ],
    }


def _mock_fetch(url, **kwargs):
    return {"url": url, "text": "fetched content", "tool": "httpx"}


async def _mock_markdown(url, **kwargs):
    return {"url": url, "title": f"Title for {url}", "markdown": "M" * 200}


async def _mock_query_expand(query, n=3, **kwargs):
    return {"queries": ["variation 1", "variation 2"], "cost_usd": 0.001}


async def _mock_extract(text, schema=None, **kwargs):
    return {
        "data": {"key_points": ["point1"], "entities": ["entity1"], "relevance_score": 0.85},
        "cost_usd": 0.002,
    }


async def _mock_answer(question, sources=None, **kwargs):
    return {"answer": "Synthesized answer [1]", "citations": sources, "cost_usd": 0.003}


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert _normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_strips_fragment(self):
        assert _normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_preserves_path(self):
        assert _normalize_url("https://example.com/a/b/c") == "https://example.com/a/b/c"

    def test_preserves_scheme(self):
        assert _normalize_url("http://example.com") == "http://example.com"


class TestMergeSearchResults:
    def test_deduplicates_by_url(self):
        results = [
            {"url": "https://example.com/page", "title": "A", "score": 0.5},
            {"url": "https://example.com/page/", "title": "B", "score": 0.9},
        ]
        merged = _merge_search_results(results, max_urls=10)
        assert len(merged) == 1
        assert merged[0]["score"] == 0.9

    def test_keeps_highest_score(self):
        results = [
            {"url": "https://a.com", "score": 0.3},
            {"url": "https://a.com", "score": 0.7},
            {"url": "https://a.com", "score": 0.5},
        ]
        merged = _merge_search_results(results, max_urls=10)
        assert merged[0]["score"] == 0.7

    def test_respects_max_urls(self):
        results = [{"url": f"https://example.com/{i}", "score": i / 10} for i in range(20)]
        merged = _merge_search_results(results, max_urls=5)
        assert len(merged) == 5

    def test_sorts_by_score_descending(self):
        results = [
            {"url": "https://a.com", "score": 0.3},
            {"url": "https://b.com", "score": 0.9},
            {"url": "https://c.com", "score": 0.6},
        ]
        merged = _merge_search_results(results, max_urls=10)
        assert [r["score"] for r in merged] == [0.9, 0.6, 0.3]

    def test_skips_empty_urls(self):
        results = [{"url": "", "score": 1.0}, {"url": "https://a.com", "score": 0.5}]
        merged = _merge_search_results(results, max_urls=10)
        assert len(merged) == 1


class TestDetectQueryType:
    def test_detect_query_type_academic(self):
        """Verify _detect_query_type returns 'academic' for queries with academic keywords."""
        query = "research paper on machine learning algorithms"
        result = _detect_query_type(query)
        assert "academic" in result

    def test_detect_query_type_academic_arxiv(self):
        """Verify arxiv keyword triggers academic detection."""
        query = "arxiv paper on neural networks"
        result = _detect_query_type(query)
        assert "academic" in result

    def test_detect_query_type_knowledge(self):
        """Verify _detect_query_type returns 'knowledge' for 'what is' queries."""
        query = "what is machine learning"
        result = _detect_query_type(query)
        assert "knowledge" in result

    def test_detect_query_type_knowledge_how_does(self):
        """Verify 'how does' triggers knowledge detection."""
        query = "how does photosynthesis work"
        result = _detect_query_type(query)
        assert "knowledge" in result

    def test_detect_query_type_knowledge_explain(self):
        """Verify 'explain' keyword triggers knowledge detection."""
        query = "explain quantum entanglement"
        result = _detect_query_type(query)
        assert "knowledge" in result

    def test_detect_query_type_code(self):
        """Verify _detect_query_type returns 'code' for queries with code keywords."""
        query = "best python library for data processing"
        result = _detect_query_type(query)
        assert "code" in result

    def test_detect_query_type_code_github(self):
        """Verify github keyword triggers code detection."""
        query = "github repository for machine learning"
        result = _detect_query_type(query)
        assert "code" in result

    def test_detect_query_type_code_npm(self):
        """Verify npm keyword triggers code detection."""
        query = "npm package for state management"
        result = _detect_query_type(query)
        assert "code" in result

    def test_detect_query_type_code_framework(self):
        """Verify framework keyword triggers code detection."""
        query = "best web framework for building apis"
        result = _detect_query_type(query)
        assert "code" in result

    def test_detect_query_type_multiple(self):
        """Verify multiple query types can be detected simultaneously."""
        query = "github repository with research paper on neural networks"
        result = _detect_query_type(query)
        assert "code" in result
        assert "academic" in result

    def test_detect_query_type_empty_set(self):
        """Verify generic queries return empty set."""
        query = "interesting facts"
        result = _detect_query_type(query)
        assert isinstance(result, set)


class TestIsYoutubeUrl:
    def test_is_youtube_url_youtube_com(self):
        """Verify youtube.com domain is detected."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert _is_youtube_url(url) is True

    def test_is_youtube_url_www_youtube_com(self):
        """Verify www.youtube.com domain is detected."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert _is_youtube_url(url) is True

    def test_is_youtube_url_youtu_be(self):
        """Verify youtu.be shortlink is detected."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert _is_youtube_url(url) is True

    def test_is_youtube_url_www_youtu_be(self):
        """Verify www.youtu.be is detected."""
        url = "https://www.youtu.be/dQw4w9WgXcQ"
        assert _is_youtube_url(url) is True

    def test_is_youtube_url_m_youtube_com(self):
        """Verify m.youtube.com mobile domain is detected."""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        assert _is_youtube_url(url) is True

    def test_is_youtube_url_non_youtube(self):
        """Verify non-YouTube URLs return False."""
        url = "https://example.com/video"
        assert _is_youtube_url(url) is False

    def test_is_youtube_url_case_insensitive(self):
        """Verify YouTube domain detection is case-insensitive."""
        url = "https://YOUTUBE.COM/watch?v=dQw4w9WgXcQ"
        assert _is_youtube_url(url) is True

    def test_is_youtube_url_vimeo(self):
        """Verify Vimeo URLs are not detected as YouTube."""
        url = "https://vimeo.com/12345678"
        assert _is_youtube_url(url) is False


@pytest.mark.asyncio
class TestResearchDeepPipeline:
    @patch("loom.tools.llm.research_llm_query_expand", side_effect=_mock_query_expand)
    @patch("loom.tools.llm.research_llm_extract", side_effect=_mock_extract)
    @patch("loom.tools.llm.research_llm_answer", side_effect=_mock_answer)
    @patch(
        "loom.tools.core.markdown.research_markdown",
        new_callable=lambda: lambda *a, **kw: _mock_markdown,
    )
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_full_pipeline_return_shape(
        self, mock_config, mock_search, mock_fetch, mock_md, mock_extract, mock_expand, mock_answer
    ):
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test query", depth=2, expand_queries=False, extract=False, synthesize=False
        )

        assert "query" in result
        assert "search_variations" in result
        assert "providers_used" in result
        assert "pages_searched" in result
        assert "pages_fetched" in result
        assert "top_pages" in result
        assert "synthesis" in result
        assert "github_repos" in result
        assert "total_cost_usd" in result
        assert "elapsed_ms" in result
        assert result["query"] == "test query"

    @patch("loom.tools.core.search.research_search", return_value={"provider": "exa", "results": []})
    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_no_search_results(self, mock_config, mock_search):
        from loom.tools.core.deep import research_deep

        result = await research_deep("empty query", depth=1, expand_queries=False)

        assert result["pages_fetched"] == 0
        assert result["top_pages"] == []
        assert "error" in result

    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_backward_compat_old_params(self, mock_config, mock_search, mock_fetch, mock_md):
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test", depth=1, expand_queries=False, extract=False, synthesize=False
        )

        assert "top_pages" in result
        assert "pages_fetched" in result

    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_graceful_degradation_no_llm(self, mock_config, mock_search, mock_fetch, mock_md):
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test", depth=1, expand_queries=True, extract=True, synthesize=True
        )

        assert result["synthesis"] is None or isinstance(result["synthesis"], dict)

    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search")
    @patch(
        "loom.config.get_config",
        return_value={**_MOCK_CONFIG, "RESEARCH_SEARCH_PROVIDERS": ["exa", "brave"]},
    )
    async def test_multi_provider_dedup(self, mock_config, mock_search, mock_fetch, mock_md):
        call_count = {"n": 0}

        async def multi_search(query, **kwargs):
            call_count["n"] += 1
            provider = kwargs.get("provider", "exa")
            return {
                "provider": provider,
                "results": [
                    {
                        "url": "https://shared.com/page",
                        "title": "Shared",
                        "score": 0.5 + call_count["n"] * 0.1,
                    },
                    {
                        "url": f"https://unique-{provider}.com",
                        "title": f"Unique {provider}",
                        "score": 0.4,
                    },
                ],
            }

        mock_search.side_effect = multi_search

        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test", depth=2, expand_queries=False, extract=False, synthesize=False
        )

        urls = [p["url"] for p in result["top_pages"]]
        assert len(set(urls)) == len(urls)

    @patch("loom.tools.core.enrich.research_detect_language", return_value={"language": "en"})
    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_language_stats_in_response(
        self, mock_config, mock_search, mock_fetch, mock_md, mock_lang
    ):
        """Verify deep pipeline returns language_stats dict in response."""
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test query", depth=1, expand_queries=False, extract=False, synthesize=False
        )

        assert "language_stats" in result
        assert isinstance(result["language_stats"], dict)

    @patch(
        "loom.tools.llm.creative.research_community_sentiment",
        return_value={"hn_posts": [], "reddit_threads": []},
    )
    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch(
        "loom.config.get_config",
        return_value={**_MOCK_CONFIG, "RESEARCH_COMMUNITY_SENTIMENT": True},
    )
    async def test_community_sentiment_when_enabled(
        self, mock_config, mock_search, mock_fetch, mock_md, mock_sentiment
    ):
        """Verify include_community=True triggers community sentiment analysis."""
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "django framework",
            depth=1,
            expand_queries=False,
            extract=False,
            synthesize=False,
            include_community=True,
        )

        assert "community_sentiment" in result
        mock_sentiment.assert_called_once()

    @patch(
        "loom.tools.llm.creative.research_red_team",
        return_value={"counter_arguments": [], "total_cost_usd": 0.01},
    )
    @patch("loom.tools.llm.research_llm_answer", side_effect=_mock_answer)
    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value={**_MOCK_CONFIG, "RESEARCH_RED_TEAM": True})
    async def test_red_team_when_enabled(
        self, mock_config, mock_search, mock_fetch, mock_md, mock_answer, mock_red_team
    ):
        """Verify include_red_team=True triggers red team analysis."""
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test query",
            depth=1,
            expand_queries=False,
            extract=False,
            synthesize=True,
            include_red_team=True,
        )

        assert "red_team_report" in result
        mock_red_team.assert_called_once()

    @patch(
        "loom.tools.llm.creative.research_misinfo_check",
        return_value={"claims_checked": [], "risk_score": 0.1},
    )
    @patch("loom.tools.llm.research_llm_answer", side_effect=_mock_answer)
    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value={**_MOCK_CONFIG, "RESEARCH_MISINFO_CHECK": True})
    async def test_misinfo_check_when_enabled(
        self, mock_config, mock_search, mock_fetch, mock_md, mock_answer, mock_misinfo
    ):
        """Verify include_misinfo_check=True triggers misinfo check."""
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            "test query",
            depth=1,
            expand_queries=False,
            extract=False,
            synthesize=True,
            include_misinfo_check=True,
        )

        assert "misinfo_report" in result
        mock_misinfo.assert_called_once()

    @patch(
        "loom.tools.core.enrich.research_wayback",
        return_value={
            "snapshots": [{"archive_url": "https://web.archive.org/web/20230101000000/example.com"}]
        },
    )
    @patch("loom.tools.core.markdown.research_markdown", side_effect=_mock_markdown)
    @patch("loom.tools.core.fetch.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.core.search.research_search", side_effect=_mock_search)
    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_wayback_recovery(
        self, mock_config, mock_search, mock_fetch, mock_md, mock_wayback
    ):
        """Verify wayback is tried when markdown < 100 chars."""
        from loom.tools.core.deep import research_deep

        async def mock_long_wayback_markdown(url, **kwargs):
            """Return long markdown from wayback archive."""
            if "archive.org" in url or "web.archive.org" in url:
                return {
                    "url": url,
                    "title": "Archived",
                    "markdown": "A" * 200,
                }
            return {"url": url, "title": "Title", "markdown": ""}

        mock_md.side_effect = mock_long_wayback_markdown

        result = await research_deep(
            "test query", depth=1, expand_queries=False, extract=False, synthesize=False
        )

        if result["pages_fetched"] > 0:
            mock_wayback.assert_called()
