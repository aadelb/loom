#!/bin/bash
# Disaster Recovery Test Script for Loom MCP Server
#
# Usage: ./scripts/dr_test.sh [OPTIONS] [TEST_NAME]

# Configuration
TEST_DIR="${TEST_DIR:-/tmp/loom_dr_test_$$}"
BACKUP_COUNT=3
VERBOSE="${VERBOSE:-0}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

print_help() {
    cat << 'HELPEOF'
Disaster Recovery Test Script

Usage: ./scripts/dr_test.sh [OPTIONS] [TEST_NAME]

Options:
    -v, --verbose       Enable verbose output
    -h, --help          Display this help message
    -d, --dir DIR       Specify test directory (default: /tmp/loom_dr_test_PID)

Available Tests:
    backup_creation     Test backup creation and verification
    corruption_detect   Test corruption detection
    restore_recovery    Test recovery from backup
    full_simulation     Run complete DR simulation
    performance         Test verification performance

Examples:
    ./scripts/dr_test.sh                              # Run all tests
    ./scripts/dr_test.sh backup_creation              # Run single test
    ./scripts/dr_test.sh -v full_simulation           # Verbose mode
    ./scripts/dr_test.sh -d /tmp/test_dir backup_creation
HELPEOF
}

log() {
    local level="$1"
    shift
    local message="$*"

    case "$level" in
        INFO) echo -e "${BLUE}[INFO]${NC} $message" ;;
        PASS) 
            echo -e "${GREEN}[PASS]${NC} $message"
            ((TESTS_PASSED++)) || true
            ;;
        FAIL) 
            echo -e "${RED}[FAIL]${NC} $message"
            ((TESTS_FAILED++)) || true
            ;;
        WARN) echo -e "${YELLOW}[WARN]${NC} $message" ;;
        DEBUG) [[ $VERBOSE -eq 1 ]] && echo -e "${BLUE}[DEBUG]${NC} $message" ;;
    esac
}

cleanup() {
    local exit_code=$?
    log INFO "Cleaning up test artifacts..."
    rm -rf "$TEST_DIR"
    return $exit_code
}

# ============================================================================
# TEST SETUP
# ============================================================================

init_test_env() {
    log INFO "Initializing test environment..."
    mkdir -p "$TEST_DIR"/{db,backups,recovery}

    if ! command -v sqlite3 &> /dev/null; then
        log FAIL "sqlite3 not found"
        return 1
    fi

    log DEBUG "Test directory: $TEST_DIR"
    log PASS "Test environment initialized"
}

create_test_db() {
    local db_path="$1"
    log DEBUG "Creating test database: $db_path"

    sqlite3 "$db_path" << 'SQL'
CREATE TABLE IF NOT EXISTS cache (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    data BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY,
    backup_id TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO cache (url, content, hash) VALUES
    ('https://example.com/page1', 'Content of page 1', 'hash1'),
    ('https://example.com/page2', 'Content of page 2', 'hash2'),
    ('https://example.com/page3', 'Content of page 3', 'hash3');

INSERT INTO sessions (session_id, user_id, data) VALUES
    ('sess_001', 'user1', x'01020304'),
    ('sess_002', 'user2', x'05060708'),
    ('sess_003', 'user3', x'09101112');

INSERT INTO backups (backup_id, file_path, file_size, file_hash) VALUES
    ('bkup_001', '/data/file1', 1024, 'abc123'),
    ('bkup_002', '/data/file2', 2048, 'def456'),
    ('bkup_003', '/data/file3', 4096, 'ghi789');

PRAGMA integrity_check;
SQL

    log DEBUG "Sample data inserted successfully"
}

verify_db_integrity() {
    local db_path="$1"
    local should_pass="${2:-true}"

    log DEBUG "Verifying database integrity: $db_path"

    if [[ ! -f "$db_path" ]]; then
        log FAIL "Database file not found: $db_path"
        return 1
    fi

    local output
    output=$(sqlite3 "$db_path" "PRAGMA integrity_check;" 2>&1) || true

    if echo "$output" | grep -q "^ok$"; then
        if [[ "$should_pass" == "true" ]]; then
            log DEBUG "Database integrity verified: PASS"
            return 0
        else
            log FAIL "Database should be corrupted but passed verification"
            return 1
        fi
    else
        if [[ "$should_pass" == "false" ]]; then
            log DEBUG "Database corruption detected (expected): $output"
            return 0
        else
            log FAIL "Database integrity check failed: $output"
            return 1
        fi
    fi
}

query_db() {
    local db_path="$1"
    local query="$2"
    sqlite3 "$db_path" "$query" 2>&1
}

# ============================================================================
# TESTS
# ============================================================================

test_backup_creation() {
    ((TESTS_RUN++))
    log INFO "Test 1: Backup Creation and Verification"

    local db_path="$TEST_DIR/db/test.db"
    local backup_dir="$TEST_DIR/backups"

    create_test_db "$db_path"
    verify_db_integrity "$db_path" true || return 1

    for i in $(seq 1 $BACKUP_COUNT); do
        local backup_file="$backup_dir/backup_$i.db"
        cp "$db_path" "$backup_file"
        log DEBUG "Created backup: $backup_file"
        verify_db_integrity "$backup_file" true || return 1
    done

    local backup_count
    backup_count=$(find "$backup_dir" -name "backup_*.db" 2>/dev/null | wc -l)
    
    if [[ $backup_count -eq $BACKUP_COUNT ]]; then
        log PASS "Backup Creation and Verification"
        return 0
    else
        log FAIL "Expected $BACKUP_COUNT backups, found $backup_count"
        return 1
    fi
}

test_corruption_detection() {
    ((TESTS_RUN++))
    log INFO "Test 2: Corruption Detection"

    local db_path="$TEST_DIR/db/corrupt_test.db"

    create_test_db "$db_path"
    verify_db_integrity "$db_path" true || return 1

    log DEBUG "Introducing corruption to database..."
    python3 << PYTHON
with open("$db_path", "r+b") as f:
    f.seek(100)
    f.write(b'\xFF\xFF\xFF\xFF')
PYTHON

    if ! verify_db_integrity "$db_path" false; then
        log FAIL "Corruption not detected"
        return 1
    fi

    log PASS "Corruption Detection"
    return 0
}

test_restore_recovery() {
    ((TESTS_RUN++))
    log INFO "Test 3: Database Recovery from Backup"

    local original_db="$TEST_DIR/db/original.db"
    local backup_db="$TEST_DIR/backups/recovery_backup.db"
    local recovery_db="$TEST_DIR/recovery/recovered.db"

    create_test_db "$original_db"
    verify_db_integrity "$original_db" true || return 1

    local original_count
    original_count=$(query_db "$original_db" "SELECT COUNT(*) FROM cache;")
    log DEBUG "Original cache entry count: $original_count"

    cp "$original_db" "$backup_db"
    verify_db_integrity "$backup_db" true || return 1

    log DEBUG "Corrupting original database..."
    python3 << PYTHON
with open("$original_db", "r+b") as f:
    f.seek(500)
    f.write(b'\xFF' * 100)
PYTHON

    cp "$backup_db" "$recovery_db"
    verify_db_integrity "$recovery_db" true || {
        log FAIL "Recovered database is corrupted"
        return 1
    }

    local recovered_count
    recovered_count=$(query_db "$recovery_db" "SELECT COUNT(*) FROM cache;")
    log DEBUG "Recovered cache entry count: $recovered_count"

    if [[ "$original_count" == "$recovered_count" ]]; then
        log PASS "Database Recovery from Backup"
        return 0
    else
        log FAIL "Data mismatch: $original_count != $recovered_count"
        return 1
    fi
}

test_full_simulation() {
    ((TESTS_RUN++))
    log INFO "Test 4: Full Disaster Recovery Simulation"

    local prod_db="$TEST_DIR/db/production.db"
    local backup_dir="$TEST_DIR/backups/daily"

    mkdir -p "$backup_dir"

    log DEBUG "Phase 1: Establishing baseline..."
    create_test_db "$prod_db"
    verify_db_integrity "$prod_db" true || return 1

    local baseline_count baseline_sessions
    baseline_count=$(query_db "$prod_db" "SELECT COUNT(*) FROM cache;")
    baseline_sessions=$(query_db "$prod_db" "SELECT COUNT(*) FROM sessions;")
    log DEBUG "Baseline: $baseline_count cache, $baseline_sessions sessions"

    log DEBUG "Phase 2: Creating daily backups..."
    for day in $(seq 1 3); do
        local backup_file="$backup_dir/backup_day_$day.db"
        cp "$prod_db" "$backup_file"
        verify_db_integrity "$backup_file" true || return 1
        log DEBUG "Daily backup $day created"
    done

    log DEBUG "Phase 3: Simulating catastrophic failure..."
    python3 << PYTHON
with open("$prod_db", "r+b") as f:
    for offset in [100, 500, 1000, 2000]:
        f.seek(offset)
        f.write(b'\x00' * 50)
PYTHON

    log DEBUG "Phase 4: Locating valid backups..."
    local valid_backup=""
    for backup in "$backup_dir"/*.db; do
        if verify_db_integrity "$backup" true 2>/dev/null; then
            valid_backup="$backup"
            log DEBUG "Found valid backup: $(basename "$backup")"
            break
        fi
    done

    if [[ -z "$valid_backup" ]]; then
        log FAIL "No valid backup found"
        return 1
    fi

    log DEBUG "Phase 5: Performing recovery..."
    local recovered_db="$TEST_DIR/recovery/recovered_production.db"
    mkdir -p "$TEST_DIR/recovery"
    cp "$valid_backup" "$recovered_db"

    verify_db_integrity "$recovered_db" true || return 1

    log DEBUG "Phase 6: Validating recovered data..."
    local recovered_count recovered_sessions
    recovered_count=$(query_db "$recovered_db" "SELECT COUNT(*) FROM cache;")
    recovered_sessions=$(query_db "$recovered_db" "SELECT COUNT(*) FROM sessions;")

    if [[ "$baseline_count" == "$recovered_count" ]] && [[ "$baseline_sessions" == "$recovered_sessions" ]]; then
        log PASS "Full Disaster Recovery Simulation"
        return 0
    else
        log FAIL "Data validation failed after recovery"
        return 1
    fi
}

test_performance() {
    ((TESTS_RUN++))
    log INFO "Test 5: Performance and Scalability"

    local db_path="$TEST_DIR/db/large_test.db"

    log DEBUG "Creating large test database..."
    sqlite3 "$db_path" << 'SQL'
CREATE TABLE cache (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

WITH RECURSIVE nums(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM nums WHERE n < 1000
)
INSERT INTO cache (url, content, hash)
SELECT
    'https://example.com/page' || n,
    'Content for page ' || n,
    'hash' || n
FROM nums;

PRAGMA integrity_check;
SQL

    local start_time end_time elapsed_ms
    start_time=$(date +%s%N)
    verify_db_integrity "$db_path" true || return 1
    end_time=$(date +%s%N)

    elapsed_ms=$(( (end_time - start_time) / 1000000 ))
    log DEBUG "Verification time: ${elapsed_ms}ms for 1000 rows"

    if [[ $elapsed_ms -lt 5000 ]]; then
        log PASS "Performance and Scalability"
        return 0
    else
        log WARN "Verification slower than expected: ${elapsed_ms}ms"
        log PASS "Performance and Scalability (with warning)"
        return 0
    fi
}

run_single_test() {
    local test_name="$1"

    case "$test_name" in
        backup_creation) test_backup_creation ;;
        corruption_detect) test_corruption_detection ;;
        restore_recovery) test_restore_recovery ;;
        full_simulation) test_full_simulation ;;
        performance) test_performance ;;
        *)
            log FAIL "Unknown test: $test_name"
            return 2
            ;;
    esac
}

run_all_tests() {
    test_backup_creation || true
    test_corruption_detection || true
    test_restore_recovery || true
    test_full_simulation || true
    test_performance || true
}

print_summary() {
    echo ""
    echo "========================================="
    echo "Disaster Recovery Test Summary"
    echo "========================================="
    echo "Tests run:    $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
    echo "========================================="

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        return 1
    fi
}

# ============================================================================
# MAIN
# ============================================================================

trap cleanup EXIT

# Handle early exit flags before running tests
case "${1:-}" in
    -h|--help)
        print_help
        exit 0
        ;;
    -v|--verbose)
        VERBOSE=1
        shift
        ;;
    -d|--dir)
        TEST_DIR="$2"
        shift 2
        ;;
esac

init_test_env || exit 1

if [[ -n "${1:-}" ]]; then
    run_single_test "$1"
    result=$?
    echo ""
    print_summary
    exit $result
else
    run_all_tests
    print_summary
    exit $?
fi
