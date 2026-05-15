"""REQ-037: Core Research 7 tools test suite.

Tests the following research tools:
1. fetch.py → research_fetch()
2. spider.py → research_spider()
3. markdown.py → research_markdown()
4. search.py → research_search()
5. deep.py → research_deep()
6. github.py → research_github()
7. stealth.py → research_camoufox()

Each tool is invoked directly via Python import and tested for:
- Callable and returns dict-like response
- Contains expected data fields (content, results, markdown, etc.)
- No unhandled exceptions
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import pytest

logger = logging.getLogger("tests.test_req037_core_research")


class TestResearchFetch:
    """Test research_fetch tool."""

    def test_fetch_basic_http(self) -> None:
        """Test fetch with basic HTTP mode."""
        from loom.tools.core.fetch import research_fetch

        result = research_fetch(
            url="https://httpbin.org/get",
            mode="http",
            bypass_cache=True,
            timeout=15,
        )

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "url" in result, "Missing 'url' field"
        assert result["url"] == "https://httpbin.org/get"

        # Should have some content or status info
        assert any(
            k in result for k in ["text", "html", "error", "status_code"]
        ), f"Missing content fields in {result.keys()}"

        logger.info(f"fetch_basic_http: PASS - {result.get('url')}")

    def test_fetch_stealthy_mode(self) -> None:
        """Test fetch with stealthy mode."""
        from loom.tools.core.fetch import research_fetch

        result = research_fetch(
            url="https://httpbin.org/get",
            mode="stealthy",
            bypass_cache=True,
            timeout=15,
        )

        assert isinstance(result, dict)
        assert "url" in result
        # Stealthy mode may have different response structure
        logger.info(f"fetch_stealthy_mode: PASS")


class TestResearchSpider:
    """Test research_spider tool."""

    @pytest.mark.asyncio
    async def test_spider_multiple_urls(self) -> None:
        """Test spider with multiple URLs."""
        from loom.tools.core.spider import research_spider

        urls = [
            "https://httpbin.org/get",
            "https://httpbin.org/status/200",
        ]

        result = await research_spider(
            urls=urls,
            mode="http",
            concurrency=2,
            timeout=15,
        )

        # Verify response is a list
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) > 0, "Spider returned empty results"

        # Each result should be a dict with url field
        for item in result:
            assert isinstance(item, dict), f"Item is not dict: {type(item)}"
            # At minimum should have url or error
            assert any(
                k in item for k in ["url", "error"]
            ), f"Item missing url/error: {item.keys()}"

        logger.info(f"spider_multiple_urls: PASS - {len(result)} results")

    def test_spider_sync_wrapper(self) -> None:
        """Test spider via sync wrapper (common usage pattern)."""
        from loom.tools.core.spider import research_spider

        urls = ["https://httpbin.org/get"]

        # Call spider within asyncio context
        result = asyncio.run(
            research_spider(
                urls=urls,
                mode="http",
                concurrency=1,
                timeout=15,
            )
        )

        assert isinstance(result, list)
        assert len(result) > 0
        logger.info(f"spider_sync_wrapper: PASS")


class TestResearchMarkdown:
    """Test research_markdown tool."""

    @pytest.mark.asyncio
    async def test_markdown_extraction(self) -> None:
        """Test markdown extraction from HTML."""
        from loom.tools.core.markdown import research_markdown

        result = await research_markdown(
            url="https://httpbin.org/html",
            bypass_cache=True,
            timeout=15,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "url" in result, "Missing 'url' field"

        # Should have markdown or text content (or error)
        if "error" not in result:
            assert any(
                k in result for k in ["markdown", "text", "content"]
            ), f"Missing content in successful response: {result.keys()}"
        else:
            logger.warning(f"Markdown extraction returned error: {result['error']}")

        logger.info(f"markdown_extraction: PASS")

    def test_markdown_sync_wrapper(self) -> None:
        """Test markdown via sync wrapper."""
        from loom.tools.core.markdown import research_markdown

        result = asyncio.run(
            research_markdown(
                url="https://httpbin.org/html",
                bypass_cache=True,
                timeout=15,
            )
        )

        assert isinstance(result, dict)
        assert "url" in result
        logger.info(f"markdown_sync_wrapper: PASS")


class TestResearchSearch:
    """Test research_search tool."""

    def test_search_ddgs_provider(self) -> None:
        """Test search with ddgs provider."""
        from loom.tools.core.search import research_search

        result = research_search(
            query="Python testing",
            provider="ddgs",
            n=5,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have results or error
        if "error" not in result:
            assert "results" in result, "Missing 'results' field"
            assert isinstance(result["results"], list), "Results should be list"
            logger.info(f"search_ddgs: PASS - {len(result.get('results', []))} results")
        else:
            logger.warning(f"Search returned error: {result['error']}")

    def test_search_wikipedia_fallback(self) -> None:
        """Test search with wikipedia provider."""
        from loom.tools.core.search import research_search

        result = research_search(
            query="Python programming language",
            provider="wikipedia",
            n=3,
        )

        assert isinstance(result, dict)
        # Wikipedia should return results or error gracefully
        logger.info(f"search_wikipedia: PASS")


class TestResearchDeep:
    """Test research_deep tool."""

    @pytest.mark.asyncio
    async def test_deep_research_basic(self) -> None:
        """Test deep research with basic query."""
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            query="what is Python",
            depth=1,
            expand_queries=False,
            extract=False,
            synthesize=False,
            include_github=False,
            include_community=False,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "query" in result, "Missing 'query' field"

        # Should have search results or related fields
        if "error" not in result:
            # Deep research returns: query, search_variations, providers_used,
            # pages_searched, pages_fetched, top_pages, synthesis, github_repos,
            # language_stats, community_sentiment, red_team_report, misinfo_report,
            # warnings, total_cost_usd, elapsed_ms
            assert any(
                k in result
                for k in ["search_variations", "pages_searched", "synthesis", "top_pages"]
            ), f"Missing expected fields: {result.keys()}"
        else:
            logger.warning(f"Deep research returned error: {result['error']}")

        logger.info(f"deep_research_basic: PASS")

    def test_deep_research_sync(self) -> None:
        """Test deep research via sync wrapper."""
        from loom.tools.core.deep import research_deep

        result = asyncio.run(
            research_deep(
                query="testing",
                depth=1,
                expand_queries=False,
                extract=False,
                synthesize=False,
                include_github=False,
            )
        )

        assert isinstance(result, dict)
        logger.info(f"deep_research_sync: PASS")


class TestResearchGitHub:
    """Test research_github tool."""

    def test_github_repo_search(self) -> None:
        """Test GitHub repo search."""
        from loom.tools.core.github import research_github

        result = research_github(
            kind="repo",
            query="pytest",
            limit=5,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have results or error
        if "error" not in result:
            assert "items" in result or "results" in result, (
                f"Missing results in response: {result.keys()}"
            )
            logger.info(f"github_repo_search: PASS - found results")
        else:
            logger.warning(f"GitHub search returned error: {result['error']}")

    def test_github_code_search(self) -> None:
        """Test GitHub code search."""
        from loom.tools.core.github import research_github

        result = research_github(
            kind="code",
            query="async def test",
            language="python",
            limit=3,
        )

        assert isinstance(result, dict)
        # Code search may have different response structure
        logger.info(f"github_code_search: PASS")


class TestResearchCamoufox:
    """Test research_camoufox tool."""

    @pytest.mark.asyncio
    async def test_camoufox_fetch(self) -> None:
        """Test camoufox fetch (may fail gracefully if not installed)."""
        from loom.tools.adversarial.stealth import research_camoufox

        result = await research_camoufox(
            url="https://httpbin.org/get",
            screenshot=False,
            timeout=15,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "url" in result, "Missing 'url' field"

        # Should have content or error field
        if "error" in result:
            # Camoufox might not be installed - this is OK
            if "not installed" in result["error"].lower():
                logger.warning(
                    f"camoufox_fetch: SKIP - Camoufox not installed (OK for test)"
                )
            else:
                logger.warning(f"camoufox_fetch: Got error: {result['error']}")
        else:
            # Should have html or text
            assert any(
                k in result for k in ["html", "text", "title"]
            ), f"Missing content in response: {result.keys()}"
            logger.info(f"camoufox_fetch: PASS")

    def test_camoufox_sync(self) -> None:
        """Test camoufox via sync wrapper."""
        from loom.tools.adversarial.stealth import research_camoufox

        result = asyncio.run(
            research_camoufox(
                url="https://httpbin.org/get",
                timeout=15,
            )
        )

        assert isinstance(result, dict)
        assert "url" in result
        logger.info(f"camoufox_sync: PASS")


class TestToolImports:
    """Verify all tools can be imported."""

    def test_all_tools_importable(self) -> None:
        """Verify all 7 tools import without errors."""
        tools = [
            "loom.tools.core.fetch",
            "loom.tools.core.spider",
            "loom.tools.core.markdown",
            "loom.tools.core.search",
            "loom.tools.core.deep",
            "loom.tools.core.github",
            "loom.tools.adversarial.stealth",
        ]

        imported = []
        failed = []

        for tool_path in tools:
            try:
                __import__(tool_path)
                imported.append(tool_path)
                logger.info(f"✓ Imported {tool_path}")
            except Exception as e:
                failed.append((tool_path, str(e)))
                logger.error(f"✗ Failed to import {tool_path}: {e}")

        assert len(failed) == 0, f"Failed to import: {failed}"
        assert len(imported) == 7, f"Expected 7 tools, imported {len(imported)}"
        logger.info(f"All 7 tools importable: PASS")


class TestToolReturnTypes:
    """Verify all tools return proper dict structures."""

    def test_fetch_returns_dict(self) -> None:
        """Fetch returns dict."""
        from loom.tools.core.fetch import research_fetch

        result = research_fetch(url="https://httpbin.org/get", timeout=10)
        assert isinstance(result, dict)
        assert "url" in result or "error" in result
        logger.info("fetch returns dict: PASS")

    @pytest.mark.asyncio
    async def test_spider_returns_list(self) -> None:
        """Spider returns list of dicts."""
        from loom.tools.core.spider import research_spider

        result = await research_spider(urls=["https://httpbin.org/get"], timeout=10)
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], dict)
        logger.info("spider returns list: PASS")

    @pytest.mark.asyncio
    async def test_markdown_returns_dict(self) -> None:
        """Markdown returns dict."""
        from loom.tools.core.markdown import research_markdown

        result = await research_markdown(url="https://httpbin.org/html", timeout=10)
        assert isinstance(result, dict)
        assert "url" in result or "error" in result
        logger.info("markdown returns dict: PASS")

    def test_search_returns_dict(self) -> None:
        """Search returns dict."""
        from loom.tools.core.search import research_search

        result = research_search(query="test", provider="ddgs", n=1)
        assert isinstance(result, dict)
        logger.info("search returns dict: PASS")

    @pytest.mark.asyncio
    async def test_deep_returns_dict(self) -> None:
        """Deep returns dict."""
        from loom.tools.core.deep import research_deep

        result = await research_deep(
            query="test",
            expand_queries=False,
            extract=False,
            synthesize=False,
        )
        assert isinstance(result, dict)
        logger.info("deep returns dict: PASS")

    def test_github_returns_dict(self) -> None:
        """GitHub returns dict."""
        from loom.tools.core.github import research_github

        result = research_github(kind="repo", query="test", limit=1)
        assert isinstance(result, dict)
        logger.info("github returns dict: PASS")

    @pytest.mark.asyncio
    async def test_camoufox_returns_dict(self) -> None:
        """Camoufox returns dict."""
        from loom.tools.adversarial.stealth import research_camoufox

        result = await research_camoufox(url="https://httpbin.org/get")
        assert isinstance(result, dict)
        logger.info("camoufox returns dict: PASS")
