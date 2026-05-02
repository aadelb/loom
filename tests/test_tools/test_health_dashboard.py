"""Tests for health_dashboard tool."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_research_dashboard_html():
    """Test that dashboard HTML generation works."""
    from loom.tools.health_dashboard import research_dashboard_html

    result = await research_dashboard_html()

    assert isinstance(result, dict)
    assert "html" in result
    assert "generated_at" in result
    assert "metrics_summary" in result

    html = result["html"]
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Loom Server Health" in html
    assert "Status" in html

    metrics = result["metrics_summary"]
    assert isinstance(metrics, dict)
    assert "status" in metrics
    assert "uptime_seconds" in metrics
    assert "tool_count" in metrics
    assert "memory_mb" in metrics
    assert "cpu_percent" in metrics


@pytest.mark.asyncio
async def test_dashboard_html_contains_sections():
    """Test that dashboard contains all expected sections."""
    from loom.tools.health_dashboard import research_dashboard_html

    result = await research_dashboard_html()
    html = result["html"]

    # Check for main sections
    assert "LLM Providers" in html
    assert "Search Providers" in html
    assert "Recent Errors" in html
    assert "Uptime" in html
    assert "Memory" in html
    assert "CPU" in html
    assert "Tools Loaded" in html


@pytest.mark.asyncio
async def test_dashboard_metrics_summary_structure():
    """Test metrics summary has expected structure."""
    from loom.tools.health_dashboard import research_dashboard_html

    result = await research_dashboard_html()
    metrics = result["metrics_summary"]

    assert metrics["status"] in ["healthy", "degraded", "unhealthy"]
    assert isinstance(metrics["uptime_seconds"], int)
    assert isinstance(metrics["tool_count"], int)
    assert isinstance(metrics["memory_mb"], (int, float))
    assert isinstance(metrics["cpu_percent"], (int, float))
    assert isinstance(metrics["llm_providers_up"], int)
    assert isinstance(metrics["search_providers_up"], int)
    assert isinstance(metrics["cache_entries"], int)
    assert isinstance(metrics["cache_size_mb"], (int, float))
    assert isinstance(metrics["active_sessions"], int)


@pytest.mark.asyncio
async def test_dashboard_html_styling():
    """Test that HTML includes required styling."""
    from loom.tools.health_dashboard import research_dashboard_html

    result = await research_dashboard_html()
    html = result["html"]

    # Check for color constants
    assert "#4CAF50" in html  # Green
    assert "#FF9800" in html  # Yellow
    assert "#F44336" in html  # Red
    assert "#1a1a2e" in html  # Dark background
    assert "#eee" in html     # Light text

    # Check for inline styles (no external deps)
    assert "<style>" in html
    assert "background:" in html
    assert "color:" in html
