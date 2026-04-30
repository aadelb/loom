"""Live integration tests for REQ-001, REQ-002, REQ-004, REQ-008 workflows."""
import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.live, pytest.mark.timeout(120)]

RESULTS_DIR = Path("tmp")


class TestREQ001Wealth:
    """REQ-001: Full research workflow 'how to be rich'."""

    @pytest.mark.asyncio
    async def test_deep_research_wealth(self):
        from loom.tools.deep import research_deep
        result = await research_deep(query="how to be rich", max_results=5)
        assert isinstance(result, dict)
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "test_req001_live.json").write_text(json.dumps(result, default=str, indent=2))


class TestREQ002AIWealth:
    """REQ-002: Full workflow 'AI for wealth generation'."""

    @pytest.mark.asyncio
    async def test_ai_wealth_search(self):
        from loom.tools.search import research_search
        result = await research_search(query="how to use AI to generate wealth 2026", provider="ddgs", max_results=5)
        assert isinstance(result, dict)
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "test_req002_live.json").write_text(json.dumps(result, default=str, indent=2))


class TestREQ004UAEJobs:
    """REQ-004: Top paying jobs UAE."""

    @pytest.mark.asyncio
    async def test_uae_jobs_search(self):
        from loom.tools.search import research_search
        result = await research_search(query="top paying jobs in UAE 2026", provider="ddgs", max_results=5)
        assert isinstance(result, dict)
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "test_req004_live.json").write_text(json.dumps(result, default=str, indent=2))


class TestREQ008MultiSearch:
    """REQ-008: Multi-engine search from 5+ engines."""

    @pytest.mark.asyncio
    async def test_multi_search(self):
        from loom.tools.multi_search import research_multi_search
        result = await research_multi_search(query="AI safety tools 2026")
        assert isinstance(result, dict)
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "test_req008_live.json").write_text(json.dumps(result, default=str, indent=2))
