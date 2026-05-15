#!/usr/bin/env bash
# Tri-model review gate — blocks git commit if review marker is missing
# Creates marker via: touch .tri-model-reviewed
# Marker is auto-deleted after successful commit

MARKER="/Users/aadel/projects/loom/.tri-model-reviewed"
CHANGED=$(cd /Users/aadel/projects/loom && git diff --name-only 2>/dev/null | wc -l | tr -d ' ')

# No changes = no review needed
if [ "$CHANGED" -eq 0 ]; then
  exit 0
fi

# Check for review marker
if [ ! -f "$MARKER" ]; then
  echo "BLOCKED: $CHANGED files changed without tri-model review."
  echo ""
  echo "Run review first:"
  echo "  1. kimi --thinking -w /Users/aadel/projects/loom -p 'review git diff for bugs, security, logic errors'"
  echo "  2. gemini -m gemini-3.1-pro-preview --approval-mode yolo 'review git diff --stat and spot issues'"
  echo "  3. touch .tri-model-reviewed"
  echo ""
  echo "Then retry your commit."
  exit 1
fi

# Marker exists — allow commit, then clean up marker
echo "Tri-model review verified. Proceeding with commit."
rm -f "$MARKER"
exit 0
