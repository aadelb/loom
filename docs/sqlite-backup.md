# SQLite Backup & WAL Checkpoint Guide

## Overview

This guide covers automated SQLite backup and Write-Ahead Logging (WAL) checkpoint management for the Loom research platform. The backup system ensures database consistency, manages WAL files, and maintains automated 30-day retention policies.

## Components

### 1. `scripts/sqlite_backup.sh`

Main backup script that performs:
- **WAL checkpointing** — Truncates Write-Ahead Log (WAL) files to reclaim disk space
- **Atomic backup** — Creates consistent hot copies using SQLite `.backup` command
- **Integrity verification** — Validates backup integrity using `PRAGMA integrity_check`
- **Retention management** — Automatically removes backups older than 30 days
- **Log rotation** — Rotates backup logs exceeding 10MB
- **Error tracking** — Detailed error reporting and statistics

### 2. `scripts/install_backup_cron.sh`

Installation script that:
- Makes `sqlite_backup.sh` executable
- Creates log directories with appropriate permissions
- Installs cron job for daily 3:00 AM execution
- Verifies cron installation
- Provides rollback capability

## Installation

### Prerequisites

- SQLite 3.8+ (for WAL support)
- Bash 4.0+
- `crontab` access (for automatic scheduling)
- Write permissions to `/opt/research-toolbox` and `/var/log/loom`

### Quick Start

```bash
# Navigate to Loom root
cd /Users/aadel/projects/loom

# Make installer executable
chmod +x scripts/install_backup_cron.sh

# Run installer
scripts/install_backup_cron.sh
```

The installer will:
1. Verify `sqlite_backup.sh` exists
2. Create `/var/log/loom/` with appropriate permissions
3. Prompt for confirmation
4. Install daily 3:00 AM backup job
5. Display verification output

### Manual Installation (No Cron)

If automated cron setup is not available:

```bash
# Make script executable
chmod +x scripts/sqlite_backup.sh

# Run backup manually
scripts/sqlite_backup.sh

# Check logs
tail -f /var/log/loom/backup.log
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOOM_DB_DIR` | `/opt/research-toolbox` | Root directory containing SQLite databases |
| `BACKUP_RETENTION_DAYS` | `30` | Days to retain backups before deletion |
| `LOG_DIR` | `/var/log/loom` | Log file output directory |

### Example Configuration

```bash
# Set custom database directory
export LOOM_DB_DIR="/opt/research-toolbox/data"

# Set 90-day retention instead of 30
export BACKUP_RETENTION_DAYS=90

# Run backup with custom settings
/Users/aadel/projects/loom/scripts/sqlite_backup.sh
```

### Cron Schedule Customization

To modify the backup schedule, edit the crontab:

```bash
crontab -e
```

Current schedule: `0 3 * * * /opt/research-toolbox/scripts/sqlite_backup.sh >> /var/log/loom/backup.log 2>&1`

**Common schedule patterns:**

| Schedule | Frequency |
|----------|-----------|
| `0 3 * * *` | Daily at 3:00 AM (default) |
| `0 */6 * * *` | Every 6 hours |
| `0 0 * * 0` | Weekly on Sunday at midnight |
| `0 0 1 * *` | Monthly on the 1st at midnight |

## How It Works

### WAL Checkpointing

SQLite uses Write-Ahead Logging (WAL) for concurrent access and crash recovery:

```
Normal database operation:
[Database] ← [WAL file] ← [Transactions]

After checkpoint:
[Database] ← (WAL truncated) ← [Transactions]
```

**Benefits of checkpointing:**
- Reduces WAL file disk usage (can grow unbounded)
- Improves read performance (consolidates changes)
- Enables WAL recycling
- Maintains crash recovery capability

**The checkpoint modes:**
- `PASSIVE` — Checkpoint if possible, don't block writes
- `RESTART` — Like PASSIVE, reset the WAL
- `RESET` — Like RESTART, but fail if reader connection exists
- `TRUNCATE` — Like RESET, truncate WAL file to zero (used here)

### Backup Strategy

The script uses SQLite's native `.backup` command:

```sql
.backup '/path/to/backup/database.db'
```

**Why `.backup` is superior to file copy:**

| Method | Atomicity | Consistency | Concurrency | Speed |
|--------|-----------|-------------|-------------|-------|
| `.backup` | ✓ Atomic | ✓ Consistent | ✓ Non-blocking | Good |
| `cp` | ✗ Multi-step | ✗ May capture partial writes | ✗ Blocks readers | Fast |
| `rsync` | ✗ Multi-step | ✗ May be inconsistent | ✗ Concurrent issues | Slower |

### Integrity Verification

After backup, the script validates:

```sql
PRAGMA integrity_check;
```

Returns:
- `ok` — Database is valid
- Error message — Corruption detected

This catches backup corruption before it becomes a disaster.

### Retention Management

Automatic cleanup of old backups:

```bash
# Find directories older than 30 days
find /opt/research-toolbox/backups -type d -mtime +30

# Delete them
rm -rf <old_directory>
```

This prevents unbounded disk growth while maintaining sufficient history for recovery scenarios.

## Output & Logging

### Log Format

```
[2026-05-04 03:00:15] Starting SQLite backup and WAL checkpoint...
[2026-05-04 03:00:15] DB_DIR: /opt/research-toolbox
[2026-05-04 03:00:15] BACKUP_DIR: /opt/research-toolbox/backups/2026-05-04
[2026-05-04 03:00:15] RETENTION_DAYS: 30
[2026-05-04 03:00:16] Processing: sessions.db (from: /opt/research-toolbox/data)
[2026-05-04 03:00:16]   ✓ WAL checkpoint complete: sessions.db
[2026-05-04 03:00:16]   ✓ Backup complete: sessions.db (size: 2048000 bytes)
[2026-05-04 03:00:16]   ✓ Backup integrity verified: sessions.db
[2026-05-04 03:00:17] Cleaned backups older than 30 days...
[2026-05-04 03:00:17] Removed 2 old backup directories (older than 30 days)
[2026-05-04 03:00:17] ==========================================
[2026-05-04 03:00:17] BACKUP SUMMARY
[2026-05-04 03:00:17] ==========================================
[2026-05-04 03:00:17] Databases backed up: 3
[2026-05-04 03:00:17] WAL checkpoints completed: 3
[2026-05-04 03:00:17] Errors encountered: 0
[2026-05-04 03:00:17] Backup location: /opt/research-toolbox/backups/2026-05-04
[2026-05-04 03:00:17] ==========================================
[2026-05-04 03:00:17] Backup completed successfully
```

### Log Location

- **Default:** `/var/log/loom/backup.log`
- **Rotation:** Automatic at 10MB
- **Archived:** `/var/log/loom/backup.log.YYYYMMDD-HHMMSS`

### Viewing Logs

```bash
# Real-time monitoring
tail -f /var/log/loom/backup.log

# Last 50 lines
tail -50 /var/log/loom/backup.log

# Search for errors
grep "ERROR" /var/log/loom/backup.log

# Get statistics
grep "BACKUP SUMMARY" -A 6 /var/log/loom/backup.log
```

## Monitoring & Verification

### Manual Backup Test

```bash
# Run backup immediately
/Users/aadel/projects/loom/scripts/sqlite_backup.sh

# Check result
echo "Exit code: $?"
tail -20 /var/log/loom/backup.log
```

Expected exit codes:
- `0` — Success
- `1` — Errors encountered

### Verify Backup Integrity

```bash
# Check backup files exist
ls -lh /opt/research-toolbox/backups/2026-05-04/

# Verify a specific backup
sqlite3 /opt/research-toolbox/backups/2026-05-04/sessions.db "PRAGMA integrity_check;"

# Query backup contents (read-only)
sqlite3 /opt/research-toolbox/backups/2026-05-04/sessions.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
```

### Cron Execution Verification

**macOS:**
```bash
log stream --level debug --predicate 'process == "cron"' | grep sqlite_backup
```

**Linux:**
```bash
sudo tail -f /var/log/syslog | grep CRON
# or
sudo journalctl -u cron --follow
```

### Disk Space Monitoring

```bash
# Check backup directory size
du -sh /opt/research-toolbox/backups/

# List backups by date (oldest first)
ls -ltr /opt/research-toolbox/backups/

# Find largest backups
find /opt/research-toolbox/backups -type f -exec ls -lh {} \; | sort -k5 -h | tail -10
```

## Troubleshooting

### Issue: "No SQLite database files found"

**Cause:** `LOOM_DB_DIR` does not contain `.db` files

**Solution:**
```bash
# Verify correct directory
export LOOM_DB_DIR="/correct/path"
find $LOOM_DB_DIR -name "*.db"

# Run backup with debugging
bash -x /Users/aadel/projects/loom/scripts/sqlite_backup.sh
```

### Issue: "Backup failed: Permission denied"

**Cause:** Script lacks write permissions to backup or log directory

**Solution:**
```bash
# Check permissions
ls -ld /opt/research-toolbox/backups
ls -ld /var/log/loom

# Fix permissions (run as admin)
sudo chmod 755 /opt/research-toolbox/backups
sudo chmod 755 /var/log/loom
sudo chown $USER:staff /var/log/loom/backup.log
```

### Issue: "WAL checkpoint failed"

**Cause:** Other processes holding locks on database

**Solution:**
```bash
# Check for open connections
lsof | grep -E "\.db(-|$)"

# Force checkpoint with PASSIVE mode (non-blocking)
sqlite3 /path/to/database.db "PRAGMA wal_checkpoint(PASSIVE);"

# Or restart the application holding the lock
```

### Issue: "Backup integrity check failed"

**Cause:** Corrupted backup file (rare)

**Solution:**
```bash
# Verify database is healthy
sqlite3 /opt/research-toolbox/data/database.db "PRAGMA integrity_check;"

# Try backup again
/Users/aadel/projects/loom/scripts/sqlite_backup.sh

# If issue persists, check disk space
df -h /opt/research-toolbox
```

### Issue: Cron job not executing

**Cause:** Multiple possible reasons

**Solutions:**
```bash
# Verify cron job is installed
crontab -l | grep sqlite_backup

# Check cron daemon is running
pgrep crond

# Verify script path is correct
ls -la /opt/research-toolbox/scripts/sqlite_backup.sh

# Check script has execute permission
chmod +x /opt/research-toolbox/scripts/sqlite_backup.sh

# Test script directly
/opt/research-toolbox/scripts/sqlite_backup.sh

# Check cron logs
log stream --predicate 'process == "cron"' (macOS)
sudo tail -f /var/log/cron (Linux)
```

## Recovery Procedures

### Restore from Backup

```bash
# List available backups
ls -la /opt/research-toolbox/backups/

# Stop application (to release locks)
sudo systemctl stop loom-server

# Restore database
sqlite3 /opt/research-toolbox/data/sessions.db < /opt/research-toolbox/backups/2026-05-03/sessions.db
# Note: Use .restore for atomic restore
# sqlite3 /opt/research-toolbox/data/sessions.db ".restore /opt/research-toolbox/backups/2026-05-03/sessions.db"

# Verify restoration
sqlite3 /opt/research-toolbox/data/sessions.db "PRAGMA integrity_check;"

# Restart application
sudo systemctl start loom-server
```

### Point-in-Time Recovery

```bash
# Find backup nearest to desired time
ls -la /opt/research-toolbox/backups/ | grep 2026-05-01

# Use that backup as recovery point
sqlite3 /opt/research-toolbox/data/sessions.db ".restore /opt/research-toolbox/backups/2026-05-01/sessions.db"
```

## Performance Considerations

### Backup Speed

Expected performance on typical deployment:
- **1GB database:** ~5-10 seconds
- **10GB database:** ~1-2 minutes
- **100GB database:** ~10-20 minutes

Backup speed depends on:
- Disk I/O performance
- Database size
- Concurrent connections
- CPU availability

### Disk Space Requirements

Backup storage needs:

```
Daily backups × retention days × number of databases

Example:
5 databases × 2GB each = 10GB per day
10GB × 30 days = 300GB for full 30-day retention
```

**Recommendation:** Allocate 1.5× calculated space for safety margin.

### Impact on Running System

- **WAL checkpointing:** Minimal impact (~100ms), non-blocking
- **Backup operation:** Non-blocking, does not lock database for reads/writes
- **Integrity checks:** Fast operation (<1 second for typical databases)

**Best practice:** Schedule backups during low-traffic periods (3:00 AM default).

## Best Practices

1. **Regular Testing** — Test restore procedures quarterly to ensure backups are usable
2. **Monitoring** — Set up alerts for backup failures (e.g., `grep ERROR /var/log/loom/backup.log`)
3. **Retention Policy** — Keep at least 7 days of backups for production systems
4. **Off-site Storage** — Consider copying daily backups to S3 or secondary storage
5. **Documentation** — Document any custom configurations in your deployment notes
6. **Access Control** — Limit backup directory access to authorized users/services
7. **Encryption** — Encrypt backups at rest if they contain sensitive data

## Integration with Other Tools

### Backup to Remote Storage

```bash
# Add to sqlite_backup.sh after BACKUP_DIR creation
aws s3 sync /opt/research-toolbox/backups/$(date +%Y-%m-%d) \
  s3://my-bucket/loom-backups/$(date +%Y-%m-%d)/
```

### Notification on Failure

```bash
# Add to sqlite_backup.sh error handling
if [ "$error_count" -gt 0 ]; then
    curl -X POST https://hooks.slack.com/... \
      -H 'Content-Type: application/json' \
      -d "{\"text\": \"Loom backup failed with $error_count errors\"}"
fi
```

### Monitoring Dashboard Integration

Extract backup metrics for monitoring:

```bash
# Extract summary for consumption by monitoring system
grep "BACKUP SUMMARY" -A 4 /var/log/loom/backup.log | tail -4
```

## See Also

- SQLite WAL documentation: https://www.sqlite.org/wal.html
- SQLite backup documentation: https://www.sqlite.org/backup.html
- Loom architecture guide: `/Users/aadel/projects/loom/docs/ARCHITECTURE_DESIGN.md`
- Loom deployment guide: `/Users/aadel/projects/loom/docs/DEPLOYMENT.md`
