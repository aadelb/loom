"""Unit tests for research_cache_stats and research_cache_clear."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from loom.tools.cache_mgmt import research_cache_clear, research_cache_stats


class TestCacheStats:
    """research_cache_stats returns expected shape and values."""

    def test_stats_empty_dir(self, tmp_cache_dir: Path) -> None:
        """Stats on empty cache dir return zeros."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        # Reset singleton so it picks up new env
        import loom.cache

        loom.cache._cache_singleton = None

        try:
            result = research_cache_stats()
            assert result["size_mb"] == 0
            assert result["entry_count"] == 0
            assert result["oldest"] is None
            assert result["newest"] is None
        finally:
            loom.cache._cache_singleton = None

    def test_stats_with_entries(self, tmp_cache_dir: Path) -> None:
        """Stats reflect files in the cache directory."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        import loom.cache

        loom.cache._cache_singleton = None

        try:
            # Create some cache entries manually
            day_dir = tmp_cache_dir / "2026-04-11"
            day_dir.mkdir()
            (day_dir / "abc123.json").write_text('{"url":"https://example.com"}')
            (day_dir / "def456.json").write_text('{"url":"https://example.org"}')

            result = research_cache_stats()
            assert result["entry_count"] == 2
            assert result["size_mb"] >= 0  # tiny test files may round to 0.0
            assert result["oldest"] is not None
            assert result["newest"] is not None
            assert str(tmp_cache_dir) in result["cache_dir"]
        finally:
            loom.cache._cache_singleton = None


class TestCacheClear:
    """research_cache_clear removes old entries."""

    def test_clear_removes_old_entries(self, tmp_cache_dir: Path) -> None:
        """Entries older than threshold are deleted."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        import loom.cache

        loom.cache._cache_singleton = None

        try:
            day_dir = tmp_cache_dir / "2026-04-11"
            day_dir.mkdir()
            old_file = day_dir / "old.json"
            old_file.write_text('{"data":"old"}')
            # Set mtime to 60 days ago
            old_time = time.time() - (60 * 24 * 3600)
            os.utime(old_file, (old_time, old_time))

            new_file = day_dir / "new.json"
            new_file.write_text('{"data":"new"}')

            result = research_cache_clear(older_than_days=30)
            assert result["deleted_count"] == 1
            assert result["freed_mb"] >= 0  # tiny file may round to 0.0 at 2dp
            assert not old_file.exists()
            assert new_file.exists()
        finally:
            loom.cache._cache_singleton = None

    def test_clear_empty_dir(self, tmp_cache_dir: Path) -> None:
        """Clear on empty dir returns zeros."""
        os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
        import loom.cache

        loom.cache._cache_singleton = None

        try:
            result = research_cache_clear(older_than_days=1)
            assert result["deleted_count"] == 0
            assert result["freed_mb"] == 0.0
        finally:
            loom.cache._cache_singleton = None
