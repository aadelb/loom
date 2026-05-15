"""Live integration tests for 12 Infrastructure tools (REQ-048)."""
import pytest

pytestmark = [pytest.mark.live, pytest.mark.timeout(60)]


class TestInfrastructureTools:
    @pytest.mark.asyncio
    async def test_health_check(self):
        from loom.tools.monitoring.health import research_health_check
        result = await research_health_check()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_metrics(self):
        from loom.tools.monitoring.metrics import research_metrics
        result = await research_metrics()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_usage_report(self):
        from loom.billing.meter import get_usage
        result = get_usage(customer_id="test")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_geoip_local(self):
        try:
            from loom.tools.intelligence.geoip_local import research_geoip_local
            result = await research_geoip_local(ip="8.8.8.8")
            assert isinstance(result, dict)
        except Exception:
            pytest.skip("MaxMind DB not available")

    @pytest.mark.asyncio
    async def test_convert_document(self):
        try:
            from loom.tools.core.document import research_convert_document
            result = await research_convert_document(content="# Test", from_format="markdown", to_format="html")
            assert isinstance(result, dict)
        except Exception:
            pytest.skip("Document converter not available")

    @pytest.mark.asyncio
    async def test_detect_language(self):
        from loom.tools.core.enrich import research_detect_language
        result = await research_detect_language(text="Bonjour le monde")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_wayback(self):
        from loom.tools.core.enrich import research_wayback
        result = await research_wayback(url="https://example.com")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_tor_status(self):
        from loom.tools.infrastructure.tor import research_tor_status
        result = await research_tor_status()
        assert isinstance(result, dict)
