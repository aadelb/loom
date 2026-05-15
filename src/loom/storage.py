"""Tiered storage management and monitoring.

Implements hot/warm/cold storage tiers based on file age, storage usage
tracking, alert generation, and per-tier breakdown statistics.

Tiers:
  - hot: files < 30 days old, SSD/instant access
  - warm: files 30-365 days old, HDD/slower access
  - cold: files > 365 days old, archive/compressed

Provides storage dashboard data for monitoring and alerting.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.storage")

# Storage tier definitions
TIERS = {
    "hot": {
        "max_age_days": 30,
        "description": "SSD, instant access",
    },
    "warm": {
        "max_age_days": 365,
        "description": "HDD, slower access",
    },
    "cold": {
        "max_age_days": None,
        "description": "Archive, compressed",
    },
}


def get_storage_stats(base_dir: Path) -> dict[str, Any]:
    """Get aggregate storage usage statistics.

    Walks the directory tree and calculates:
      - total size in bytes and MB
      - file count
      - size breakdown by file extension

    Args:
        base_dir: root directory to analyze

    Returns:
        Dict with keys:
          - total_size_bytes: total size in bytes
          - total_size_mb: total size in MB (rounded to 2 decimals)
          - file_count: number of files
          - by_extension: dict mapping extension (str) to size in MB
    """
    total_size: int = 0
    file_count: int = 0
    by_extension: dict[str, int] = {}

    base_dir = Path(base_dir)
    if not base_dir.exists():
        log.warning("storage_stats_dir_missing path=%s", base_dir)
        return {
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "file_count": 0,
            "by_extension": {},
        }

    for root, dirs, files in os.walk(base_dir):
        for f in files:
            path = Path(root) / f
            try:
                size = path.stat().st_size
                total_size += size
                file_count += 1
                ext = path.suffix or "(no ext)"
                by_extension[ext] = by_extension.get(ext, 0) + size
            except OSError as e:
                log.debug("storage_stats_file_error path=%s: %s", path, e)
                continue

    # Convert extension sizes to MB
    by_extension_mb = {
        k: round(v / (1024 * 1024), 2) for k, v in by_extension.items()
    }

    return {
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "file_count": file_count,
        "by_extension": by_extension_mb,
    }


def check_storage_alerts(
    base_dir: Path, max_size_gb: float = 50.0
) -> list[dict[str, Any]]:
    """Check storage usage and generate alerts.

    Calculates storage usage as percentage of max_size_gb and generates
    alerts based on threshold:
      - critical: >= 90%
      - warning: >= 80% and < 90%
      - info: >= 50% and < 80%

    Args:
        base_dir: root directory to check
        max_size_gb: maximum allowed storage in GB (default: 50)

    Returns:
        List of alert dicts, each with keys:
          - level: "critical", "warning", or "info"
          - message: human-readable alert message
          - action: recommended action (e.g., "expand_or_archive")
    """
    stats = get_storage_stats(base_dir)
    usage_bytes = stats["total_size_bytes"]
    max_bytes = max_size_gb * (1024 ** 3)
    usage_gb = usage_bytes / (1024 ** 3)
    usage_pct = round((usage_bytes / max_bytes * 100), 1) if max_bytes > 0 else 0.0

    alerts: list[dict[str, Any]] = []

    if usage_pct >= 90:
        alerts.append(
            {
                "level": "critical",
                "message": f"Storage at {usage_pct}% ({usage_gb:.1f}GB/{max_size_gb}GB)",
                "action": "expand_or_archive",
            }
        )
        log.warning("storage_alert_critical usage_pct=%s", usage_pct)
    elif usage_pct >= 80:
        alerts.append(
            {
                "level": "warning",
                "message": f"Storage at {usage_pct}% ({usage_gb:.1f}GB/{max_size_gb}GB)",
                "action": "review_retention",
            }
        )
        log.warning("storage_alert_warning usage_pct=%s", usage_pct)
    elif usage_pct >= 50:
        alerts.append(
            {
                "level": "info",
                "message": f"Storage at {usage_pct}% ({usage_gb:.1f}GB/{max_size_gb}GB)",
            }
        )
        log.info("storage_alert_info usage_pct=%s", usage_pct)

    return alerts


def classify_file_tier(file_path: Path) -> str:
    """Classify a file into a storage tier based on age.

    Determines tier by comparing file modification time to current time:
      - hot: age <= 30 days
      - warm: age > 30 days and <= 365 days
      - cold: age > 365 days

    Args:
        file_path: path to file

    Returns:
        Tier string: "hot", "warm", or "cold"
    """
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        age = datetime.now(timezone.utc) - mtime
        days_old = age.days

        if days_old <= 30:
            return "hot"
        elif days_old <= 365:
            return "warm"
        else:
            return "cold"
    except OSError as e:
        log.debug("storage_classify_file_error path=%s: %s", file_path, e)
        return "cold"


def get_tier_breakdown(base_dir: Path) -> dict[str, dict[str, Any]]:
    """Get file count and size per storage tier.

    Walks the directory tree, classifies each file into a tier,
    and aggregates count and size statistics per tier.

    Args:
        base_dir: root directory to analyze

    Returns:
        Dict mapping tier name to stats dict with keys:
          - count: number of files in tier
          - size_bytes: total size in bytes
          - size_mb: total size in MB (rounded to 2 decimals)
    """
    breakdown: dict[str, dict[str, Any]] = {
        tier: {"count": 0, "size_bytes": 0} for tier in TIERS
    }

    base_dir = Path(base_dir)
    if not base_dir.exists():
        log.warning("storage_breakdown_dir_missing path=%s", base_dir)
        for tier in breakdown:
            breakdown[tier]["size_mb"] = 0.0
        return breakdown

    for root, dirs, files in os.walk(base_dir):
        for f in files:
            path = Path(root) / f
            try:
                tier = classify_file_tier(path)
                breakdown[tier]["count"] += 1
                breakdown[tier]["size_bytes"] += path.stat().st_size
            except OSError as e:
                log.debug("storage_breakdown_file_error path=%s: %s", path, e)
                continue

    # Convert size_bytes to size_mb
    for tier in breakdown:
        breakdown[tier]["size_mb"] = round(
            breakdown[tier]["size_bytes"] / (1024 * 1024), 2
        )

    return breakdown


def get_storage_dashboard(
    base_dir: Path, max_size_gb: float = 50.0
) -> dict[str, Any]:
    """Generate a complete storage dashboard with stats, tiers, and alerts.

    Combines get_storage_stats(), get_tier_breakdown(), and
    check_storage_alerts() into a single dashboard view.

    Args:
        base_dir: root directory to analyze
        max_size_gb: maximum allowed storage in GB (default: 50)

    Returns:
        Dict with keys:
          - stats: result from get_storage_stats()
          - tiers: result from get_tier_breakdown()
          - alerts: list from check_storage_alerts()
          - max_size_gb: configured maximum size
    """
    return {
        "stats": get_storage_stats(base_dir),
        "tiers": get_tier_breakdown(base_dir),
        "alerts": check_storage_alerts(base_dir, max_size_gb),
        "max_size_gb": max_size_gb,
    }
