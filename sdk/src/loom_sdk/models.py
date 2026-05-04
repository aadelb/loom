"""Type-safe response models for Loom SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    """Search result from a query."""

    url: str
    title: str
    snippet: str
    provider: str
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResponse:
    """Response from search operations."""

    query: str
    results: list[SearchResult]
    total_count: int
    provider: str
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FetchResult:
    """Result from fetching a URL."""

    url: str
    content_type: str
    status_code: int
    body_length: int
    title: str | None = None
    markdown: str | None = None
    extraction_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeepResearchResult:
    """Result from deep research query."""

    query: str
    sources: list[SearchResult]
    key_findings: list[str]
    summary: str | None = None
    citations: list[str] = field(default_factory=list)
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMSummarizeResult:
    """Result from LLM summarization."""

    input_text: str
    summary: str
    word_count: int
    model: str | None = None
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthStatus:
    """Server health status response."""

    status: str
    version: str | None = None
    uptime_seconds: float | None = None
    tools_available: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResponse:
    """Generic response from tool invocation."""

    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
