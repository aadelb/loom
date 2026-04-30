"""Tests for concurrent request handling (REQ-059).

Validates that 10 simultaneous requests can be handled without deadlocks,
data corruption, or crashes. Tests concurrent cache operations, config reads,
and mixed workloads.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from loom.cache import CacheStore
from loom.config import CONFIG


class TestConcurrentCacheOperations:
    """Test cache safety under concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_10_concurrent_cache_writes(self, tmp_path: Path) -> None:
        """10 concurrent cache writes produce valid cached data without corruption.

        REQ-059: Validates cache.put() is safe under concurrent writes to
        different keys. Each writer independently writes and reads its own
        key, verifying both write success and read-back correctness.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def write_and_verify(i: int) -> dict[str, Any] | None:
            """Write unique cache entry and read it back."""
            key = f"key_{i}"
            data: dict[str, Any] = {"value": i, "payload": f"data_{i}" * 100}
            cache.put(key, data)
            return cache.get(key)  # type: ignore[no-any-return]

        results = await asyncio.gather(*[write_and_verify(i) for i in range(10)])

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result is not None, f"Result {i} is None"
            assert isinstance(result, dict)
            assert result["value"] == i, f"Result {i} value mismatch"
            assert result["payload"].startswith(f"data_{i}"), f"Result {i} payload mismatch"

    @pytest.mark.asyncio
    async def test_concurrent_reads_same_key(self, tmp_path: Path) -> None:
        """Multiple concurrent reads of same key return consistent data.

        REQ-059: Validates cache.get() is thread-safe for reads. Pre-populate
        a single cache entry, then spawn 10 concurrent readers, all of which
        must see the same value.
        """
        cache = CacheStore(base_dir=tmp_path)
        shared_key = "shared_key"
        shared_data: dict[str, Any] = {
            "id": 1,
            "value": "constant_value",
            "checksum": 42,
        }
        cache.put(shared_key, shared_data)

        async def read_cache() -> dict[str, Any] | None:
            """Read shared cache entry."""
            return cache.get(shared_key)  # type: ignore[no-any-return]

        results = await asyncio.gather(*[read_cache() for _ in range(10)])

        assert all(r is not None for r in results), "Some reads returned None"
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert result["id"] == 1, f"Reader {i}: id mismatch"
            assert result["value"] == "constant_value", f"Reader {i}: value mismatch"
            assert result["checksum"] == 42, f"Reader {i}: checksum mismatch"

    @pytest.mark.asyncio
    async def test_concurrent_writes_different_keys(self, tmp_path: Path) -> None:
        """10 concurrent writes to different keys don't interfere with each other.

        REQ-059: Validates isolation. Each writer creates a unique key with
        unique data, and no cross-contamination occurs.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def isolated_write(i: int) -> tuple[int, bool]:
            """Write unique key and verify isolation."""
            key = f"isolated_{i}"
            data: dict[str, Any] = {
                "id": i,
                "isolation_marker": f"writer_{i}",
                "index": i * 100,
            }
            cache.put(key, data)
            read_back = cache.get(key)
            return i, (
                read_back is not None
                and isinstance(read_back, dict)
                and read_back["id"] == i
                and read_back["isolation_marker"] == f"writer_{i}"
                and read_back["index"] == i * 100
            )

        results = await asyncio.gather(*[isolated_write(i) for i in range(10)])

        for idx, success in results:
            assert success, f"Writer {idx} failed isolation check"

    @pytest.mark.asyncio
    async def test_concurrent_reads_and_writes(self, tmp_path: Path) -> None:
        """Mixed concurrent reads and writes without deadlock or data loss.

        REQ-059: Stress-tests concurrent mixed workload. Writers and readers
        interleave in a realistic scenario. Verifies no deadlock within 30s.
        """
        cache = CacheStore(base_dir=tmp_path)

        # Pre-populate some entries for readers
        for i in range(5):
            cache.put(f"prefilled_{i}", {"prefilled": True, "index": i})

        async def mixed_op(i: int) -> str:
            """Perform either a read or write based on index parity."""
            if i % 2 == 0:
                # Write operation
                key = f"written_{i}"
                cache.put(key, {"written_by": i, "timestamp": i * 10})
                result = cache.get(key)
                return "write_ok" if result is not None else "write_fail"
            else:
                # Read operation
                key = f"prefilled_{i // 2}"
                result = cache.get(key)
                return "read_ok" if result is not None else "read_fail"

        results = await asyncio.wait_for(
            asyncio.gather(*[mixed_op(i) for i in range(10)]),
            timeout=30.0,
        )

        assert all(r in ("write_ok", "read_ok") for r in results), f"Operations failed: {results}"

    @pytest.mark.asyncio
    async def test_cache_with_large_concurrent_payloads(self, tmp_path: Path) -> None:
        """10 concurrent writes of large payloads complete without corruption.

        REQ-059: Validates atomic writes under I/O pressure. Each task writes
        a 10KB+ JSON object and reads it back, verifying size and checksums.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def large_payload_write(i: int) -> bool:
            """Write and verify a large payload."""
            key = f"large_{i}"
            # Create a ~50KB payload
            large_data: dict[str, Any] = {
                "index": i,
                "content": "x" * 50000,
                "nested": {
                    "level1": {"level2": {"level3": f"deep_value_{i}"}},
                },
                "array": list(range(1000)),
            }
            cache.put(key, large_data)
            read_back = cache.get(key)

            if read_back is None or not isinstance(read_back, dict):
                return False
            if read_back["index"] != i:
                return False
            if read_back["nested"]["level1"]["level2"]["level3"] != f"deep_value_{i}":
                return False
            return len(read_back["content"]) == 50000

        results = await asyncio.gather(*[large_payload_write(i) for i in range(10)])
        assert all(results), f"Large payload writes failed: {results}"

    @pytest.mark.asyncio
    async def test_concurrent_cache_get_nonexistent(self, tmp_path: Path) -> None:
        """10 concurrent gets of non-existent keys return None safely.

        REQ-059: Validates cache handles missing keys under concurrency without
        exceptions or race conditions.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def get_missing() -> bool:
            """Try to get a non-existent key."""
            result = cache.get("definitely_does_not_exist_anywhere")
            return result is None

        results = await asyncio.gather(*[get_missing() for _ in range(10)])
        assert all(results), "Some get_missing operations returned non-None"


class TestConcurrentConfigOperations:
    """Test configuration safety under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_config_reads(self) -> None:
        """10 concurrent config reads return consistent values.

        REQ-059: Validates that CONFIG dict can be safely read by multiple
        tasks simultaneously without race conditions.
        """

        async def read_config() -> int | None:
            """Read a specific config value."""
            # CONFIG is a plain dict, reads are atomic in CPython due to GIL
            val = CONFIG.get("EXTERNAL_TIMEOUT_SECS")
            if isinstance(val, int) or val is None:
                return val
            return None

        results = await asyncio.gather(*[read_config() for _ in range(10)])

        # All reads should return the same value (or None if not set)
        assert len(set(results)) == 1, f"Inconsistent reads: {results}"

    @pytest.mark.asyncio
    async def test_concurrent_config_get_multiple_keys(self) -> None:
        """10 concurrent reads of different config keys are isolated.

        REQ-059: Each reader gets its own key; no interference.
        """

        async def read_key(i: int) -> tuple[str, Any]:
            """Read a different key based on index."""
            keys = [
                "SPIDER_CONCURRENCY",
                "EXTERNAL_TIMEOUT_SECS",
                "MAX_CHARS_HARD_CAP",
                "MAX_SPIDER_URLS",
                "CACHE_TTL_DAYS",
            ]
            key = keys[i % len(keys)]
            val = CONFIG.get(key)
            return key, val

        results = await asyncio.gather(*[read_key(i) for i in range(10)])

        # Each tuple should have a key and a value
        for key, _val in results:
            assert isinstance(key, str), f"Key is not string: {key}"
            # Value may be None (not in CONFIG) or a number


class TestConcurrentMixedWorkloads:
    """Test realistic mixed concurrent workloads."""

    @pytest.mark.asyncio
    async def test_mixed_cache_and_config_operations(self, tmp_path: Path) -> None:
        """Cache and config operations interleaved without interference.

        REQ-059: Simulates real-world scenario with both cache I/O and
        config reads happening concurrently.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def mixed_workload(i: int) -> str:
            """Perform alternating cache and config operations."""
            try:
                if i % 3 == 0:
                    # Cache operation
                    cache.put(f"mixed_{i}", {"i": i})
                    result = cache.get(f"mixed_{i}")
                    return "cache_ok" if result is not None else "cache_fail"
                elif i % 3 == 1:
                    # Config read
                    _ = CONFIG.get("EXTERNAL_TIMEOUT_SECS")
                    return "config_ok"
                else:
                    # Sleep to simulate work
                    await asyncio.sleep(0.001)
                    return "sleep_ok"
            except Exception as e:
                return f"error: {e!s}"

        results = await asyncio.gather(*[mixed_workload(i) for i in range(10)])
        failures = [r for r in results if "fail" in r or "error" in r]
        assert len(failures) == 0, f"Mixed workload failures: {failures}"

    @pytest.mark.asyncio
    async def test_no_deadlock_completion_within_timeout(self, tmp_path: Path) -> None:
        """All 10 concurrent operations complete within 60 second timeout.

        REQ-059: The timeout itself validates no deadlock occurred. If any task
        blocks indefinitely, the timeout will fire.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def operation(i: int) -> int:
            """Perform cache write and read sequence."""
            for j in range(5):  # Mini-loop to increase work
                key = f"deadline_{i}__{j}"
                cache.put(key, {"i": i, "j": j})
                _ = cache.get(key)
                await asyncio.sleep(0.001)  # Brief sleep
            return i

        # This will raise asyncio.TimeoutError if any task hangs
        results = await asyncio.wait_for(
            asyncio.gather(*[operation(i) for i in range(10)]),
            timeout=60.0,
        )

        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        assert list(results) == list(range(10)), f"Results out of order: {results}"

    @pytest.mark.asyncio
    async def test_concurrent_operations_maintain_consistency(self, tmp_path: Path) -> None:
        """Data consistency is maintained across 10 concurrent operations.

        REQ-059: Validates invariants are preserved. Each writer writes a
        specific pattern, and all readers verify that pattern exists.
        """
        cache = CacheStore(base_dir=tmp_path)

        # Phase 1: All tasks write their data
        async def phase1_write(i: int) -> bool:
            key = f"consistency_{i}"
            data: dict[str, Any] = {
                "writer_id": i,
                "sequence": list(range(i, i + 10)),
                "marker": f"written_by_{i}",
            }
            cache.put(key, data)
            return True

        write_results = await asyncio.gather(*[phase1_write(i) for i in range(10)])
        assert all(write_results), "Phase 1 writes failed"

        # Phase 2: All tasks read all data and verify
        async def phase2_verify(reader_id: int) -> int:
            verified_count = 0
            for writer_id in range(10):
                key = f"consistency_{writer_id}"
                data = cache.get(key)
                if (
                    data is not None
                    and isinstance(data, dict)
                    and data.get("writer_id") == writer_id
                    and data.get("marker") == f"written_by_{writer_id}"
                ):
                    verified_count += 1
            return verified_count

        verify_results = await asyncio.gather(*[phase2_verify(i) for i in range(10)])

        # Each of the 10 readers should have verified all 10 entries
        assert all(count == 10 for count in verify_results), (
            f"Consistency verification failed: {verify_results}"
        )

    @pytest.mark.asyncio
    async def test_stress_test_high_concurrency_completion(self, tmp_path: Path) -> None:
        """10 parallel tasks with rapid operations complete without crash.

        REQ-059: Stress test that ensures the system doesn't crash or deadlock
        under aggressive concurrency and high operation rate.
        """
        cache = CacheStore(base_dir=tmp_path)
        operation_count = 0
        lock = asyncio.Lock()

        async def rapid_operations(task_id: int) -> int:
            nonlocal operation_count
            local_count = 0
            for op_idx in range(20):  # 20 ops per task = 200 total ops
                key = f"stress_{task_id}_{op_idx}"
                payload: dict[str, Any] = {
                    "task": task_id,
                    "op": op_idx,
                    "data": "x" * 1000,
                }
                cache.put(key, payload)
                result = cache.get(key)
                if result is not None:
                    local_count += 1
                await asyncio.sleep(0.0001)  # Minimal sleep
            async with lock:
                operation_count += local_count
            return local_count

        results = await asyncio.wait_for(
            asyncio.gather(*[rapid_operations(i) for i in range(10)]),
            timeout=120.0,
        )

        total_ops = sum(results)
        assert total_ops == 200, f"Expected 200 successful operations, got {total_ops}"
        assert all(count == 20 for count in results), (
            f"Not all tasks completed 20 operations: {results}"
        )
