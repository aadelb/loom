"""Async HTTP client for Loom MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from loom_sdk.models import (
    DeepResearchResult,
    FetchResult,
    HealthStatus,
    LLMSummarizeResult,
    SearchResponse,
    SearchResult,
    ToolResponse,
)

logger = logging.getLogger(__name__)


class LoomClient:
    """Async HTTP client for Loom MCP research server.

    Provides high-level methods for common research operations:
    - search: Multi-provider semantic search
    - fetch: Extract content from URLs
    - deep_research: Multi-stage research pipeline
    - llm_summarize: LLM-powered text summarization
    - health: Server health check
    - call_tool: Generic tool invocation

    Attributes:
        base_url: Server endpoint (default: http://localhost:8787)
        api_key: Optional API authentication key
        timeout: Request timeout in seconds (default: 60)
        max_retries: Maximum retry attempts on 5xx errors (default: 3)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8787",
        api_key: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize Loom client.

        Args:
            base_url: Server endpoint URL
            api_key: Optional API authentication key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on 5xx errors

        Raises:
            ValueError: If base_url is invalid
        """
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LoomClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Response JSON as dictionary

        Raises:
            httpx.HTTPError: If request fails after retries
            json.JSONDecodeError: If response is not valid JSON
        """
        client = await self._ensure_client()
        url = f"/{endpoint}".lstrip("/")

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    wait_time = 2 ** attempt + 0.1 * attempt
                    logger.warning(
                        f"Server error on attempt {attempt + 1}, "
                        f"retrying in {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
                    raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection error, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def search(
        self,
        query: str,
        provider: str = "auto",
        n: int = 10,
    ) -> SearchResponse:
        """Multi-provider semantic search.

        Args:
            query: Search query string
            provider: Search provider (auto, exa, tavily, brave, etc.)
            n: Number of results to return (1-100)

        Returns:
            SearchResponse with ranked results

        Raises:
            ValueError: If query is empty or n is out of range
            httpx.HTTPError: If request fails
        """
        if not query or not isinstance(query, str):
            raise ValueError("query must be a non-empty string")
        if not 1 <= n <= 100:
            raise ValueError("n must be between 1 and 100")

        start_time = time.time()
        response_data = await self._request(
            "POST",
            "/api/search",
            json={"query": query, "provider": provider, "n": n},
        )

        results = [SearchResult(**result) for result in response_data.get("results", [])]
        execution_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=results,
            total_count=response_data.get("total_count", len(results)),
            provider=response_data.get("provider", provider),
            execution_time_ms=execution_time_ms,
            metadata=response_data.get("metadata", {}),
        )

    async def fetch(
        self,
        url: str,
        mode: str = "auto",
    ) -> FetchResult:
        """Fetch and extract content from URL.

        Args:
            url: URL to fetch
            mode: Fetch mode (http, stealthy, dynamic, auto)

        Returns:
            FetchResult with extracted content

        Raises:
            ValueError: If URL is invalid
            httpx.HTTPError: If request fails
        """
        if not url or not isinstance(url, str):
            raise ValueError("url must be a non-empty string")

        start_time = time.time()
        response_data = await self._request(
            "POST",
            "/api/fetch",
            json={"url": url, "mode": mode},
        )
        execution_time_ms = (time.time() - start_time) * 1000

        return FetchResult(
            url=response_data.get("url", url),
            content_type=response_data.get("content_type", "unknown"),
            status_code=response_data.get("status_code", 200),
            body_length=response_data.get("body_length", 0),
            title=response_data.get("title"),
            markdown=response_data.get("markdown"),
            extraction_time_ms=execution_time_ms,
            metadata=response_data.get("metadata", {}),
        )

    async def deep_research(
        self,
        query: str,
        max_results: int = 10,
    ) -> DeepResearchResult:
        """Execute 12-stage deep research pipeline.

        Automatically detects query type and routes through:
        - Academic papers (arXiv)
        - Knowledge queries (Wikipedia)
        - Code search (GitHub)
        - General research (multi-provider)

        Args:
            query: Research query string
            max_results: Maximum results to return (1-50)

        Returns:
            DeepResearchResult with sources, findings, and citations

        Raises:
            ValueError: If query is empty or max_results is out of range
            httpx.HTTPError: If request fails
        """
        if not query or not isinstance(query, str):
            raise ValueError("query must be a non-empty string")
        if not 1 <= max_results <= 50:
            raise ValueError("max_results must be between 1 and 50")

        start_time = time.time()
        response_data = await self._request(
            "POST",
            "/api/deep-research",
            json={"query": query, "max_results": max_results},
        )
        execution_time_ms = (time.time() - start_time) * 1000

        sources = [SearchResult(**source) for source in response_data.get("sources", [])]
        citations = response_data.get("citations", [])
        key_findings = response_data.get("key_findings", [])

        return DeepResearchResult(
            query=query,
            sources=sources,
            key_findings=key_findings,
            summary=response_data.get("summary"),
            citations=citations,
            execution_time_ms=execution_time_ms,
            metadata=response_data.get("metadata", {}),
        )

    async def llm_summarize(
        self,
        text: str,
        max_words: int = 200,
        model: str | None = None,
    ) -> LLMSummarizeResult:
        """Summarize text using LLM cascade.

        Automatically selects best available LLM provider:
        - Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic, vLLM

        Args:
            text: Text to summarize
            max_words: Maximum summary length in words (50-2000)
            model: Optional specific model to use

        Returns:
            LLMSummarizeResult with summary and metadata

        Raises:
            ValueError: If text is empty or max_words is out of range
            httpx.HTTPError: If request fails
        """
        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")
        if not 50 <= max_words <= 2000:
            raise ValueError("max_words must be between 50 and 2000")

        start_time = time.time()
        response_data = await self._request(
            "POST",
            "/api/llm/summarize",
            json={
                "text": text,
                "max_words": max_words,
                "model": model,
            },
        )
        execution_time_ms = (time.time() - start_time) * 1000

        return LLMSummarizeResult(
            input_text=text,
            summary=response_data.get("summary", ""),
            word_count=response_data.get("word_count", 0),
            model=response_data.get("model"),
            execution_time_ms=execution_time_ms,
            metadata=response_data.get("metadata", {}),
        )

    async def health(self) -> HealthStatus:
        """Check server health and availability.

        Returns:
            HealthStatus with server info and metrics

        Raises:
            httpx.HTTPError: If request fails
        """
        start_time = time.time()
        response_data = await self._request("GET", "/health")
        execution_time_ms = (time.time() - start_time) * 1000

        return HealthStatus(
            status=response_data.get("status", "unknown"),
            version=response_data.get("version"),
            uptime_seconds=response_data.get("uptime_seconds"),
            tools_available=response_data.get("tools_available"),
            metadata={"latency_ms": execution_time_ms, **response_data.get("metadata", {})},
        )

    async def call_tool(
        self,
        tool_name: str,
        **params: Any,
    ) -> ToolResponse:
        """Invoke any Loom tool by name with parameters.

        Generic interface for accessing tools not covered by specific methods.

        Args:
            tool_name: Name of the tool to invoke
            **params: Tool-specific parameters

        Returns:
            ToolResponse with execution result

        Raises:
            ValueError: If tool_name is empty
            httpx.HTTPError: If request fails
        """
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError("tool_name must be a non-empty string")

        start_time = time.time()
        response_data = await self._request(
            "POST",
            f"/api/tools/{tool_name}",
            json=params,
        )
        execution_time_ms = (time.time() - start_time) * 1000

        return ToolResponse(
            tool_name=tool_name,
            success=response_data.get("success", True),
            data=response_data.get("data"),
            error=response_data.get("error"),
            execution_time_ms=execution_time_ms,
            metadata=response_data.get("metadata", {}),
        )
