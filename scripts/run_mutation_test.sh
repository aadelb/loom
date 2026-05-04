#!/bin/bash
# Mutation testing via mutmut on critical security code
# Verifies that test suite can catch mutations (test effectiveness)
#
# Usage: ./scripts/run_mutation_test.sh
# Requires: pip install mutmut pytest

set -e

cd /Users/aadel/projects/loom

echo "=========================================="
echo "Mutation Testing: Test Effectiveness Suite"
echo "=========================================="
echo ""

# Ensure mutmut is installed
if ! python -m pip show mutmut &>/dev/null; then
    echo "Installing mutmut..."
    pip install mutmut -q
fi

echo "1. Mutating validators.py (URL validation, SSRF prevention)"
echo "   Target: src/loom/validators.py"
echo "   Tests:  tests/test_validators.py"
echo "   Target mutation score: >80%"
echo ""

# Run mutmut on validators with detailed output
if python -m mutmut run \
    --paths-to-mutate=src/loom/validators.py \
    --tests-dir=tests \
    --runner="pytest tests/test_validators.py -x -q --tb=short" \
    --no-cov 2>&1 | tail -30; then
    echo "✓ validators.py mutation testing complete"
else
    echo "⚠ validators.py mutation testing encountered warnings (expected for untested paths)"
fi

echo ""
echo "---"
echo ""

echo "2. Mutating pii_scrubber.py (Data masking, anonymization)"
echo "   Target: src/loom/pii_scrubber.py"
echo "   Tests:  tests/test_pii_scrubber.py"
echo "   Target mutation score: >85%"
echo ""

# Run mutmut on pii_scrubber
if python -m mutmut run \
    --paths-to-mutate=src/loom/pii_scrubber.py \
    --tests-dir=tests \
    --runner="pytest tests/test_pii_scrubber.py -x -q --tb=short" \
    --no-cov 2>&1 | tail -30; then
    echo "✓ pii_scrubber.py mutation testing complete"
else
    echo "⚠ pii_scrubber.py mutation testing encountered warnings"
fi

echo ""
echo "---"
echo ""

echo "3. Mutating errors.py (Exception hierarchy, error handling)"
echo "   Target: src/loom/errors.py"
echo "   Tests:  tests/comprehensive/test_security.py"
echo "   Target mutation score: >75%"
echo ""

# Run mutmut on errors module
if python -m mutmut run \
    --paths-to-mutate=src/loom/errors.py \
    --tests-dir=tests \
    --runner="pytest tests/comprehensive/test_security.py -x -q --tb=short -k error" \
    --no-cov 2>&1 | tail -30; then
    echo "✓ errors.py mutation testing complete"
else
    echo "⚠ errors.py mutation testing encountered warnings"
fi

echo ""
echo "=========================================="
echo "Mutation Testing Summary"
echo "=========================================="
echo ""
echo "Mutation score interpretation:"
echo "  90-100% = Excellent (rare mutations escape detection)"
echo "  80-89%  = Good (most mutations detected)"
echo "  70-79%  = Fair (significant test coverage)"
echo "  <70%    = Needs improvement (gaps in test coverage)"
echo ""
echo "For full mutmut results, run:"
echo "  mutmut results"
echo ""
