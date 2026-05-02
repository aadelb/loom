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


def research_cache_analyze() -> dict[str, Any]:
    """Analyze cache usage: total size, oldest/newest, daily stats, largest files, hit rate estimate."""
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

    files, daily_stats_dict, timestamps, total_bytes, file_sizes = [], {}, [], 0, []
    for pattern in ("*.json.gz", "*.json"):
        for f in cache_dir.rglob(pattern):
            try:
                if f.is_file():
                    stat = f.stat()
                    size_bytes, mtime = stat.st_size, stat.st_mtime
                    files.append(f)
                    total_bytes += size_bytes
                    timestamps.append(mtime)
                    file_sizes.append((f, size_bytes))
                    date_key = f.parent.name
                    if date_key not in daily_stats_dict:
                        daily_stats_dict[date_key] = {"entries": 0, "size_bytes": 0}
                    daily_stats_dict[date_key]["entries"] += 1
                    daily_stats_dict[date_key]["size_bytes"] += size_bytes
            except FileNotFoundError:
                pass

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

    oldest_ts = (
        _dt.datetime.fromtimestamp(min(timestamps), _dt.UTC).isoformat() if timestamps else None
    )
    newest_ts = (
        _dt.datetime.fromtimestamp(max(timestamps), _dt.UTC).isoformat() if timestamps else None
    )
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    largest_files = [
        {"path": str(f.relative_to(cache_dir)), "size_kb": round(sz / 1024, 2)}
        for f, sz in file_sizes[:10]
    ]
    daily_stats = [
        {
            "date": k,
            "entries": daily_stats_dict[k]["entries"],
            "size_mb": round(daily_stats_dict[k]["size_bytes"] / (1024 * 1024), 2),
        }
        for k in sorted(daily_stats_dict.keys())
    ]

    if timestamps:
        now = _dt.datetime.now(_dt.UTC).timestamp()
        recent = sum(1 for t in timestamps if now - t < 7 * 24 * 3600)
        week_old = sum(1 for t in timestamps if 7 * 24 * 3600 <= now - t < 14 * 24 * 3600)
        older = sum(1 for t in timestamps if now - t >= 14 * 24 * 3600)
        hit_rate = int((recent * 0.5 + week_old * 0.3 + older * 0.1) / len(timestamps) * 100)
    else:
        hit_rate = 0

    return {
        "total_entries": len(files),
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "oldest_entry": oldest_ts,
        "newest_entry": newest_ts,
        "daily_stats": daily_stats,
        "largest_files": largest_files,
        "hit_rate_estimate": hit_rate,
        "cache_dir": str(cache_dir),
    }


def research_cache_optimize(
    max_age_days: int = 30, max_size_mb: int = 500, dry_run: bool = True
) -> dict[str, Any]:
    """Optimize cache: remove entries older than max_age_days or exceeding max_size_mb."""
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

    files_to_check, total_bytes = [], 0
    for pattern in ("*.json.gz", "*.json"):
        for f in cache_dir.rglob(pattern):
            try:
                stat = f.stat()
                files_to_check.append((f, stat.st_mtime, stat.st_size))
                total_bytes += stat.st_size
            except FileNotFoundError:
                pass

    cutoff_time = _dt.datetime.now(_dt.UTC).timestamp() - (max_age_days * 24 * 3600)
    files_to_remove = [(f, sz) for f, mtime, sz in files_to_check if mtime < cutoff_time]
    space_to_free = sum(sz for _, sz in files_to_remove)

    if total_bytes - space_to_free > max_size_mb * 1024 * 1024:
        remaining = [
            (f, mtime, sz) for f, mtime, sz in files_to_check if (f, sz) not in files_to_remove
        ]
        remaining.sort(key=lambda x: x[1])
        current_size = total_bytes - space_to_free
        for f, _mtime, sz in remaining:
            if current_size <= max_size_mb * 1024 * 1024:
                break
            if (f, sz) not in files_to_remove:
                files_to_remove.append((f, sz))
                space_to_free += sz
                current_size -= sz

    if not dry_run:
        for f, _ in files_to_remove:
            try:
                f.unlink()
            except OSError as e:
                logger.warning("cache_optimize_delete_failed path=%s: %s", f, e)
        for d in cache_dir.iterdir():
            try:
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            except OSError:
                pass

    return {
        "dry_run": dry_run,
        "entries_to_remove": len(files_to_remove),
        "space_to_free_mb": round(space_to_free / (1024 * 1024), 2),
        "entries_to_keep": len(files_to_check) - len(files_to_remove),
        "new_total_size_mb": round((total_bytes - space_to_free) / (1024 * 1024), 2),
    }
