"""Tests for the backup system tools."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import loom.tools.infrastructure.backup_system


@pytest.fixture
def temp_loom_dir(tmp_path):
    """Create a temporary Loom data directory with test databases."""
    loom_dir = tmp_path / ".loom"
    loom_dir.mkdir()

    # Create test SQLite files
    db_files = ["auth.db", "change_monitor.db", "checkpoints.db", "dlq.db"]
    for db_file in db_files:
        (loom_dir / db_file).write_bytes(b"test sqlite data")

    # Create test config
    (tmp_path / "config.json").write_text('{"test": "config"}')

    return tmp_path, loom_dir


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory with test content."""
    cache_dir = tmp_path / ".cache" / "loom"
    cache_dir.mkdir(parents=True)

    # Create test cache entries
    (cache_dir / "2025-05-01").mkdir(parents=True)
    (cache_dir / "2025-05-01" / "cache1.json").write_text('{"data": "test"}')
    (cache_dir / "2025-05-02").mkdir(parents=True)
    (cache_dir / "2025-05-02" / "cache2.json").write_text('{"data": "test2"}')

    return cache_dir


@pytest.mark.asyncio
async def test_backup_create_all(temp_loom_dir, tmp_path):
    """Test creating a backup with all targets."""
    tmp_path, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            with patch.object(
                backup_system, "_get_config_file", return_value=tmp_path / "config.json"
            ):
                result = await backup_system.research_backup_create(target="all")

                assert "backup_id" in result
                assert "path" in result
                assert "files_backed_up" in result
                assert "total_size_mb" in result
                assert "timestamp" in result

                # Verify backup directory exists
                backup_path = Path(result["path"])
                assert backup_path.exists()

                # Verify files were backed up
                assert len(result["files_backed_up"]) > 0
                assert result["total_size_mb"] > 0


@pytest.mark.asyncio
async def test_backup_create_sqlite_only(temp_loom_dir):
    """Test creating a backup with SQLite target only."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            result = await backup_system.research_backup_create(target="sqlite")

            assert "backup_id" in result
            backup_path = Path(result["path"])
            assert backup_path.exists()

            # Verify only DB files were backed up
            db_files = list(backup_path.glob("*.db"))
            assert len(db_files) > 0


@pytest.mark.asyncio
async def test_backup_create_cache_only(temp_loom_dir, temp_cache_dir):
    """Test creating a backup with cache target only."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            with patch.object(
                backup_system, "_get_cache_dir", return_value=temp_cache_dir
            ):
                result = await backup_system.research_backup_create(target="cache")

                backup_path = Path(result["path"])
                cache_backup = backup_path / "cache"
                assert cache_backup.exists()


@pytest.mark.asyncio
async def test_backup_create_config_only(temp_loom_dir, tmp_path):
    """Test creating a backup with config target only."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            with patch.object(
                backup_system, "_get_config_file", return_value=tmp_path / "config.json"
            ):
                result = await backup_system.research_backup_create(target="config")

                backup_path = Path(result["path"])
                config_backup = backup_path / "config.json"
                assert config_backup.exists()


@pytest.mark.asyncio
async def test_backup_list_empty(temp_loom_dir):
    """Test listing backups when none exist."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_backup_dir", return_value=loom_dir / "backups"):
        result = await backup_system.research_backup_list()

        assert "backups" in result
        assert "total_backups" in result
        assert "total_size_mb" in result
        assert result["total_backups"] == 0
        assert len(result["backups"]) == 0


@pytest.mark.asyncio
async def test_backup_list_multiple(temp_loom_dir):
    """Test listing multiple backups."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            # Create two backups
            await backup_system.research_backup_create(target="sqlite")
            await asyncio.sleep(0.1)  # Ensure different timestamp
            await backup_system.research_backup_create(target="sqlite")

            result = await backup_system.research_backup_list()

            assert result["total_backups"] == 2
            assert len(result["backups"]) == 2

            # Verify backup entries have required fields
            for backup in result["backups"]:
                assert "id" in backup
                assert "timestamp" in backup
                assert "size_mb" in backup
                assert "files_count" in backup


@pytest.mark.asyncio
async def test_backup_restore_dry_run(temp_loom_dir):
    """Test dry-run restore (no actual file modification)."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            # Create a backup first
            create_result = await backup_system.research_backup_create(
                target="sqlite"
            )
            backup_id = create_result["backup_id"]

            # Dry-run restore
            restore_result = await backup_system.research_backup_restore(
                backup_id=backup_id, target="sqlite", dry_run=True
            )

            assert restore_result["backup_id"] == backup_id
            assert restore_result["dry_run"] is True
            assert len(restore_result["restored_files"]) > 0
            assert isinstance(restore_result["warnings"], list)


@pytest.mark.asyncio
async def test_backup_restore_not_found(temp_loom_dir):
    """Test restore with non-existent backup."""
    _, loom_dir = temp_loom_dir

    with patch.object(
        backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
    ):
        result = await backup_system.research_backup_restore(
            backup_id="2099-01-01_000000", target="all", dry_run=True
        )

        assert result["backup_id"] == "2099-01-01_000000"
        assert len(result["restored_files"]) == 0
        assert len(result["warnings"]) > 0
        assert "not found" in result["warnings"][0].lower()


@pytest.mark.asyncio
async def test_backup_restore_actual(temp_loom_dir):
    """Test actual restore (non-dry-run)."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        with patch.object(
            backup_system, "_get_backup_dir", return_value=loom_dir / "backups"
        ):
            # Create a backup
            create_result = await backup_system.research_backup_create(
                target="sqlite"
            )
            backup_id = create_result["backup_id"]

            # Modify a DB file to verify restore works
            db_file = list(loom_dir.glob("*.db"))[0]
            original_content = db_file.read_bytes()
            db_file.write_bytes(b"modified content")

            # Restore (not dry-run)
            restore_result = await backup_system.research_backup_restore(
                backup_id=backup_id, target="sqlite", dry_run=False
            )

            # Verify the file was restored
            assert db_file.read_bytes() == original_content
            assert restore_result["dry_run"] is False


def test_helper_get_loom_data_dir():
    """Test _get_loom_data_dir helper."""
    result = backup_system._get_loom_data_dir()
    assert isinstance(result, Path)
    assert "loom" in str(result)


def test_helper_get_backup_dir():
    """Test _get_backup_dir helper."""
    result = backup_system._get_backup_dir()
    assert isinstance(result, Path)
    assert result.exists()
    assert "backups" in str(result)


def test_helper_get_cache_dir():
    """Test _get_cache_dir helper."""
    result = backup_system._get_cache_dir()
    assert isinstance(result, Path)
    assert "cache" in str(result) and "loom" in str(result)


def test_helper_get_config_file():
    """Test _get_config_file helper."""
    result = backup_system._get_config_file()
    assert isinstance(result, Path)
    assert result.name == "config.json"


def test_helper_calculate_size_mb(tmp_path):
    """Test _calculate_size_mb helper."""
    # Test with a file
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"a" * 1024 * 1024)  # 1 MB
    size_mb = backup_system._calculate_size_mb(test_file)
    assert 0.99 < size_mb < 1.01  # Allow small rounding difference

    # Test with a directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_bytes(b"a" * 1024 * 512)  # 0.5 MB
    (test_dir / "file2.txt").write_bytes(b"a" * 1024 * 512)  # 0.5 MB
    size_mb = backup_system._calculate_size_mb(test_dir)
    assert 0.99 < size_mb < 1.01

    # Test with non-existent path
    size_mb = backup_system._calculate_size_mb(tmp_path / "nonexistent")
    assert size_mb == 0.0


def test_helper_get_sqlite_files(temp_loom_dir):
    """Test _get_sqlite_files helper."""
    _, loom_dir = temp_loom_dir

    with patch.object(backup_system, "_get_loom_data_dir", return_value=loom_dir):
        result = backup_system._get_sqlite_files()

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(f.suffix == ".db" for f in result)
        assert all(f.exists() for f in result)
