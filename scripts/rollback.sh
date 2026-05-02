#!/bin/bash
# Loom Rollback Script — safely revert changes
# Usage:
#   ./scripts/rollback.sh status    — show current state + last 5 commits
#   ./scripts/rollback.sh backup    — create named backup of critical files
#   ./scripts/rollback.sh revert    — revert last commit (safe, new commit)
#   ./scripts/rollback.sh restore   — restore from backup
#   ./scripts/rollback.sh deploy    — deploy current state to Hetzner
#   ./scripts/rollback.sh emergency — full emergency rollback (revert + deploy)

set -e

BACKUP_DIR=".rollback_backups"
CRITICAL_FILES="src/loom/server.py src/loom/params.py src/loom/logging_config.py src/loom/config.py"

case "${1:-status}" in
  status)
    echo "=== ROLLBACK STATUS ==="
    echo "Current commit: $(git log --oneline -1)"
    echo "Branch: $(git branch --show-current)"
    echo ""
    echo "Last 5 commits (revert targets):"
    git log --oneline -5
    echo ""
    echo "Uncommitted changes:"
    git status --short | head -10
    echo ""
    echo "Backups available:"
    ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "  None"
    echo ""
    echo "Server status:"
    ssh hetzner "systemctl is-active research-toolbox 2>/dev/null && curl -sf http://127.0.0.1:8787/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"  HEALTHY: {d[\"tool_count\"]} tools, uptime {d[\"uptime_seconds\"]}s\")' 2>/dev/null || echo '  DOWN or unreachable'"
    ;;

  backup)
    NAME="${2:-$(date +%Y%m%d_%H%M%S)}"
    mkdir -p "$BACKUP_DIR"
    tar czf "$BACKUP_DIR/backup_${NAME}.tar.gz" $CRITICAL_FILES 2>/dev/null
    echo "Backup created: $BACKUP_DIR/backup_${NAME}.tar.gz"
    echo "Files backed up:"
    tar tzf "$BACKUP_DIR/backup_${NAME}.tar.gz"
    echo ""
    echo "Current commit: $(git log --oneline -1)"
    echo "To restore: ./scripts/rollback.sh restore $NAME"
    ;;

  revert)
    echo "=== REVERTING LAST COMMIT ==="
    echo "Will revert: $(git log --oneline -1)"
    echo ""
    # Create backup first
    mkdir -p "$BACKUP_DIR"
    tar czf "$BACKUP_DIR/pre_revert_$(date +%Y%m%d_%H%M%S).tar.gz" $CRITICAL_FILES 2>/dev/null
    echo "Pre-revert backup saved."
    echo ""
    git revert HEAD --no-edit
    echo ""
    echo "Reverted. New state: $(git log --oneline -1)"
    echo "Run: ./scripts/rollback.sh deploy  — to push revert to Hetzner"
    ;;

  restore)
    NAME="${2}"
    if [ -z "$NAME" ]; then
      echo "Usage: ./scripts/rollback.sh restore <backup_name>"
      echo "Available backups:"
      ls "$BACKUP_DIR"/*.tar.gz 2>/dev/null
      exit 1
    fi
    ARCHIVE="$BACKUP_DIR/backup_${NAME}.tar.gz"
    if [ ! -f "$ARCHIVE" ]; then
      echo "Backup not found: $ARCHIVE"
      exit 1
    fi
    echo "Restoring from: $ARCHIVE"
    tar xzf "$ARCHIVE"
    echo "Restored. Verify with: python3 scripts/pre_deploy.py"
    ;;

  deploy)
    echo "=== DEPLOYING TO HETZNER ==="
    echo "Running pre-deploy check first..."
    python3 scripts/pre_deploy.py
    if [ $? -ne 0 ]; then
      echo "PRE-DEPLOY FAILED. Aborting deployment."
      exit 1
    fi
    echo ""
    echo "Deploying..."
    rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='.claude' src/ hetzner:/opt/research-toolbox/src/
    echo ""
    echo "Restarting server..."
    ssh hetzner "sudo systemctl restart research-toolbox"
    echo "Waiting 12s for startup..."
    sleep 12
    echo ""
    ssh hetzner "curl -sf http://127.0.0.1:8787/health | python3 -m json.tool" || echo "HEALTH CHECK FAILED"
    ;;

  emergency)
    echo "=== EMERGENCY ROLLBACK ==="
    echo "Step 1: Revert last commit..."
    git revert HEAD --no-edit
    echo ""
    echo "Step 2: Deploy reverted code..."
    rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='.claude' src/ hetzner:/opt/research-toolbox/src/
    ssh hetzner "sudo systemctl restart research-toolbox"
    sleep 12
    echo ""
    echo "Step 3: Verify..."
    ssh hetzner "curl -sf http://127.0.0.1:8787/health" && echo "SERVER RECOVERED" || echo "STILL BROKEN — manual intervention needed"
    ;;

  *)
    echo "Usage: ./scripts/rollback.sh {status|backup|revert|restore|deploy|emergency}"
    exit 1
    ;;
esac
