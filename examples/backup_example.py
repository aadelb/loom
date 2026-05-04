#!/usr/bin/env python3
"""Example usage of the Loom backup and rollback system.

This script demonstrates:
1. Creating backups of critical files
2. Listing backups
3. Restoring from backups
4. Cleaning up old backups
5. Thread-safe concurrent operations
"""

import asyncio
import tempfile
import time
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loom.backup_manager import (
    BackupManager,
    get_backup_manager,
    research_backup_create,
    research_backup_restore,
    research_backup_list,
    research_backup_cleanup,
)


def example_1_basic_backup_restore() -> None:
    """Example 1: Basic backup and restore operations."""
    print("\n" + "="*60)
    print("Example 1: Basic Backup and Restore")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(backup_dir=tmpdir)

        # Create test file
        test_file = Path(tmpdir) / "test_file.txt"
        test_file.write_text("Original content")
        print(f"\n✓ Created test file: {test_file}")
        print(f"  Content: {test_file.read_text()}")

        # Create backup
        backup_id = manager.backup(str(test_file))
        print(f"\n✓ Created backup: {backup_id}")

        # Modify file
        test_file.write_text("Modified content")
        print(f"\n✓ Modified file content: {test_file.read_text()}")

        # Restore from backup
        success = manager.restore(backup_id)
        print(f"\n✓ Restored from backup (success={success})")
        print(f"  Content: {test_file.read_text()}")


def example_2_multiple_backups() -> None:
    """Example 2: Creating multiple backups of the same file."""
    print("\n" + "="*60)
    print("Example 2: Multiple Backups and Version History")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(backup_dir=tmpdir, max_backups_per_file=5)

        # Create test file
        test_file = Path(tmpdir) / "versioned_file.txt"
        test_file.write_text("Version 1")
        print(f"\n✓ Created test file: {test_file}")

        # Create multiple versions
        backup_ids = []
        for i in range(1, 4):
            test_file.write_text(f"Version {i + 1}")
            backup_id = manager.backup(str(test_file))
            backup_ids.append(backup_id)
            print(f"  {i}. Backup {backup_id}: {test_file.read_text()}")
            time.sleep(0.01)

        # List all backups
        backups = manager.list_backups(str(test_file))
        print(f"\n✓ Total backups: {len(backups)}")
        for i, backup in enumerate(backups, 1):
            print(f"  {i}. {backup.backup_id}")
            print(f"     Size: {backup.file_size} bytes")
            print(f"     Created: {backup.created_at}")


def example_3_safe_file_modification() -> None:
    """Example 3: Safe file modification workflow."""
    print("\n" + "="*60)
    print("Example 3: Safe File Modification Workflow")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(backup_dir=tmpdir)

        # Step 1: Backup original
        original_file = Path(tmpdir) / "config.json"
        original_file.write_text('{"setting": "original"}')

        backup_id = manager.backup(str(original_file))
        print(f"\n✓ Step 1: Created backup {backup_id}")

        # Step 2: Attempt modification
        try:
            original_file.write_text('{"setting": "modified"}')
            print(f"✓ Step 2: Modified file")

            # Simulate testing
            print(f"✓ Step 3: Testing changes...")

            # Step 4: Verify changes work (in real scenario)
            print(f"✓ Step 4: Changes verified successfully!")
            print(f"  Final content: {original_file.read_text()}")

        except Exception as e:
            print(f"\n✗ Error during modification: {e}")
            print(f"  Rolling back to backup {backup_id}...")
            manager.restore(backup_id)
            print(f"  Content restored: {original_file.read_text()}")


def example_4_listing_backups() -> None:
    """Example 4: Listing and filtering backups."""
    print("\n" + "="*60)
    print("Example 4: Listing and Filtering Backups")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(backup_dir=tmpdir)

        # Create backups for multiple files
        files = [
            Path(tmpdir) / "server.py",
            Path(tmpdir) / "params.py",
            Path(tmpdir) / "config.json",
        ]

        print("\n✓ Creating backups for multiple files:")
        for file_path in files:
            file_path.write_text(f"Content of {file_path.name}")
            manager.backup(str(file_path))
            print(f"  - {file_path.name}")

        # List all backups
        all_backups = manager.list_backups()
        print(f"\n✓ Total backups in system: {len(all_backups)}")

        # Filter by file
        print(f"\n✓ Backups for server.py:")
        server_backups = manager.list_backups(str(files[0]))
        for backup in server_backups:
            print(f"  - {backup.backup_id}")
            print(f"    Path: {backup.file_path}")
            print(f"    Size: {backup.file_size} bytes")


def example_5_cleanup() -> None:
    """Example 5: Cleanup old backups."""
    print("\n" + "="*60)
    print("Example 5: Backup Cleanup")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(
            backup_dir=tmpdir,
            max_backups_per_file=5,
            retention_days=1,
        )

        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Content")

        # Create multiple backups
        print("\n✓ Creating 3 backups:")
        for i in range(3):
            backup_id = manager.backup(str(test_file))
            print(f"  {i + 1}. {backup_id}")
            time.sleep(0.01)

        # List before cleanup
        backups_before = manager.list_backups(str(test_file))
        print(f"\n✓ Backups before cleanup: {len(backups_before)}")

        # Cleanup (default 30 days, so nothing should be deleted)
        deleted = manager.cleanup(days=30)
        print(f"✓ Deleted {deleted} old backups (retention: 30 days)")

        # Cleanup with 0 days (deletes all)
        deleted = manager.cleanup(days=0)
        print(f"✓ Deleted {deleted} old backups (retention: 0 days)")

        backups_after = manager.list_backups(str(test_file))
        print(f"✓ Backups after cleanup: {len(backups_after)}")


async def example_6_mcp_tools() -> None:
    """Example 6: Using MCP tool functions."""
    print("\n" + "="*60)
    print("Example 6: MCP Tool Usage")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Test content")

        # Create backup using MCP tool
        create_result = await research_backup_create(str(test_file))
        print(f"\n✓ research_backup_create result:")
        print(f"  Success: {create_result['success']}")
        if create_result['success']:
            backup_id = create_result['backup_id']
            print(f"  Backup ID: {backup_id}")

            # List backups using MCP tool
            list_result = await research_backup_list()
            print(f"\n✓ research_backup_list result:")
            print(f"  Total backups: {list_result['count']}")

            # Restore using MCP tool
            restore_result = await research_backup_restore(backup_id)
            print(f"\n✓ research_backup_restore result:")
            print(f"  Success: {restore_result['success']}")

            # Cleanup using MCP tool
            cleanup_result = await research_backup_cleanup(days=1)
            print(f"\n✓ research_backup_cleanup result:")
            print(f"  Deleted: {cleanup_result['deleted_count']}")


def main() -> None:
    """Run all examples."""
    print("\n" + "#"*60)
    print("# Loom Backup and Rollback System Examples")
    print("#"*60)

    # Run synchronous examples
    example_1_basic_backup_restore()
    example_2_multiple_backups()
    example_3_safe_file_modification()
    example_4_listing_backups()
    example_5_cleanup()

    # Run async examples
    print("\n" + "#"*60)
    print("# Async MCP Tools Example")
    print("#"*60)
    asyncio.run(example_6_mcp_tools())

    print("\n" + "#"*60)
    print("# Examples Complete!")
    print("#"*60)
    print("\nFor more information, see docs/backup_system.md")


if __name__ == "__main__":
    main()
