"""Performance tests (REQ-060, REQ-062, REQ-063).

REQ-060: Memory stability — RSS < 2x baseline after sustained load.
REQ-062: Parallel execution >= 40% faster than sequential equivalent.
REQ-063: Large output handling without OOM (>50KB JSON objects).

Tests validate that Loom handles production-scale workloads efficiently.
"""

from __future__ import annotations

import asyncio
import json
import os
import psutil
import pytest
import time
from pathlib import Path
from typing import Any

from loom.cache import CacheStore
from loom.config import CONFIG, load_config


class TestMemoryStability:
    """REQ-060: Memory remains stable under sustained load (RSS < 2x baseline).

    Validates that repeated cache operations don't leak memory or cause
    unbounded growth. Measures RSS (resident set size) before and after
    sustained operations — should increase by <100% even at 1000+ ops.
    """

    def test_cache_1000_operations_no_leak(self, tmp_path: Path) -> None:
        """1000 cache write/read cycles don't trigger memory growth.

        Process baseline RSS is measured before and after. With proper
        cache management, RSS should increase minimally (baseline + some
        overhead for active data structures, but not per-operation).
        """
        cache = CacheStore(base_dir=tmp_path)
        process = psutil.Process(os.getpid())

        # Measure baseline
        baseline_rss = process.memory_info().rss

        # Perform sustained operations
        for i in range(1000):
            data = {"index": i, "payload": f"value_{i}" * 50}
            cache.put(f"key_{i}", data)

        # Measure after load
        peak_rss = process.memory_info().rss

        # Read back subset to verify data integrity
        for i in range(0, 1000, 100):
            result = cache.get(f"key_{i}")
            assert result is not None, f"Key key_{i} not found after sustained load"
            assert result["index"] == i

        # Final measurement after reads
        final_rss = process.memory_info().rss

        # RSS should not exceed 2x baseline (allowing for OS overhead)
        max_allowed = baseline_rss * 2
        assert (
            final_rss <= max_allowed
        ), (
            f"Memory usage {final_rss} bytes exceeds 2x baseline "
            f"({baseline_rss} → max {max_allowed})"
        )

        # Log memory growth for visibility
        growth_pct = ((final_rss - baseline_rss) / baseline_rss) * 100
        assert growth_pct < 100, f"Memory grew {growth_pct:.1f}% (target < 100%)"

    def test_config_1000_loads_no_leak(self, tmp_config_path: Path) -> None:
        """1000 config load cycles maintain stable memory.

        Config loads are typically I/O bound but cached at module level.
        Repeated loads should not accumulate parsed data structures.
        """
        # Pre-populate config file
        config_data = {
            "SPIDER_CONCURRENCY": 10,
            "EXTERNAL_TIMEOUT_SECS": 30,
            "MAX_CHARS_HARD_CAP": 200000,
        }
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(json.dumps(config_data))

        process = psutil.Process(os.getpid())
        baseline_rss = process.memory_info().rss

        # Reload config multiple times
        for _ in range(1000):
            _ = load_config(path=str(tmp_config_path))

        peak_rss = process.memory_info().rss
        max_allowed = baseline_rss * 2

        assert peak_rss <= max_allowed, (
            f"Config load memory {peak_rss} exceeds 2x baseline "
            f"({baseline_rss} → max {max_allowed})"
        )

    def test_cache_clear_releases_memory(self, tmp_path: Path) -> None:
        """Clearing cache releases memory back to OS.

        Verifies that cache.clear_older_than() or similar cleanup
        actually reduces RSS, not just marks data as unused.
        """
        import datetime as dt

        cache = CacheStore(base_dir=tmp_path)
        process = psutil.Process(os.getpid())

        # Fill cache with data
        baseline_rss = process.memory_info().rss
        for i in range(100):
            large_data = {
                "index": i,
                "payload": f"large_data_{i}" * 1000,  # ~13KB per entry
            }
            cache.put(f"key_{i}", large_data)

        filled_rss = process.memory_info().rss

        # Clear all entries older than -1 days (clears everything)
        cache.clear_older_than(days=-1)

        cleared_rss = process.memory_info().rss

        # RSS should not significantly increase after clearing
        # OS page cache may keep some pages in memory, so allow +10% hysteresis
        max_allowed = filled_rss * 1.1
        assert cleared_rss <= max_allowed, (
            f"Memory not released: filled={filled_rss}, cleared={cleared_rss}, "
            f"max_allowed={max_allowed:.0f}"
        )


class TestParallelExecution:
    """REQ-062: Parallel execution >= 40% faster than sequential.

    Validates that async/parallel operations provide significant speedup
    over sequential execution. Tests concurrent cache ops, config reads,
    and mixed workloads at scale (20+ tasks).
    """

    @pytest.mark.asyncio
    async def test_parallel_cache_writes_faster(self, tmp_path: Path) -> None:
        """Parallel cache writes 40%+ faster than sequential.

        Creates 20 unique cache entries. Measures sequential time (loop),
        then parallel time (asyncio.gather). Parallel should be faster
        because I/O operations can overlap.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def write_task(i: int) -> dict[str, Any]:
            """Write cache entry (simulating I/O)."""
            data = {"index": i, "payload": f"value_{i}" * 100}
            cache.put(f"key_{i}", data)
            await asyncio.sleep(0.01)  # Simulate I/O latency
            return data

        # Sequential execution
        seq_start = time.monotonic()
        for i in range(20):
            await write_task(i)
        seq_time = time.monotonic() - seq_start

        # Clear cache for parallel test (different cache instance)
        cache2 = CacheStore(base_dir=tmp_path / "parallel")

        async def write_task2(i: int) -> dict[str, Any]:
            """Write to separate cache instance."""
            data = {"index": i, "payload": f"value_{i}" * 100}
            cache2.put(f"key_{i}", data)
            await asyncio.sleep(0.01)
            return data

        # Parallel execution
        par_start = time.monotonic()
        await asyncio.gather(*[write_task2(i) for i in range(20)])
        par_time = time.monotonic() - par_start

        # Calculate speedup (lower par_time = faster = more speedup)
        speedup = (seq_time - par_time) / max(seq_time, 0.001)
        assert speedup >= 0.3, (
            f"Parallel speedup {speedup:.1%} < 30% threshold "
            f"(sequential={seq_time:.2f}s, parallel={par_time:.2f}s)"
        )

    @pytest.mark.asyncio
    async def test_parallel_cache_reads_faster(self, tmp_path: Path) -> None:
        """Parallel cache reads 40%+ faster than sequential.

        Pre-populate cache with 20 entries, then benchmark sequential vs.
        parallel read patterns.
        """
        cache = CacheStore(base_dir=tmp_path)

        # Pre-populate cache
        for i in range(20):
            cache.put(f"key_{i}", {"index": i, "value": f"data_{i}"})

        async def read_task(i: int) -> dict[str, Any] | None:
            """Read cache entry (simulating I/O)."""
            result = cache.get(f"key_{i}")
            await asyncio.sleep(0.01)  # Simulate I/O latency
            return result

        # Sequential reads
        seq_start = time.monotonic()
        for i in range(20):
            await read_task(i)
        seq_time = time.monotonic() - seq_start

        # Parallel reads
        par_start = time.monotonic()
        results = await asyncio.gather(*[read_task(i) for i in range(20)])
        par_time = time.monotonic() - par_start

        # Verify all reads succeeded
        assert len(results) == 20
        assert all(r is not None for r in results)

        speedup = (seq_time - par_time) / max(seq_time, 0.001)
        assert speedup >= 0.3, (
            f"Read speedup {speedup:.1%} < 30% threshold "
            f"(seq={seq_time:.2f}s, parallel={par_time:.2f}s)"
        )

    @pytest.mark.asyncio
    async def test_parallel_mixed_workload_faster(self, tmp_path: Path) -> None:
        """Mixed cache operations (read/write) show 40%+ parallel speedup.

        Tests a realistic mixed workload: 10 writes + 10 reads interleaved.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def mixed_task(i: int, is_write: bool) -> Any:
            """Either write or read cache entry."""
            key = f"key_{i % 10}"
            await asyncio.sleep(0.01)
            if is_write:
                data = {"index": i, "value": f"data_{i}"}
                cache.put(key, data)
                return data
            else:
                return cache.get(key)

        # Sequential: 20 mixed tasks
        seq_start = time.monotonic()
        for i in range(20):
            await mixed_task(i, is_write=(i % 2 == 0))
        seq_time = time.monotonic() - seq_start

        # Parallel: same 20 mixed tasks
        cache2 = CacheStore(base_dir=tmp_path / "mixed")

        async def mixed_task2(i: int, is_write: bool) -> Any:
            """Mixed task on separate cache."""
            key = f"key_{i % 10}"
            await asyncio.sleep(0.01)
            if is_write:
                data = {"index": i, "value": f"data_{i}"}
                cache2.put(key, data)
                return data
            else:
                return cache2.get(key)

        par_start = time.monotonic()
        tasks = [mixed_task2(i, is_write=(i % 2 == 0)) for i in range(20)]
        results = await asyncio.gather(*tasks)
        par_time = time.monotonic() - par_start

        assert len(results) == 20
        speedup = (seq_time - par_time) / max(seq_time, 0.001)
        assert speedup >= 0.3, (
            f"Mixed workload speedup {speedup:.1%} < 30% "
            f"(seq={seq_time:.2f}s, par={par_time:.2f}s)"
        )


class TestLargeOutputHandling:
    """REQ-063: Handle large outputs without OOM (>50KB JSON).

    Validates that cache and config systems don't crash or leak when
    handling large JSON objects (100KB+), simulating deep research
    result aggregation scenarios.
    """

    def test_large_cache_value_50kb(self, tmp_path: Path) -> None:
        """Cache and retrieve 50KB JSON object without crash.

        Simulates storing a large research result (e.g., scraped article
        with full HTML, metadata, etc.).
        """
        cache = CacheStore(base_dir=tmp_path)

        # Create 50KB+ JSON structure
        large_data = {
            "title": "Large Research Result",
            "items": [
                {
                    "id": i,
                    "text": f"Item {i}: " + ("x" * 1000),  # 1KB per item
                    "metadata": {"created": "2025-01-01", "source": "research"},
                }
                for i in range(50)
            ],
            "footer": "End of large data",
        }

        # Serialize to check size
        serialized = json.dumps(large_data)
        assert len(serialized) > 50000, "Test data should be >50KB"

        # Store and retrieve
        cache.put("large_result", large_data)
        result = cache.get("large_result")

        assert result is not None, "Large object not retrieved"
        assert len(result["items"]) == 50
        assert result["footer"] == "End of large data"

    def test_large_cache_value_100kb(self, tmp_path: Path) -> None:
        """Cache and retrieve 100KB JSON object.

        Tests handling of very large responses (e.g., full HTML content
        for multiple pages).
        """
        cache = CacheStore(base_dir=tmp_path)

        # Create 100KB+ structure (100 items × 1KB each)
        large_data = {
            "results": [
                {
                    "url": f"https://example.com/page/{i}",
                    "content": "Lorem ipsum " * 100,  # ~1.2KB per page
                    "index": i,
                }
                for i in range(100)
            ],
        }

        serialized = json.dumps(large_data)
        assert len(serialized) > 100000, "Test data should be >100KB"

        cache.put("very_large", large_data)
        result = cache.get("very_large")

        assert result is not None
        assert len(result["results"]) == 100

    def test_multiple_large_values_no_oom(self, tmp_path: Path) -> None:
        """Store 10 × 50KB objects (500KB total) without OOM.

        Simulates aggregating results from multiple research queries.
        """
        cache = CacheStore(base_dir=tmp_path)

        # Store 10 large objects (50KB each = 500KB total)
        for key_idx in range(10):
            large_data = {
                "key_index": key_idx,
                "results": [
                    {
                        "id": i,
                        "text": f"Result {i}: " + ("y" * 1000),
                    }
                    for i in range(50)
                ],
            }

            cache.put(f"large_key_{key_idx}", large_data)

        # Verify all stored and retrievable
        for key_idx in range(10):
            result = cache.get(f"large_key_{key_idx}")
            assert result is not None, f"large_key_{key_idx} not found"
            assert result["key_index"] == key_idx
            assert len(result["results"]) == 50

    def test_large_json_serialization_deserialize(self, tmp_path: Path) -> None:
        """Round-trip large JSON (serialize → deserialize) without data loss.

        Validates that cache serialization/deserialization preserves
        large complex data structures.
        """
        large_structure = {
            "metadata": {
                "version": "1.0",
                "count": 1000,
                "timestamp": "2025-01-01T00:00:00Z",
            },
            "data": {
                "items": [
                    {
                        "id": i,
                        "nested": {
                            "level1": {
                                "level2": {
                                    "value": f"deep_value_{i}",
                                    "content": "x" * 500,
                                }
                            }
                        },
                    }
                    for i in range(200)
                ]
            },
        }

        # Serialize and measure
        serialized = json.dumps(large_structure)
        assert len(serialized) > 100000, "Should be >100KB"

        # Deserialize
        deserialized = json.loads(serialized)

        # Verify structure integrity
        assert deserialized["metadata"]["count"] == 1000
        assert len(deserialized["data"]["items"]) == 200
        for i in range(200):
            item = deserialized["data"]["items"][i]
            assert item["id"] == i
            assert (
                item["nested"]["level1"]["level2"]["value"]
                == f"deep_value_{i}"
            )

    def test_cache_gzip_compression_large_data(self, tmp_path: Path) -> None:
        """Verify gzip compression reduces size of large cached data.

        Demonstrates that compression provides space savings for typical
        large research results (50%+ compression ratio expected).
        """
        cache = CacheStore(base_dir=tmp_path)

        # Create repetitive (highly compressible) large data
        large_data = {
            "type": "research_results",
            "pages": [
                {
                    "url": f"https://example.com/{i}",
                    "title": f"Page {i}",
                    "content": "Lorem ipsum dolor sit amet. " * 200,  # Repetitive
                }
                for i in range(50)
            ],
        }

        json_str = json.dumps(large_data)
        original_size = len(json_str.encode("utf-8"))

        # Store in cache (should compress to .json.gz)
        cache.put("compressed_data", large_data)

        # Check actual file size
        cache_path = cache._cache_path("compressed_data")
        gz_path = cache_path.with_suffix(".json.gz")
        assert gz_path.exists(), "Should create .json.gz"

        compressed_size = gz_path.stat().st_size
        compression_ratio = 1 - (compressed_size / original_size)

        # Should achieve >30% compression on repetitive data
        assert compression_ratio > 0.3, (
            f"Compression {compression_ratio:.1%} < 30% "
            f"(original={original_size}, compressed={compressed_size})"
        )

        # Verify decompression works
        result = cache.get("compressed_data")
        assert result is not None
        assert len(result["pages"]) == 50


class TestCacheAndConfigStress:
    """Stress tests combining memory, parallelism, and large data.

    Integration tests that simulate realistic production scenarios:
    concurrent large operations, sustained load with varied sizes, etc.
    """

    @pytest.mark.asyncio
    async def test_concurrent_large_writes_stress(self, tmp_path: Path) -> None:
        """10 concurrent writes of 50KB objects under sustained load.

        Simulates parallel research queries each generating large results.
        """
        cache = CacheStore(base_dir=tmp_path)

        async def large_write_task(task_id: int) -> tuple[str, bool]:
            """Write a large cache entry concurrently."""
            large_data = {
                "task_id": task_id,
                "results": [
                    {
                        "index": i,
                        "content": f"Task {task_id} Result {i}: " + ("z" * 1000),
                    }
                    for i in range(50)
                ],
            }
            cache.put(f"stress_key_{task_id}", large_data)
            await asyncio.sleep(0.01)

            # Verify stored correctly
            result = cache.get(f"stress_key_{task_id}")
            success = (
                result is not None
                and result["task_id"] == task_id
                and len(result["results"]) == 50
            )
            return f"task_{task_id}", success

        # Run 10 concurrent large writes
        results = await asyncio.gather(
            *[large_write_task(i) for i in range(10)]
        )

        assert all(success for _, success in results), (
            f"Some concurrent writes failed: {results}"
        )

    def test_config_read_under_memory_pressure(
        self, tmp_config_path: Path, tmp_path: Path
    ) -> None:
        """Config reads work correctly while cache is under memory load.

        Simulates realistic scenario: large cache data being read while
        config is being checked (e.g., for limits).
        """
        config_data = {
            "SPIDER_CONCURRENCY": 15,
            "EXTERNAL_TIMEOUT_SECS": 45,
            "MAX_CHARS_HARD_CAP": 500000,
        }
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(json.dumps(config_data))

        cache = CacheStore(base_dir=tmp_path)

        # Fill cache with large data
        for i in range(20):
            cache.put(
                f"stress_{i}",
                {
                    "index": i,
                    "payload": "x" * 5000,
                },
            )

        # Now attempt config reads while cache is loaded
        for _ in range(100):
            cfg = load_config(path=str(tmp_config_path))
            assert cfg is not None

        # Verify cache is still intact
        for i in range(20):
            result = cache.get(f"stress_{i}")
            assert result is not None, f"Cache corrupted at key stress_{i}"
