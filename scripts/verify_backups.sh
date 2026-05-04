#!/bin/bash
# Backup verification script for Loom MCP server
#
# Purpose: Verify integrity of all SQLite backups in the daily backup directory
# Usage: ./scripts/verify_backups.sh
#
# Exit codes:
#   0 - All backups verified successfully
#   1 - One or more corrupted backups detected
#   2 - Backup directory not found
#   3 - No backups to verify

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/research-toolbox/backups/$(date +%Y-%m-%d)}"
VERBOSE="${VERBOSE:-0}"
LOG_FILE="${LOG_FILE:-/tmp/backup_verification.log}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)
            echo -e "${BLUE}[INFO]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        SUCCESS)
            echo -e "${GREEN}[✓]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Verify a single database file
verify_database() {
    local db_file="$1"
    local db_name=$(basename "$db_file")

    if [[ $VERBOSE -eq 1 ]]; then
        log INFO "Verifying: $db_name"
    fi

    # Check if sqlite3 is available
    if ! command -v sqlite3 &> /dev/null; then
        log WARN "sqlite3 not found, skipping verification of $db_name"
        return 2
    fi

    # Run pragma integrity_check
    if output=$(sqlite3 "$db_file" "PRAGMA integrity_check;" 2>&1); then
        if echo "$output" | grep -q "^ok$"; then
            log SUCCESS "$db_name"
            return 0
        else
            log ERROR "$db_name CORRUPTED: $output"
            return 1
        fi
    else
        log ERROR "$db_name FAILED to verify: $output"
        return 1
    fi
}

# Verify all databases in backup directory
verify_all_backups() {
    local total=0
    local errors=0
    local skipped=0

    log INFO "Backup verification started"
    log INFO "Backup directory: $BACKUP_DIR"

    # Check if backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log ERROR "Backup directory not found: $BACKUP_DIR"
        return 2
    fi

    # Find all .db files
    local db_count=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.db" 2>/dev/null | wc -l)

    if [[ $db_count -eq 0 ]]; then
        log WARN "No database backups found in: $BACKUP_DIR"
        return 3
    fi

    log INFO "Found $db_count database file(s) to verify"

    # Verify each database
    while IFS= read -r db_file; do
        if verify_database "$db_file"; then
            :
        else
            local result=$?
            if [[ $result -eq 2 ]]; then
                ((skipped++))
            else
                ((errors++))
            fi
        fi
        ((total++))
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.db" 2>/dev/null | sort)

    # Generate summary report
    log INFO "========================================="
    log INFO "Backup Verification Summary"
    log INFO "========================================="
    log INFO "Total databases verified: $total"

    if [[ $errors -gt 0 ]]; then
        log ERROR "Corrupted databases: $errors"
    else
        log SUCCESS "All databases passed integrity check"
    fi

    if [[ $skipped -gt 0 ]]; then
        log WARN "Skipped (sqlite3 unavailable): $skipped"
    fi

    # Calculate additional statistics
    if [[ $db_count -gt 0 ]]; then
        local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | awk '{print $1}')
        log INFO "Total backup size: $total_size"

        local oldest_file=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.db" -printf '%T@ %p\n' 2>/dev/null | sort -n | head -1 | awk '{print $2}')
        if [[ -n "$oldest_file" ]]; then
            local oldest_date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$oldest_file" 2>/dev/null || stat -c "%y" "$oldest_file" 2>/dev/null)
            log INFO "Oldest backup: $oldest_date"
        fi

        local newest_file=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.db" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | awk '{print $2}')
        if [[ -n "$newest_file" ]]; then
            local newest_date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$newest_file" 2>/dev/null || stat -c "%y" "$newest_file" 2>/dev/null)
            log INFO "Newest backup: $newest_date"
        fi
    fi

    log INFO "========================================="
    log INFO "Log file: $LOG_FILE"

    # Return appropriate exit code
    if [[ $errors -gt 0 ]]; then
        return 1
    fi
    return 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -d|--directory)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            -h|--help)
                print_help
                exit 0
                ;;
            *)
                log ERROR "Unknown argument: $1"
                print_help
                exit 1
                ;;
        esac
    done
}

# Print help message
print_help() {
    cat << EOF
Backup Verification Script

Usage: $0 [OPTIONS]

Options:
    -d, --directory DIR   Specify backup directory (default: /opt/research-toolbox/backups/YYYY-MM-DD)
    -v, --verbose        Enable verbose output
    -l, --log FILE       Specify log file location (default: /tmp/backup_verification.log)
    -h, --help           Display this help message

Environment Variables:
    BACKUP_DIR           Override default backup directory
    VERBOSE              Set to 1 for verbose output
    LOG_FILE             Override default log file location

Examples:
    # Verify default backup directory
    $0

    # Verify specific backup directory with verbose output
    $0 -d /path/to/backups -v

    # Verify and log to custom file
    $0 -l /var/log/backup_check.log

Exit Codes:
    0 - All backups verified successfully
    1 - One or more corrupted backups detected
    2 - Backup directory not found
    3 - No backups to verify
EOF
}

# Main execution
main() {
    # Initialize log file
    : > "$LOG_FILE"

    # Parse arguments
    parse_args "$@"

    # Run verification
    verify_all_backups
    local exit_code=$?

    # Print exit code summary
    case $exit_code in
        0)
            log SUCCESS "Verification completed successfully"
            ;;
        1)
            log ERROR "Verification failed: Corrupted backups detected"
            ;;
        2)
            log ERROR "Verification failed: Backup directory not found"
            ;;
        3)
            log WARN "Verification inconclusive: No backups found"
            ;;
    esac

    exit $exit_code
}

# Execute main function
main "$@"
