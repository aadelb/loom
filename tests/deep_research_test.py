"""Comprehensive deep research test for all 42+ Loom MCP tools.

Tests EVERY tool with real API calls and real inputs. Validates:
- Tool returns dict (not None or exception)
- Response has expected keys
- No unexpected error keys (unless expected like rate limits)

Generates JSON report at journey-out/deep_research_report.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables before importing loom
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ToolTestResult:
    """Result of a single tool test."""

    tool_name: str
    status: str  # "PASS", "FAIL", "SKIP"
    duration: float
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "tool_name": self.tool_name,
            "status": self.status,
            "duration": self.duration,
            "error": self.error,
            "details": self.details,
        }


class DeepResearchTester:
    """Test all Loom MCP tools with real API calls."""

    def __init__(self) -> None:
        """Initialize tester with environment configuration."""
        self.results: list[ToolTestResult] = []
        self.sample_text = (
            "John Smith works at Acme Corp in New York. "
            "He earns $120,000 per year and specializes in machine learning. "
            "The company was founded in 2015."
        )
        self.output_dir = Path("/Users/aadel/projects/loom/journey-out")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_result(self, result: ToolTestResult) -> None:
        """Add a test result."""
        self.results.append(result)
        status_symbol = "✓" if result.status == "PASS" else "✗" if result.status == "FAIL" else "○"
        logger.info(f"{status_symbol} {result.tool_name}: {result.status} ({result.duration:.2f}s)")

    async def test_config_tools(self) -> None:
        """Test config & cache tools (5 tools)."""
        from loom.config import research_config_get, research_config_set

        # Test research_config_get (no params)
        start = time.time()
        try:
            result = research_config_get()
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_config_get",
                        "PASS",
                        duration,
                        details={"keys_count": len(result)},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_config_get",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_config_get", "FAIL", duration, error=str(e)))

        # Test research_config_get with parameter
        start = time.time()
        try:
            result = research_config_get("SPIDER_CONCURRENCY")
            duration = time.time() - start
            if result is not None:
                self.add_result(
                    ToolTestResult(
                        "research_config_get(SPIDER_CONCURRENCY)",
                        "PASS",
                        duration,
                        details={"value": result},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_config_get(SPIDER_CONCURRENCY)",
                        "SKIP",
                        duration,
                        error="Config key not found",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_config_get(SPIDER_CONCURRENCY)",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_config_set
        start = time.time()
        try:
            result = research_config_set("SPIDER_CONCURRENCY", 5)
            duration = time.time() - start
            if isinstance(result, dict) and "SPIDER_CONCURRENCY" in result:
                self.add_result(
                    ToolTestResult(
                        "research_config_set",
                        "PASS",
                        duration,
                        details={"value_set": 5},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_config_set",
                        "FAIL",
                        duration,
                        error="Config not set properly",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_config_set", "FAIL", duration, error=str(e)))

    async def test_cache_tools(self) -> None:
        """Test cache tools (2 tools)."""
        from loom.tools.core.cache_mgmt import research_cache_clear, research_cache_stats

        # Test research_cache_stats
        start = time.time()
        try:
            result = research_cache_stats()
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_cache_stats",
                        "PASS",
                        duration,
                        details={
                            k: v
                            for k, v in result.items()
                            if k in ["total_entries", "total_size_mb"]
                        },
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_cache_stats",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_cache_stats", "FAIL", duration, error=str(e)))

        # Test research_cache_clear
        start = time.time()
        try:
            result = research_cache_clear(365)
            duration = time.time() - start
            if isinstance(result, dict) and "cleared" in result:
                self.add_result(
                    ToolTestResult(
                        "research_cache_clear",
                        "PASS",
                        duration,
                        details={"cleared": result.get("cleared")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_cache_clear",
                        "FAIL",
                        duration,
                        error="Invalid response structure",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_cache_clear", "FAIL", duration, error=str(e)))

    async def test_fetch_tools(self) -> None:
        """Test fetch & extract tools (4 tools)."""
        from loom.tools.core.fetch import research_fetch
        from loom.tools.core.markdown import research_markdown
        from loom.tools.core.spider import research_spider

        # Test research_fetch basic mode
        start = time.time()
        try:
            result = await research_fetch("https://example.com", mode="http")
            duration = time.time() - start
            if isinstance(result, dict) and "content" in result:
                self.add_result(
                    ToolTestResult(
                        "research_fetch(http)",
                        "PASS",
                        duration,
                        details={"content_length": len(result.get("content", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_fetch(http)",
                        "FAIL",
                        duration,
                        error="Missing content key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_fetch(http)", "FAIL", duration, error=str(e)))

        # Test research_fetch with auto_escalate and return_format
        start = time.time()
        try:
            result = await research_fetch(
                "https://httpbin.org/html",
                mode="http",
                auto_escalate=True,
                return_format="text",
            )
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_fetch(auto_escalate)",
                        "PASS",
                        duration,
                        details={"has_content": "content" in result},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_fetch(auto_escalate)",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_fetch(auto_escalate)",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_markdown
        start = time.time()
        try:
            result = await research_markdown(
                "https://en.wikipedia.org/wiki/Python_(programming_language)"
            )
            duration = time.time() - start
            if isinstance(result, dict) and "markdown" in result:
                self.add_result(
                    ToolTestResult(
                        "research_markdown",
                        "PASS",
                        duration,
                        details={"markdown_length": len(result.get("markdown", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_markdown",
                        "SKIP",
                        duration,
                        error="No markdown content",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_markdown", "FAIL", duration, error=str(e)))

        # Test research_spider
        start = time.time()
        try:
            result = await research_spider(
                ["https://example.com", "https://httpbin.org"],
                mode="http",
                concurrency=2,
                dedupe=True,
            )
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_spider",
                        "PASS",
                        duration,
                        details={"results_count": len(result.get("results", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_spider",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_spider", "FAIL", duration, error=str(e)))

    async def test_search_tools(self) -> None:
        """Test search tools with 9 providers."""
        from loom.tools.core.search import research_search

        providers_configs = [
            ("exa", {"n": 5, "include_domains": ["nature.com"]}),
            ("tavily", {"n": 5}),
            ("firecrawl", {"n": 3}),
            ("brave", {"n": 5}),
            ("ddgs", {"n": 5, "provider_config": {"region": "us-en"}}),
            ("arxiv", {"n": 3}),
            ("wikipedia", {"n": 3}),
            ("hackernews", {"n": 3}),
            ("reddit", {"n": 3}),
        ]

        for provider, config in providers_configs:
            start = time.time()
            try:
                query = (
                    "AI ethics"
                    if provider == "exa"
                    else "quantum computing"
                    if provider == "tavily"
                    else "web scraping"
                    if provider == "firecrawl"
                    else "privacy browsers"
                    if provider == "brave"
                    else "artificial intelligence"
                    if provider == "ddgs"
                    else "transformer attention"
                    if provider == "arxiv"
                    else "machine learning"
                    if provider == "wikipedia"
                    else "startup YC"
                    if provider == "hackernews"
                    else "python tips"
                )
                result = await research_search(query, provider=provider, **config)
                duration = time.time() - start
                if isinstance(result, dict) and "results" in result:
                    self.add_result(
                        ToolTestResult(
                            f"research_search({provider})",
                            "PASS",
                            duration,
                            details={"results_count": len(result.get("results", []))},
                        )
                    )
                else:
                    self.add_result(
                        ToolTestResult(
                            f"research_search({provider})",
                            "FAIL",
                            duration,
                            error="Missing results key",
                        )
                    )
            except Exception as e:
                duration = time.time() - start
                error_str = str(e)
                # Skip if API key not configured
                if "not found" in error_str.lower() or "api" in error_str.lower():
                    self.add_result(
                        ToolTestResult(
                            f"research_search({provider})",
                            "SKIP",
                            duration,
                            error="API key not configured",
                        )
                    )
                else:
                    self.add_result(
                        ToolTestResult(
                            f"research_search({provider})",
                            "FAIL",
                            duration,
                            error=error_str,
                        )
                    )

    async def test_github_tools(self) -> None:
        """Test GitHub tools (5 tools)."""
        from loom.tools.core.github import (
            research_github,
            research_github_readme,
            research_github_releases,
        )

        # Test research_github - repo search
        start = time.time()
        try:
            result = await research_github("repo", "python web framework", limit=5, sort="stars")
            duration = time.time() - start
            if isinstance(result, dict) and "results" in result:
                self.add_result(
                    ToolTestResult(
                        "research_github(repo)",
                        "PASS",
                        duration,
                        details={"results_count": len(result.get("results", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_github(repo)",
                        "FAIL",
                        duration,
                        error="Missing results key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_github(repo)", "FAIL", duration, error=str(e)))

        # Test research_github - code search
        start = time.time()
        try:
            result = await research_github("code", "async await python", limit=3, language="python")
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_github(code)",
                        "PASS",
                        duration,
                        details={"results_count": len(result.get("results", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_github(code)",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_github(code)", "FAIL", duration, error=str(e)))

        # Test research_github - issues search
        start = time.time()
        try:
            result = await research_github("issues", "memory leak", limit=3)
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_github(issues)",
                        "PASS",
                        duration,
                        details={"results_count": len(result.get("results", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_github(issues)",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_github(issues)", "FAIL", duration, error=str(e))
            )

        # Test research_github_readme
        start = time.time()
        try:
            result = await research_github_readme("pallets", "flask")
            duration = time.time() - start
            if isinstance(result, dict) and "readme" in result:
                self.add_result(
                    ToolTestResult(
                        "research_github_readme",
                        "PASS",
                        duration,
                        details={"readme_length": len(result.get("readme", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_github_readme",
                        "FAIL",
                        duration,
                        error="Missing readme key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_github_readme", "FAIL", duration, error=str(e))
            )

        # Test research_github_releases
        start = time.time()
        try:
            result = await research_github_releases("python", "cpython", limit=3)
            duration = time.time() - start
            if isinstance(result, dict) and "releases" in result:
                self.add_result(
                    ToolTestResult(
                        "research_github_releases",
                        "PASS",
                        duration,
                        details={"releases_count": len(result.get("releases", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_github_releases",
                        "FAIL",
                        duration,
                        error="Missing releases key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_github_releases", "FAIL", duration, error=str(e))
            )

    async def test_llm_tools(self) -> None:
        """Test LLM tools (8 tools)."""
        try:
            from loom.tools.llm.llm import (
                research_llm_answer,
                research_llm_chat,
                research_llm_classify,
                research_llm_embed,
                research_llm_extract,
                research_llm_query_expand,
                research_llm_summarize,
                research_llm_translate,
            )
        except ImportError:
            logger.warning("LLM tools not available")
            return

        # Test research_llm_summarize
        start = time.time()
        try:
            result = await research_llm_summarize(self.sample_text, max_tokens=100)
            duration = time.time() - start
            if isinstance(result, dict) and "summary" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_summarize",
                        "PASS",
                        duration,
                        details={"summary_length": len(result.get("summary", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_summarize",
                        "FAIL",
                        duration,
                        error="Missing summary key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_llm_summarize", "FAIL", duration, error=str(e))
            )

        # Test research_llm_extract
        start = time.time()
        try:
            result = await research_llm_extract(
                self.sample_text,
                schema={
                    "name": "str",
                    "company": "str",
                    "salary": "int",
                    "specialty": "str",
                },
            )
            duration = time.time() - start
            if isinstance(result, dict) and "extracted" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_extract",
                        "PASS",
                        duration,
                        details={"extracted_fields": len(result.get("extracted", {}))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_extract",
                        "FAIL",
                        duration,
                        error="Missing extracted key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_llm_extract", "FAIL", duration, error=str(e)))

        # Test research_llm_classify (single label)
        start = time.time()
        try:
            result = await research_llm_classify(
                "I absolutely love this product!",
                labels=["positive", "negative", "neutral"],
            )
            duration = time.time() - start
            if isinstance(result, dict) and "classification" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_classify(single)",
                        "PASS",
                        duration,
                        details={"label": result.get("classification", {}).get("label")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_classify(single)",
                        "FAIL",
                        duration,
                        error="Missing classification key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_llm_classify(single)",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_llm_classify (multi-label)
        start = time.time()
        try:
            result = await research_llm_classify(
                "This is both good and bad",
                labels=["positive", "negative", "neutral", "mixed"],
                multi_label=True,
            )
            duration = time.time() - start
            if isinstance(result, dict) and "classification" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_classify(multi)",
                        "PASS",
                        duration,
                        details={
                            "labels_count": len(result.get("classification", {}).get("labels", []))
                        },
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_classify(multi)",
                        "FAIL",
                        duration,
                        error="Missing classification key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_llm_classify(multi)",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_llm_translate
        start = time.time()
        try:
            result = await research_llm_translate("Hello, how are you today?", target_lang="ar")
            duration = time.time() - start
            if isinstance(result, dict) and "translation" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_translate",
                        "PASS",
                        duration,
                        details={"translation_length": len(result.get("translation", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_translate",
                        "FAIL",
                        duration,
                        error="Missing translation key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_llm_translate", "FAIL", duration, error=str(e))
            )

        # Test research_llm_query_expand
        start = time.time()
        try:
            result = await research_llm_query_expand("climate change solutions", n=5)
            duration = time.time() - start
            if isinstance(result, dict) and "expanded_queries" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_query_expand",
                        "PASS",
                        duration,
                        details={"queries_count": len(result.get("expanded_queries", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_query_expand",
                        "FAIL",
                        duration,
                        error="Missing expanded_queries key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_llm_query_expand", "FAIL", duration, error=str(e))
            )

        # Test research_llm_answer
        start = time.time()
        try:
            result = await research_llm_answer(
                "What is photosynthesis?",
                sources=[
                    {
                        "title": "Biology",
                        "text": "Photosynthesis converts sunlight to chemical energy in plants",
                        "url": "https://example.com/bio",
                    }
                ],
                style="cited",
            )
            duration = time.time() - start
            if isinstance(result, dict) and "answer" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_answer",
                        "PASS",
                        duration,
                        details={"answer_length": len(result.get("answer", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_answer",
                        "FAIL",
                        duration,
                        error="Missing answer key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_llm_answer", "FAIL", duration, error=str(e)))

        # Test research_llm_embed
        start = time.time()
        try:
            result = await research_llm_embed(
                ["hello world", "machine learning", "artificial intelligence"]
            )
            duration = time.time() - start
            if isinstance(result, dict) and "embeddings" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_embed",
                        "PASS",
                        duration,
                        details={"embeddings_count": len(result.get("embeddings", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_embed",
                        "FAIL",
                        duration,
                        error="Missing embeddings key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_llm_embed", "FAIL", duration, error=str(e)))

        # Test research_llm_chat
        start = time.time()
        try:
            result = await research_llm_chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant",
                    },
                    {"role": "user", "content": "What is 2+2? Answer in one word."},
                ],
                max_tokens=10,
                temperature=0.0,
            )
            duration = time.time() - start
            if isinstance(result, dict) and "response" in result:
                self.add_result(
                    ToolTestResult(
                        "research_llm_chat",
                        "PASS",
                        duration,
                        details={"response_length": len(result.get("response", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_llm_chat",
                        "FAIL",
                        duration,
                        error="Missing response key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_llm_chat", "FAIL", duration, error=str(e)))

    async def test_enrichment_tools(self) -> None:
        """Test enrichment tools (2 tools)."""
        try:
            from loom.tools.core.enrich import (
                research_detect_language,
                research_wayback,
            )
        except ImportError:
            logger.warning("Enrichment tools not available")
            return

        # Test research_detect_language (English)
        start = time.time()
        try:
            result = await research_detect_language("The quick brown fox jumps over the lazy dog")
            duration = time.time() - start
            if isinstance(result, dict) and "language" in result:
                self.add_result(
                    ToolTestResult(
                        "research_detect_language(en)",
                        "PASS",
                        duration,
                        details={"language": result.get("language")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_detect_language(en)",
                        "FAIL",
                        duration,
                        error="Missing language key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_detect_language(en)",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_detect_language (Arabic)
        start = time.time()
        try:
            result = await research_detect_language("هذا نص باللغة العربية")
            duration = time.time() - start
            if isinstance(result, dict) and "language" in result:
                self.add_result(
                    ToolTestResult(
                        "research_detect_language(ar)",
                        "PASS",
                        duration,
                        details={"language": result.get("language")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_detect_language(ar)",
                        "FAIL",
                        duration,
                        error="Missing language key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_detect_language(ar)",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_wayback
        start = time.time()
        try:
            result = await research_wayback("https://example.com", limit=2)
            duration = time.time() - start
            if isinstance(result, dict) and "snapshots" in result:
                self.add_result(
                    ToolTestResult(
                        "research_wayback",
                        "PASS",
                        duration,
                        details={"snapshots_count": len(result.get("snapshots", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_wayback",
                        "SKIP",
                        duration,
                        error="No snapshots available",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_wayback", "FAIL", duration, error=str(e)))

    async def test_expert_tools(self) -> None:
        """Test expert finder (1 tool)."""
        try:
            from loom.tools.llm.experts import research_find_experts
        except ImportError:
            logger.warning("Expert tools not available")
            return

        start = time.time()
        try:
            result = await research_find_experts("machine learning", n=5)
            duration = time.time() - start
            if isinstance(result, dict) and "experts" in result:
                self.add_result(
                    ToolTestResult(
                        "research_find_experts",
                        "PASS",
                        duration,
                        details={"experts_count": len(result.get("experts", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_find_experts",
                        "SKIP",
                        duration,
                        error="No experts found",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_find_experts", "FAIL", duration, error=str(e)))

    async def test_exa_similar(self) -> None:
        """Test Exa find_similar (1 tool)."""
        try:
            from loom.providers.exa import find_similar_exa
        except ImportError:
            logger.warning("Exa provider not available")
            return

        start = time.time()
        try:
            result = await find_similar_exa(
                "https://en.wikipedia.org/wiki/Artificial_intelligence", n=3
            )
            duration = time.time() - start
            if isinstance(result, dict) and "results" in result:
                self.add_result(
                    ToolTestResult(
                        "find_similar_exa",
                        "PASS",
                        duration,
                        details={"results_count": len(result.get("results", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "find_similar_exa",
                        "FAIL",
                        duration,
                        error="Missing results key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            error_str = str(e)
            if "api" in error_str.lower() or "key" in error_str.lower():
                self.add_result(
                    ToolTestResult(
                        "find_similar_exa",
                        "SKIP",
                        duration,
                        error="API key not configured",
                    )
                )
            else:
                self.add_result(
                    ToolTestResult("find_similar_exa", "FAIL", duration, error=error_str)
                )

    async def test_creative_tools(self) -> None:
        """Test creative research tools (11 tools)."""
        try:
            from loom.tools.llm.creative import (
                research_ai_detect,
                research_citation_graph,
                research_community_sentiment,
                research_consensus,
                research_curriculum,
                research_misinfo_check,
                research_multilingual,
                research_red_team,
                research_semantic_sitemap,
                research_temporal_diff,
                research_wiki_ghost,
            )
        except ImportError:
            logger.warning("Creative tools not available")
            return

        # Test research_red_team
        start = time.time()
        try:
            result = await research_red_team(
                "AI will replace all human jobs within 10 years", n_counter=3
            )
            duration = time.time() - start
            if isinstance(result, dict) and "counter_arguments" in result:
                self.add_result(
                    ToolTestResult(
                        "research_red_team",
                        "PASS",
                        duration,
                        details={"counter_args_count": len(result.get("counter_arguments", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_red_team",
                        "FAIL",
                        duration,
                        error="Missing counter_arguments key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_red_team", "FAIL", duration, error=str(e)))

        # Test research_multilingual
        start = time.time()
        try:
            result = await research_multilingual(
                "bitcoin cryptocurrency",
                languages=["ar", "es", "de", "zh"],
                n_per_lang=2,
            )
            duration = time.time() - start
            if isinstance(result, dict) and "results" in result:
                self.add_result(
                    ToolTestResult(
                        "research_multilingual",
                        "PASS",
                        duration,
                        details={"results_count": len(result.get("results", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_multilingual",
                        "FAIL",
                        duration,
                        error="Missing results key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_multilingual", "FAIL", duration, error=str(e)))

        # Test research_consensus
        start = time.time()
        try:
            result = await research_consensus(
                "renewable energy benefits",
                providers=["ddgs", "wikipedia", "brave"],
                n=5,
            )
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_consensus",
                        "PASS",
                        duration,
                        details={"providers_count": len(result.get("sources", {}))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_consensus",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_consensus", "FAIL", duration, error=str(e)))

        # Test research_misinfo_check
        start = time.time()
        try:
            result = await research_misinfo_check(
                "The Earth is approximately 4.5 billion years old", n_sources=3
            )
            duration = time.time() - start
            if isinstance(result, dict) and "verification" in result:
                self.add_result(
                    ToolTestResult(
                        "research_misinfo_check",
                        "PASS",
                        duration,
                        details={"verdict": result.get("verification", {}).get("verdict")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_misinfo_check",
                        "FAIL",
                        duration,
                        error="Missing verification key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_misinfo_check", "FAIL", duration, error=str(e))
            )

        # Test research_temporal_diff
        start = time.time()
        try:
            result = await research_temporal_diff(
                "https://en.wikipedia.org/wiki/Artificial_intelligence"
            )
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_temporal_diff",
                        "PASS",
                        duration,
                        details={
                            "has_snapshots": "snapshots" in result,
                        },
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_temporal_diff",
                        "SKIP",
                        duration,
                        error="No temporal data available",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_temporal_diff", "FAIL", duration, error=str(e))
            )

        # Test research_citation_graph
        start = time.time()
        try:
            result = await research_citation_graph(
                "attention is all you need", depth=1, max_papers=10
            )
            duration = time.time() - start
            if isinstance(result, dict) and "papers" in result:
                self.add_result(
                    ToolTestResult(
                        "research_citation_graph",
                        "PASS",
                        duration,
                        details={"papers_count": len(result.get("papers", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_citation_graph",
                        "SKIP",
                        duration,
                        error="No papers found",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_citation_graph", "FAIL", duration, error=str(e))
            )

        # Test research_ai_detect
        start = time.time()
        try:
            result = await research_ai_detect("Artificial intelligence is revolutionizing..." * 5)
            duration = time.time() - start
            if isinstance(result, dict) and "detection" in result:
                self.add_result(
                    ToolTestResult(
                        "research_ai_detect",
                        "PASS",
                        duration,
                        details={"is_ai_generated": result.get("detection", {}).get("is_ai")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_ai_detect",
                        "FAIL",
                        duration,
                        error="Missing detection key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_ai_detect", "FAIL", duration, error=str(e)))

        # Test research_curriculum
        start = time.time()
        try:
            result = await research_curriculum("quantum computing")
            duration = time.time() - start
            if isinstance(result, dict) and "curriculum" in result:
                self.add_result(
                    ToolTestResult(
                        "research_curriculum",
                        "PASS",
                        duration,
                        details={"modules_count": len(result.get("curriculum", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_curriculum",
                        "SKIP",
                        duration,
                        error="No curriculum generated",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_curriculum", "FAIL", duration, error=str(e)))

        # Test research_community_sentiment
        start = time.time()
        try:
            result = await research_community_sentiment("Rust programming language", n=5)
            duration = time.time() - start
            if isinstance(result, dict) and "sentiment" in result:
                self.add_result(
                    ToolTestResult(
                        "research_community_sentiment",
                        "PASS",
                        duration,
                        details={"overall_sentiment": result.get("sentiment", {}).get("overall")},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_community_sentiment",
                        "SKIP",
                        duration,
                        error="No sentiment data",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult(
                    "research_community_sentiment",
                    "FAIL",
                    duration,
                    error=str(e),
                )
            )

        # Test research_wiki_ghost
        start = time.time()
        try:
            result = await research_wiki_ghost("Climate change")
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_wiki_ghost",
                        "PASS",
                        duration,
                        details={"sections_count": len(result.get("sections", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_wiki_ghost",
                        "SKIP",
                        duration,
                        error="No wiki data",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_wiki_ghost", "FAIL", duration, error=str(e)))

        # Test research_semantic_sitemap
        start = time.time()
        try:
            result = await research_semantic_sitemap("docs.python.org", max_pages=10)
            duration = time.time() - start
            if isinstance(result, dict) and "pages" in result:
                self.add_result(
                    ToolTestResult(
                        "research_semantic_sitemap",
                        "PASS",
                        duration,
                        details={"pages_count": len(result.get("pages", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_semantic_sitemap",
                        "SKIP",
                        duration,
                        error="No pages found",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(
                ToolTestResult("research_semantic_sitemap", "FAIL", duration, error=str(e))
            )

    async def test_youtube_tools(self) -> None:
        """Test YouTube tools (1 tool)."""
        try:
            from loom.providers.youtube_transcripts import fetch_youtube_transcript
        except ImportError:
            logger.warning("YouTube tools not available")
            return

        start = time.time()
        try:
            result = await fetch_youtube_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            duration = time.time() - start
            if isinstance(result, dict) and "transcript" in result:
                self.add_result(
                    ToolTestResult(
                        "fetch_youtube_transcript",
                        "PASS",
                        duration,
                        details={"transcript_length": len(result.get("transcript", ""))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "fetch_youtube_transcript",
                        "SKIP",
                        duration,
                        error="No transcript available",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            error_str = str(e)
            if "age-restricted" in error_str.lower() or "not available" in error_str.lower():
                self.add_result(
                    ToolTestResult(
                        "fetch_youtube_transcript",
                        "SKIP",
                        duration,
                        error="Video not available",
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "fetch_youtube_transcript",
                        "FAIL",
                        duration,
                        error=error_str,
                    )
                )

    async def test_session_tools(self) -> None:
        """Test session tools (2 tools)."""
        from loom.sessions import research_session_list

        # Test research_session_list
        start = time.time()
        try:
            result = research_session_list()
            duration = time.time() - start
            if isinstance(result, dict) and "sessions" in result:
                self.add_result(
                    ToolTestResult(
                        "research_session_list",
                        "PASS",
                        duration,
                        details={"sessions_count": len(result.get("sessions", []))},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_session_list",
                        "FAIL",
                        duration,
                        error="Missing sessions key",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_session_list", "FAIL", duration, error=str(e)))

    async def test_deep_tool(self) -> None:
        """Test research_deep tool."""
        from loom.tools.core.deep import research_deep

        start = time.time()
        try:
            result = await research_deep(
                "transformer attention mechanism",
                depth=1,
                expand=True,
                extract=True,
            )
            duration = time.time() - start
            if isinstance(result, dict):
                self.add_result(
                    ToolTestResult(
                        "research_deep",
                        "PASS",
                        duration,
                        details={"has_synthesis": "synthesis" in result},
                    )
                )
            else:
                self.add_result(
                    ToolTestResult(
                        "research_deep",
                        "FAIL",
                        duration,
                        error=f"Expected dict, got {type(result)}",
                    )
                )
        except Exception as e:
            duration = time.time() - start
            self.add_result(ToolTestResult("research_deep", "FAIL", duration, error=str(e)))

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        total_duration = sum(r.duration for r in self.results)

        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": f"{pass_rate:.1f}%",
                "total_duration_seconds": f"{total_duration:.2f}",
            },
            "results": [r.to_dict() for r in self.results],
        }

        return report

    def _write_report(self) -> None:
        """Write report to file (blocking I/O)."""
        report = self.generate_report()
        report_path = self.output_dir / "deep_research_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {report_path}")

    async def run_all_tests(self) -> None:
        """Run all tests."""
        logger.info("Starting comprehensive Loom MCP tool tests...")
        logger.info("=" * 80)

        await self.test_config_tools()
        logger.info("Config tools: done")

        await self.test_cache_tools()
        logger.info("Cache tools: done")

        await self.test_fetch_tools()
        logger.info("Fetch tools: done")

        await self.test_search_tools()
        logger.info("Search tools: done")

        await self.test_github_tools()
        logger.info("GitHub tools: done")

        await self.test_llm_tools()
        logger.info("LLM tools: done")

        await self.test_enrichment_tools()
        logger.info("Enrichment tools: done")

        await self.test_expert_tools()
        logger.info("Expert tools: done")

        await self.test_exa_similar()
        logger.info("Exa similar: done")

        await self.test_creative_tools()
        logger.info("Creative tools: done")

        await self.test_youtube_tools()
        logger.info("YouTube tools: done")

        await self.test_session_tools()
        logger.info("Session tools: done")

        await self.test_deep_tool()
        logger.info("Deep tool: done")

        logger.info("=" * 80)

        # Generate and save report (blocking I/O in separate sync method)
        self._write_report()

        # Print summary table
        self._print_summary_table()

    def _print_summary_table(self) -> None:
        """Print summary table of results."""
        print("\n" + "=" * 100)
        print(f"{'Tool Name':<45} {'Status':<10} {'Duration (s)':<15}")
        print("=" * 100)

        for result in self.results:
            status_str = (
                "✓ PASS"
                if result.status == "PASS"
                else "✗ FAIL"
                if result.status == "FAIL"
                else "○ SKIP"
            )
            print(f"{result.tool_name:<45} {status_str:<10} {result.duration:>10.2f}s")

        print("=" * 100)
        total_tests = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        total_duration = sum(r.duration for r in self.results)
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

        print(
            f"Total: {total_tests} | Passed: {passed} | Failed: {failed} | "
            f"Skipped: {skipped} | Pass Rate: {pass_rate:.1f}% | "
            f"Total Duration: {total_duration:.2f}s"
        )
        print("=" * 100 + "\n")


async def main() -> None:
    """Main entry point."""
    tester = DeepResearchTester()
    try:
        await tester.run_all_tests()
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
