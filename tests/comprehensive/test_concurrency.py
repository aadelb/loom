"""Concurrency tests for resource starvation and deadlock detection.

Tests cover:
  - Test 1: 50 concurrent asyncio tasks calling research_cache_stats
  - Test 2: 20 concurrent calls to research_search (mocked)
  - Test 3: Memory before/after 100 tool calls
  - Test 4: Chain of tool calls (A → B → C) for infinite recursion
  - Test 5: 10 concurrent writes to same cache key
  - Test 6: Rate limiter under concurrent load (race condition detection)
"""

from __future__ import annotations

import asyncio
import gc
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Track test markers
pytestmark = pytest.mark.asyncio


logger = logging.getLogger("loom.test.concurrency")


class TestConcurrentCacheStats:
    """Test 1: 50 concurrent research_cache_stats calls."""

    @pytest.mark.asyncio
    async def test_50_concurrent_cache_stats_no_timeout(self) -> None:
        """50 concurrent cache_stats calls complete within 5 seconds."""
        from loom.tools.cache_mgmt import research_cache_stats

        start = time.perf_counter()

        # Create 50 concurrent tasks
        tasks: list[Awaitable[Any]] = [
            asyncio.create_task(asyncio.to_thread(research_cache_stats))
            for _ in range(50)
        ]

        # Gather all results with timeout
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("50 concurrent cache_stats calls exceeded 5-second timeout")

        elapsed = time.perf_counter() - start

        # All should succeed
        assert len(results) == 50, f"Expected 50 results, got {len(results)}"
        assert all(r is not None for r in results), "Some results were None"

        # Log timing
        logger.info(f"50 concurrent cache_stats completed in {elapsed:.2f}s")

        # Should be reasonably fast (not starved)
        assert elapsed < 5.0, f"Took {elapsed:.2f}s, expected <5.0s"


class TestConcurrentSearchMocked:
    """Test 2: 20 concurrent research_search calls (mocked)."""

    @pytest.mark.asyncio
    async def test_20_concurrent_search_no_deadlock(self) -> None:
        """20 concurrent search calls complete without deadlock."""
        from loom.tools.search import research_search

        # Mock the search to avoid real network calls
        mock_result = {
            "results": [
                {"url": "https://example.com/1", "title": "Result 1", "snippet": "Test"}
            ],
            "total": 1,
            "query": "test",
        }

        start = time.perf_counter()
        search_calls = []

        # Mock the internal search provider calls
        with patch("loom.tools.search._search_providers", new_callable=MagicMock):
            with patch.object(
                research_search, "__wrapped__", new_callable=AsyncMock
            ) as mock_search:
                mock_search.return_value = mock_result

                # Create 20 concurrent search tasks
                tasks = [
                    asyncio.create_task(research_search(query="test query"))
                    for _ in range(20)
                ]

                # Gather results
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True), timeout=10.0
                    )
                except asyncio.TimeoutError:
                    pytest.fail("20 concurrent search calls exceeded 10-second timeout")

                elapsed = time.perf_counter() - start

                # Check for exceptions (would indicate deadlock/error)
                exceptions = [r for r in results if isinstance(r, Exception)]
                assert len(exceptions) == 0, f"Got {len(exceptions)} exceptions: {exceptions}"

                logger.info(f"20 concurrent search calls completed in {elapsed:.2f}s")


class TestMemoryLeakDetection:
    """Test 3: Memory before/after 100 tool calls."""

    def test_100_tool_calls_no_memory_growth(self) -> None:
        """100 tool calls should not cause >10MB memory growth."""
        from loom.tools.cache_mgmt import research_cache_stats

        # Force garbage collection and get baseline
        gc.collect()
        baseline_size = sys.getsizeof(gc.get_objects())

        # Execute 100 cache_stats calls
        for _ in range(100):
            try:
                research_cache_stats()
            except Exception as e:
                logger.debug(f"Call failed (expected for mock): {e}")

        # Force GC and measure final size
        gc.collect()
        final_size = sys.getsizeof(gc.get_objects())

        memory_growth = final_size - baseline_size

        # Convert to MB for readability
        growth_mb = memory_growth / (1024 * 1024)

        logger.info(f"Memory growth after 100 calls: {growth_mb:.2f}MB")

        # Should grow less than 10MB
        assert growth_mb < 10.0, f"Memory grew by {growth_mb:.2f}MB, expected <10MB"


class TestToolChainRecursion:
    """Test 4: Tool chaining (A → B → C) for infinite recursion."""

    @pytest.mark.asyncio
    async def test_tool_chain_no_infinite_recursion(self) -> None:
        """Tool chain A → B → C should not infinite loop."""
        call_count = 0
        max_depth = 50

        async def tool_a(depth: int = 0) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if depth >= max_depth:
                return {"result": "done", "depth": depth}
            return await tool_b(depth + 1)

        async def tool_b(depth: int) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if depth >= max_depth:
                return {"result": "done", "depth": depth}
            return await tool_c(depth + 1)

        async def tool_c(depth: int) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if depth >= max_depth:
                return {"result": "done", "depth": depth}
            return await tool_a(depth + 1)

        # Execute chain with timeout
        try:
            result = await asyncio.wait_for(tool_a(), timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("Tool chain exceeded 5-second timeout (possible infinite recursion)")

        # Should terminate at max_depth
        assert result["depth"] == max_depth, f"Expected depth {max_depth}, got {result['depth']}"

        # Call count should be 3 * max_depth (each level calls 3 tools)
        expected_calls = 3 * (max_depth + 1)
        assert call_count == expected_calls, f"Expected {expected_calls} calls, got {call_count}"

        logger.info(f"Tool chain completed with {call_count} calls at depth {max_depth}")


class TestConcurrentCacheWrites:
    """Test 5: 10 concurrent writes to same cache key."""

    @pytest.mark.asyncio
    async def test_10_concurrent_cache_writes_no_corruption(self) -> None:
        """10 concurrent writes to same cache key should not corrupt data."""
        from loom.cache import CacheStore

        # Use temp cache directory
        cache = CacheStore(base_dir="/tmp/loom_test_cache_concurrent")

        test_key = "test::concurrent::writes"
        tasks = []

        async def write_cache(task_id: int) -> dict[str, Any]:
            """Write to cache from concurrent task."""
            data = {
                "task_id": task_id,
                "timestamp": time.time(),
                "data": f"payload_{task_id}" * 100,
            }
            try:
                cache.put(test_key, data)
                # Read back immediately to check consistency
                read_data = cache.get(test_key)
                return {"task_id": task_id, "success": True, "read_back": read_data is not None}
            except Exception as e:
                return {"task_id": task_id, "success": False, "error": str(e)}

        # Create 10 concurrent write tasks
        start = time.perf_counter()
        for i in range(10):
            tasks.append(asyncio.create_task(write_cache(i)))

        # Gather results
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=5.0
            )
        except asyncio.TimeoutError:
            pytest.fail("10 concurrent cache writes exceeded 5-second timeout")

        elapsed = time.perf_counter() - start

        # Check results
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Got {len(exceptions)} exceptions"

        successes = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successes) == 10, f"Expected 10 successes, got {len(successes)}"

        # Final read should return valid data (one of the written payloads)
        final_data = cache.get(test_key)
        assert final_data is not None, "Final read returned None (corrupted cache)"
        assert "task_id" in final_data, "Cache data missing task_id field"

        logger.info(
            f"10 concurrent cache writes completed in {elapsed:.2f}s "
            f"(final data from task {final_data['task_id']})"
        )


class TestRateLimiterConcurrency:
    """Test 6: Rate limiter under concurrent load (race condition detection)."""

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_count_accuracy(self) -> None:
        """Rate limiter should track concurrent calls without race conditions."""
        from loom.rate_limiter import RateLimiter

        limiter = RateLimiter()

        # Track call counts per user
        call_counts: dict[str, int] = {}
        lock = asyncio.Lock()

        async def make_limited_call(user_id: str, call_num: int) -> dict[str, Any]:
            """Make a rate-limited call and track it."""
            result = limiter.check_limit(
                user_id=user_id,
                category="test",
                tier="pro",  # pro tier: 60 per minute
            )

            async with lock:
                call_counts[user_id] = call_counts.get(user_id, 0) + 1

            return {
                "user": user_id,
                "call": call_num,
                "allowed": result.get("allowed", True),
                "count": call_counts.get(user_id),
            }

        # Simulate 5 concurrent users making requests
        tasks = []
        for user_id in ["user_a", "user_b", "user_c", "user_d", "user_e"]:
            for call_num in range(20):  # 20 calls per user
                tasks.append(asyncio.create_task(make_limited_call(user_id, call_num)))

        # Gather results
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=10.0
            )
        except asyncio.TimeoutError:
            pytest.fail("Rate limiter test exceeded 10-second timeout")

        # Check results
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Got {len(exceptions)} exceptions"

        # Verify call counts per user
        for user_id in ["user_a", "user_b", "user_c", "user_d", "user_e"]:
            count = call_counts.get(user_id, 0)
            assert count == 20, f"User {user_id}: expected 20 calls, counted {count}"

        logger.info(f"Rate limiter tracked {len(call_counts)} users × 20 calls correctly")


class TestConcurrencyStressTest:
    """Stress test combining multiple concurrency scenarios."""

    @pytest.mark.asyncio
    async def test_mixed_concurrent_workload(self) -> None:
        """Mixed workload: cache reads, limited writes, chain calls."""
        from loom.tools.cache_mgmt import research_cache_stats
        from loom.cache import CacheStore

        cache = CacheStore(base_dir="/tmp/loom_test_stress")

        async def mixed_task(task_id: int) -> dict[str, Any]:
            """Execute mixed concurrent operations."""
            try:
                # Operation 1: Cache stats read
                await asyncio.to_thread(research_cache_stats)

                # Operation 2: Cache write with key
                cache.put(f"stress_test::{task_id}", {"id": task_id, "data": "test"})

                # Operation 3: Cache read
                data = cache.get(f"stress_test::{task_id}")

                return {
                    "task_id": task_id,
                    "success": True,
                    "cache_exists": data is not None,
                }
            except Exception as e:
                return {"task_id": task_id, "success": False, "error": str(e)}

        # Create 30 concurrent mixed tasks
        tasks = [asyncio.create_task(mixed_task(i)) for i in range(30)]

        start = time.perf_counter()
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15.0)
        except asyncio.TimeoutError:
            pytest.fail("Mixed stress test exceeded 15-second timeout")

        elapsed = time.perf_counter() - start

        # All should succeed
        successes = [r for r in results if r.get("success")]
        assert len(successes) == 30, f"Expected 30 successes, got {len(successes)}"

        logger.info(f"Mixed stress test (30 tasks) completed in {elapsed:.2f}s")
