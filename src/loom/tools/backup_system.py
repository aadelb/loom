"""Backup system for Loom's persistent data (SQLite, cache, config).

Implements three core operations:
  1. research_backup_create: Create timestamped backup of all persistent data
  2. research_backup_list: List available backups with metadata
  3. research_backup_restore: Restore from backup with dry-run support
"""

from __future__ import annotations

import logging
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.backup")


def _get_loom_data_dir() -> Path:
    """Get the main Loom data directory (~/.loom)."""
    return Path("~/.loom").expanduser()


def _get_backup_dir() -> Path:
    """Get the backup directory (~/.loom/backups)."""
    backup_dir = _get_loom_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


_VALID_TARGETS = {"all", "sqlite", "cache", "config"}
_BACKUP_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}$")


def _get_sqlite_files() -> list[Path]:
    """Get all SQLite database files in ~/.loom (including subdirectories)."""
    loom_dir = _get_loom_data_dir()
    backups_dir = _get_backup_dir()
    db_files = [
        f for f in loom_dir.rglob("*.db")
        if not str(f).startswith(str(backups_dir))
    ]
    return sorted(db_files)


def _get_cache_dir() -> Path:
    """Get the cache directory (~/.cache/loom)."""
    return Path("~/.cache/loom").expanduser()


def _get_config_file() -> Path:
    """Get the config file (./config.json)."""
    return Path("config.json").resolve()


def _calculate_size_mb(path: Path) -> float:
    """Calculate total size of a file or directory in MB."""
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    elif path.is_dir():
        total_bytes = sum(
            f.stat().st_size for f in path.rglob("*") if f.is_file()
        )
        return total_bytes / (1024 * 1024)
    return 0.0


async def research_backup_create(
    target: str = "all",
) -> dict[str, Any]:
    """Create a backup of Loom's persistent data.

    Creates a timestamped backup directory under ~/.loom/backups/YYYY-MM-DD_HHMMSS/
    containing copies of SQLite databases, cache, and config.

    Args:
        target: Backup target - "all" (default), "sqlite", "cache", or "config"

    Returns:
        Dict with:
        - backup_id: Timestamp ID (YYYY-MM-DD_HHMMSS)
        - path: Absolute path to backup directory
        - files_backed_up: List of backed-up file paths
        - total_size_mb: Total backup size in MB
        - timestamp: ISO 8601 timestamp
    """
    if target not in _VALID_TARGETS:
        return {"error": f"Invalid target '{target}', must be one of: {', '.join(sorted(_VALID_TARGETS))}"}

    now = datetime.now(UTC)
    backup_id = now.strftime("%Y-%m-%d_%H%M%S")
    backup_path = _get_backup_dir() / backup_id
    backup_path.mkdir(parents=True, exist_ok=True)

    files_backed_up: list[str] = []
    total_size_mb = 0.0

    try:
        # Backup SQLite files
        if target in ("all", "sqlite"):
            sqlite_files = _get_sqlite_files()
            loom_dir = _get_loom_data_dir()
            for db_file in sqlite_files:
                try:
                    rel_path = db_file.relative_to(loom_dir)
                    dest = backup_path / "sqlite" / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(db_file, dest)
                    files_backed_up.append(str(db_file))
                    total_size_mb += _calculate_size_mb(dest)
                except Exception as e:
                    logger.warning(
                        "backup_sqlite_failed file=%s error=%s",
                        db_file.name,
                        e,
                    )

        # Backup cache directory
        if target in ("all", "cache"):
            cache_dir = _get_cache_dir()
            if cache_dir.exists():
                try:
                    dest_cache = backup_path / "cache"
                    shutil.copytree(
                        cache_dir, dest_cache, dirs_exist_ok=True
                    )
                    files_backed_up.append(str(cache_dir))
                    total_size_mb += _calculate_size_mb(dest_cache)
                except Exception as e:
                    logger.warning(
                        "backup_cache_failed error=%s",
                        e,
                    )

        # Backup config file
        if target in ("all", "config"):
            config_file = _get_config_file()
            if config_file.exists():
                try:
                    dest_config = backup_path / "config.json"
                    shutil.copy2(config_file, dest_config)
                    files_backed_up.append(str(config_file))
                    total_size_mb += _calculate_size_mb(dest_config)
                except Exception as e:
                    logger.warning(
                        "backup_config_failed error=%s",
                        e,
                    )

        return {
            "backup_id": backup_id,
            "path": str(backup_path),
            "files_backed_up": files_backed_up,
            "total_size_mb": round(total_size_mb, 2),
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        logger.error("backup_create_failed error=%s", e)
        # Clean up partial backup on error
        if backup_path.exists():
            shutil.rmtree(backup_path, ignore_errors=True)
        raise


async def research_backup_list() -> dict[str, Any]:
    """List available backups with metadata.

    Scans ~/.loom/backups/ for backup directories and returns summary info.

    Returns:
        Dict with:
        - backups: List of dicts with id, timestamp, size_mb, files_count
        - total_backups: Number of backups
        - total_size_mb: Combined size of all backups
    """
    backup_dir = _get_backup_dir()
    backups: list[dict[str, Any]] = []
    total_size_mb = 0.0

    if not backup_dir.exists():
        return {
            "backups": [],
            "total_backups": 0,
            "total_size_mb": 0.0,
        }

    for backup_folder in sorted(backup_dir.iterdir()):
        if not backup_folder.is_dir():
            continue

        backup_id = backup_folder.name
        size_mb = _calculate_size_mb(backup_folder)
        files_count = sum(
            1 for _ in backup_folder.rglob("*") if _.is_file()
        )

        # Parse timestamp from backup ID (YYYY-MM-DD_HHMMSS)
        try:
            ts = datetime.strptime(
                backup_id, "%Y-%m-%d_%H%M%S"
            ).replace(tzinfo=UTC)
            timestamp = ts.isoformat()
        except ValueError:
            timestamp = "unknown"

        backups.append({
            "id": backup_id,
            "timestamp": timestamp,
            "size_mb": round(size_mb, 2),
            "files_count": files_count,
        })

        total_size_mb += size_mb

    return {
        "backups": backups,
        "total_backups": len(backups),
        "total_size_mb": round(total_size_mb, 2),
    }


async def research_backup_restore(
    backup_id: str,
    target: str = "all",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Restore from a backup.

    If dry_run=True, lists what WOULD be restored without modifying files.
    If dry_run=False, copies backup files back to their original locations.

    Args:
        backup_id: Backup ID (e.g., "2025-05-02_143022")
        target: Restore target - "all" (default), "sqlite", "cache", or "config"
        dry_run: If True, simulate restore; if False, perform actual restore

    Returns:
        Dict with:
        - backup_id: Backup ID that was restored
        - restored_files: List of restored file paths
        - dry_run: Whether this was a dry-run
        - warnings: List of warning messages
    """
    warnings: list[str] = []
    restored_files: list[str] = []

    if target not in _VALID_TARGETS:
        return {"backup_id": backup_id, "restored_files": [], "dry_run": dry_run, "warnings": [f"Invalid target '{target}'"]}

    if not _BACKUP_ID_RE.match(backup_id):
        return {"backup_id": backup_id, "restored_files": [], "dry_run": dry_run, "warnings": ["Invalid backup_id format (expected YYYY-MM-DD_HHMMSS)"]}

    backup_path = _get_backup_dir() / backup_id
    if not backup_path.exists():
        warnings.append(f"Backup '{backup_id}' not found")
        return {
            "backup_id": backup_id,
            "restored_files": [],
            "dry_run": dry_run,
            "warnings": warnings,
        }

    try:
        # Restore SQLite files
        if target in ("all", "sqlite"):
            sqlite_backup = backup_path / "sqlite"
            search_path = sqlite_backup if sqlite_backup.is_dir() else backup_path
            for db_file in search_path.rglob("*.db"):
                try:
                    rel = db_file.relative_to(search_path) if sqlite_backup.is_dir() else Path(db_file.name)
                    original_path = _get_loom_data_dir() / rel
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    if not dry_run:
                        shutil.copy2(db_file, original_path)
                    restored_files.append(str(original_path))
                except Exception as e:
                    warnings.append(
                        f"Failed to restore {db_file.name}: {e}"
                    )

        # Restore cache directory
        if target in ("all", "cache"):
            cache_backup = backup_path / "cache"
            if cache_backup.exists():
                try:
                    cache_dest = _get_cache_dir()
                    if not dry_run:
                        shutil.copytree(cache_backup, cache_dest, dirs_exist_ok=True)
                    restored_files.append(str(cache_dest))
                except Exception as e:
                    warnings.append(f"Failed to restore cache: {e}")

        # Restore config file
        if target in ("all", "config"):
            config_backup = backup_path / "config.json"
            if config_backup.exists():
                try:
                    config_dest = _get_config_file()
                    if not dry_run:
                        shutil.copy2(config_backup, config_dest)
                    restored_files.append(str(config_dest))
                except Exception as e:
                    warnings.append(f"Failed to restore config: {e}")

        return {
            "backup_id": backup_id,
            "restored_files": restored_files,
            "dry_run": dry_run,
            "warnings": warnings,
        }

    except Exception as e:
        logger.error("backup_restore_failed backup_id=%s error=%s", backup_id, e)
        warnings.append(f"Restore operation failed: {e}")
        return {
            "backup_id": backup_id,
            "restored_files": restored_files,
            "dry_run": dry_run,
            "warnings": warnings,
        }
