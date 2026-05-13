"""Pytest fixtures for Brain test suite."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.brain.types import ToolMeta


@pytest.fixture
def mock_brain_index() -> dict[str, ToolMeta]:
    """Mock Brain index with a small set of test tools."""
    return {
        "research_search": ToolMeta(
            name="research_search",
            description="Search the web",
            parameters={"query": {"type": "string", "required": True}},
            categories=["search"],
            is_async=True,
        ),
        "research_fetch": ToolMeta(
            name="research_fetch",
            description="Fetch URL content",
            parameters={"url": {"type": "string", "required": True}},
            categories=["fetch"],
            is_async=True,
        ),
        "research_cert_analyze": ToolMeta(
            name="research_cert_analyze",
            description="Analyze SSL certificate",
            parameters={"domain": {"type": "string", "required": True}},
            categories=["security"],
            is_async=True,
        ),
        "research_cve_lookup": ToolMeta(
            name="research_cve_lookup",
            description="Look up CVE information",
            parameters={"cve_id": {"type": "string", "required": True}},
            categories=["security"],
            is_async=True,
        ),
        "research_llm_summarize": ToolMeta(
            name="research_llm_summarize",
            description="Summarize text using LLM",
            parameters={"text": {"type": "string", "required": True}},
            categories=["llm"],
            is_async=True,
        ),
    }


@pytest.fixture
def mock_tool_function() -> AsyncMock:
    """Mock tool async function."""
    async def _tool(**kwargs: Any) -> dict[str, Any]:
        return {"success": True, "data": "test_result"}

    return AsyncMock(side_effect=_tool)


@pytest.fixture
def mock_tool_function_sync() -> MagicMock:
    """Mock tool sync function."""
    def _tool(**kwargs: Any) -> dict[str, Any]:
        return {"success": True, "data": "test_result"}

    return MagicMock(side_effect=_tool)


@pytest.fixture
def mock_memory_state() -> dict[str, Any]:
    """Mock memory state with usage history."""
    return {
        "history": [
            {
                "tool": "research_search",
                "query": "python tutorials",
                "success": True,
                "elapsed_ms": 1200,
            },
            {
                "tool": "research_fetch",
                "query": "python tutorials",
                "success": True,
                "elapsed_ms": 2300,
            },
        ],
        "tool_stats": {
            "research_search": {"calls": 5, "successes": 4, "failures": 1, "total_ms": 5500},
            "research_fetch": {"calls": 3, "successes": 3, "failures": 0, "total_ms": 7000},
        },
    }
