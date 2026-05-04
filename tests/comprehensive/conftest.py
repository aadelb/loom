"""Pytest fixtures for Loom comprehensive test suite.

Provides shared fixtures for:
  - Mock LLM responses
  - Test URLs with safety
  - Async event loop configuration
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


@pytest.fixture
def mock_llm_response() -> dict[str, Any]:
    """Return a minimal valid LLM response fixture.

    Simulates responses from Groq, OpenAI, Anthropic, etc.
    """
    return {
        "id": "chatcmpl-test-12345",
        "object": "text_completion",
        "created": 1700000000,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the LLM.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 18,
            "total_tokens": 30,
        },
    }


@pytest.fixture
def test_url() -> str:
    """Return a valid test URL for public domain."""
    return "https://example.com"


@pytest.fixture
def private_url() -> str:
    """Return a private IP URL (should be rejected by SSRF validator)."""
    return "http://192.168.1.1"


@pytest.fixture
def localhost_url() -> str:
    """Return a localhost URL (should be rejected)."""
    return "http://localhost:8080"


@pytest.fixture
async def async_event_loop() -> Any:
    """Provide asyncio event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_search_response() -> dict[str, Any]:
    """Return a minimal valid search response fixture."""
    return {
        "results": [
            {
                "url": "https://example.com/page1",
                "title": "Example Page 1",
                "snippet": "This is an example search result.",
            },
            {
                "url": "https://example.com/page2",
                "title": "Example Page 2",
                "snippet": "Another example result.",
            },
        ],
        "total": 2,
        "query": "test query",
    }


@pytest.fixture
def mock_fetch_response() -> dict[str, Any]:
    """Return a minimal valid fetch response fixture."""
    return {
        "url": "https://example.com",
        "status_code": 200,
        "content": "<html><body>Test content</body></html>",
        "headers": {"content-type": "text/html"},
        "elapsed": 0.123,
    }


@pytest.fixture
def mock_markdown_response() -> dict[str, Any]:
    """Return a minimal valid markdown extraction response."""
    return {
        "url": "https://example.com",
        "markdown": "# Example Page\n\nThis is test content.",
        "title": "Example Page",
        "extracted_at": "2025-01-01T10:00:00Z",
    }


@pytest.fixture
def critical_tools() -> list[str]:
    """Return list of critical tools that must work."""
    return [
        "research_search",
        "research_fetch",
        "research_markdown",
        "research_deep",
        "research_llm_summarize",
        "research_cache_stats",
        "research_session_list",
        "research_config_get",
    ]
