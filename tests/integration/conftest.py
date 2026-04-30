"""Pytest fixtures for live integration tests.

Provides fixtures for testing the 7 core research tools:
  - research_fetch
  - research_spider
  - research_markdown
  - research_search
  - research_deep
  - research_github
  - research_camoufox

These fixtures skip gracefully if the Loom package is not installed or if
network is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

logger = logging.getLogger("tests.integration.conftest")


@pytest.fixture
def live_test_logger() -> logging.Logger:
    """Return a configured logger for live tests."""
    return logger


@pytest.fixture
def example_urls() -> dict[str, str]:
    """Provide stable, public URLs for testing."""
    return {
        "example": "https://example.com",
        "github": "https://github.com",
        "wikipedia": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    }


@pytest.fixture
def example_queries() -> dict[str, str]:
    """Provide example search queries for testing."""
    return {
        "ai_safety": "AI safety 2026",
        "test": "test query",
        "loom": "loom MCP",
        "python": "python programming",
    }
