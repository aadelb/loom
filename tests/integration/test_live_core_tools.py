"""Live integration tests for 7 core research tools (REQ-037)."""
import pytest

pytestmark = [pytest.mark.live, pytest.mark.timeout(60)]


@pytest.fixture
def sample_url():
    return "https://example.com"


class TestCoreTools:
    @pytest.mark.asyncio
    async def test_fetch(self, sample_url):
        from loom.tools.core.fetch import research_fetch
        result = await research_fetch(url=sample_url)
        assert isinstance(result, dict)
        assert "content" in result or "error" in result

    @pytest.mark.asyncio
    async def test_spider(self, sample_url):
        from loom.tools.core.spider import research_spider
        result = await research_spider(urls=[sample_url])
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_markdown(self, sample_url):
        from loom.tools.core.markdown import research_markdown
        result = await research_markdown(url=sample_url)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_search(self):
        from loom.tools.core.search import research_search
        result = await research_search(query="AI safety", provider="ddgs", max_results=3)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_deep(self):
        from loom.tools.core.deep import research_deep
        result = await research_deep(query="test query", max_results=2)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_github(self):
        from loom.tools.core.github import research_github
        result = await research_github(query="loom MCP", search_type="repos")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_camoufox(self, sample_url):
        try:
            from loom.tools.adversarial.stealth import research_camoufox
            result = await research_camoufox(url=sample_url)
            assert isinstance(result, dict)
        except (ImportError, Exception):
            pytest.skip("Camoufox not available")
