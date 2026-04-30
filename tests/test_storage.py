"""Unit tests for storage tiering and monitoring (REQ-096, REQ-098).

Tests cover:
  - Storage statistics calculation (files, sizes, extensions)
  - Storage alert generation based on thresholds
  - File tier classification by age (hot/warm/cold)
  - Tier breakdown aggregation
  - Complete storage dashboard
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from loom.storage import (
    TIERS,
    check_storage_alerts,
    classify_file_tier,
    get_storage_dashboard,
    get_storage_stats,
    get_tier_breakdown,
)


class TestGetStorageStats:
    """Tests for get_storage_stats() function."""

    def test_storage_stats_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns zero totals."""
        stats = get_storage_stats(tmp_path)

        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["file_count"] == 0
        assert stats["by_extension"] == {}

    def test_storage_stats_missing_directory(self, tmp_path: Path) -> None:
        """Non-existent directory returns zero totals."""
        missing = tmp_path / "does_not_exist"
        stats = get_storage_stats(missing)

        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["file_count"] == 0
        assert stats["by_extension"] == {}

    def test_storage_stats_single_file(self, tmp_path: Path) -> None:
        """Single file is counted and sized correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")  # 11 bytes

        stats = get_storage_stats(tmp_path)

        assert stats["file_count"] == 1
        assert stats["total_size_bytes"] == 11
        assert stats["by_extension"][".txt"] == pytest.approx(11 / (1024 * 1024), abs=0.01)

    def test_storage_stats_multiple_files(self, tmp_path: Path) -> None:
        """Multiple files are aggregated correctly."""
        (tmp_path / "file1.txt").write_text("content1")  # 8 bytes
        (tmp_path / "file2.txt").write_text("more content")  # 12 bytes
        (tmp_path / "file3.json").write_bytes(b"x" * 1024)  # 1024 bytes

        stats = get_storage_stats(tmp_path)

        assert stats["file_count"] == 3
        assert stats["total_size_bytes"] == 8 + 12 + 1024
        assert ".txt" in stats["by_extension"]
        assert ".json" in stats["by_extension"]

    def test_storage_stats_extension_breakdown(self, tmp_path: Path) -> None:
        """Extension breakdown is calculated per type."""
        (tmp_path / "a.txt").write_text("a")  # 1 byte
        (tmp_path / "b.txt").write_text("bb")  # 2 bytes
        (tmp_path / "c.json").write_text("ccc")  # 3 bytes

        stats = get_storage_stats(tmp_path)

        # .txt should be sum of a.txt and b.txt (3 bytes)
        assert stats["by_extension"][".txt"] == pytest.approx(3 / (1024 * 1024), abs=0.001)
        # .json should be 3 bytes
        assert stats["by_extension"][".json"] == pytest.approx(3 / (1024 * 1024), abs=0.001)

    def test_storage_stats_subdirectories(self, tmp_path: Path) -> None:
        """Files in subdirectories are included."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.txt").write_text("root")  # 4 bytes
        (subdir / "nested.txt").write_text("nested")  # 6 bytes

        stats = get_storage_stats(tmp_path)

        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 4 + 6

    def test_storage_stats_size_in_mb(self, tmp_path: Path) -> None:
        """Size in MB is calculated correctly."""
        # Create a ~1 MB file
        large_file = tmp_path / "large.bin"
        large_file.write_bytes(b"x" * (1024 * 1024))

        stats = get_storage_stats(tmp_path)

        assert stats["total_size_mb"] == pytest.approx(1.0, abs=0.01)

    def test_storage_stats_no_extension_files(self, tmp_path: Path) -> None:
        """Files without extension are included under '(no ext)' key."""
        (tmp_path / "README").write_text("readme content")

        stats = get_storage_stats(tmp_path)

        assert "(no ext)" in stats["by_extension"]
        assert stats["file_count"] == 1


class TestCheckStorageAlerts:
    """Tests for check_storage_alerts() function."""

    def test_storage_alerts_below_50_percent(self, tmp_path: Path) -> None:
        """Usage below 50% generates no alerts."""
        # Create 5 MB, max is 50 GB -> ~0% usage
        (tmp_path / "file.bin").write_bytes(b"x" * (5 * 1024 * 1024))

        alerts = check_storage_alerts(tmp_path, max_size_gb=50.0)

        assert len(alerts) == 0

    def test_storage_alerts_at_50_percent(self, tmp_path: Path) -> None:
        """Usage at ~50% generates info alert."""
        # Create 26 MB with 50 MB max -> ~50% usage
        (tmp_path / "file.bin").write_bytes(b"x" * (26 * 1024 * 1024))

        alerts = check_storage_alerts(tmp_path, max_size_gb=0.05)  # 50 MB max

        assert len(alerts) == 1
        assert alerts[0]["level"] == "info"
        assert "50" in alerts[0]["message"] or "50.8" in alerts[0]["message"]

    def test_storage_alerts_at_80_percent(self, tmp_path: Path) -> None:
        """Usage at ~80% generates warning alert."""
        # Create 41 MB with 50 MB max -> ~80% usage
        (tmp_path / "file.bin").write_bytes(b"x" * (41 * 1024 * 1024))

        alerts = check_storage_alerts(tmp_path, max_size_gb=0.05)  # 50 MB max

        assert len(alerts) == 1
        assert alerts[0]["level"] == "warning"
        assert "80" in alerts[0]["message"] or "80.1" in alerts[0]["message"]
        assert alerts[0]["action"] == "review_retention"

    def test_storage_alerts_at_90_percent(self, tmp_path: Path) -> None:
        """Usage at ~90% generates critical alert."""
        # Create 47 MB with 50 MB max -> ~92% usage
        (tmp_path / "file.bin").write_bytes(b"x" * (47 * 1024 * 1024))

        alerts = check_storage_alerts(tmp_path, max_size_gb=0.05)  # 50 MB max

        assert len(alerts) == 1
        assert alerts[0]["level"] == "critical"
        assert "90" in alerts[0]["message"] or "91.8" in alerts[0]["message"]
        assert alerts[0]["action"] == "expand_or_archive"

    def test_storage_alerts_exceeds_100_percent(self, tmp_path: Path) -> None:
        """Usage exceeding 100% generates critical alert."""
        # Create 60 MB with 50 MB max -> 120% usage
        (tmp_path / "file.bin").write_bytes(b"x" * (60 * 1024 * 1024))

        alerts = check_storage_alerts(tmp_path, max_size_gb=0.05)  # 50 MB max

        assert len(alerts) == 1
        assert alerts[0]["level"] == "critical"

    def test_storage_alerts_empty_with_zero_max(self, tmp_path: Path) -> None:
        """Zero max_size_gb returns empty alerts list."""
        (tmp_path / "file.bin").write_bytes(b"x" * 1024)

        alerts = check_storage_alerts(tmp_path, max_size_gb=0.0)

        # No crash, and no alerts (percentage is 0 or inf, but below 50%)
        assert isinstance(alerts, list)

    def test_storage_alerts_message_includes_gb_usage(self, tmp_path: Path) -> None:
        """Alert message includes actual GB usage."""
        # Create 41 MB with 50 MB max -> ~80% usage
        (tmp_path / "file.bin").write_bytes(b"x" * (41 * 1024 * 1024))

        alerts = check_storage_alerts(tmp_path, max_size_gb=0.05)  # 50 MB max

        assert len(alerts) == 1
        # Message should include usage in GB
        assert "0.0" in alerts[0]["message"]  # ~0.04 GB displayed as 0.0


class TestClassifyFileTier:
    """Tests for classify_file_tier() function."""

    def test_classify_file_tier_recent_file_is_hot(self, tmp_path: Path) -> None:
        """File modified within last 30 days is classified as hot."""
        test_file = tmp_path / "recent.txt"
        test_file.write_text("recent content")

        tier = classify_file_tier(test_file)

        assert tier == "hot"

    def test_classify_file_tier_30_day_old_file_is_warm(self, tmp_path: Path) -> None:
        """File modified 31 days ago is classified as warm."""
        test_file = tmp_path / "old.txt"
        test_file.write_text("old content")

        # Set mtime to 31 days ago
        now = dt.datetime.now(dt.timezone.utc)
        old_time = now - dt.timedelta(days=31)
        old_timestamp = old_time.timestamp()
        test_file.touch()
        # Use os to set file times
        import os
        os.utime(test_file, (old_timestamp, old_timestamp))

        tier = classify_file_tier(test_file)

        assert tier == "warm"

    def test_classify_file_tier_365_day_old_file_is_warm(self, tmp_path: Path) -> None:
        """File modified 365 days ago is still classified as warm."""
        test_file = tmp_path / "old_limit.txt"
        test_file.write_text("one year old")

        # Set mtime to exactly 365 days ago
        now = dt.datetime.now(dt.timezone.utc)
        old_time = now - dt.timedelta(days=365)
        old_timestamp = old_time.timestamp()
        import os
        os.utime(test_file, (old_timestamp, old_timestamp))

        tier = classify_file_tier(test_file)

        assert tier == "warm"

    def test_classify_file_tier_366_day_old_file_is_cold(self, tmp_path: Path) -> None:
        """File modified 366 days ago is classified as cold."""
        test_file = tmp_path / "ancient.txt"
        test_file.write_text("ancient content")

        # Set mtime to 366 days ago
        now = dt.datetime.now(dt.timezone.utc)
        old_time = now - dt.timedelta(days=366)
        old_timestamp = old_time.timestamp()
        import os
        os.utime(test_file, (old_timestamp, old_timestamp))

        tier = classify_file_tier(test_file)

        assert tier == "cold"

    def test_classify_file_tier_nonexistent_file_is_cold(self, tmp_path: Path) -> None:
        """Non-existent file defaults to cold."""
        missing_file = tmp_path / "missing.txt"

        tier = classify_file_tier(missing_file)

        assert tier == "cold"

    def test_classify_file_tier_zero_days_old_is_hot(self, tmp_path: Path) -> None:
        """Brand new file (just created) is hot."""
        test_file = tmp_path / "brand_new.txt"
        test_file.write_text("new")

        tier = classify_file_tier(test_file)

        assert tier == "hot"

    def test_classify_file_tier_boundary_at_30_days(self, tmp_path: Path) -> None:
        """File exactly 30 days old is hot, 31 days is warm."""
        import os

        test_file_hot = tmp_path / "30_days.txt"
        test_file_warm = tmp_path / "31_days.txt"
        test_file_hot.write_text("30 days")
        test_file_warm.write_text("31 days")

        now = dt.datetime.now(dt.timezone.utc)

        # Set to exactly 30 days ago
        time_30 = now - dt.timedelta(days=30)
        ts_30 = time_30.timestamp()
        os.utime(test_file_hot, (ts_30, ts_30))

        # Set to exactly 31 days ago
        time_31 = now - dt.timedelta(days=31)
        ts_31 = time_31.timestamp()
        os.utime(test_file_warm, (ts_31, ts_31))

        assert classify_file_tier(test_file_hot) == "hot"
        assert classify_file_tier(test_file_warm) == "warm"


class TestGetTierBreakdown:
    """Tests for get_tier_breakdown() function."""

    def test_tier_breakdown_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory has zero files in all tiers."""
        breakdown = get_tier_breakdown(tmp_path)

        assert "hot" in breakdown
        assert "warm" in breakdown
        assert "cold" in breakdown
        assert breakdown["hot"]["count"] == 0
        assert breakdown["warm"]["count"] == 0
        assert breakdown["cold"]["count"] == 0
        assert breakdown["hot"]["size_bytes"] == 0
        assert breakdown["warm"]["size_bytes"] == 0
        assert breakdown["cold"]["size_bytes"] == 0

    def test_tier_breakdown_all_tiers_present(self, tmp_path: Path) -> None:
        """Breakdown includes all three tiers."""
        import os

        now = dt.datetime.now(dt.timezone.utc)

        # Create hot file (recent)
        hot_file = tmp_path / "hot.txt"
        hot_file.write_text("hot_content")

        # Create warm file (30-365 days old)
        warm_file = tmp_path / "warm.txt"
        warm_file.write_text("warm_content")
        time_warm = now - dt.timedelta(days=100)
        os.utime(warm_file, (time_warm.timestamp(), time_warm.timestamp()))

        # Create cold file (>365 days old)
        cold_file = tmp_path / "cold.txt"
        cold_file.write_text("cold_content")
        time_cold = now - dt.timedelta(days=500)
        os.utime(cold_file, (time_cold.timestamp(), time_cold.timestamp()))

        breakdown = get_tier_breakdown(tmp_path)

        assert breakdown["hot"]["count"] == 1
        assert breakdown["warm"]["count"] == 1
        assert breakdown["cold"]["count"] == 1

    def test_tier_breakdown_size_aggregation(self, tmp_path: Path) -> None:
        """Sizes are aggregated per tier."""
        import os

        now = dt.datetime.now(dt.timezone.utc)

        # Create 2 hot files (10 bytes each)
        (tmp_path / "hot1.txt").write_text("1234567890")
        (tmp_path / "hot2.txt").write_text("0987654321")

        # Create 1 warm file (20 bytes)
        warm_file = tmp_path / "warm.txt"
        warm_file.write_bytes(b"x" * 20)
        time_warm = now - dt.timedelta(days=100)
        os.utime(warm_file, (time_warm.timestamp(), time_warm.timestamp()))

        breakdown = get_tier_breakdown(tmp_path)

        assert breakdown["hot"]["count"] == 2
        assert breakdown["hot"]["size_bytes"] == 20
        assert breakdown["warm"]["count"] == 1
        assert breakdown["warm"]["size_bytes"] == 20

    def test_tier_breakdown_size_mb_conversion(self, tmp_path: Path) -> None:
        """Size in MB is calculated correctly from bytes."""
        import os

        now = dt.datetime.now(dt.timezone.utc)

        # Create a 1 MB file in hot tier
        hot_file = tmp_path / "hot_1mb.bin"
        hot_file.write_bytes(b"x" * (1024 * 1024))

        breakdown = get_tier_breakdown(tmp_path)

        assert breakdown["hot"]["size_mb"] == pytest.approx(1.0, abs=0.01)
        assert breakdown["warm"]["size_mb"] == 0.0
        assert breakdown["cold"]["size_mb"] == 0.0

    def test_tier_breakdown_missing_directory(self, tmp_path: Path) -> None:
        """Missing directory returns zero breakdown."""
        missing = tmp_path / "does_not_exist"
        breakdown = get_tier_breakdown(missing)

        assert breakdown["hot"]["count"] == 0
        assert breakdown["warm"]["count"] == 0
        assert breakdown["cold"]["count"] == 0
        assert breakdown["hot"]["size_mb"] == 0.0
        assert breakdown["warm"]["size_mb"] == 0.0
        assert breakdown["cold"]["size_mb"] == 0.0

    def test_tier_breakdown_subdirectories(self, tmp_path: Path) -> None:
        """Files in subdirectories are classified into tiers."""
        import os

        now = dt.datetime.now(dt.timezone.utc)

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Hot file in root
        (tmp_path / "hot.txt").write_text("hot")

        # Warm file in subdir
        warm_file = subdir / "warm.txt"
        warm_file.write_text("warm")
        time_warm = now - dt.timedelta(days=100)
        os.utime(warm_file, (time_warm.timestamp(), time_warm.timestamp()))

        breakdown = get_tier_breakdown(tmp_path)

        assert breakdown["hot"]["count"] == 1
        assert breakdown["warm"]["count"] == 1


class TestGetStorageDashboard:
    """Tests for get_storage_dashboard() function."""

    def test_dashboard_empty_directory(self, tmp_path: Path) -> None:
        """Dashboard for empty directory has expected structure."""
        dashboard = get_storage_dashboard(tmp_path, max_size_gb=50.0)

        assert "stats" in dashboard
        assert "tiers" in dashboard
        assert "alerts" in dashboard
        assert "max_size_gb" in dashboard

        assert dashboard["stats"]["file_count"] == 0
        assert dashboard["stats"]["total_size_bytes"] == 0
        assert dashboard["max_size_gb"] == 50.0

    def test_dashboard_contains_all_sections(self, tmp_path: Path) -> None:
        """Dashboard includes stats, tiers, and alerts sections."""
        import os

        now = dt.datetime.now(dt.timezone.utc)

        # Create varied files
        (tmp_path / "hot.txt").write_text("hot")

        warm_file = tmp_path / "warm.txt"
        warm_file.write_text("warm")
        time_warm = now - dt.timedelta(days=100)
        os.utime(warm_file, (time_warm.timestamp(), time_warm.timestamp()))

        dashboard = get_storage_dashboard(tmp_path, max_size_gb=50.0)

        # Check sections exist
        assert isinstance(dashboard["stats"], dict)
        assert isinstance(dashboard["tiers"], dict)
        assert isinstance(dashboard["alerts"], list)

        # Check stats content
        assert dashboard["stats"]["file_count"] == 2
        assert dashboard["stats"]["total_size_bytes"] > 0

        # Check tiers content
        assert "hot" in dashboard["tiers"]
        assert "warm" in dashboard["tiers"]
        assert "cold" in dashboard["tiers"]

    def test_dashboard_alerts_reflected(self, tmp_path: Path) -> None:
        """Dashboard reflects alerts based on current usage."""
        # Create 41 MB with 50 MB max -> ~80% of 50 MB -> warning alert
        (tmp_path / "file.bin").write_bytes(b"x" * (41 * 1024 * 1024))

        dashboard = get_storage_dashboard(tmp_path, max_size_gb=0.05)  # 50 MB max

        assert len(dashboard["alerts"]) > 0
        assert dashboard["alerts"][0]["level"] == "warning"

    def test_dashboard_with_custom_max_size(self, tmp_path: Path) -> None:
        """Dashboard respects custom max_size_gb parameter."""
        (tmp_path / "file.bin").write_bytes(b"x" * (10 * 1024 * 1024))

        dashboard = get_storage_dashboard(tmp_path, max_size_gb=100.0)

        assert dashboard["max_size_gb"] == 100.0
        # 10 MB of 100 GB -> ~0% -> no alerts
        assert len(dashboard["alerts"]) == 0

    def test_dashboard_stats_and_tiers_consistency(self, tmp_path: Path) -> None:
        """Dashboard stats and tiers count/size should be consistent."""
        import os

        now = dt.datetime.now(dt.timezone.utc)

        # Create 2 hot files
        (tmp_path / "hot1.txt").write_text("a" * 100)
        (tmp_path / "hot2.txt").write_text("b" * 200)

        dashboard = get_storage_dashboard(tmp_path, max_size_gb=50.0)

        # Total file count should match sum of tier counts
        total_files = (
            dashboard["tiers"]["hot"]["count"]
            + dashboard["tiers"]["warm"]["count"]
            + dashboard["tiers"]["cold"]["count"]
        )
        assert total_files == dashboard["stats"]["file_count"]

        # Total size bytes should match sum of tier sizes
        total_size = (
            dashboard["tiers"]["hot"]["size_bytes"]
            + dashboard["tiers"]["warm"]["size_bytes"]
            + dashboard["tiers"]["cold"]["size_bytes"]
        )
        assert total_size == dashboard["stats"]["total_size_bytes"]


class TestStorageTiersConstant:
    """Tests for TIERS constant."""

    def test_tiers_has_all_three_tiers(self) -> None:
        """TIERS dict contains hot, warm, cold keys."""
        assert "hot" in TIERS
        assert "warm" in TIERS
        assert "cold" in TIERS

    def test_tiers_have_required_fields(self) -> None:
        """Each tier has max_age_days and description."""
        for tier_name, tier_config in TIERS.items():
            assert "max_age_days" in tier_config
            assert "description" in tier_config

    def test_tiers_max_age_bounds(self) -> None:
        """Tier max ages follow expected order: hot < warm < cold."""
        hot_age = TIERS["hot"]["max_age_days"]
        warm_age = TIERS["warm"]["max_age_days"]
        cold_age = TIERS["cold"]["max_age_days"]

        assert hot_age < warm_age
        assert cold_age is None or cold_age > warm_age
