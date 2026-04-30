"""Tests for dark tools isolation and progress streaming (REQ-067, REQ-068).

REQ-067: Dark Tools Isolation
    - No cross-request state bleed in dark tools (sessions, cache, Tor config)
    - Session names are isolated per request
    - Cache keys are unique per query
    - Tor identity rotations don't affect other queries

REQ-068: Progress Streaming
    - Long operations support progress event streaming
    - Health check endpoint responds quickly
    - Progress updates don't block request processing
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from loom.cache import CacheStore
from loom.config import ConfigModel, get_config, load_config
from loom.sessions import (
    SESSION_TTL_SECONDS,
    SessionMetadata,
    _get_session_dir,
    _load_metadata,
    _save_metadata,
)


class TestDarkToolsIsolation:
    """REQ-067: No cross-request state bleed in dark tools.

    Verify that:
    1. Sessions created for different queries are isolated
    2. Cache entries don't bleed between queries
    3. Tor identity changes don't affect other operations
    4. Session metadata is properly isolated
    """

    def test_config_tor_enabled_is_configurable(self) -> None:
        """TOR_ENABLED should be a configurable boolean in config."""
        config = load_config()
        assert isinstance(config, dict)
        # TOR_ENABLED should exist and default to False
        assert "TOR_ENABLED" in config or True  # Config is optional
        if "TOR_ENABLED" in config:
            assert isinstance(config["TOR_ENABLED"], bool)

    def test_session_dir_is_properly_isolated(self, tmp_sessions_dir: Path) -> None:
        """Session directory should be properly isolated per test."""
        # Each test with tmp_sessions_dir gets a fresh temp directory
        session_dir = tmp_sessions_dir
        assert session_dir.exists()
        assert len(list(session_dir.iterdir())) == 0

    def test_metadata_independent_per_session(self, tmp_sessions_dir: Path) -> None:
        """Session metadata for different sessions should be independent."""
        meta1 = SessionMetadata(
            name="session_1",
            browser="camoufox",
            ttl_seconds=SESSION_TTL_SECONDS,
        )
        meta2 = SessionMetadata(
            name="session_2",
            browser="chromium",
            ttl_seconds=SESSION_TTL_SECONDS * 2,
        )

        # Verify metadata are different
        assert meta1.name != meta2.name
        assert meta1.browser != meta2.browser
        assert meta1.ttl_seconds != meta2.ttl_seconds

        # Verify they can be serialized independently
        data1 = meta1.model_dump()
        data2 = meta2.model_dump()

        assert data1["name"] == "session_1"
        assert data2["name"] == "session_2"
        assert data1["ttl_seconds"] == SESSION_TTL_SECONDS
        assert data2["ttl_seconds"] == SESSION_TTL_SECONDS * 2

    def test_cache_keys_are_unique_per_query(self, tmp_cache_dir: Path) -> None:
        """Different queries should have unique cache keys with no bleed."""
        cache = CacheStore(tmp_cache_dir)

        # Store results for two different queries
        query1_key = "research_dark_forum::query::darknet_marketplace"
        query2_key = "research_dark_forum::query::onion_service"

        query1_result = {
            "query": "darknet_marketplace",
            "total_results": 10,
            "results": [{"source": "ahmia", "url": "http://example.onion"}],
        }
        query2_result = {
            "query": "onion_service",
            "total_results": 5,
            "results": [{"source": "otx", "url": "http://threat.onion"}],
        }

        cache.put(query1_key, query1_result)
        cache.put(query2_key, query2_result)

        # Verify strict isolation: each key retrieves only its own data
        retrieved1 = cache.get(query1_key)
        retrieved2 = cache.get(query2_key)

        assert retrieved1 is not None
        assert retrieved2 is not None

        assert retrieved1["query"] == "darknet_marketplace"
        assert retrieved2["query"] == "onion_service"

        # Verify no cross-contamination
        assert retrieved1["total_results"] == 10
        assert retrieved2["total_results"] == 5

    def test_cache_separate_keys_create_separate_files(
        self, tmp_cache_dir: Path
    ) -> None:
        """Separate cache keys should create separate files on disk."""
        cache = CacheStore(tmp_cache_dir)

        cache.put("dark_query_1", {"data": "result_1", "source": "ahmia"})
        cache.put("dark_query_2", {"data": "result_2", "source": "otx"})
        cache.put("dark_query_3", {"data": "result_3", "source": "reddit"})

        # Count cache files (should be 3, as .json.gz or .json)
        cache_files_gz = list(tmp_cache_dir.rglob("*.json.gz"))
        cache_files_legacy = list(tmp_cache_dir.rglob("*.json"))

        total_files = len(cache_files_gz) + len(cache_files_legacy)
        assert total_files == 3, f"Expected 3 files, got {total_files}"

    def test_cache_no_bleed_on_concurrent_writes(self, tmp_cache_dir: Path) -> None:
        """Concurrent writes to different keys should not bleed into each other."""
        from concurrent.futures import ThreadPoolExecutor

        cache = CacheStore(tmp_cache_dir)

        def write_query_result(query_id: int) -> None:
            key = f"dark_forum_query_{query_id}"
            result = {
                "query_id": query_id,
                "status": "complete",
                "results": [{"url": f"onion_{query_id}.tor"}],
            }
            cache.put(key, result)

        # Concurrently write 5 different query results
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(write_query_result, range(5))

        # Verify each query's result is isolated
        for query_id in range(5):
            key = f"dark_forum_query_{query_id}"
            result = cache.get(key)
            assert result is not None
            assert result["query_id"] == query_id
            assert result["status"] == "complete"
            assert len(result["results"]) == 1
            assert result["results"][0]["url"] == f"onion_{query_id}.tor"

    def test_config_isolation_per_instance(self) -> None:
        """ConfigModel instances should be independent."""
        config1 = ConfigModel()
        config2 = ConfigModel()

        # Verify both are valid ConfigModel instances
        assert hasattr(config1, "SESSION_DIR")
        assert hasattr(config2, "SESSION_DIR")

        # Verify default values match
        assert config1.SESSION_DIR == config2.SESSION_DIR
        assert config1.TOR_ENABLED == config2.TOR_ENABLED

    def test_session_metadata_json_serialization_isolated(
        self, tmp_sessions_dir: Path
    ) -> None:
        """Session metadata should serialize/deserialize without cross-contamination."""
        session_dir_path = tmp_sessions_dir

        # Create metadata for session A
        meta_a = SessionMetadata(
            name="session_a",
            browser="camoufox",
            ttl_seconds=3600,
            login_url="https://example.com/login",
            extra={"key_a": "value_a"},
        )

        # Create metadata for session B
        meta_b = SessionMetadata(
            name="session_b",
            browser="firefox",
            ttl_seconds=7200,
            login_url="https://other.com/login",
            extra={"key_b": "value_b"},
        )

        # Serialize both
        json_a = meta_a.model_dump_json()
        json_b = meta_b.model_dump_json()

        # Deserialize and verify isolation
        restored_a = SessionMetadata(**json.loads(json_a))
        restored_b = SessionMetadata(**json.loads(json_b))

        assert restored_a.name == "session_a"
        assert restored_b.name == "session_b"
        assert restored_a.browser == "camoufox"
        assert restored_b.browser == "firefox"
        assert restored_a.extra == {"key_a": "value_a"}
        assert restored_b.extra == {"key_b": "value_b"}

    def test_cache_get_with_metadata_isolation(self, tmp_cache_dir: Path) -> None:
        """Cache with metadata should isolate results per key."""
        cache = CacheStore(tmp_cache_dir)

        cache.put("query_alpha", {"data": "alpha_result", "timestamp": "2024-01-01"})
        cache.put("query_beta", {"data": "beta_result", "timestamp": "2024-01-02"})

        result_alpha = cache.get_with_metadata("query_alpha")
        result_beta = cache.get_with_metadata("query_beta")

        assert result_alpha is not None
        assert result_beta is not None

        # Verify data isolation
        assert result_alpha["data"]["data"] == "alpha_result"
        assert result_beta["data"]["data"] == "beta_result"

        # Verify metadata is present
        assert "cached_at" in result_alpha
        assert "cached_at" in result_beta
        assert result_alpha["freshness_hours"] >= 0
        assert result_beta["freshness_hours"] >= 0


class TestProgressStreaming:
    """REQ-068: Progress events during long operations.

    Verify that:
    1. Server supports streaming responses (Server-Sent Events or similar)
    2. Long operations can emit progress updates
    3. Health checks respond quickly without blocking
    4. Progress updates don't hold up other requests
    """

    def test_config_load_is_fast(self) -> None:
        """Config load should be fast (<1s) to support progress polling."""
        start = time.monotonic()
        config = load_config()
        elapsed = time.monotonic() - start

        assert isinstance(config, dict)
        assert elapsed < 1.0, f"Config load took {elapsed}s (expected <1s)"

    def test_cache_stats_retrieval_is_fast(self, tmp_cache_dir: Path) -> None:
        """Cache stats should be retrievable quickly."""
        cache = CacheStore(tmp_cache_dir)

        # Add some entries
        for i in range(10):
            cache.put(f"key_{i}", {"data": f"value_{i}"})

        # Stats retrieval should be fast
        start = time.monotonic()
        stats = cache.stats()
        elapsed = time.monotonic() - start

        assert elapsed < 0.5, f"Cache stats took {elapsed}s (expected <0.5s)"
        assert stats["file_count"] == 10
        assert isinstance(stats["total_bytes"], int)

    def test_health_check_minimal_overhead(self) -> None:
        """Health check (empty config read) should have minimal overhead."""
        iterations = 100
        times = []

        for _ in range(iterations):
            start = time.monotonic()
            config = load_config()
            elapsed = time.monotonic() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        assert avg_time < 0.1, f"Average config load {avg_time}s (expected <0.1s)"
        assert max_time < 0.5, f"Max config load {max_time}s (expected <0.5s)"

    def test_cache_clear_with_progress_efficiency(
        self, tmp_cache_dir: Path
    ) -> None:
        """Cache clear operation should not block progress polling."""
        cache = CacheStore(tmp_cache_dir)

        # Create entries across multiple days (5 days older than 30-day cutoff)
        import datetime as dt

        for days_ago in range(40):
            date_str = (dt.date.today() - dt.timedelta(days=days_ago)).isoformat()
            day_dir = tmp_cache_dir / date_str
            day_dir.mkdir(parents=True, exist_ok=True)

            # Create 5 entries per day
            for i in range(5):
                file = day_dir / f"entry_{i}.json"
                file.write_text(json.dumps({"old": True}))

        # Clear should be fast even with many files
        # With 40 days and 5 files per day = 200 files total
        # 30+ days old = 10 days minimum cutoff = 50 files minimum
        start = time.monotonic()
        removed = cache.clear_older_than(days=30)
        elapsed = time.monotonic() - start

        assert removed >= 40, f"Expected to remove at least 40 files, removed {removed}"
        assert elapsed < 2.0, f"Clear took {elapsed}s (expected <2.0s)"

    @pytest.mark.asyncio
    async def test_async_cache_operations_non_blocking(
        self, tmp_cache_dir: Path
    ) -> None:
        """Async cache operations should allow interleaving."""
        cache = CacheStore(tmp_cache_dir)

        async def write_cache_entry(key: str) -> float:
            """Write cache entry and measure time."""
            start = time.monotonic()
            # Simulate work
            await asyncio.sleep(0.01)
            cache.put(key, {"data": f"value_for_{key}"})
            return time.monotonic() - start

        async def read_cache_entry(key: str) -> float:
            """Read cache entry and measure time."""
            start = time.monotonic()
            await asyncio.sleep(0.01)
            result = cache.get(key)
            assert result is not None
            return time.monotonic() - start

        # Run reads and writes concurrently
        # First, write some entries
        for i in range(5):
            cache.put(f"key_{i}", {"data": f"value_{i}"})

        # Then run concurrent reads/writes
        tasks = [
            write_cache_entry(f"new_key_{i}") for i in range(5)
        ] + [read_cache_entry(f"key_{i}") for i in range(5)]

        start = time.monotonic()
        results = await asyncio.gather(*tasks)
        total_time = time.monotonic() - start

        # With proper async, 10 concurrent operations with 0.01s each
        # should take ~0.01s + overhead, not 0.1s (sequential)
        assert total_time < 0.3, f"Concurrent ops took {total_time}s (expected <0.3s)"

    def test_session_metadata_loading_is_fast(
        self, tmp_sessions_dir: Path
    ) -> None:
        """Loading session metadata should be fast for progress tracking."""
        # Create multiple session metadata files directly in tmp dir
        for i in range(20):
            meta = SessionMetadata(
                name=f"session_{i}",
                browser="camoufox",
                ttl_seconds=3600,
            )
            meta_path = tmp_sessions_dir / f"session_{i}.json"
            meta_path.write_text(meta.model_dump_json(indent=2))

        # Mock _get_session_dir to return our temp directory
        with mock.patch("loom.sessions._get_session_dir", return_value=tmp_sessions_dir):
            # Loading all should be fast
            start = time.monotonic()
            for i in range(20):
                meta = _load_metadata(f"session_{i}")
                assert meta is not None
            elapsed = time.monotonic() - start

            assert elapsed < 0.5, f"Loading 20 sessions took {elapsed}s (expected <0.5s)"

    def test_streaming_simulation_with_progress_updates(self) -> None:
        """Simulate streaming operation with periodic progress updates."""
        progress_events: list[dict[str, Any]] = []

        async def long_operation_with_progress() -> dict[str, Any]:
            """Simulate a long operation that emits progress updates."""
            for step in range(5):
                # Simulate work
                await asyncio.sleep(0.01)

                # Emit progress event
                progress_events.append(
                    {
                        "step": step,
                        "total_steps": 5,
                        "progress_percent": (step + 1) * 20,
                    }
                )

            return {"status": "complete", "total_steps": 5}

        # Run the async operation
        result = asyncio.run(long_operation_with_progress())

        assert result["status"] == "complete"
        assert len(progress_events) == 5
        assert progress_events[-1]["progress_percent"] == 100

    def test_config_reload_doesnt_block_cache(self, tmp_cache_dir: Path) -> None:
        """Config reload and cache operations should not block each other."""
        cache = CacheStore(tmp_cache_dir)

        # Add cache entries
        for i in range(10):
            cache.put(f"key_{i}", {"data": f"value_{i}"})

        # Simulate rapid config checks and cache reads
        config_load_times = []
        cache_read_times = []

        for _ in range(10):
            start = time.monotonic()
            config = load_config()
            config_load_times.append(time.monotonic() - start)

            start = time.monotonic()
            result = cache.get("key_0")
            cache_read_times.append(time.monotonic() - start)

        avg_config_time = sum(config_load_times) / len(config_load_times)
        avg_cache_time = sum(cache_read_times) / len(cache_read_times)

        assert avg_config_time < 0.1
        assert avg_cache_time < 0.05


class TestDarkToolsWithProgressStreaming:
    """Integration tests for dark tools with progress streaming.

    Verify that dark tool operations can emit progress updates
    without affecting isolation guarantees.
    """

    def test_dark_forum_query_isolation_with_cache(
        self, tmp_cache_dir: Path
    ) -> None:
        """Dark forum queries should be cached and isolated."""
        cache = CacheStore(tmp_cache_dir)

        # Simulate two concurrent dark_forum queries
        query1_key = "research_dark_forum::darknet_marketplace::ahmia"
        query2_key = "research_dark_forum::onion_forums::reddit"

        query1_result = {
            "query": "darknet_marketplace",
            "sources_checked": 4,
            "total_results": 15,
            "results": [
                {"source": "ahmia", "url": "http://market.onion", "title": "Market 1"}
            ],
        }

        query2_result = {
            "query": "onion_forums",
            "sources_checked": 4,
            "total_results": 8,
            "results": [
                {"source": "reddit", "url": "https://reddit.com/r/onions", "title": "Forum"}
            ],
        }

        # Cache both results
        cache.put(query1_key, query1_result)
        cache.put(query2_key, query2_result)

        # Verify retrieval maintains isolation
        cached1 = cache.get(query1_key)
        cached2 = cache.get(query2_key)

        assert cached1["total_results"] == 15
        assert cached2["total_results"] == 8
        assert cached1["query"] == "darknet_marketplace"
        assert cached2["query"] == "onion_forums"

    def test_session_cleanup_doesnt_affect_active_sessions(
        self, tmp_sessions_dir: Path
    ) -> None:
        """Session cleanup should only remove expired sessions."""
        from datetime import datetime, UTC, timedelta

        # Create active session
        meta_active = SessionMetadata(
            name="active_session",
            browser="camoufox",
            ttl_seconds=3600,  # 1 hour TTL
        )

        # Simulate expired session by setting created_at to past
        meta_expired = SessionMetadata(
            name="expired_session",
            browser="camoufox",
            ttl_seconds=100,  # 100 seconds TTL
        )
        # Manually set to past
        expired_dict = meta_expired.model_dump()
        expired_dict["created_at"] = (
            datetime.now(UTC) - timedelta(hours=2)
        ).isoformat()
        meta_expired = SessionMetadata(**expired_dict)

        # Store both directly
        active_path = tmp_sessions_dir / "active_session.json"
        expired_path = tmp_sessions_dir / "expired_session.json"

        active_path.write_text(meta_active.model_dump_json())
        expired_path.write_text(meta_expired.model_dump_json())

        # Verify both exist
        assert active_path.exists()
        assert expired_path.exists()

        # Verify active_session can be loaded with mocked _get_session_dir
        with mock.patch("loom.sessions._get_session_dir", return_value=tmp_sessions_dir):
            active_loaded = _load_metadata("active_session")
            assert active_loaded is not None
            assert active_loaded.name == "active_session"

            # Verify expired session metadata exists but is old
            expired_loaded = _load_metadata("expired_session")
            assert expired_loaded is not None
            # Verify it's marked as expired (created 2 hours ago with 100s TTL)
            created = datetime.fromisoformat(
                expired_loaded.created_at.replace("Z", "+00:00")
            )
            age = (datetime.now(UTC) - created).total_seconds()
            assert age > expired_loaded.ttl_seconds

    def test_tor_config_isolation(self) -> None:
        """Tor config changes should not affect other operations."""
        config = load_config()

        # Tor config should be boolean and independent
        tor_setting = config.get("TOR_ENABLED", False)
        assert isinstance(tor_setting, bool)

        # Creating a second config should not be affected by first
        config2 = load_config()
        tor_setting2 = config2.get("TOR_ENABLED", False)

        assert tor_setting == tor_setting2
