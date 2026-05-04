#!/bin/bash
# Comprehensive test suite runner for Loom MCP server
# Runs all test files with appropriate markers and output

set -e

echo "=============================================="
echo "LOOM COMPREHENSIVE TEST SUITE"
echo "=============================================="
echo ""

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$TEST_DIR/../.." && pwd)"
RESULTS_FILE="/tmp/test_results.txt"

# Clear previous results
> "$RESULTS_FILE"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Test Directory: $TEST_DIR"
echo "Project Root: $PROJECT_ROOT"
echo "Results File: $RESULTS_FILE"
echo ""

# Change to project root for proper imports
cd "$PROJECT_ROOT"

# Run each test category
echo "Running comprehensive test suite..."
echo "=================================="
echo ""

# Smoke tests
echo -e "${YELLOW}[1/9] Running smoke tests...${NC}"
if pytest "$TEST_DIR/test_smoke.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Smoke tests passed${NC}"
else
    echo -e "${RED}✗ Smoke tests failed${NC}"
fi
echo ""

# Unit tests
echo -e "${YELLOW}[2/9] Running unit tests...${NC}"
if pytest "$TEST_DIR/test_unit_tools.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
fi
echo ""

# Integration tests
echo -e "${YELLOW}[3/9] Running integration tests...${NC}"
if pytest "$TEST_DIR/test_integration_pipeline.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
fi
echo ""

# Functional tests
echo -e "${YELLOW}[4/9] Running functional tests...${NC}"
if pytest "$TEST_DIR/test_functional.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Functional tests passed${NC}"
else
    echo -e "${RED}✗ Functional tests failed${NC}"
fi
echo ""

# Security tests
echo -e "${YELLOW}[5/9] Running security tests...${NC}"
if pytest "$TEST_DIR/test_security.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Security tests passed${NC}"
else
    echo -e "${RED}✗ Security tests failed${NC}"
fi
echo ""

# Performance tests
echo -e "${YELLOW}[6/9] Running performance tests...${NC}"
if pytest "$TEST_DIR/test_performance.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Performance tests passed${NC}"
else
    echo -e "${RED}✗ Performance tests failed${NC}"
fi
echo ""

# Load tests
echo -e "${YELLOW}[7/9] Running load tests...${NC}"
if pytest "$TEST_DIR/test_load.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Load tests passed${NC}"
else
    echo -e "${RED}✗ Load tests failed${NC}"
fi
echo ""

# API key tests
echo -e "${YELLOW}[8/9] Running API key validation tests...${NC}"
if pytest "$TEST_DIR/test_api_keys.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ API key tests passed${NC}"
else
    echo -e "${RED}✗ API key tests failed${NC}"
fi
echo ""

# Regression tests
echo -e "${YELLOW}[9/9] Running regression tests...${NC}"
if pytest "$TEST_DIR/test_regression.py" -v --timeout=300 --tb=short -q 2>&1 | tee -a "$RESULTS_FILE"; then
    echo -e "${GREEN}✓ Regression tests passed${NC}"
else
    echo -e "${RED}✗ Regression tests failed${NC}"
fi
echo ""

# Summary
echo "=============================================="
echo "TEST SUITE COMPLETE"
echo "=============================================="
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""

# Print summary from results file
echo "Test Summary:"
echo "============"
tail -20 "$RESULTS_FILE"

echo ""
echo "To view full results: cat $RESULTS_FILE"
echo ""
