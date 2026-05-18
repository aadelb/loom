"""Live E2E journey tests against local Loom API server.

Five smoke tests via httpx synchronous client against
http://127.0.0.1:8788/api/v1/.

Run with: pytest -m live tests/test_journey_new.py
"""

from __future__ import annotations

import pytest
import httpx

BASE_URL = "http://127.0.0.1:8788"


@pytest.mark.live
def test_health_check() -> None:
    """GET /api/v1/health returns healthy."""
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/api/v1/health")
    response.raise_for_status()
    data = response.json()
    assert data.get("status") == "healthy"


@pytest.mark.live
def test_tool_list() -> None:
    """GET /api/v1/tools returns 900+ tools."""
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/api/v1/tools")
    response.raise_for_status()
    data = response.json()
    assert data.get("count", 0) >= 900
    assert len(data.get("tools", {})) >= 900


@pytest.mark.live
def test_search() -> None:
    """POST /api/v1/tools/research_search returns results."""
    payload = {"query": "artificial intelligence", "provider": "ddgs", "n": 3}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/api/v1/tools/research_search", json=payload)
    response.raise_for_status()
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0


@pytest.mark.live
def test_hcs_score() -> None:
    """POST /api/v1/tools/research_hcs_score scores text."""
    payload = {"text": "Step 1: open the terminal. Step 2: run the command."}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/api/v1/tools/research_hcs_score", json=payload)
    response.raise_for_status()
    data = response.json()
    assert "hcs_score" in data
    assert data["hcs_score"] > 0


@pytest.mark.live
def test_smart_call() -> None:
    """POST /api/v1/tools/research_smart_call economy mode returns output."""
    payload = {"query": "python web scraping libraries", "quality_mode": "economy"}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/api/v1/tools/research_smart_call", json=payload)
    response.raise_for_status()
    data = response.json()
    assert "final_output" in data
    assert len(str(data["final_output"])) > 0
