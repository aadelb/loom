"""Loom SDK Client — Python interface to Loom MCP server.

Provides async methods for search, deep research, prompt reframing,
multi-LLM querying, and tool discovery.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from .models import (
    AskAllResponse,
    FetchResult,
    HealthCheckResponse,
    LLMResponse,
    ResearchReport,
    ReframeResult,
    SearchResponse,
    SearchResult,
    SpiderResponse,
    ToolListResponse,
)

logger = logging.getLogger(__name__)


class LoomClient:
    """Async client for Loom MCP server.

    Provides methods to call research tools, fetch content, reframe prompts,
    and query multiple LLM providers simultaneously.

    Example:
        ```python
        client = LoomClient("http://127.0.0.1:8787")
        results = await client.search("AI safety research", provider="exa", n=10)
        report = await client.deep("what is transformers")
        ```
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8787",
        api_key: str | None = None,
        timeout: float = 300.0,
    ):
        """Initialize Loom client.

        Args:
            server_url: URL of Loom MCP server (default: http://127.0.0.1:8787)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 300)
        """
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                base_url=self.server_url,
            )
        return self._client

    async def _call_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Call a Loom MCP tool.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool parameters

        Returns:
            Dict response from tool
        """
        client = await self._ensure_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": kwargs,
            },
        }

        try:
            response = await client.post(
                "/mcp",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            if "result" in data:
                return data["result"].get("content", [{}])[0].get("text")
            if "error" in data:
                raise LoomClientError(
                    f"Tool {tool_name} error: {data['error'].get('message', 'Unknown')}"
                )

            return data
        except httpx.HTTPError as e:
            raise LoomClientError(f"HTTP error calling {tool_name}: {e}") from e
        except json.JSONDecodeError as e:
            raise LoomClientError(f"Invalid JSON response from {tool_name}: {e}") from e

    async def search(
        self,
        query: str,
        provider: str | None = None,
        n: int = 10,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        language: str | None = None,
        **kwargs: Any,
    ) -> SearchResponse:
        """Search using research_search.

        Args:
            query: Search query
            provider: Search provider (exa, tavily, firecrawl, brave, etc.)
            n: Number of results to return
            include_domains: Domains to include
            exclude_domains: Domains to exclude
            start_date: ISO date string (YYYY-MM-DD)
            end_date: ISO date string (YYYY-MM-DD)
            language: Language hint (ISO 639-1)
            **kwargs: Additional provider-specific args

        Returns:
            SearchResponse with results
        """
        params = {
            "query": query,
            "n": n,
        }
        if provider:
            params["provider"] = provider
        if include_domains:
            params["include_domains"] = include_domains
        if exclude_domains:
            params["exclude_domains"] = exclude_domains
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if language:
            params["language"] = language
        params.update(kwargs)

        result = await self._call_tool("research_search", **params)
        if isinstance(result, str):
            result = json.loads(result)

        results = []
        for item in result.get("results", []):
            results.append(SearchResult(**item))

        return SearchResponse(
            provider=result.get("provider", "unknown"),
            query=query,
            results=results,
            count=len(results),
            error=result.get("error"),
        )

    async def fetch(
        self,
        url: str,
        mode: str = "stealthy",
        auto_escalate: bool = False,
        solve_cloudflare: bool = True,
        bypass_cache: bool = False,
        max_chars: int = 20000,
        **kwargs: Any,
    ) -> FetchResult:
        """Fetch a single URL using research_fetch.

        Args:
            url: URL to fetch
            mode: Fetch mode (http, stealthy, dynamic)
            auto_escalate: Auto-escalate to dynamic if stealthy fails
            solve_cloudflare: Solve Cloudflare challenges
            bypass_cache: Bypass content cache
            max_chars: Max characters to return
            **kwargs: Additional args (headers, cookies, auth, etc.)

        Returns:
            FetchResult with content
        """
        params = {
            "url": url,
            "mode": mode,
            "auto_escalate": auto_escalate,
            "solve_cloudflare": solve_cloudflare,
            "bypass_cache": bypass_cache,
            "max_chars": max_chars,
        }
        params.update(kwargs)

        result = await self._call_tool("research_fetch", **params)
        if isinstance(result, str):
            result = json.loads(result)

        return FetchResult(
            url=url,
            status_code=result.get("status_code", 200),
            content=result.get("content"),
            html=result.get("html"),
            json_data=result.get("json"),
            encoding=result.get("encoding", "utf-8"),
            error=result.get("error"),
        )

    async def spider(
        self,
        urls: list[str],
        mode: str = "stealthy",
        max_chars_each: int = 5000,
        concurrency: int = 5,
        dedupe: bool = True,
        **kwargs: Any,
    ) -> SpiderResponse:
        """Fetch multiple URLs in parallel using research_spider.

        Args:
            urls: List of URLs to fetch
            mode: Fetch mode (http, stealthy, dynamic)
            max_chars_each: Max chars per URL
            concurrency: Number of concurrent requests
            dedupe: Deduplicate results
            **kwargs: Additional args

        Returns:
            SpiderResponse with all results
        """
        params = {
            "urls": urls,
            "mode": mode,
            "max_chars_each": max_chars_each,
            "concurrency": concurrency,
            "dedupe": dedupe,
        }
        params.update(kwargs)

        result = await self._call_tool("research_spider", **params)
        if isinstance(result, str):
            result = json.loads(result)

        results = []
        for item in result.get("results", []):
            results.append(
                SpiderResult(
                    url=item.get("url", ""),
                    status_code=item.get("status_code", 200),
                    content=item.get("content"),
                    encoding=item.get("encoding", "utf-8"),
                    error=item.get("error"),
                )
            )

        return SpiderResponse(
            urls_queued=result.get("urls_queued", len(urls)),
            urls_succeeded=result.get("urls_succeeded", len(results)),
            urls_failed=result.get("urls_failed", 0),
            results=results,
            error=result.get("error"),
        )

    async def deep(
        self,
        query: str,
        max_results: int | None = None,
        include_sentiment: bool = False,
        include_redteam: bool = False,
        **kwargs: Any,
    ) -> ResearchReport:
        """Run full deep research pipeline using research_deep.

        Args:
            query: Research query
            max_results: Max results to include
            include_sentiment: Include sentiment analysis
            include_redteam: Include red-team analysis
            **kwargs: Additional args

        Returns:
            ResearchReport with findings, sources, and citations
        """
        params = {
            "query": query,
        }
        if max_results is not None:
            params["max_results"] = max_results
        if include_sentiment:
            params["include_sentiment"] = include_sentiment
        if include_redteam:
            params["include_redteam"] = include_redteam
        params.update(kwargs)

        result = await self._call_tool("research_deep", **params)
        if isinstance(result, str):
            result = json.loads(result)

        return ResearchReport(
            query=query,
            summary=result.get("summary"),
            findings=result.get("findings", []),
            sources=result.get("sources", []),
            citations=result.get("citations", {}),
            related_queries=result.get("related_queries", []),
            sentiment=result.get("sentiment"),
            confidence=float(result.get("confidence", 0.0)),
            error=result.get("error"),
        )

    async def reframe(
        self,
        prompt: str,
        strategy: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> ReframeResult:
        """Reframe a prompt using research_reframe.

        Args:
            prompt: Original prompt to reframe
            strategy: Reframing strategy name (if None, auto-select)
            model: Target model (claude, gpt, gemini, etc.)
            **kwargs: Additional args

        Returns:
            ReframeResult with reframed prompt
        """
        params = {
            "prompt": prompt,
        }
        if strategy:
            params["strategy"] = strategy
        if model:
            params["model"] = model
        params.update(kwargs)

        result = await self._call_tool("research_reframe", **params)
        if isinstance(result, str):
            result = json.loads(result)

        return ReframeResult(
            original_prompt=prompt,
            strategy_name=result.get("strategy_name", strategy or "auto"),
            reframed_prompt=result.get("reframed_prompt", prompt),
            category=result.get("category"),
            difficulty=result.get("difficulty"),
            description=result.get("description"),
            safety_flags=result.get("safety_flags", []),
            error=result.get("error"),
        )

    async def ask_all_llms(
        self,
        prompt: str,
        max_tokens: int = 500,
        include_reframe: bool = False,
        **kwargs: Any,
    ) -> AskAllResponse:
        """Send prompt to all available LLM providers using research_ask_all_llms.

        Args:
            prompt: Prompt to send to all providers
            max_tokens: Max tokens per response
            include_reframe: Auto-reframe refused prompts
            **kwargs: Additional args

        Returns:
            AskAllResponse with all provider responses
        """
        params = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "include_reframe": include_reframe,
        }
        params.update(kwargs)

        result = await self._call_tool("research_ask_all_llms", **params)
        if isinstance(result, str):
            result = json.loads(result)

        responses = []
        for item in result.get("responses", []):
            responses.append(
                LLMResponse(
                    provider=item.get("provider", "unknown"),
                    prompt=prompt,
                    response=item.get("response"),
                    tokens_used=item.get("tokens_used", 0),
                    latency_ms=item.get("latency_ms", 0.0),
                    error=item.get("error"),
                )
            )

        return AskAllResponse(
            prompt=prompt,
            responses=responses,
            providers_queried=result.get("providers_queried", len(responses)),
            providers_responded=result.get("providers_responded", len(responses)),
            providers_refused=result.get("providers_refused", 0),
            fastest_provider=result.get("fastest_provider"),
            fastest_latency_ms=result.get("fastest_latency_ms", 0.0),
            total_latency_ms=result.get("total_latency_ms", 0.0),
            reframe_results=result.get("reframe_results", {}),
            error=result.get("error"),
        )

    async def list_tools(self) -> ToolListResponse:
        """List all available tools using research_list_tools.

        Returns:
            ToolListResponse with all tools and metadata
        """
        result = await self._call_tool("research_list_tools")
        if isinstance(result, str):
            result = json.loads(result)

        return ToolListResponse(
            total_tools=result.get("total_tools", 0),
            tools=result.get("tools", []),
            categories=result.get("categories", []),
            error=result.get("error"),
        )

    async def health_check(self) -> HealthCheckResponse:
        """Check server health using research_health_check.

        Returns:
            HealthCheckResponse with server status
        """
        result = await self._call_tool("research_health_check")
        if isinstance(result, str):
            result = json.loads(result)

        return HealthCheckResponse(
            status=result.get("status", "unknown"),
            version=result.get("version", "0.0.0"),
            uptime_seconds=result.get("uptime_seconds", 0.0),
            tools_available=result.get("tools_available", 0),
            providers_available=result.get("providers_available", []),
            error=result.get("error"),
        )

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> LoomClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


class LoomClientError(Exception):
    """Base exception for Loom SDK errors."""

    pass
