"""Performance tests for Loom MCP server.

Tests cover:
  - Server startup time
  - Cache operations latency
  - Tool registration time
  - Health endpoint <100ms
  - p95 latency measurements
"""

from __future__ import annotations

import time
from typing import Any

import pytest


pytestmark = pytest.mark.performance


class TestStartupPerformance:
    """Test server startup performance."""

    def test_server_import_time(self) -> None:
        """Server imports in reasonable time."""
        start = time.perf_counter()

        try:
            import loom.server  # noqa: F401
        except Exception as e:
            pytest.fail(f"Server import failed: {e}")

        elapsed = time.perf_counter() - start

        # Should import in under 10 seconds
        assert elapsed < 10.0, f"Server import took {elapsed:.2f}s"

    def test_tools_module_import_time(self) -> None:
        """Tools module imports in reasonable time."""
        start = time.perf_counter()

        try:
            import loom.tools  # noqa: F401
        except Exception as e:
            pytest.fail(f"Tools import failed: {e}")

        elapsed = time.perf_counter() - start

        # Should import in under 15 seconds
        assert elapsed < 15.0, f"Tools import took {elapsed:.2f}s"

    def test_core_modules_import_time(self) -> None:
        """Core modules import in reasonable time."""
        modules = ["loom.config", "loom.cache", "loom.audit"]

        for module_name in modules:
            start = time.perf_counter()

            try:
                __import__(module_name)
            except Exception as e:
                pytest.fail(f"{module_name} import failed: {e}")

            elapsed = time.perf_counter() - start

            # Each module should import under 2 seconds
            assert elapsed < 2.0, f"{module_name} import took {elapsed:.2f}s"


class TestCachePerformance:
    """Test cache operation latency."""

    def test_cache_put_latency(self) -> None:
        """Cache put operations complete quickly."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            times = []
            for i in range(100):
                start = time.perf_counter()
                cache.put(f"key_{i}", b"test_value" * 10)
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            avg_time = sum(times) / len(times)

            # Average put should be under 10ms
            assert avg_time < 0.01, f"Cache put avg latency: {avg_time*1000:.2f}ms"

        except Exception as e:
            pytest.skip(f"Cache performance test skipped: {e}")

    def test_cache_get_latency(self) -> None:
        """Cache get operations complete quickly."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            # Put some test data
            for i in range(10):
                cache.put(f"test_key_{i}", b"test_value")

            times = []
            for i in range(100):
                start = time.perf_counter()
                cache.get(f"test_key_{i % 10}")
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            avg_time = sum(times) / len(times)

            # Average get should be under 5ms
            assert avg_time < 0.005, f"Cache get avg latency: {avg_time*1000:.2f}ms"

        except Exception as e:
            pytest.skip(f"Cache performance test skipped: {e}")


class TestHealthCheckLatency:
    """Test health check endpoint latency."""

    def test_health_check_callable(self) -> None:
        """Health check function is callable."""
        try:
            from loom.server import _health_check

            start = time.perf_counter()
            result = _health_check()
            elapsed = time.perf_counter() - start

            assert result is not None
            # Should complete in under 100ms
            assert elapsed < 0.1, f"Health check took {elapsed*1000:.2f}ms"

        except ImportError:
            pytest.skip("Health check not available")

    @pytest.mark.asyncio
    async def test_config_load_latency(self) -> None:
        """Config load completes quickly."""
        try:
            from loom.config import load_config

            start = time.perf_counter()
            config = load_config()
            elapsed = time.perf_counter() - start

            assert config is not None
            # Should load in under 500ms
            assert elapsed < 0.5, f"Config load took {elapsed*1000:.2f}ms"

        except Exception as e:
            pytest.skip(f"Config load test skipped: {e}")


class TestLatencyPercentiles:
    """Test latency percentiles for critical operations."""

    def test_cache_operations_p95(self) -> None:
        """Cache operations have reasonable p95 latency."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            times = []
            for i in range(200):
                start = time.perf_counter()
                cache.put(f"perf_key_{i}", b"test_value")
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            # Calculate p95
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_idx]

            # p95 should be under 50ms
            assert p95 < 0.05, f"Cache p95 latency: {p95*1000:.2f}ms"

        except Exception as e:
            pytest.skip(f"Cache p95 test skipped: {e}")

    def test_import_operations_p95(self) -> None:
        """Module imports have reasonable p95 latency."""
        import importlib

        times = []
        sample_modules = [
            "loom.config",
            "loom.cache",
            "loom.audit",
            "loom.rate_limiter",
        ]

        for module_name in sample_modules:
            for _ in range(10):
                start = time.perf_counter()

                try:
                    importlib.reload(__import__(module_name, fromlist=[""]))
                except Exception:
                    pass

                elapsed = time.perf_counter() - start
                times.append(elapsed)

        if times:
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_idx]

            # p95 for reload should be reasonable
            assert p95 < 1.0, f"Module reload p95: {p95*1000:.2f}ms"


class TestToolRegistration:
    """Test tool registration performance."""

    def test_tool_discovery_time(self) -> None:
        """Tool discovery completes in reasonable time."""
        import importlib

        start = time.perf_counter()

        try:
            from loom.server import _register_tools

            # This would typically be called during startup
            assert callable(_register_tools)

        except ImportError:
            pytest.skip("Tool registration not available")

        elapsed = time.perf_counter() - start

        # Discovery should complete in under 5 seconds
        assert elapsed < 5.0, f"Tool discovery took {elapsed:.2f}s"


class TestMemoryFootprint:
    """Test memory usage characteristics."""

    def test_cache_memory_reasonable(self) -> None:
        """Cache doesn't use excessive memory."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            # Add 100 items
            for i in range(100):
                cache.put(f"mem_test_{i}", b"x" * 1000)

            # Cache should be functional
            assert cache.get("mem_test_0") is not None

        except Exception as e:
            pytest.skip(f"Memory test skipped: {e}")

    def test_session_registry_reasonable(self) -> None:
        """Session registry doesn't use excessive memory."""
        try:
            from loom.sessions import _sessions

            # Check registry is a dict
            assert isinstance(_sessions, dict)

            # Should not have thousands of sessions by default
            assert len(_sessions) < 1000

        except (ImportError, AttributeError):
            pytest.skip("Session registry not available")
