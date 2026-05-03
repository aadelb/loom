"""Loom SDK — Python client for Loom MCP research server.

Provides async methods for web search, content fetching, deep research,
prompt reframing, and multi-LLM querying.

Example:
    ```python
    from loom_sdk import LoomClient

    async with LoomClient("http://127.0.0.1:8787") as client:
        # Search
        results = await client.search("AI safety", provider="exa", n=10)

        # Deep research
        report = await client.deep("what is transformers architecture")

        # Multi-LLM
        responses = await client.ask_all_llms("What is AGI?")

        # Reframe prompts
        reframed = await client.reframe("unsafe prompt", strategy="ethical_anchor")
    ```
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Ahmed Adel Bakr Alderai"

from .client import LoomClient, LoomClientError
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
    ToolInfo,
    ToolListResponse,
)

__all__ = [
    "LoomClient",
    "LoomClientError",
    "SearchResult",
    "SearchResponse",
    "FetchResult",
    "SpiderResponse",
    "ResearchReport",
    "ReframeResult",
    "LLMResponse",
    "AskAllResponse",
    "ToolInfo",
    "ToolListResponse",
    "HealthCheckResponse",
]
