"""Pytest fixtures for Loom test suite.

Provides:
  - Temp directories (cache, sessions, config)
  - Mock HTTP transport (httpx MockTransport)
  - Mock MCP server (in-process FastMCP)
  - Fixture model cards and API responses
  - Environment variable isolation
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from httpx import MockTransport, Response


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    """Reset rate limiter state between tests to prevent cross-test contamination."""
    from loom.rate_limiter import reset_all

    reset_all()
    yield
    reset_all()


@pytest.fixture
def tmp_cache_dir() -> Path:
    """Temporary cache directory for isolated tests."""
    with TemporaryDirectory(prefix="loom_cache_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tmp_sessions_dir() -> Path:
    """Temporary sessions directory for isolated tests."""
    with TemporaryDirectory(prefix="loom_sessions_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tmp_config_path() -> Path:
    """Temporary config file path for isolated tests."""
    with TemporaryDirectory(prefix="loom_config_") as tmpdir:
        yield Path(tmpdir) / "config.json"


@pytest.fixture
def mock_httpx_transport() -> MockTransport:
    """Provide an httpx MockTransport for HTTP testing.

    Caller can set responses via transport._responses dict or
    use .mock_response() to add specific URL responses.
    """

    def callback(request):  # type: ignore
        url = str(request.url)
        status = 200
        content = b"{}"

        # Route based on URL for common cases
        if "huggingface.co" in url:
            content = b'{"status":"ok"}'
            status = 200
        elif "arxiv.org" in url:
            content = b'<html><title>arXiv</title><body>Paper</body></html>'
            status = 200
        elif ("127.0.0.1" in url or "localhost" in url or "169.254" in url or
              "10.0.0.1" in url or "192.168" in url or "172.16" in url):
            status = 403
        else:
            status = 200
            content = b'<html><body>Mock page</body></html>'

        return Response(status_code=status, content=content)

    return MockTransport(callback)


@pytest.fixture
def env_no_api_keys() -> None:
    """Clear API keys from environment for tests that should not hit real APIs."""
    keys_to_clear = [
        "NVIDIA_NIM_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "EXA_API_KEY",
        "TAVILY_API_KEY",
    ]
    old_vals = {}
    for key in keys_to_clear:
        old_vals[key] = os.environ.pop(key, None)

    yield

    # Restore
    for key, val in old_vals.items():
        if val is not None:
            os.environ[key] = val


@pytest.fixture
def fixture_fanar_model_card() -> str:
    """Load or create a minimal HTML fixture for model card testing.

    Returns path to fixture file. Creates a small generic model card HTML.
    """
    fixture_dir = Path(__file__).parent / "fixtures"
    fixture_dir.mkdir(exist_ok=True)

    fixture_file = fixture_dir / "fanar_card.html"

    # Create a minimal generic model card if not present
    if not fixture_file.exists():
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Example AI Model Card</title>
</head>
<body>
    <div class="model-header">
        <h1>Example Model Card</h1>
        <p>This is a placeholder model card for testing purposes.</p>
    </div>
    <div class="model-content">
        <section>
            <h2>Model Details</h2>
            <p>Version: 1.0.0</p>
            <p>Architecture: Transformer-based</p>
            <p>Parameters: 7B</p>
        </section>
        <section>
            <h2>Intended Use</h2>
            <p>This model is designed for research and testing purposes.</p>
        </section>
        <section>
            <h2>Performance</h2>
            <p>Benchmarks and performance data would appear here.</p>
        </section>
    </div>
</body>
</html>"""
        fixture_file.write_text(html_content, encoding="utf-8")

    return str(fixture_file)


@pytest.fixture
def fixture_exa_search_response() -> dict[str, Any]:
    """Return a minimal valid Exa search response fixture."""
    return {
        "results": [
            {
                "url": "https://example.com/result1",
                "title": "Example Result 1",
                "snippet": "This is an example search result.",
                "published_date": "2024-01-01",
            },
            {
                "url": "https://example.com/result2",
                "title": "Example Result 2",
                "snippet": "Another example result.",
                "published_date": "2024-01-02",
            },
        ],
        "autopromptString": "example query",
    }


@pytest.fixture
def fixture_tavily_search_response() -> dict[str, Any]:
    """Return a minimal valid Tavily search response fixture."""
    return {
        "results": [
            {
                "title": "Example Tavily Result 1",
                "url": "https://example.com/tavily1",
                "content": "Example content from Tavily.",
                "score": 0.95,
            },
            {
                "title": "Example Tavily Result 2",
                "url": "https://example.com/tavily2",
                "content": "More example content.",
                "score": 0.87,
            },
        ],
        "query": "example query",
        "response_time": 0.123,
    }


@pytest.fixture
def fixture_nvidia_nim_chat_response() -> dict[str, Any]:
    """Return a minimal valid NVIDIA NIM chat response fixture."""
    return {
        "id": "chatcmpl-example",
        "object": "text_completion",
        "created": 1700000000,
        "model": "meta-llama3-8b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is an example response from NVIDIA NIM.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "total_tokens": 25,
        },
    }


@pytest.fixture
def fixture_journey_dir() -> Path:
    """Create a minimal journey fixtures directory with sample data."""
    fixture_dir = Path(__file__).parent / "fixtures" / "journey"
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Create pages subdirectory
    pages_dir = fixture_dir / "pages"
    pages_dir.mkdir(exist_ok=True)

    # Create a sample example model card fixture
    example_card = pages_dir / "example_model_card.html"
    if not example_card.exists():
        example_card.write_text("""<!DOCTYPE html>
<html>
<head><title>Example Model Card</title></head>
<body>
    <h1>Example Model</h1>
    <p>This is an example model card for journey testing.</p>
</body>
</html>""")

    # Create sample search response fixtures
    exa_fixture = fixture_dir / "exa_search_example.json"
    if not exa_fixture.exists():
        exa_fixture.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "url": "https://example.com/1",
                            "title": "Example 1",
                            "snippet": "Example snippet.",
                        }
                    ]
                },
                indent=2,
            )
        )

    return fixture_dir
