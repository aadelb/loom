#!/bin/bash
# Qdrant Disaster Recovery — Automated Snapshot Script
# Creates snapshots of all collections via Qdrant REST API
# Run daily via cron: 0 3 * * * /opt/loom-v3/scripts/qdrant_backup.sh
#
# Author: Ahmed Adel Bakr Alderai

set -euo pipefail

QDRANT_URL="http://localhost:6333"
BACKUP_DIR="/data/backups/qdrant"
MAX_SNAPSHOTS=7  # Keep 7 days of snapshots
DATE=$(date +%Y-%m-%d_%H%M)
LOG="/var/log/qdrant_backup.log"

mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "=== Qdrant Backup Started ==="

# Get all collections
COLLECTIONS=$(curl -s "$QDRANT_URL/collections" | python3 -c "
import json, sys
d = json.load(sys.stdin)
cols = d.get('result', {}).get('collections', [])
for c in cols:
    print(c['name'])
")

TOTAL=0
FAILED=0

for COLLECTION in $COLLECTIONS; do
    log "Snapshotting: $COLLECTION"

    # Create snapshot via API
    RESULT=$(curl -s -X POST "$QDRANT_URL/collections/$COLLECTION/snapshots" 2>/dev/null)
    SNAPSHOT_NAME=$(echo "$RESULT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('result', {}).get('name', ''))
except:
    print('')
" 2>/dev/null)

    if [ -n "$SNAPSHOT_NAME" ]; then
        # Download snapshot to backup dir
        DEST="$BACKUP_DIR/${DATE}_${COLLECTION}.snapshot"
        curl -s "$QDRANT_URL/collections/$COLLECTION/snapshots/$SNAPSHOT_NAME" -o "$DEST" 2>/dev/null

        if [ -f "$DEST" ] && [ -s "$DEST" ]; then
            SIZE=$(du -h "$DEST" | cut -f1)
            log "  OK: $COLLECTION → $DEST ($SIZE)"
            TOTAL=$((TOTAL + 1))
        else
            log "  FAIL: download empty for $COLLECTION"
            FAILED=$((FAILED + 1))
            rm -f "$DEST"
        fi

        # Clean up snapshot from Qdrant storage
        curl -s -X DELETE "$QDRANT_URL/collections/$COLLECTION/snapshots/$SNAPSHOT_NAME" >/dev/null 2>&1
    else
        log "  FAIL: snapshot creation failed for $COLLECTION"
        FAILED=$((FAILED + 1))
    fi
done

# Cleanup old backups (keep MAX_SNAPSHOTS days)
find "$BACKUP_DIR" -name "*.snapshot" -mtime +$MAX_SNAPSHOTS -delete 2>/dev/null
OLD_DELETED=$(find "$BACKUP_DIR" -name "*.snapshot" -mtime +$MAX_SNAPSHOTS 2>/dev/null | wc -l)

log "=== Backup Complete: $TOTAL OK, $FAILED failed, $OLD_DELETED old removed ==="
log "Backup location: $BACKUP_DIR"
log "Total backup size: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
