"""Live journey tests against local Loom API server.

Runs 5 smoke tests via httpx synchronous client against
http://127.0.0.1:8788/api/v1/.
"""

from __future__ import annotations

import pytest
import httpx

BASE_URL = "http://127.0.0.1:8788/api/v1"


@pytest.mark.live
def test_health() -> None:
    """GET /health returns status=healthy."""
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/health")
    response.raise_for_status()
    data = response.json()
    assert data.get("status") == "healthy"


@pytest.mark.live
def test_tool_count() -> None:
    """GET /health returns tool_count > 900."""
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/health")
    response.raise_for_status()
    data = response.json()
    assert data.get("tool_count", 0) > 900


@pytest.mark.live
def test_search() -> None:
    """POST /tools/research_search returns results for python query."""
    payload = {"query": "python", "n": 2}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/tools/research_search", json=payload)
    response.raise_for_status()
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0


@pytest.mark.live
def test_hcs() -> None:
    """POST /tools/research_hcs_score returns hcs_score > 0."""
    payload = {"text": "step 1 do this step 2 do that"}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/tools/research_hcs_score", json=payload)
    response.raise_for_status()
    data = response.json()
    assert data.get("hcs_score", 0) > 0


@pytest.mark.live
def test_config() -> None:
    """POST /tools/research_config_get returns value for LLM_CASCADE_ORDER."""
    payload = {"key": "LLM_CASCADE_ORDER"}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/tools/research_config_get", json=payload)
    response.raise_for_status()
    data = response.json()
    assert "value" in data
    assert data["value"] is not None
