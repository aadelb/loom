"""Tests for the redesigned research_deep 7-stage pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from loom.tools.deep import _merge_search_results, _normalize_url

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


@pytest.mark.asyncio
class TestResearchDeepPipeline:
    @patch(
        "loom.tools.deep.research_markdown", new_callable=lambda: lambda *a, **kw: _mock_markdown
    )
    @patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch)
    @patch("loom.tools.deep.research_search", side_effect=_mock_search)
    @patch("loom.tools.deep.get_config", return_value=_MOCK_CONFIG)
    async def test_full_pipeline_return_shape(self, mock_config, mock_search, mock_fetch, mock_md):
        with (
            patch("loom.tools.llm.research_llm_query_expand", side_effect=_mock_query_expand),
            patch("loom.tools.llm.research_llm_extract", side_effect=_mock_extract),
            patch("loom.tools.llm.research_llm_answer", side_effect=_mock_answer),
        ):
            from loom.tools.deep import research_deep

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

    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_no_search_results(self, mock_config):
        with patch(
            "loom.tools.deep.research_search", return_value={"provider": "exa", "results": []}
        ):
            from loom.tools.deep import research_deep

            result = await research_deep("empty query", depth=1, expand_queries=False)

        assert result["pages_fetched"] == 0
        assert result["top_pages"] == []
        assert "error" in result

    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_backward_compat_old_params(self, mock_config):
        with (
            patch("loom.tools.deep.research_search", side_effect=_mock_search),
            patch("loom.tools.deep.research_markdown", side_effect=_mock_markdown),
            patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch),
        ):
            from loom.tools.deep import research_deep

            result = await research_deep(
                "test", depth=1, expand_queries=False, extract=False, synthesize=False
            )

        assert "top_pages" in result
        assert "pages_fetched" in result

    @patch("loom.config.get_config", return_value=_MOCK_CONFIG)
    async def test_graceful_degradation_no_llm(self, mock_config):
        with (
            patch("loom.tools.deep.research_search", side_effect=_mock_search),
            patch("loom.tools.deep.research_markdown", side_effect=_mock_markdown),
            patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch),
        ):
            from loom.tools.deep import research_deep

            result = await research_deep(
                "test", depth=1, expand_queries=True, extract=True, synthesize=True
            )

        assert result["synthesis"] is None or isinstance(result["synthesis"], dict)

    @patch(
        "loom.config.get_config",
        return_value={**_MOCK_CONFIG, "RESEARCH_SEARCH_PROVIDERS": ["exa", "brave"]},
    )
    async def test_multi_provider_dedup(self, mock_config):
        call_count = {"n": 0}

        def multi_search(query, **kwargs):
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

        with (
            patch("loom.tools.deep.research_search", side_effect=multi_search),
            patch("loom.tools.deep.research_markdown", side_effect=_mock_markdown),
            patch("loom.tools.deep.research_fetch", side_effect=_mock_fetch),
        ):
            from loom.tools.deep import research_deep

            result = await research_deep(
                "test", depth=2, expand_queries=False, extract=False, synthesize=False
            )

        urls = [p["url"] for p in result["top_pages"]]
        assert len(set(urls)) == len(urls)
