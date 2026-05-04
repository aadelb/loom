#!/bin/bash
# Daily SQLite backup + WAL checkpoint for Loom databases
# Author: Ahmed Adel Bakr Alderai
# Purpose: Safely backup all SQLite databases, checkpoint WAL files, and maintain 30-day retention

set -euo pipefail

# Configuration
BACKUP_DIR="/opt/research-toolbox/backups/$(date +%Y-%m-%d)"
DB_DIR="${LOOM_DB_DIR:-/opt/research-toolbox}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
LOG_DIR="${LOG_DIR:-/var/log/loom}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Ensure directories exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_DIR/backup.log"
}

error_exit() {
    echo "[$TIMESTAMP] ERROR: $1" | tee -a "$LOG_DIR/backup.log"
    exit 1
}

log "Starting SQLite backup and WAL checkpoint..."
log "DB_DIR: $DB_DIR"
log "BACKUP_DIR: $BACKUP_DIR"
log "RETENTION_DAYS: $RETENTION_DAYS"

# Track backup statistics
backup_count=0
checkpoint_count=0
error_count=0

# Find all .db files (excluding backups directory)
db_files=$(find "$DB_DIR" -maxdepth 2 -name "*.db" -not -path "*/backups/*" 2>/dev/null || true)

if [ -z "$db_files" ]; then
    log "WARNING: No SQLite database files found in $DB_DIR"
else
    # Process each database file
    while IFS= read -r db; do
        name=$(basename "$db")
        db_path=$(dirname "$db")

        log "Processing: $name (from: $db_path)"

        # Step 1: Checkpoint WAL file to truncate it
        # PRAGMA wal_checkpoint(TRUNCATE) returns three integers:
        # - busy: number of busy connections
        # - pagesBackedUp: number of pages written
        # - pageSize: database page size
        if sqlite3 "$db" "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null 2>&1; then
            ((checkpoint_count++))
            log "  ✓ WAL checkpoint complete: $name"
        else
            log "  ✗ WAL checkpoint failed: $name"
            ((error_count++))
        fi

        # Step 2: Backup using SQLite .backup command (atomic, safe, consistent)
        # This creates a hot copy without locking
        backup_file="$BACKUP_DIR/$name"
        if sqlite3 "$db" ".backup '$backup_file'" >/dev/null 2>&1; then
            backup_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo "unknown")
            ((backup_count++))
            log "  ✓ Backup complete: $name (size: $backup_size bytes)"
        else
            log "  ✗ Backup failed: $name"
            ((error_count++))
        fi

        # Step 3: Verify backup integrity (optional but recommended)
        if [ -f "$backup_file" ]; then
            if sqlite3 "$backup_file" "PRAGMA integrity_check;" >/dev/null 2>&1; then
                log "  ✓ Backup integrity verified: $name"
            else
                log "  ✗ Backup integrity check failed: $name (backup may be corrupted)"
                ((error_count++))
            fi
        fi
    done <<< "$db_files"
fi

# Step 4: Clean backups older than retention period
log "Cleaning backups older than $RETENTION_DAYS days..."
old_backup_count=$(find "/opt/research-toolbox/backups" -type d -mtime +$RETENTION_DAYS -not -path "/opt/research-toolbox/backups" 2>/dev/null | wc -l || echo "0")

if [ "$old_backup_count" -gt 0 ]; then
    find "/opt/research-toolbox/backups" -type d -mtime +$RETENTION_DAYS -not -path "/opt/research-toolbox/backups" -exec rm -rf {} + 2>/dev/null || true
    log "Removed $old_backup_count old backup directories (older than $RETENTION_DAYS days)"
fi

# Step 5: Rotate backup log if it exceeds 10MB
if [ -f "$LOG_DIR/backup.log" ]; then
    log_size=$(stat -f%z "$LOG_DIR/backup.log" 2>/dev/null || stat -c%s "$LOG_DIR/backup.log" 2>/dev/null || echo "0")
    if [ "$log_size" -gt 10485760 ]; then
        mv "$LOG_DIR/backup.log" "$LOG_DIR/backup.log.$(date +%Y%m%d-%H%M%S)"
        log "Log rotated (size was $log_size bytes)"
    fi
fi

# Summary
log "=========================================="
log "BACKUP SUMMARY"
log "=========================================="
log "Databases backed up: $backup_count"
log "WAL checkpoints completed: $checkpoint_count"
log "Errors encountered: $error_count"
log "Backup location: $BACKUP_DIR"
log "=========================================="

if [ "$error_count" -gt 0 ]; then
    error_exit "Backup completed with $error_count errors"
else
    log "Backup completed successfully"
    exit 0
fi
