#!/usr/bin/env bash

# Load testing script for Loom MCP server
# Usage: ./run_load_test.sh [headless|ui] [--quick|--sustained|--stress]

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default parameters
MODE="${1:-headless}"
TEST_TYPE="${2:-}"
USERS=50
SPAWN_RATE=10
RUN_TIME=60
HOST="http://localhost:8787"
LOCUST_FILE="$(dirname "${BASH_SOURCE[0]}")/locustfile.py"
CONFIG_FILE="$(dirname "${BASH_SOURCE[0]}")/config.py"

# Validate Locust installation
if ! command -v locust &> /dev/null; then
    echo -e "${RED}Error: locust not found. Install with: pip install locust${NC}"
    exit 1
fi

# Check if server is running
check_server() {
    if ! curl -s -m 2 "$HOST/health" > /dev/null 2>&1; then
        echo -e "${RED}Error: Server not accessible at $HOST${NC}"
        echo -e "${YELLOW}Start server with: loom serve${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Server is running${NC}"
}

# Parse test type and adjust parameters
parse_test_type() {
    case "$TEST_TYPE" in
        --quick)
            USERS=10
            SPAWN_RATE=5
            RUN_TIME=30
            echo -e "${BLUE}Quick test: $USERS users, ${RUN_TIME}s duration${NC}"
            ;;
        --sustained)
            USERS=50
            SPAWN_RATE=10
            RUN_TIME=300
            echo -e "${BLUE}Sustained test: $USERS users, ${RUN_TIME}s duration${NC}"
            ;;
        --stress)
            USERS=200
            SPAWN_RATE=50
            RUN_TIME=120
            echo -e "${YELLOW}Stress test: $USERS users, ${RUN_TIME}s duration${NC}"
            ;;
        *)
            echo -e "${BLUE}Default test: $USERS users, ${RUN_TIME}s duration${NC}"
            ;;
    esac
}

# Run headless mode (CI-friendly)
run_headless() {
    echo -e "${BLUE}Starting headless load test...${NC}"
    locust \
        -f "$LOCUST_FILE" \
        --headless \
        -u "$USERS" \
        -r "$SPAWN_RATE" \
        --run-time "${RUN_TIME}s" \
        --host "$HOST" \
        --csv=tests/load/results \
        --csv-prefix=load_test \
        --loglevel INFO
}

# Run web UI mode (interactive)
run_ui() {
    echo -e "${BLUE}Starting Locust web UI...${NC}"
    echo -e "${YELLOW}Open browser to: http://localhost:8089${NC}"
    locust \
        -f "$LOCUST_FILE" \
        -u "$USERS" \
        -r "$SPAWN_RATE" \
        --run-time "${RUN_TIME}s" \
        --host "$HOST" \
        --csv=tests/load/results \
        --csv-prefix=load_test \
        --loglevel INFO
}

# Print test configuration
print_config() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║      LOOM LOAD TEST CONFIGURATION       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo -e "${BLUE}Mode:${NC}              $MODE"
    echo -e "${BLUE}Users:${NC}             $USERS"
    echo -e "${BLUE}Spawn Rate:${NC}        $SPAWN_RATE users/sec"
    echo -e "${BLUE}Duration:${NC}          ${RUN_TIME}s"
    echo -e "${BLUE}Server:${NC}            $HOST"
    echo -e "${BLUE}Test File:${NC}         $LOCUST_FILE"
    echo ""
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ Load test completed successfully${NC}"
    else
        echo -e "${RED}✗ Load test failed with exit code $exit_code${NC}"
    fi
    return $exit_code
}

trap cleanup EXIT

# Main execution
main() {
    check_server
    parse_test_type
    print_config

    case "$MODE" in
        headless)
            run_headless
            ;;
        ui)
            run_ui
            ;;
        *)
            echo -e "${RED}Error: Unknown mode '$MODE'${NC}"
            echo "Usage: $0 [headless|ui] [--quick|--sustained|--stress]"
            exit 1
            ;;
    esac
}

main
