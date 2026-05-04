"""File backup and rollback system for high-risk changes.

Provides a BackupManager class for creating, restoring, and managing
file backups with automatic cleanup and rotation policies.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.backup_manager")

# Global lock for thread-safe backup operations
_backup_lock = threading.RLock()

# Singleton instance
_backup_manager_instance: BackupManager | None = None


@dataclass(frozen=True)
class BackupMetadata:
    """Immutable backup metadata."""

    backup_id: str
    file_path: str
    original_filename: str
    created_at: str
    file_size: int
    file_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class BackupInfo:
    """Immutable backup information."""

    backup_id: str
    file_path: str
    filename: str
    created_at: str
    file_size: int
    backup_path: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class BackupManager:
    """Manages file backups with automatic rotation and cleanup.

    Features:
    - Atomic backup creation with metadata tracking
    - Restore from backup with integrity verification
    - Automatic rotation (max 100 backups per file)
    - Cleanup of old backups (configurable retention days)
    - Thread-safe operations
    """

    def __init__(
        self,
        backup_dir: str | None = None,
        max_backups_per_file: int = 100,
        retention_days: int = 30,
    ):
        """Initialize BackupManager.

        Args:
            backup_dir: Backup directory path. Defaults to ~/.loom/backups
            max_backups_per_file: Maximum backups to keep per file
            retention_days: Default retention period in days
        """
        if backup_dir is None:
            backup_dir = os.path.expanduser("~/.loom/backups")

        self.backup_dir = Path(backup_dir)
        self.max_backups_per_file = max_backups_per_file
        self.retention_days = retention_days

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata directory
        self.metadata_dir = self.backup_dir / ".metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info("BackupManager initialized", extra={
            "backup_dir": str(self.backup_dir),
            "max_backups_per_file": max_backups_per_file,
            "retention_days": retention_days,
        })

    @staticmethod
    def _compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
        """Compute hash of file contents.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (sha256, md5, etc)

        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.new(algorithm)
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
        except (IOError, OSError) as e:
            logger.error("Failed to compute file hash", extra={
                "file_path": file_path,
                "error": str(e),
            })
            return ""
        return hasher.hexdigest()

    @staticmethod
    def _generate_backup_id() -> str:
        """Generate backup ID from current timestamp.

        Returns:
            Backup ID in format: YYYYMMDDTHHmmss_microseconds
        """
        now = datetime.now(UTC)
        return now.strftime("%Y%m%dT%H%M%S") + f"_{now.microsecond:06d}"

    def _get_file_metadata_path(self, original_file_path: str) -> Path:
        """Get metadata file path for a given original file.

        Args:
            original_file_path: Path to original file

        Returns:
            Path to metadata JSON file
        """
        file_hash = hashlib.md5(original_file_path.encode()).hexdigest()
        return self.metadata_dir / f"{file_hash}.json"

    def _load_file_metadata(self, original_file_path: str) -> list[dict[str, Any]]:
        """Load backup metadata for a file.

        Args:
            original_file_path: Path to original file

        Returns:
            List of backup metadata dictionaries
        """
        metadata_path = self._get_file_metadata_path(original_file_path)
        if not metadata_path.exists():
            return []

        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.warning("Failed to load metadata", extra={
                "file_path": original_file_path,
                "error": str(e),
            })
            return []

    def _save_file_metadata(
        self,
        original_file_path: str,
        metadata_list: list[dict[str, Any]],
    ) -> None:
        """Save backup metadata for a file.

        Args:
            original_file_path: Path to original file
            metadata_list: List of metadata dictionaries
        """
        metadata_path = self._get_file_metadata_path(original_file_path)
        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata_list, f, indent=2)
        except IOError as e:
            logger.error("Failed to save metadata", extra={
                "file_path": original_file_path,
                "error": str(e),
            })

    def _rotate_old_backups(self, original_file_path: str) -> None:
        """Remove oldest backups if max count exceeded.

        Args:
            original_file_path: Path to original file
        """
        metadata_list = self._load_file_metadata(original_file_path)

        # Sort by creation time, oldest first
        metadata_list.sort(key=lambda x: x["created_at"])

        # Remove oldest backups if exceeding max
        while len(metadata_list) > self.max_backups_per_file:
            oldest = metadata_list.pop(0)
            backup_path = Path(oldest["backup_path"])

            # Delete backup file
            if backup_path.exists():
                try:
                    backup_path.unlink()
                    logger.info("Rotated old backup", extra={
                        "backup_id": oldest["backup_id"],
                        "backup_path": str(backup_path),
                    })
                except OSError as e:
                    logger.warning("Failed to delete old backup", extra={
                        "backup_path": str(backup_path),
                        "error": str(e),
                    })

        self._save_file_metadata(original_file_path, metadata_list)

    def backup(self, file_path: str) -> str:
        """Create a backup of the specified file.

        Args:
            file_path: Path to file to backup

        Returns:
            Backup ID (timestamp string)

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If backup creation fails
        """
        with _backup_lock:
            # Validate file exists
            source_path = Path(file_path)
            if not source_path.exists():
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            if not source_path.is_file():
                error_msg = f"Path is not a file: {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Generate backup ID
            backup_id = self._generate_backup_id()
            filename = source_path.name
            backup_path = self.backup_dir / f"{backup_id}_{filename}"

            try:
                # Copy file atomically
                shutil.copy2(source_path, backup_path)

                # Compute file hash
                file_hash = self._compute_file_hash(str(backup_path))
                file_size = backup_path.stat().st_size

                # Create metadata
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    file_path=file_path,
                    original_filename=filename,
                    created_at=datetime.now(UTC).isoformat(),
                    file_size=file_size,
                    file_hash=file_hash,
                )

                # Load existing metadata
                metadata_list = self._load_file_metadata(file_path)
                metadata_list.append(metadata.to_dict())

                # Save updated metadata
                self._save_file_metadata(file_path, metadata_list)

                # Rotate old backups
                self._rotate_old_backups(file_path)

                logger.info("File backed up successfully", extra={
                    "backup_id": backup_id,
                    "file_path": file_path,
                    "backup_path": str(backup_path),
                    "file_size": file_size,
                    "file_hash": file_hash,
                })

                return backup_id

            except (IOError, OSError) as e:
                error_msg = f"Failed to create backup: {str(e)}"
                logger.error(error_msg, extra={
                    "file_path": file_path,
                    "backup_path": str(backup_path),
                })
                raise IOError(error_msg) from e

    def restore(self, backup_id: str, target_path: str | None = None) -> bool:
        """Restore file from backup.

        Args:
            backup_id: Backup ID to restore
            target_path: Path to restore to. If None, restores to original location.

        Returns:
            True if restore successful, False otherwise
        """
        with _backup_lock:
            # Find backup file
            backup_files = list(self.backup_dir.glob(f"{backup_id}_*"))

            if not backup_files:
                logger.error("Backup not found", extra={
                    "backup_id": backup_id,
                })
                return False

            if len(backup_files) > 1:
                logger.warning("Multiple backups found for ID", extra={
                    "backup_id": backup_id,
                    "count": len(backup_files),
                })

            backup_path = backup_files[0]

            # Find original file path from metadata
            original_file_path = None
            for metadata_path in self.metadata_dir.glob("*.json"):
                try:
                    with open(metadata_path, "r") as f:
                        metadata_list = json.load(f)
                        for entry in metadata_list:
                            if entry["backup_id"] == backup_id:
                                original_file_path = entry["file_path"]
                                break
                except (IOError, json.JSONDecodeError):
                    continue

                if original_file_path:
                    break

            if not original_file_path and not target_path:
                logger.error("Cannot determine restore target", extra={
                    "backup_id": backup_id,
                })
                return False

            # Determine target
            restore_to = Path(target_path) if target_path else Path(original_file_path)

            try:
                # Create backup of current file before restore (if it exists)
                if restore_to.exists():
                    pre_restore_backup_id = self._generate_backup_id()
                    pre_restore_path = self.backup_dir / f"{pre_restore_backup_id}_pre-restore_{restore_to.name}"
                    shutil.copy2(restore_to, pre_restore_path)
                    logger.info("Created pre-restore backup", extra={
                        "pre_restore_id": pre_restore_backup_id,
                        "path": str(pre_restore_path),
                    })

                # Restore file
                restore_to.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, restore_to)

                # Verify integrity by comparing hashes
                restored_hash = self._compute_file_hash(str(restore_to))
                backup_hash = self._compute_file_hash(str(backup_path))

                if restored_hash != backup_hash:
                    logger.error("Hash mismatch after restore", extra={
                        "backup_id": backup_id,
                        "backup_hash": backup_hash,
                        "restored_hash": restored_hash,
                    })
                    return False

                logger.info("File restored successfully", extra={
                    "backup_id": backup_id,
                    "restore_to": str(restore_to),
                })
                return True

            except (IOError, OSError) as e:
                logger.error("Failed to restore backup", extra={
                    "backup_id": backup_id,
                    "error": str(e),
                })
                return False

    def list_backups(self, file_path: str = "") -> list[BackupInfo]:
        """List all backups, optionally filtered by file path.

        Args:
            file_path: Optional file path filter. If empty, lists all backups.

        Returns:
            List of BackupInfo objects, sorted by creation time (newest first)
        """
        backups: list[dict[str, Any]] = []

        # Scan metadata files
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata_list = json.load(f)
                    for entry in metadata_list:
                        # Filter by file_path if provided
                        if file_path and entry["file_path"] != file_path:
                            continue

                        backup_id = entry["backup_id"]
                        original_filename = entry["original_filename"]
                        backup_file = self.backup_dir / f"{backup_id}_{original_filename}"

                        backups.append({
                            "backup_id": backup_id,
                            "file_path": entry["file_path"],
                            "filename": original_filename,
                            "created_at": entry["created_at"],
                            "file_size": entry["file_size"],
                            "backup_path": str(backup_file),
                        })
            except (IOError, json.JSONDecodeError):
                continue

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        return [BackupInfo(**b) for b in backups]

    def cleanup(self, days: int | None = None) -> int:
        """Delete backups older than specified number of days.

        Args:
            days: Number of days to retain. Defaults to self.retention_days

        Returns:
            Number of backups deleted
        """
        with _backup_lock:
            if days is None:
                days = self.retention_days

            cutoff_time = datetime.now(UTC) - timedelta(days=days)
            deleted_count = 0

            all_backups = self.list_backups()

            for backup_info in all_backups:
                try:
                    backup_time = datetime.fromisoformat(backup_info.created_at)
                    if backup_time < cutoff_time:
                        backup_path = Path(backup_info.backup_path)
                        if backup_path.exists():
                            backup_path.unlink()
                            deleted_count += 1
                            logger.info("Deleted old backup", extra={
                                "backup_id": backup_info.backup_id,
                                "file_path": backup_info.file_path,
                            })

                        # Update metadata
                        metadata_list = self._load_file_metadata(
                            backup_info.file_path
                        )
                        metadata_list = [
                            m for m in metadata_list
                            if m["backup_id"] != backup_info.backup_id
                        ]
                        self._save_file_metadata(
                            backup_info.file_path,
                            metadata_list,
                        )

                except (ValueError, IOError) as e:
                    logger.warning("Failed to cleanup backup", extra={
                        "backup_id": backup_info.backup_id,
                        "error": str(e),
                    })

            logger.info("Backup cleanup completed", extra={
                "deleted_count": deleted_count,
                "retention_days": days,
            })

            return deleted_count


def get_backup_manager(
    backup_dir: str | None = None,
    max_backups_per_file: int = 100,
    retention_days: int = 30,
) -> BackupManager:
    """Get or create singleton BackupManager instance.

    Args:
        backup_dir: Backup directory path
        max_backups_per_file: Maximum backups per file
        retention_days: Retention period in days

    Returns:
        BackupManager instance
    """
    global _backup_manager_instance

    with _backup_lock:
        if _backup_manager_instance is None:
            _backup_manager_instance = BackupManager(
                backup_dir=backup_dir,
                max_backups_per_file=max_backups_per_file,
                retention_days=retention_days,
            )

        return _backup_manager_instance


# MCP Tool Functions
async def research_backup_create(file_path: str) -> dict[str, Any]:
    """Create a backup of a file.

    Args:
        file_path: Path to file to backup

    Returns:
        Dictionary with backup_id and status
    """
    try:
        manager = get_backup_manager()
        backup_id = manager.backup(file_path)
        return {
            "success": True,
            "backup_id": backup_id,
            "file_path": file_path,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        error_msg = f"Backup failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "file_path": file_path,
        }


async def research_backup_restore(
    backup_id: str,
    target_path: str | None = None,
) -> dict[str, Any]:
    """Restore a file from backup.

    Args:
        backup_id: Backup ID to restore
        target_path: Optional path to restore to

    Returns:
        Dictionary with restore status
    """
    try:
        manager = get_backup_manager()
        success = manager.restore(backup_id, target_path)
        return {
            "success": success,
            "backup_id": backup_id,
            "target_path": target_path,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        error_msg = f"Restore failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "backup_id": backup_id,
        }


async def research_backup_list(
    file_path: str = "",
) -> dict[str, Any]:
    """List all backups.

    Args:
        file_path: Optional file path filter

    Returns:
        Dictionary with list of backups
    """
    try:
        manager = get_backup_manager()
        backups = manager.list_backups(file_path)
        return {
            "success": True,
            "count": len(backups),
            "backups": [b.to_dict() for b in backups],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        error_msg = f"Failed to list backups: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
        }


async def research_backup_cleanup(days: int = 30) -> dict[str, Any]:
    """Clean up backups older than specified days.

    Args:
        days: Number of days to retain (default: 30)

    Returns:
        Dictionary with cleanup status
    """
    try:
        manager = get_backup_manager()
        deleted_count = manager.cleanup(days)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "retention_days": days,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        error_msg = f"Cleanup failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
        }
