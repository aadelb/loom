"""Cache analytics tools for understanding cache usage patterns.

Provides tools to analyze cache distribution, growth patterns, and
optimization recommendations.
"""

from __future__ import annotations

import datetime as _dt
import logging
from pathlib import Path
from typing import Any

from loom.cache import get_cache

logger = logging.getLogger("loom.tools.cache_analytics")


async def research_cache_analyze() -> dict[str, Any]:
    """Analyze the content hash cache at ~/.cache/loom/.

    Scans daily directories, counts files, calculates sizes, and identifies:
    - Oldest and newest cache entries
    - Largest files
    - Most active days (by entry count and total size)
    - Estimated hit rate based on cache age distribution

    Returns:
        Dict with:
        - total_entries: Total number of cache files
        - total_size_mb: Total cache size in MB
        - oldest_entry: Oldest file timestamp (ISO format)
        - newest_entry: Newest file timestamp (ISO format)
        - daily_stats: List of {date, entries, size_mb} for each day
        - largest_files: List of {path, size_kb} for top 10 files
        - hit_rate_estimate: Estimated hit rate (0-100) based on age
        - cache_dir: Full path to cache directory
    """
    cache = get_cache()
    cache_dir = Path(cache.base_dir)

    if not cache_dir.exists():
        return {
            "total_entries": 0,
            "total_size_mb": 0.0,
            "oldest_entry": None,
            "newest_entry": None,
            "daily_stats": [],
            "largest_files": [],
            "hit_rate_estimate": 0,
            "cache_dir": str(cache_dir),
        }

    # Collect all cache files (both compressed and legacy)
    files: list[Path] = []
    for pattern in ("*.json.gz", "*.json"):
        for f in cache_dir.rglob(pattern):
            try:
                if f.is_file():
                    files.append(f)
            except FileNotFoundError:
                continue

    if not files:
        return {
            "total_entries": 0,
            "total_size_mb": 0.0,
            "oldest_entry": None,
            "newest_entry": None,
            "daily_stats": [],
            "largest_files": [],
            "hit_rate_estimate": 0,
            "cache_dir": str(cache_dir),
        }

    # Aggregate by date directory
    daily_stats_dict: dict[str, dict[str, Any]] = {}
    timestamps: list[float] = []
    total_bytes = 0
    file_sizes: list[tuple[Path, int]] = []

    for f in files:
        try:
            stat = f.stat()
            size_bytes = stat.st_size
            mtime = stat.st_mtime

            total_bytes += size_bytes
            timestamps.append(mtime)
            file_sizes.append((f, size_bytes))

            # Aggregate by date directory
            date_key = f.parent.name
            if date_key not in daily_stats_dict:
                daily_stats_dict[date_key] = {"entries": 0, "size_bytes": 0}
            daily_stats_dict[date_key]["entries"] += 1
            daily_stats_dict[date_key]["size_bytes"] += size_bytes
        except FileNotFoundError:
            continue

    # Compute totals
    total_entries = len(files)
    total_size_mb = total_bytes / (1024 * 1024)

    # Oldest and newest entries
    oldest_mtime = min(timestamps) if timestamps else None
    newest_mtime = max(timestamps) if timestamps else None
    oldest_ts = (
        _dt.datetime.fromtimestamp(oldest_mtime, _dt.UTC).isoformat()
        if oldest_mtime
        else None
    )
    newest_ts = (
        _dt.datetime.fromtimestamp(newest_mtime, _dt.UTC).isoformat()
        if newest_mtime
        else None
    )

    # Top 10 largest files
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    largest_files = [
        {"path": str(f.relative_to(cache_dir)), "size_kb": round(size / 1024, 2)}
        for f, size in file_sizes[:10]
    ]

    # Daily stats with sorted dates
    daily_stats = [
        {
            "date": date_key,
            "entries": daily_stats_dict[date_key]["entries"],
            "size_mb": round(daily_stats_dict[date_key]["size_bytes"] / (1024 * 1024), 2),
        }
        for date_key in sorted(daily_stats_dict.keys())
    ]

    # Estimate hit rate: newer files are more likely to be hit
    # Assume 50% hit rate for files < 7 days old, 30% for 7-14 days, 10% for > 14 days
    hit_rate_estimate = 0.0
    if timestamps:
        now = _dt.datetime.now(_dt.UTC).timestamp()
        week_cutoff = 7 * 24 * 3600
        fortnight_cutoff = 14 * 24 * 3600

        recent = sum(1 for t in timestamps if now - t < week_cutoff)
        week_old = sum(1 for t in timestamps if week_cutoff <= now - t < fortnight_cutoff)
        older = sum(1 for t in timestamps if now - t >= fortnight_cutoff)

        hit_rate_estimate = (recent * 0.5 + week_old * 0.3 + older * 0.1) / len(timestamps)
        hit_rate_estimate = int(hit_rate_estimate * 100)

    return {
        "total_entries": total_entries,
        "total_size_mb": round(total_size_mb, 2),
        "oldest_entry": oldest_ts,
        "newest_entry": newest_ts,
        "daily_stats": daily_stats,
        "largest_files": largest_files,
        "hit_rate_estimate": hit_rate_estimate,
        "cache_dir": str(cache_dir),
    }


async def research_cache_optimize(
    max_age_days: int = 30,
    max_size_mb: int = 500,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Suggest or execute cache optimization.

    Identifies entries older than max_age_days and calculates space savings.
    If total size exceeds max_size_mb, additionally flags oldest entries for
    removal (oldest first) until size target is met.

    Args:
        max_age_days: Remove entries older than this many days
        max_size_mb: Target maximum cache size in MB
        dry_run: If True, only report; if False, delete and report

    Returns:
        Dict with:
        - dry_run: Whether this was a dry-run
        - entries_to_remove: Count of entries marked for removal
        - space_to_free_mb: Total space to be freed in MB
        - entries_to_keep: Count of entries to keep
        - new_total_size_mb: Estimated size after cleanup
    """
    cache = get_cache()
    cache_dir = Path(cache.base_dir)

    if not cache_dir.exists():
        return {
            "dry_run": dry_run,
            "entries_to_remove": 0,
            "space_to_free_mb": 0.0,
            "entries_to_keep": 0,
            "new_total_size_mb": 0.0,
        }

    # Collect all cache files with timestamps
    files_to_check: list[tuple[Path, float, int]] = []
    total_bytes = 0

    for pattern in ("*.json.gz", "*.json"):
        for f in cache_dir.rglob(pattern):
            try:
                stat = f.stat()
                size_bytes = stat.st_size
                mtime = stat.st_mtime
                total_bytes += size_bytes
                files_to_check.append((f, mtime, size_bytes))
            except FileNotFoundError:
                continue

    # Identify entries to remove
    cutoff_time = _dt.datetime.now(_dt.UTC).timestamp() - (max_age_days * 24 * 3600)
    files_to_remove: list[tuple[Path, int]] = []

    # First pass: remove entries older than max_age_days
    for f, mtime, size in files_to_check:
        if mtime < cutoff_time:
            files_to_remove.append((f, size))

    space_to_free = sum(size for _, size in files_to_remove)

    # Second pass: if still over size limit, remove oldest entries
    if total_bytes - space_to_free > max_size_mb * 1024 * 1024:
        remaining = [
            (f, mtime, size)
            for f, mtime, size in files_to_check
            if (f, size) not in files_to_remove
        ]
        remaining.sort(key=lambda x: x[1])  # Sort by timestamp (oldest first)

        current_size = total_bytes - space_to_free
        for f, _mtime, size in remaining:
            if current_size <= max_size_mb * 1024 * 1024:
                break
            if (f, size) not in files_to_remove:
                files_to_remove.append((f, size))
                space_to_free += size
                current_size -= size

    # Execute or report
    removed_count = 0
    if not dry_run:
        for f, _size in files_to_remove:
            try:
                f.unlink()
                removed_count += 1
            except FileNotFoundError:
                continue
            except OSError as e:
                logger.warning("cache_optimize_delete_failed path=%s: %s", f, e)

        # Try to remove empty date directories
        for day_dir in cache_dir.iterdir():
            try:
                if day_dir.is_dir() and not any(day_dir.iterdir()):
                    day_dir.rmdir()
            except OSError:
                pass

    return {
        "dry_run": dry_run,
        "entries_to_remove": len(files_to_remove),
        "space_to_free_mb": round(space_to_free / (1024 * 1024), 2),
        "entries_to_keep": len(files_to_check) - len(files_to_remove),
        "new_total_size_mb": round((total_bytes - space_to_free) / (1024 * 1024), 2),
    }
