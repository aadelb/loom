# Backup and Rollback System

## Overview

The backup and rollback system provides a comprehensive solution for protecting against unintended changes to critical files in Loom. It's designed specifically for high-risk modifications to files like `server.py`, `params.py`, and other infrastructure modules.

## Features

- **Atomic Backup Creation**: Files are copied with metadata tracking (timestamps, file hashes, sizes)
- **Integrity Verification**: SHA-256 hashing ensures backup integrity during restore
- **Automatic Rotation**: Maintains max 100 backups per file with oldest-first eviction
- **Flexible Cleanup**: Delete backups older than N days with metadata pruning
- **Thread-Safe Operations**: All operations protected by thread-safe locks
- **Metadata Tracking**: JSON-based metadata registry for audit trails
- **Pre-Restore Backup**: Automatically creates backup before restoring to enable undo
- **MCP Tools**: Exposed as research_backup_* functions for programmatic access

## Architecture

### Directory Structure

```
~/.loom/backups/
├── TIMESTAMP_MICROSECONDS_filename.ext    # Backup file
├── .metadata/
│   └── {md5_hash_of_original_path}.json   # Metadata registry
```

### Metadata Format

```json
[
  {
    "backup_id": "20240504T181234_567890",
    "file_path": "/path/to/original/file.txt",
    "original_filename": "file.txt",
    "created_at": "2024-05-04T18:12:34.567890+00:00",
    "file_size": 1024,
    "file_hash": "abc123def456..."
  }
]
```

## Usage

### Python API

#### BackupManager Class

```python
from loom.backup_manager import BackupManager, get_backup_manager

# Get singleton instance
manager = get_backup_manager()

# Create backup
backup_id = manager.backup("/path/to/file.txt")
# Returns: "20240504T181234_567890"

# Restore from backup
success = manager.restore(backup_id)

# Restore to different path
success = manager.restore(backup_id, "/path/to/restore/location.txt")

# List all backups
all_backups = manager.list_backups()

# List backups for specific file
file_backups = manager.list_backups("/path/to/file.txt")

# Cleanup old backups (default: 30 days)
deleted_count = manager.cleanup(days=30)
```

#### Backup Info Objects

```python
# BackupInfo contains:
backup.backup_id      # ID of backup
backup.file_path      # Original file path
backup.filename       # Original filename
backup.created_at     # ISO format timestamp
backup.file_size      # Size in bytes
backup.backup_path    # Full path to backup file

# Convert to dict
backup_dict = backup.to_dict()
```

### MCP Tools

#### research_backup_create

Create a backup of a file.

**Parameters:**
- `file_path` (str, required): Path to file to backup

**Returns:**
```json
{
  "success": true,
  "backup_id": "20240504T181234_567890",
  "file_path": "/path/to/file.txt",
  "timestamp": "2024-05-04T18:12:34.567890+00:00"
}
```

#### research_backup_restore

Restore a file from backup.

**Parameters:**
- `backup_id` (str, required): Backup ID to restore
- `target_path` (str, optional): Path to restore to. If None, restores to original location.

**Returns:**
```json
{
  "success": true,
  "backup_id": "20240504T181234_567890",
  "target_path": "/path/to/file.txt",
  "timestamp": "2024-05-04T18:12:34.567890+00:00"
}
```

#### research_backup_list

List all backups with optional filtering.

**Parameters:**
- `file_path` (str, optional): Filter by file path

**Returns:**
```json
{
  "success": true,
  "count": 5,
  "backups": [
    {
      "backup_id": "20240504T181234_567890",
      "file_path": "/path/to/file.txt",
      "filename": "file.txt",
      "created_at": "2024-05-04T18:12:34.567890+00:00",
      "file_size": 1024,
      "backup_path": "/home/user/.loom/backups/20240504T181234_567890_file.txt"
    }
  ],
  "timestamp": "2024-05-04T18:12:34.567890+00:00"
}
```

#### research_backup_cleanup

Delete backups older than specified days.

**Parameters:**
- `days` (int, default: 30): Number of days to retain

**Returns:**
```json
{
  "success": true,
  "deleted_count": 3,
  "retention_days": 30,
  "timestamp": "2024-05-04T18:12:34.567890+00:00"
}
```

## Recommended Workflow

### Before Making High-Risk Changes

```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()

# Backup critical files
server_backup_id = manager.backup("/Users/aadel/projects/loom/src/loom/server.py")
params_backup_id = manager.backup("/Users/aadel/projects/loom/src/loom/params.py")

print(f"Backups created:")
print(f"  server.py: {server_backup_id}")
print(f"  params.py: {params_backup_id}")

# Now make your changes...
# If something goes wrong, restore immediately
# manager.restore(server_backup_id)
# manager.restore(params_backup_id)
```

### Automated Backup Before Git Operations

```python
import subprocess
from loom.backup_manager import get_backup_manager

def safe_git_commit(files_to_backup, commit_message):
    """Safely commit with automatic backups."""
    manager = get_backup_manager()
    
    # Backup all files
    backups = {}
    for filepath in files_to_backup:
        backup_id = manager.backup(filepath)
        backups[filepath] = backup_id
        print(f"Backed up {filepath}: {backup_id}")
    
    try:
        # Perform git operation
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("✓ Commit successful")
    except subprocess.CalledProcessError as e:
        print(f"✗ Commit failed: {e}")
        print("Restoring from backups...")
        for filepath, backup_id in backups.items():
            manager.restore(backup_id)
        raise

safe_git_commit(
    ["src/loom/server.py", "src/loom/params.py"],
    "feat: integrate backup system"
)
```

### Manual Rollback Procedure

If a change causes issues:

```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()

# List recent backups
backups = manager.list_backups("/path/to/file.txt")
print("Recent backups:")
for backup in backups[:5]:
    print(f"  {backup.backup_id} - {backup.created_at} ({backup.file_size} bytes)")

# Restore the most recent known-good backup
if backups:
    manager.restore(backups[0].backup_id)
    print(f"✓ Restored {backups[0].backup_id}")
```

## Rotation Policy

- **Max Backups Per File**: 100 (configurable)
- **Rotation Strategy**: Oldest-first eviction when limit exceeded
- **Default Retention**: 30 days (configurable)
- **Cleanup Trigger**: Automatic on `cleanup()` call or after rotation

## Integrity Verification

Each backup includes:

1. **File Hash (SHA-256)**: Computed at creation time and verified on restore
2. **File Size**: Tracks changes in file length
3. **Timestamp**: ISO 8601 format for audit trail
4. **Original Path**: Enables restore to original location

If hash verification fails during restore, the operation is rejected with an error.

## Security Considerations

1. **Backup Directory Permissions**:
   ```bash
   chmod 700 ~/.loom/backups      # Owner read/write/execute only
   chmod 600 ~/.loom/backups/**/*  # Owner read/write only
   ```

2. **Metadata Privacy**:
   - Metadata files use MD5 hash of original path (not reversible)
   - Backup file names include timestamps but not sensitive content

3. **No Encryption by Default**:
   - Backups are plain copies of original files
   - For sensitive files, use file-level encryption (e.g., `gpg`, `age`)

4. **Pre-Restore Backups**:
   - Automatically creates `pre-restore_{timestamp}_{filename}` backups
   - Enables undo of restore operations
   - Identified with `"pre-restore_"` prefix in backup names

## Testing

### Unit Tests

```bash
# Run all backup manager tests
pytest tests/test_backup_manager.py -v

# Run specific test class
pytest tests/test_backup_manager.py::TestBackupManagerBasics -v

# Run with coverage
pytest tests/test_backup_manager.py --cov=src/loom/backup_manager
```

### Integration Example

```python
import tempfile
from pathlib import Path
from loom.backup_manager import BackupManager

# Create temp directories
with tempfile.TemporaryDirectory() as backup_dir:
    with tempfile.TemporaryDirectory() as source_dir:
        # Initialize manager
        manager = BackupManager(backup_dir=backup_dir)
        
        # Create test file
        test_file = Path(source_dir) / "test.txt"
        test_file.write_text("original content")
        
        # Test backup/restore cycle
        backup_id = manager.backup(str(test_file))
        test_file.write_text("modified content")
        manager.restore(backup_id)
        
        assert test_file.read_text() == "original content"
        print("✓ Integration test passed")
```

## Troubleshooting

### Backup Creation Fails

**Issue**: `FileNotFoundError: File not found: /path/to/file`

**Solution**: Verify the file exists:
```bash
ls -la /path/to/file
```

### Restore Fails with Hash Mismatch

**Issue**: Backup file is corrupted or disk issue

**Solution**:
1. Check disk space
2. Verify file permissions
3. Try restore to different location:
   ```python
   manager.restore(backup_id, "/tmp/restored_file.txt")
   ```
4. If successful, manually copy to original location

### Too Many Backups

**Issue**: Rotation policy not working as expected

**Solution**: Manual cleanup:
```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()
deleted = manager.cleanup(days=7)  # Keep only 7-day old backups
print(f"Deleted {deleted} old backups")
```

### Metadata Corruption

**Issue**: JSON parsing errors in metadata

**Solution**: Reset metadata and rebuild from existing backups:
```bash
# Backup important backups to external location
cp -r ~/.loom/backups/* /secure/location/

# Remove corrupted metadata
rm ~/.loom/backups/.metadata/*.json

# Backups are still intact, can restore manually using backup_id
```

## Performance Characteristics

- **Backup Creation**: O(file_size) disk I/O + O(1) metadata update
- **Restore**: O(file_size) disk I/O + hash verification
- **Listing**: O(num_backups * log(num_backups)) for sorting
- **Cleanup**: O(num_backups) metadata scans + O(deleted_count) disk operations

Typical performance:
- 100 MB file backup: ~500ms
- Restore: ~500ms + hash verification (100+ MB/sec)
- List 100 backups: <100ms
- Cleanup 10 old backups: ~200ms

## Configuration

### Default Settings

```python
BackupManager(
    backup_dir="~/.loom/backups",
    max_backups_per_file=100,
    retention_days=30,
)
```

### Customize on Startup

```python
from loom.backup_manager import get_backup_manager

# Create custom instance
manager = get_backup_manager(
    backup_dir="/custom/backup/path",
    max_backups_per_file=50,        # Keep only 50 per file
    retention_days=7,               # 7-day retention
)
```

## Version History

### v1.0 (2024-05-04)

- Initial release
- Atomic backup creation with metadata
- Restore with integrity verification
- Automatic rotation policy
- Thread-safe operations
- MCP tool exposure
- Comprehensive test suite (80%+ coverage)
