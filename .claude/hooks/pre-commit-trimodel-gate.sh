#!/bin/bash
# Tri-Model Gate — enforces Implementer ≠ Reviewer ≠ Tester before commit
# This hook checks that the commit message documents all 3 stages.
#
# Required in commit message (any format):
#   Impl: <model>
#   Review: <model>  (must differ from Impl)
#   Test: <model>    (must differ from both)
#
# Skip with: SKIP_TRIMODEL=1 git commit (for documentation-only commits)

set -euo pipefail

# Allow skipping for docs/config commits
if [[ "${SKIP_TRIMODEL:-0}" == "1" ]]; then
    exit 0
fi

# Read the commit message
COMMIT_MSG_FILE="$1"
if [[ ! -f "$COMMIT_MSG_FILE" ]]; then
    exit 0
fi

MSG=$(cat "$COMMIT_MSG_FILE")

# Skip for trivial commits (docs, chore, ci)
if echo "$MSG" | head -1 | grep -qiE '^(docs|chore|ci|style)\('; then
    exit 0
fi

# Check for tri-model markers
IMPL=$(echo "$MSG" | grep -ioP '(?<=Impl:\s?)\w+' | head -1)
REVIEW=$(echo "$MSG" | grep -ioP '(?<=Review:\s?)\w+' | head -1)
TEST=$(echo "$MSG" | grep -ioP '(?<=Test:\s?)\w+' | head -1)

if [[ -z "$IMPL" || -z "$REVIEW" || -z "$TEST" ]]; then
    echo ""
    echo "⛔ TRI-MODEL GATE: Commit blocked!"
    echo ""
    echo "   Every code commit must document 3 distinct AI models:"
    echo "   Impl: <model>    — who wrote the code"
    echo "   Review: <model>  — who reviewed (different from Impl)"
    echo "   Test: <model>    — who tested (different from both)"
    echo ""
    echo "   Add to commit message, e.g.:"
    echo "   Impl: kimi | Review: deepseek | Test: gemini"
    echo ""
    echo "   Skip for docs: SKIP_TRIMODEL=1 git commit ..."
    echo ""
    exit 1
fi

# Verify all 3 are different
if [[ "$IMPL" == "$REVIEW" || "$IMPL" == "$TEST" || "$REVIEW" == "$TEST" ]]; then
    echo ""
    echo "⛔ TRI-MODEL GATE: Models must be DIFFERENT!"
    echo "   Impl=$IMPL, Review=$REVIEW, Test=$TEST"
    echo "   Rule: Implementer ≠ Reviewer ≠ Tester"
    echo ""
    exit 1
fi

echo "✓ Tri-model gate passed: Impl=$IMPL, Review=$REVIEW, Test=$TEST"
exit 0
