"""Tests for backup_manager module.

Tests cover:
- Backup creation with metadata tracking
- Restore operations with integrity verification
- Listing backups with filtering
- Automatic rotation of old backups
- Cleanup of expired backups
- Thread safety
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from loom.backup_manager import (
    BackupInfo,
    BackupManager,
    BackupMetadata,
    get_backup_manager,
    research_backup_cleanup,
    research_backup_create,
    research_backup_list,
    research_backup_restore,
)


@pytest.fixture
def temp_backup_dir() -> str:
    """Create temporary backup directory."""
    tmpdir = tempfile.mkdtemp(prefix="loom_backup_test_")
    yield tmpdir
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture
def temp_source_dir() -> str:
    """Create temporary source directory for test files."""
    tmpdir = tempfile.mkdtemp(prefix="loom_source_test_")
    yield tmpdir
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture
def backup_manager(temp_backup_dir: str) -> BackupManager:
    """Create BackupManager instance with temp directory."""
    return BackupManager(
        backup_dir=temp_backup_dir,
        max_backups_per_file=5,
        retention_days=30,
    )


class TestBackupManagerBasics:
    """Test basic backup manager functionality."""

    def test_backup_manager_initialization(self, temp_backup_dir: str) -> None:
        """Test BackupManager initialization."""
        manager = BackupManager(backup_dir=temp_backup_dir)
        assert manager.backup_dir.exists()
        assert manager.metadata_dir.exists()
        assert manager.max_backups_per_file == 100
        assert manager.retention_days == 30

    def test_backup_creation(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test creating a backup."""
        # Create test file
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("test content")

        # Create backup
        backup_id = backup_manager.backup(str(test_file))

        assert backup_id
        assert len(backup_id) > 0

        # Verify backup file exists
        backup_files = list(backup_manager.backup_dir.glob(f"{backup_id}_*"))
        assert len(backup_files) == 1
        assert backup_files[0].exists()

        # Verify content
        assert backup_files[0].read_text() == "test content"

    def test_backup_nonexistent_file(self, backup_manager: BackupManager) -> None:
        """Test backing up nonexistent file."""
        with pytest.raises(FileNotFoundError):
            backup_manager.backup("/nonexistent/path/file.txt")

    def test_backup_directory_fails(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test that backing up a directory fails."""
        with pytest.raises(ValueError):
            backup_manager.backup(temp_source_dir)

    def test_restore_backup(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test restoring a backup."""
        # Create test file
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("original content")

        # Create backup
        backup_id = backup_manager.backup(str(test_file))

        # Modify original file
        test_file.write_text("modified content")

        # Restore backup
        success = backup_manager.restore(backup_id)
        assert success

        # Verify restored content
        assert test_file.read_text() == "original content"

    def test_restore_to_different_path(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test restoring backup to different path."""
        # Create test file
        source_file = Path(temp_source_dir) / "source.txt"
        source_file.write_text("source content")

        # Create backup
        backup_id = backup_manager.backup(str(source_file))

        # Restore to different path
        restore_path = Path(temp_source_dir) / "restored.txt"
        success = backup_manager.restore(backup_id, str(restore_path))
        assert success
        assert restore_path.exists()
        assert restore_path.read_text() == "source content"

    def test_restore_nonexistent_backup(
        self,
        backup_manager: BackupManager,
    ) -> None:
        """Test restoring nonexistent backup."""
        success = backup_manager.restore("nonexistent_backup_id")
        assert not success


class TestBackupMetadata:
    """Test backup metadata handling."""

    def test_metadata_creation(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test metadata is created for backups."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("test content")

        backup_id = backup_manager.backup(str(test_file))

        # Check metadata file exists
        metadata_files = list(backup_manager.metadata_dir.glob("*.json"))
        assert len(metadata_files) > 0

        # Load and verify metadata
        for metadata_file in metadata_files:
            with open(metadata_file, "r") as f:
                metadata_list = json.load(f)
                matching = [m for m in metadata_list if m["backup_id"] == backup_id]
                if matching:
                    entry = matching[0]
                    assert entry["file_path"] == str(test_file)
                    assert entry["original_filename"] == "test.txt"
                    assert entry["file_size"] == len("test content")
                    assert len(entry["file_hash"]) == 64  # SHA256 hex digest
                    break

    def test_backup_metadata_immutability(self) -> None:
        """Test BackupMetadata is immutable."""
        metadata = BackupMetadata(
            backup_id="test_id",
            file_path="/path/to/file.txt",
            original_filename="file.txt",
            created_at="2024-01-01T00:00:00+00:00",
            file_size=1024,
            file_hash="abc123",
        )

        # Verify frozen (immutable)
        with pytest.raises(AttributeError):
            metadata.backup_id = "modified"  # type: ignore


class TestBackupListing:
    """Test listing and filtering backups."""

    def test_list_all_backups(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test listing all backups."""
        # Create multiple test files
        file1 = Path(temp_source_dir) / "file1.txt"
        file1.write_text("content1")
        file2 = Path(temp_source_dir) / "file2.txt"
        file2.write_text("content2")

        # Create backups
        backup_manager.backup(str(file1))
        backup_manager.backup(str(file2))

        # List all backups
        backups = backup_manager.list_backups()
        assert len(backups) >= 2

    def test_list_backups_filtered_by_file(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test listing backups filtered by file path."""
        file1 = Path(temp_source_dir) / "file1.txt"
        file1.write_text("content1")
        file2 = Path(temp_source_dir) / "file2.txt"
        file2.write_text("content2")

        backup_manager.backup(str(file1))
        backup_manager.backup(str(file2))

        # List backups for file1 only
        backups = backup_manager.list_backups(str(file1))
        assert all(b.file_path == str(file1) for b in backups)
        assert len(backups) >= 1

    def test_backup_info_conversion(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test BackupInfo to_dict conversion."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("content")

        backup_manager.backup(str(test_file))
        backups = backup_manager.list_backups()

        assert len(backups) > 0
        backup = backups[0]
        backup_dict = backup.to_dict()

        assert "backup_id" in backup_dict
        assert "file_path" in backup_dict
        assert "filename" in backup_dict
        assert "created_at" in backup_dict
        assert "file_size" in backup_dict
        assert "backup_path" in backup_dict


class TestBackupRotation:
    """Test automatic backup rotation."""

    def test_backup_rotation(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test that old backups are removed when max count exceeded."""
        test_file = Path(temp_source_dir) / "test.txt"

        # Create more backups than max_backups_per_file
        backup_ids = []
        for i in range(backup_manager.max_backups_per_file + 3):
            test_file.write_text(f"content {i}")
            backup_id = backup_manager.backup(str(test_file))
            backup_ids.append(backup_id)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # List backups
        backups = backup_manager.list_backups(str(test_file))

        # Should have at most max_backups_per_file
        assert len(backups) <= backup_manager.max_backups_per_file

        # Oldest backups should be removed
        remaining_ids = [b.backup_id for b in backups]
        # First few IDs should not be in remaining
        assert backup_ids[0] not in remaining_ids


class TestBackupCleanup:
    """Test backup cleanup functionality."""

    def test_cleanup_old_backups(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test cleanup of old backups."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("content")

        backup_id = backup_manager.backup(str(test_file))

        # Manually modify metadata to make backup appear old
        metadata_path = backup_manager._get_file_metadata_path(str(test_file))
        with open(metadata_path, "r") as f:
            metadata_list = json.load(f)

        # Set created_at to 40 days ago
        old_time = (datetime.now(UTC) - timedelta(days=40)).isoformat()
        for entry in metadata_list:
            if entry["backup_id"] == backup_id:
                entry["created_at"] = old_time

        with open(metadata_path, "w") as f:
            json.dump(metadata_list, f)

        # Run cleanup with 30-day retention
        deleted_count = backup_manager.cleanup(days=30)
        assert deleted_count > 0

        # Verify backup is removed
        backups = backup_manager.list_backups(str(test_file))
        assert all(b.backup_id != backup_id for b in backups)

    def test_cleanup_recent_backups_preserved(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test that recent backups are preserved during cleanup."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("content")

        backup_id = backup_manager.backup(str(test_file))

        # Run cleanup with 30-day retention
        deleted_count = backup_manager.cleanup(days=30)

        # Recent backup should not be deleted
        assert deleted_count == 0

        # Backup should still exist
        backups = backup_manager.list_backups(str(test_file))
        assert any(b.backup_id == backup_id for b in backups)


class TestThreadSafety:
    """Test thread safety of backup operations."""

    def test_concurrent_backups(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test creating backups concurrently."""
        results: list[str | Exception] = []
        errors: list[str] = []

        def create_backup(i: int) -> None:
            try:
                test_file = Path(temp_source_dir) / f"test_{i}.txt"
                test_file.write_text(f"content {i}")
                backup_id = backup_manager.backup(str(test_file))
                results.append(backup_id)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = [
            threading.Thread(target=create_backup, args=(i,))
            for i in range(10)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all backups succeeded
        assert len(errors) == 0
        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_restore(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test restoring backups concurrently."""
        # Create test file and backup
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("original")
        backup_id = backup_manager.backup(str(test_file))

        results: list[bool] = []
        errors: list[str] = []

        def restore_backup() -> None:
            try:
                success = backup_manager.restore(backup_id)
                results.append(success)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = [threading.Thread(target=restore_backup) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all restores succeeded
        assert len(errors) == 0
        assert all(results)


class TestMCPTools:
    """Test MCP tool functions."""

    @pytest.mark.asyncio
    async def test_research_backup_create(
        self,
        temp_source_dir: str,
    ) -> None:
        """Test research_backup_create MCP tool."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("content")

        result = await research_backup_create(str(test_file))

        assert result["success"]
        assert "backup_id" in result
        assert result["file_path"] == str(test_file)

    @pytest.mark.asyncio
    async def test_research_backup_restore(
        self,
        temp_source_dir: str,
    ) -> None:
        """Test research_backup_restore MCP tool."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("original")

        # Create backup
        backup_result = await research_backup_create(str(test_file))
        assert backup_result["success"]
        backup_id = backup_result["backup_id"]

        # Modify file
        test_file.write_text("modified")

        # Restore
        restore_result = await research_backup_restore(backup_id)

        assert restore_result["success"]
        assert restore_result["backup_id"] == backup_id

    @pytest.mark.asyncio
    async def test_research_backup_list(
        self,
        temp_source_dir: str,
    ) -> None:
        """Test research_backup_list MCP tool."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("content")

        # Create backup
        await research_backup_create(str(test_file))

        # List backups
        list_result = await research_backup_list()

        assert list_result["success"]
        assert isinstance(list_result["count"], int)
        assert isinstance(list_result["backups"], list)

    @pytest.mark.asyncio
    async def test_research_backup_cleanup(self) -> None:
        """Test research_backup_cleanup MCP tool."""
        result = await research_backup_cleanup(days=30)

        assert "success" in result
        assert "deleted_count" in result
        assert "retention_days" in result


class TestComputeFileHash:
    """Test file hash computation."""

    def test_compute_sha256_hash(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test SHA256 hash computation."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("test content")

        hash_value = backup_manager._compute_file_hash(str(test_file), "sha256")

        # SHA256 hex digest is 64 characters
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_hash_consistency(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test that hash is consistent for same content."""
        test_file = Path(temp_source_dir) / "test.txt"
        test_file.write_text("test content")

        hash1 = backup_manager._compute_file_hash(str(test_file))
        hash2 = backup_manager._compute_file_hash(str(test_file))

        assert hash1 == hash2

    def test_hash_differs_for_different_content(
        self,
        backup_manager: BackupManager,
        temp_source_dir: str,
    ) -> None:
        """Test that hash differs for different content."""
        file1 = Path(temp_source_dir) / "file1.txt"
        file1.write_text("content 1")

        file2 = Path(temp_source_dir) / "file2.txt"
        file2.write_text("content 2")

        hash1 = backup_manager._compute_file_hash(str(file1))
        hash2 = backup_manager._compute_file_hash(str(file2))

        assert hash1 != hash2


class TestSingletonPattern:
    """Test BackupManager singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton after each test."""
        import loom.backup_manager
        loom.backup_manager._backup_manager_instance = None
        yield
        loom.backup_manager._backup_manager_instance = None

    def test_get_backup_manager_singleton(self) -> None:
        """Test get_backup_manager returns singleton."""
        manager1 = get_backup_manager()
        manager2 = get_backup_manager()

        assert manager1 is manager2

    def test_get_backup_manager_custom_params(
        self,
        temp_backup_dir: str,
    ) -> None:
        """Test get_backup_manager with custom parameters."""
        manager = get_backup_manager(
            backup_dir=temp_backup_dir,
            max_backups_per_file=50,
            retention_days=60,
        )

        assert manager.max_backups_per_file == 50
        assert manager.retention_days == 60
