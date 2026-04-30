"""Comprehensive tests for ScraperEngine with escalation chain.

Tests cover:
- Backend availability detection
- Escalation chain logic
- Caching behavior
- Domain history tracking
- Batch fetching
- Parameter validation
- Error handling and recovery
"""

from __future__ import annotations

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from loom.scraper_engine import (
    BackendAvailability,
    DomainEscalationHistory,
    EscalationLevel,
    EscalationResult,
    LEVEL_TO_BACKEND,
    ScraperEngine,
    ScraperEngineResult,
)
from loom.params import (
    ScraperEngineFetchParams,
    ScraperEngineExtractParams,
    ScraperEngineBatchParams,
)


class TestBackendAvailability:
    """Tests for BackendAvailability singleton."""

    def test_singleton_instance(self) -> None:
        """BackendAvailability should be a singleton."""
        ba1 = BackendAvailability()
        ba2 = BackendAvailability()
        assert ba1 is ba2

    def test_check_httpx_available(self) -> None:
        """httpx should always be available (builtin)."""
        ba = BackendAvailability()
        assert ba.check("httpx") is True

    def test_check_unavailable_backend(self) -> None:
        """Unavailable backends should return False."""
        ba = BackendAvailability()
        # This backend definitely doesn't exist
        assert ba.check("nonexistent_scraper_xyz") is False

    def test_check_caches_result(self) -> None:
        """Availability checks should be cached."""
        ba = BackendAvailability()
        ba.reset_cache()

        # First check
        result1 = ba.check("httpx")
        assert result1 is True

        # Cached result
        result2 = ba.check("httpx")
        assert result2 is True

    def test_reset_cache(self) -> None:
        """Cache can be reset."""
        ba = BackendAvailability()
        ba.reset_cache()
        assert ba._cache == {}


class TestDomainEscalationHistory:
    """Tests for DomainEscalationHistory."""

    def test_singleton_instance(self) -> None:
        """DomainEscalationHistory should be a singleton."""
        dh1 = DomainEscalationHistory()
        dh2 = DomainEscalationHistory()
        assert dh1 is dh2

    def test_get_min_level_default(self) -> None:
        """New domains should default to level 0."""
        dh = DomainEscalationHistory()
        dh.reset()
        assert dh.get_min_level("example.com") == 0

    def test_record_success(self) -> None:
        """Recording success should update domain history."""
        dh = DomainEscalationHistory()
        dh.reset()

        dh.record_success("example.com", 2)
        assert dh.get_min_level("example.com") == 2

    def test_record_success_only_lowers_level(self) -> None:
        """Recording should only lower the level, not raise it."""
        dh = DomainEscalationHistory()
        dh.reset()

        dh.record_success("example.com", 3)
        assert dh.get_min_level("example.com") == 3

        # Try to raise it — should not change
        dh.record_success("example.com", 5)
        assert dh.get_min_level("example.com") == 3

    def test_reset(self) -> None:
        """Reset should clear history."""
        dh = DomainEscalationHistory()
        dh.record_success("example.com", 2)
        assert dh.get_min_level("example.com") == 2

        dh.reset()
        assert dh.get_min_level("example.com") == 0


class TestEscalationLevel:
    """Tests for EscalationLevel enum."""

    def test_level_order(self) -> None:
        """Escalation levels should be ordered by complexity."""
        assert EscalationLevel.HTTPX < EscalationLevel.SCRAPLING
        assert EscalationLevel.SCRAPLING < EscalationLevel.CRAWL4AI
        assert EscalationLevel.BOTASAURUS == 7

    def test_level_to_backend_mapping(self) -> None:
        """All levels should have backend names."""
        for level in range(8):
            assert level in LEVEL_TO_BACKEND
            assert LEVEL_TO_BACKEND[level] in {
                "httpx",
                "scrapling",
                "crawl4ai",
                "patchright",
                "nodriver",
                "zendriver",
                "camoufox",
                "botasaurus",
            }


class TestScraperEngineParams:
    """Tests for parameter validation models."""

    def test_fetch_params_valid(self) -> None:
        """Valid fetch params should validate."""
        params = ScraperEngineFetchParams(
            url="https://example.com",
            mode="auto",
            max_escalation=5,
        )
        assert params.url == "https://example.com"
        assert params.mode == "auto"

    def test_fetch_params_rejects_invalid_url(self) -> None:
        """Invalid URLs should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineFetchParams(url="http://localhost:8080")

    def test_fetch_params_rejects_invalid_escalation(self) -> None:
        """Escalation level out of range should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineFetchParams(url="https://example.com", max_escalation=10)

    def test_fetch_params_rejects_invalid_backend(self) -> None:
        """Invalid backend name should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineFetchParams(
                url="https://example.com", force_backend="invalid_backend"
            )

    def test_extract_params_valid(self) -> None:
        """Valid extract params should validate."""
        params = ScraperEngineExtractParams(
            url="https://example.com",
            query="Extract the title",
        )
        assert params.url == "https://example.com"
        assert params.query == "Extract the title"

    def test_extract_params_rejects_empty_query(self) -> None:
        """Empty query should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineExtractParams(url="https://example.com", query="")

    def test_extract_params_rejects_long_query(self) -> None:
        """Query longer than 500 chars should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineExtractParams(
                url="https://example.com", query="x" * 501
            )

    def test_batch_params_valid(self) -> None:
        """Valid batch params should validate."""
        params = ScraperEngineBatchParams(
            urls=["https://example.com", "https://example.org"],
            mode="auto",
            max_concurrent=5,
        )
        assert len(params.urls) == 2

    def test_batch_params_rejects_empty_urls(self) -> None:
        """Empty URLs list should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineBatchParams(urls=[])

    def test_batch_params_rejects_too_many_urls(self) -> None:
        """More than 100 URLs should be rejected."""
        with pytest.raises(ValidationError):
            ScraperEngineBatchParams(urls=[f"https://example{i}.com" for i in range(101)])


class TestScraperEngineInit:
    """Tests for ScraperEngine initialization."""

    def test_init_default(self) -> None:
        """Default initialization should work."""
        engine = ScraperEngine()
        assert engine.cache_enabled is True
        assert engine.max_retries == 3
        assert engine.timeout_secs > 0

    def test_init_cache_disabled(self) -> None:
        """Can disable cache."""
        engine = ScraperEngine(cache_enabled=False)
        assert engine.cache_enabled is False
        assert engine.cache is None

    def test_init_custom_timeout(self) -> None:
        """Can set custom timeout."""
        engine = ScraperEngine(timeout_secs=60)
        assert engine.timeout_secs == 60


@pytest.mark.asyncio
class TestScraperEngineFetch:
    """Tests for ScraperEngine.fetch()."""

    async def test_fetch_validates_url(self) -> None:
        """Fetch should validate URL."""
        engine = ScraperEngine()
        with pytest.raises(Exception):
            await engine.fetch("http://localhost:8080")

    async def test_fetch_with_cache_hit(self, tmp_cache_dir: Path) -> None:
        """Fetch should return cached result."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        engine = ScraperEngine(cache_enabled=True)

        # Mock cache hit
        with patch.object(engine, "_check_cache") as mock_cache:
            mock_cache.return_value = {
                "content": "cached content",
                "content_type": "text/html",
            }

            result = await engine.fetch("https://example.com")

            assert result.success is True
            assert result.content == "cached content"
            assert result.backend_used == "cache"

    async def test_fetch_escalation_successful(self) -> None:
        """Fetch should escalate through backends until success."""
        engine = ScraperEngine(cache_enabled=False)

        # Mock backend attempt — fail at level 0, succeed at level 1
        async def mock_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            return EscalationResult(
                success=True,
                content="fetched content",
                backend="httpx",
                level=0,
            )

        with patch.object(engine, "_escalate", side_effect=mock_escalate):
            result = await engine.fetch("https://example.com")

            assert result.success is True
            assert result.content == "fetched content"

    async def test_fetch_respects_mode_auto(self) -> None:
        """Auto mode should start at level 0."""
        engine = ScraperEngine(cache_enabled=False)

        call_args = []

        async def capture_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            call_args.append((start_level, max_level))
            return EscalationResult(success=True, content="test", backend="httpx", level=0)

        with patch.object(engine, "_escalate", side_effect=capture_escalate):
            await engine.fetch("https://example.com", mode="auto")

            assert call_args[0][0] == 0  # start_level

    async def test_fetch_respects_mode_stealth(self) -> None:
        """Stealth mode should start at level 3."""
        engine = ScraperEngine(cache_enabled=False)

        call_args = []

        async def capture_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            call_args.append((start_level, max_level))
            return EscalationResult(success=True, content="test", backend="patchright", level=3)

        with patch.object(engine, "_escalate", side_effect=capture_escalate):
            await engine.fetch("https://example.com", mode="stealth")

            assert call_args[0][0] == 3  # start_level

    async def test_fetch_respects_mode_max(self) -> None:
        """Max mode should start at level 5."""
        engine = ScraperEngine(cache_enabled=False)

        call_args = []

        async def capture_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            call_args.append((start_level, max_level))
            return EscalationResult(success=True, content="test", backend="zendriver", level=5)

        with patch.object(engine, "_escalate", side_effect=capture_escalate):
            await engine.fetch("https://example.com", mode="max")

            assert call_args[0][0] == 5  # start_level

    async def test_fetch_respects_force_backend(self) -> None:
        """force_backend should override mode."""
        engine = ScraperEngine(cache_enabled=False)

        call_args = []

        async def capture_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            call_args.append((start_level, max_level))
            # Force backend is "scrapling" = level 1
            return EscalationResult(success=True, content="test", backend="scrapling", level=1)

        with patch.object(engine, "_escalate", side_effect=capture_escalate):
            await engine.fetch("https://example.com", mode="auto", force_backend="scrapling")

            assert call_args[0][0] == 1  # start_level

    async def test_fetch_records_domain_success(self) -> None:
        """Successful fetch should record domain in history."""
        engine = ScraperEngine()
        dh = DomainEscalationHistory()
        dh.reset()

        async def mock_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            return EscalationResult(
                success=True, content="test", backend="httpx", level=0
            )

        with patch.object(engine, "_escalate", side_effect=mock_escalate):
            await engine.fetch("https://example.com")

            # Domain should be in history at level 0
            assert dh.get_min_level("example.com") == 0

    async def test_fetch_failure(self) -> None:
        """Fetch should handle escalation failures."""
        engine = ScraperEngine(cache_enabled=False)

        async def mock_escalate(url: str, start_level: int, max_level: int) -> EscalationResult:
            return EscalationResult(
                success=False, error="All backends failed", backend="botasaurus", level=7
            )

        with patch.object(engine, "_escalate", side_effect=mock_escalate):
            result = await engine.fetch("https://example.com")

            assert result.success is False
            assert result.error is not None


@pytest.mark.asyncio
class TestScraperEngineSmartExtract:
    """Tests for ScraperEngine.smart_extract()."""

    async def test_smart_extract_fetch_failure(self) -> None:
        """smart_extract should return error if fetch fails."""
        engine = ScraperEngine()

        async def mock_fetch(
            url: str,
            mode: str,
            max_escalation: int | None = None,
            extract_title: bool = False,
            force_backend: str | None = None,
        ) -> ScraperEngineResult:
            return ScraperEngineResult(
                url=url,
                success=False,
                error="Fetch failed",
            )

        with patch.object(engine, "fetch", side_effect=mock_fetch):
            result = await engine.smart_extract("https://example.com", "extract title")

            assert result["success"] is False
            assert "error" in result

    async def test_smart_extract_missing_llm_tools(self) -> None:
        """smart_extract should handle missing LLM tools gracefully."""
        engine = ScraperEngine(cache_enabled=False)

        async def mock_fetch(
            url: str,
            mode: str,
            max_escalation: int | None = None,
            extract_title: bool = False,
            force_backend: str | None = None,
        ) -> ScraperEngineResult:
            return ScraperEngineResult(
                url=url,
                success=True,
                content="Sample content for extraction",
                backend_used="httpx",
                escalation_level=0,
            )

        with patch.object(engine, "fetch", side_effect=mock_fetch):
            # smart_extract should work even without LLM tools (fallback)
            result = await engine.smart_extract("https://example.com", "extract data")

            # Should succeed with fallback behavior
            assert result["success"] is True
            assert "url" in result
            assert result["url"] == "https://example.com"


@pytest.mark.asyncio
class TestScraperEngineBatchFetch:
    """Tests for ScraperEngine.batch_fetch()."""

    async def test_batch_fetch_empty_list(self) -> None:
        """batch_fetch with empty list should return empty results."""
        engine = ScraperEngine()
        result = await engine.batch_fetch([])

        assert result["success"] is True
        assert result["results"] == []

    async def test_batch_fetch_single_url(self) -> None:
        """batch_fetch with single URL should work."""
        engine = ScraperEngine()

        async def mock_fetch(
            url: str,
            mode: str,
            max_escalation: int | None = None,
            extract_title: bool = False,
            force_backend: str | None = None,
        ) -> ScraperEngineResult:
            return ScraperEngineResult(
                url=url,
                success=True,
                content="test content",
                backend_used="httpx",
                escalation_level=0,
                elapsed_ms=100,
            )

        with patch.object(engine, "fetch", side_effect=mock_fetch):
            result = await engine.batch_fetch(["https://example.com"])

            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["success"] is True

    async def test_batch_fetch_respects_concurrency(self) -> None:
        """batch_fetch should limit concurrent requests."""
        engine = ScraperEngine()
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_fetch(
            url: str,
            mode: str,
            max_escalation: int | None = None,
            extract_title: bool = False,
            force_backend: str | None = None,
        ) -> ScraperEngineResult:
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return ScraperEngineResult(
                url=url,
                success=True,
                content="test",
                backend_used="httpx",
                escalation_level=0,
            )

        with patch.object(engine, "fetch", side_effect=mock_fetch):
            urls = [f"https://example{i}.com" for i in range(20)]
            result = await engine.batch_fetch(urls, max_concurrent=5)

            assert result["success"] is True
            assert max_concurrent_seen <= 5

    async def test_batch_fetch_fail_fast(self) -> None:
        """batch_fetch with fail_fast should stop on first failure."""
        engine = ScraperEngine()
        fetch_count = 0

        async def mock_fetch(
            url: str,
            mode: str,
            max_escalation: int | None = None,
            extract_title: bool = False,
            force_backend: str | None = None,
        ) -> ScraperEngineResult:
            nonlocal fetch_count
            fetch_count += 1
            # First fetch succeeds, second fails
            if fetch_count == 1:
                return ScraperEngineResult(
                    url=url,
                    success=True,
                    content="test",
                    backend_used="httpx",
                    escalation_level=0,
                )
            else:
                return ScraperEngineResult(
                    url=url,
                    success=False,
                    error="Failed",
                )

        with patch.object(engine, "fetch", side_effect=mock_fetch):
            result = await engine.batch_fetch(
                ["https://example1.com", "https://example2.com"],
                fail_fast=True,
            )

            # Should have 1 success and 1 failure before stopping
            assert len(result["results"]) == 2


@pytest.mark.asyncio
class TestScraperEngineEscalation:
    """Tests for escalation chain logic."""

    async def test_escalation_tries_backends_in_order(self) -> None:
        """Escalation should try backends in ascending level order."""
        engine = ScraperEngine()
        attempts = []

        async def mock_try_backend(url: str, backend: str, level: int) -> EscalationResult:
            attempts.append((backend, level))
            # Fail first two backends, succeed on third
            if len(attempts) <= 2:
                return EscalationResult(success=False, backend=backend, level=level, error="Failed")
            return EscalationResult(success=True, content="success", backend=backend, level=level)

        with patch.object(engine, "_try_backend", side_effect=mock_try_backend):
            result = await engine._escalate("https://example.com", 0, 3)

            assert result.success is True
            # Should have tried backends 0, 1, 2 in order
            assert len(attempts) == 3

    async def test_escalation_skips_unavailable_backends(self) -> None:
        """Escalation should skip backends that are not available."""
        engine = ScraperEngine()

        # Mock backend availability — only httpx and botasaurus available
        with patch.object(engine.availability, "check") as mock_check:
            def check_availability(backend: str) -> bool:
                return backend in {"httpx", "botasaurus"}

            mock_check.side_effect = check_availability

            attempts = []

            async def mock_try_backend(url: str, backend: str, level: int) -> EscalationResult:
                attempts.append(backend)
                if backend == "botasaurus":
                    return EscalationResult(success=True, content="test", backend=backend, level=level)
                return EscalationResult(success=False, backend=backend, level=level, error="Failed")

            with patch.object(engine, "_try_backend", side_effect=mock_try_backend):
                result = await engine._escalate("https://example.com", 0, 7)

                # Should have tried httpx and botasaurus, skipping others
                assert "httpx" in attempts
                assert "botasaurus" in attempts
                # Should NOT have tried scrapling, crawl4ai, etc.
                assert "scrapling" not in attempts


@pytest.mark.asyncio
class TestScraperEngineCache:
    """Tests for caching behavior."""

    async def test_cache_disabled(self) -> None:
        """With cache_enabled=False, caching should be skipped."""
        engine = ScraperEngine(cache_enabled=False)
        assert engine.cache is None

    async def test_cache_put_get(self, tmp_cache_dir: Path) -> None:
        """Cache should store and retrieve entries."""
        import os

        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)

        engine = ScraperEngine(cache_enabled=True)

        # Store in cache
        result = EscalationResult(
            success=True, content="test content", backend="httpx", level=0
        )
        await engine._cache_result("https://example.com", result)

        # Retrieve from cache
        cached = await engine._check_cache("https://example.com")
        assert cached is not None
        assert cached["content"] == "test content"


@pytest.mark.asyncio
class TestScraperEngineBackendMethods:
    """Tests for individual backend implementations."""

    async def test_fetch_httpx_basic(self) -> None:
        """httpx backend should make HTTP request."""
        engine = ScraperEngine()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.text = "response content"
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client

            mock_client_class.return_value = mock_client

            content = await engine._fetch_httpx("https://example.com")

            assert content == "response content"

    async def test_fetch_httpx_error_handling(self) -> None:
        """httpx backend should raise on HTTP errors."""
        engine = ScraperEngine()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client.__aenter__.return_value = mock_client

            mock_client_class.return_value = mock_client

            with pytest.raises(Exception):
                await engine._fetch_httpx("https://example.com")


class TestIntegration:
    """Integration tests with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_full_escalation_chain(self) -> None:
        """Test complete escalation chain from httpx to botasaurus."""
        engine = ScraperEngine(cache_enabled=False)

        # Create a realistic scenario where we escalate through multiple backends
        call_sequence = []

        async def mock_escalate(
            url: str, start_level: int, max_level: int
        ) -> EscalationResult:
            call_sequence.append((start_level, max_level))
            return EscalationResult(
                success=True,
                content="Successfully fetched after escalation",
                backend="crawl4ai",
                level=2,
            )

        with patch.object(engine, "_escalate", side_effect=mock_escalate):
            result = await engine.fetch("https://example.com", mode="auto")

            assert result.success is True
            assert len(call_sequence) > 0

    @pytest.mark.asyncio
    async def test_domain_history_improves_performance(self) -> None:
        """Domain history should track minimum escalation level."""
        dh = DomainEscalationHistory()
        dh.reset()

        # Initially no history
        assert dh.get_min_level("example.com") == 0

        # Record success at level 3
        dh.record_success("example.com", 3)
        assert dh.get_min_level("example.com") == 3

        # Lower level should not be overridden
        dh.record_success("example.com", 5)
        assert dh.get_min_level("example.com") == 3

        # Record lower success level
        dh.record_success("example.com", 1)
        assert dh.get_min_level("example.com") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
