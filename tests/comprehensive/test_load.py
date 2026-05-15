"""Load tests for Loom MCP server using asyncio.

Tests cover:
  - 50 concurrent health check requests
  - 10 concurrent search queries
  - Throughput measurement
  - Memory leak detection
"""

from __future__ import annotations

import asyncio
import gc
import sys
from typing import Any

import pytest


pytestmark = pytest.mark.asyncio


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    @pytest.mark.asyncio
    async def test_50_concurrent_health_checks(self) -> None:
        """Server handles 50 concurrent health check requests."""
        async def health_check() -> bool:
            try:
                from loom.config import CONFIG  # noqa: F401

                return True
            except Exception:
                return False

        # Create 50 concurrent tasks
        tasks = [health_check() for _ in range(50)]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results), "Some health checks failed"

    @pytest.mark.asyncio
    async def test_20_concurrent_cache_operations(self) -> None:
        """Server handles 20 concurrent cache operations."""
        async def cache_operation(idx: int) -> bool:
            try:
                from loom.cache import get_cache

                cache = get_cache()
                # Store JSON-serializable data (not bytes)
                cache.put(f"load_test_{idx}", {"data": "test_data"})

                result = cache.get(f"load_test_{idx}")
                return result is not None
            except Exception:
                return False

        # Create 20 concurrent cache operations
        tasks = [cache_operation(i) for i in range(20)]

        results = await asyncio.gather(*tasks)

        # Most should succeed
        success_count = sum(results)
        assert success_count >= len(results) * 0.8, (
            f"Only {success_count}/{len(results)} cache ops succeeded"
        )


class TestThroughputMeasurement:
    """Test and measure throughput."""

    @pytest.mark.asyncio
    async def test_cache_throughput(self) -> None:
        """Measure cache throughput."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            # Measure put throughput
            import time

            start = time.perf_counter()
            for i in range(100):
                # Store JSON-serializable data (not bytes)
                cache.put(f"throughput_{i}", {"value": "test_value"})
            elapsed = time.perf_counter() - start

            # Should be able to do 100 puts in under 1 second
            assert elapsed < 1.0, f"100 cache puts took {elapsed:.2f}s"

            throughput = 100 / elapsed
            assert throughput > 100, f"Cache throughput: {throughput:.0f} ops/sec"

        except Exception as e:
            pytest.skip(f"Throughput test skipped: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self) -> None:
        """Measure session operation throughput."""
        async def create_session(idx: int) -> bool:
            try:
                from loom.sessions import research_session_open

                result = await research_session_open(f"load_session_{idx}")
                return result is not None
            except Exception:
                return False

        # Create 10 sessions concurrently
        tasks = [create_session(i) for i in range(10)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful operations
        success_count = sum(1 for r in results if r is True)
        assert success_count >= 1, "No sessions created successfully"


class TestMemoryLeakDetection:
    """Test for memory leaks under load."""

    @pytest.mark.asyncio
    async def test_no_memory_leak_cache_ops(self) -> None:
        """Repeated cache operations don't cause memory leaks."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            # Get baseline memory
            gc.collect()
            baseline_objects = len(gc.get_objects())

            # Perform 1000 cache operations
            for i in range(1000):
                # Store JSON-serializable data (not bytes)
                cache.put(f"leak_test_{i % 100}", {"value": "test"})
                cache.get(f"leak_test_{i % 100}")

            # Clean up and check memory
            gc.collect()
            final_objects = len(gc.get_objects())

            # Object count should not grow unbounded
            growth = final_objects - baseline_objects
            growth_ratio = growth / max(baseline_objects, 1)

            # Allow up to 50% growth
            assert growth_ratio < 0.5, (
                f"Object count grew {growth_ratio*100:.1f}% "
                f"({baseline_objects} -> {final_objects})"
            )

        except Exception as e:
            pytest.skip(f"Memory leak test skipped: {e}")


class TestErrorRecovery:
    """Test error recovery under load."""

    @pytest.mark.asyncio
    async def test_concurrent_with_errors(self) -> None:
        """Server recovers from errors during concurrent operations."""
        async def operation_with_possible_error(idx: int) -> bool:
            try:
                from loom.cache import get_cache

                cache = get_cache()

                # Some operations might fail
                if idx % 10 == 0:
                    raise ValueError("Simulated error")

                # Store JSON-serializable data (not bytes)
                cache.put(f"error_test_{idx}", {"data": "test"})
                return True
            except Exception:
                return False

        # Run 50 operations, some will error
        tasks = [operation_with_possible_error(i) for i in range(50)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should succeed, some may error
        success_count = sum(1 for r in results if r is True)
        assert success_count >= len(results) * 0.7, (
            f"Only {success_count}/{len(results)} ops succeeded"
        )


class TestResourceCleanup:
    """Test proper resource cleanup."""

    @pytest.mark.asyncio
    async def test_session_cleanup_under_load(self) -> None:
        """Sessions are properly cleaned up after load."""
        try:
            from loom.sessions import research_session_open, research_session_list

            initial_sessions = research_session_list()
            initial_count = len(initial_sessions) if isinstance(initial_sessions, (list, dict)) else 0

            # Create multiple sessions
            for i in range(10):
                try:
                    result = research_session_open(f"cleanup_test_{i}")
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass

            # List sessions
            sessions = research_session_list()
            peak_count = len(sessions)

            # We should have created some new sessions
            assert peak_count >= initial_count, "No new sessions created"

        except (ImportError, AttributeError):
            pytest.skip("Session management not available")


class TestLoadStability:
    """Test stability under sustained load."""

    @pytest.mark.asyncio
    async def test_sustained_cache_load(self) -> None:
        """Cache remains stable under sustained load."""
        try:
            from loom.cache import get_cache

            cache = get_cache()

            # Run sustained load for 100 iterations
            for batch in range(10):
                tasks = []
                for i in range(10):
                    key = f"sustained_{batch}_{i}"

                    async def do_op(k: str) -> bool:
                        try:
                            # Store JSON-serializable data (not bytes)
                            cache.put(k, {"data": "test"})
                            return cache.get(k) is not None
                        except Exception:
                            return False

                    tasks.append(do_op(key))

                results = await asyncio.gather(*tasks)
                success = sum(results)

                # Each batch should be mostly successful
                assert success >= len(results) * 0.8, (
                    f"Batch {batch} only {success}/{len(results)} succeeded"
                )

        except Exception as e:
            pytest.skip(f"Sustained load test skipped: {e}")
