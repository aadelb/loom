# Backup System Quick Start

## TL;DR - Before Making Critical Changes

```python
from loom.backup_manager import get_backup_manager

# Get the backup manager
manager = get_backup_manager()

# Backup critical file before changes
backup_id = manager.backup("/Users/aadel/projects/loom/src/loom/server.py")
print(f"Backup created: {backup_id}")

# Make your changes...

# If something breaks, restore immediately
manager.restore(backup_id)
print("✓ Restored successfully")
```

## Common Scenarios

### Scenario 1: Backup Before Code Changes

```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()

# Before modifying server.py
backup_id = manager.backup("/Users/aadel/projects/loom/src/loom/server.py")

# ... make changes ...

# Verify changes work, then you can delete the backup if happy
# Or restore if something breaks
manager.restore(backup_id)
```

### Scenario 2: Multiple File Backup (Safe Git Operation)

```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()

files = [
    "/Users/aadel/projects/loom/src/loom/server.py",
    "/Users/aadel/projects/loom/src/loom/params.py",
]

# Create backups for all files
backups = {}
for filepath in files:
    backup_id = manager.backup(filepath)
    backups[filepath] = backup_id
    print(f"✓ Backed up {filepath}: {backup_id}")

# ... make changes and test ...

# If all is good, you're done. If not, restore all:
for filepath, backup_id in backups.items():
    manager.restore(backup_id)
    print(f"✓ Restored {filepath}")
```

### Scenario 3: List Recent Backups

```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()

# List all backups for a specific file
backups = manager.list_backups("/Users/aadel/projects/loom/src/loom/server.py")

print(f"Found {len(backups)} backups:")
for i, backup in enumerate(backups[:5], 1):
    print(f"{i}. {backup.backup_id} - {backup.created_at} ({backup.file_size} bytes)")
```

### Scenario 4: Cleanup Old Backups

```python
from loom.backup_manager import get_backup_manager

manager = get_backup_manager()

# Delete backups older than 14 days
deleted = manager.cleanup(days=14)
print(f"Deleted {deleted} old backups")
```

## Using via MCP Tools (in Claude)

```python
# Create backup
result = await research_backup_create("/path/to/file.txt")
if result["success"]:
    backup_id = result["backup_id"]
    print(f"Backup created: {backup_id}")

# Restore backup
result = await research_backup_restore(backup_id)
if result["success"]:
    print("✓ Restored successfully")

# List all backups
result = await research_backup_list()
for backup in result["backups"]:
    print(f"  {backup['backup_id']} - {backup['file_path']}")

# Cleanup old backups
result = await research_backup_cleanup(days=30)
print(f"Deleted {result['deleted_count']} backups")
```

## File Structure

All backups are stored in `~/.loom/backups/`:

```
~/.loom/backups/
├── 20240504T181234_567890_server.py           # Actual backup file
├── 20240504T165432_123456_params.py           # Another backup
├── 20240503T142359_789012_audit.py            # Old backup
└── .metadata/
    ├── a1b2c3d4e5f6...json                    # Metadata for server.py backups
    └── f6e5d4c3b2a1...json                    # Metadata for params.py backups
```

## Important Notes

1. **Backup ID Format**: `YYYYMMDDTHHmmss_MICROSECONDS`
   - Example: `20240504T181234_567890`
   - Unique timestamp with microsecond precision

2. **Max Backups**: 100 per file (oldest are automatically deleted)

3. **Default Retention**: 30 days (older backups are eligible for cleanup)

4. **Verification**: SHA-256 hash verified on restore

5. **Thread-Safe**: All operations use locking for concurrent access

## Testing the System

```python
import tempfile
from pathlib import Path
from loom.backup_manager import BackupManager

# Create temp backup directory
with tempfile.TemporaryDirectory() as tmpdir:
    manager = BackupManager(backup_dir=tmpdir)
    
    # Create test file
    test_file = Path(tmpdir) / "test_source.txt"
    test_file.write_text("original content")
    
    # Test backup
    backup_id = manager.backup(str(test_file))
    print(f"✓ Backup created: {backup_id}")
    
    # Modify file
    test_file.write_text("modified content")
    
    # Restore
    success = manager.restore(backup_id)
    print(f"✓ Restore {'successful' if success else 'failed'}")
    
    # Verify
    assert test_file.read_text() == "original content"
    print("✓ Content verified")
```

## Running Tests

```bash
# Test the entire backup manager module
pytest tests/test_backup_manager.py -v

# Test specific functionality
pytest tests/test_backup_manager.py::TestBackupManagerBasics -v
pytest tests/test_backup_manager.py::TestBackupRotation -v
pytest tests/test_backup_manager.py::TestThreadSafety -v

# Run with coverage
pytest tests/test_backup_manager.py --cov=src/loom/backup_manager --cov-report=term-missing
```

## Troubleshooting

### File not found error
```python
# Make sure file exists
from pathlib import Path
assert Path("/path/to/file").exists()
manager.backup("/path/to/file")
```

### Too many backups
```python
# Clean up old ones
manager.cleanup(days=7)  # Keep only 7-day old backups
```

### Can't restore to specific location
```python
# Make sure directory exists
from pathlib import Path
restore_path = Path("/custom/location/file.txt")
restore_path.parent.mkdir(parents=True, exist_ok=True)
manager.restore(backup_id, str(restore_path))
```

## Next Steps

- Read full documentation: `docs/backup_system.md`
- View test examples: `tests/test_backup_manager.py`
- Check source code: `src/loom/backup_manager.py`
