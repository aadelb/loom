"""Pydantic models for Loom SDK responses.

Typed data models for search results, research reports, reframing results,
and other API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Single search result from research_search."""

    title: str
    url: str
    snippet: str | None = None
    date: str | None = None
    author: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response from research_search."""

    provider: str
    query: str
    results: list[SearchResult]
    count: int = Field(default=0)
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FetchResult(BaseModel):
    """Result from research_fetch."""

    url: str
    status_code: int = 200
    content: str | None = None
    html: str | None = None
    json_data: dict[str, Any] | None = None
    screenshot: bytes | None = None
    encoding: str = "utf-8"
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SpiderResult(BaseModel):
    """Result from research_spider (multi-URL fetch)."""

    url: str
    status_code: int = 200
    content: str | None = None
    size_bytes: int = 0
    encoding: str = "utf-8"
    error: str | None = None


class SpiderResponse(BaseModel):
    """Response from research_spider."""

    urls_queued: int
    urls_succeeded: int
    urls_failed: int
    results: list[SpiderResult]
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResearchReport(BaseModel):
    """Response from research_deep (deep research pipeline)."""

    query: str
    summary: str | None = None
    findings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    citations: dict[str, str] = Field(default_factory=dict)
    related_queries: list[str] = Field(default_factory=list)
    sentiment: str | None = None
    confidence: float = 0.0
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReframeResult(BaseModel):
    """Response from research_reframe (prompt reframing)."""

    original_prompt: str
    strategy_name: str
    reframed_prompt: str
    category: str | None = None
    difficulty: str | None = None
    description: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    error: str | None = None


class LLMResponse(BaseModel):
    """Response from a single LLM provider."""

    provider: str
    prompt: str
    response: str | None = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AskAllResponse(BaseModel):
    """Response from research_ask_all_llms."""

    prompt: str
    responses: list[LLMResponse] = Field(default_factory=list)
    providers_queried: int = 0
    providers_responded: int = 0
    providers_refused: int = 0
    fastest_provider: str | None = None
    fastest_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    reframe_results: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ToolInfo(BaseModel):
    """Information about a single tool."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    category: str | None = None


class ToolListResponse(BaseModel):
    """Response from research_list_tools."""

    total_tools: int
    tools: list[ToolInfo] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    error: str | None = None


class HealthCheckResponse(BaseModel):
    """Response from health check."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: float = 0.0
    tools_available: int = 0
    providers_available: list[str] = Field(default_factory=list)
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
