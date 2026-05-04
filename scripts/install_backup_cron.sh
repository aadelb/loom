#!/bin/bash
# Install SQLite backup cron job
# Author: Ahmed Adel Bakr Alderai
# Purpose: Set up automated daily backups for SQLite databases

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQLITE_BACKUP_SCRIPT="$SCRIPT_DIR/sqlite_backup.sh"
BACKUP_LOG="/var/log/loom/backup.log"
BACKUP_LOG_DIR="$(dirname "$BACKUP_LOG")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}SQLite Backup Cron Installation${NC}"
echo "=================================="

# Check if script exists
if [ ! -f "$SQLITE_BACKUP_SCRIPT" ]; then
    echo -e "${RED}ERROR: sqlite_backup.sh not found at $SQLITE_BACKUP_SCRIPT${NC}"
    exit 1
fi

echo "✓ Found sqlite_backup.sh"

# Make script executable
chmod +x "$SQLITE_BACKUP_SCRIPT"
echo "✓ Made sqlite_backup.sh executable"

# Create log directory if it doesn't exist
if [ ! -d "$BACKUP_LOG_DIR" ]; then
    sudo mkdir -p "$BACKUP_LOG_DIR"
    sudo chmod 755 "$BACKUP_LOG_DIR"
fi
echo "✓ Created log directory: $BACKUP_LOG_DIR"

# Create empty log file if it doesn't exist
if [ ! -f "$BACKUP_LOG" ]; then
    sudo touch "$BACKUP_LOG"
    sudo chmod 644 "$BACKUP_LOG"
fi
echo "✓ Created log file: $BACKUP_LOG"

# Check current crontab
echo ""
echo "Current crontab entries:"
echo "========================"
crontab -l 2>/dev/null || echo "(no crontab currently installed)"

# Cron job definition
# Run daily at 3:00 AM
CRON_SCHEDULE="0 3 * * *"
CRON_COMMAND="$SQLITE_BACKUP_SCRIPT >> $BACKUP_LOG 2>&1"
CRON_JOB="$CRON_SCHEDULE $CRON_COMMAND"

echo ""
echo "New cron job to be installed:"
echo "============================="
echo "$CRON_JOB"
echo ""
echo "Schedule: Daily at 3:00 AM"
echo "Log output: $BACKUP_LOG"
echo ""

# Get user confirmation
read -p "Install this cron job? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installation cancelled${NC}"
    exit 0
fi

# Install cron job
# Use a temporary file to avoid issues with existing crontab
TEMP_CRONTAB=$(mktemp)
trap "rm -f $TEMP_CRONTAB" EXIT

# Export existing crontab to temp file (ignore error if no crontab exists)
crontab -l 2>/dev/null > "$TEMP_CRONTAB" || true

# Check if job already exists
if grep -Fxq "$CRON_JOB" "$TEMP_CRONTAB" 2>/dev/null; then
    echo -e "${YELLOW}Cron job already installed${NC}"
    exit 0
fi

# Add new job to temp file
echo "$CRON_JOB" >> "$TEMP_CRONTAB"

# Install the new crontab
crontab "$TEMP_CRONTAB"

echo -e "${GREEN}✓ Cron job installed successfully${NC}"
echo ""
echo "Verification:"
echo "============="
crontab -l | grep "sqlite_backup.sh" || echo "(job may not be visible yet)"

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "==========="
echo "1. Verify backup execution: tail -f $BACKUP_LOG"
echo "2. Test backup manually: $SQLITE_BACKUP_SCRIPT"
echo "3. Check cron logs: log stream --level debug --predicate 'process == \"cron\"' (macOS)"
echo "                    or: sudo tail -f /var/log/syslog | grep CRON (Linux)"
echo ""
