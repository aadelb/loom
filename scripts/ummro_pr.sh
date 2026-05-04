#!/bin/bash
# Automated UMMRO PR workflow
# Usage: ./scripts/ummro_pr.sh "description of changes" [file1] [file2] ...
# Example: ./scripts/ummro_pr.sh "Add compliance check tool" src/loom/tools/compliance.py
#
# Workflow:
# 1. Creates a new branch in the UMMRO repo
# 2. Copies specified files
# 3. Saves PR metadata record in loom/ummro_prs/
# 4. User commits, pushes, and creates PR manually

set -e

DESCRIPTION="${1:-}"
shift || true
FILES=("$@")

UMMRO_DIR="${HOME}/projects/ummro"
LOOM_UMMRO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/ummro_prs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BRANCH_DATE=$(date +%Y%m%d)
BRANCH_TIME=$(date +%H%M%S)

# Validation
if [ -z "$DESCRIPTION" ]; then
    echo "ERROR: Description required"
    echo "Usage: $0 'description of changes' [file1] [file2] ..."
    exit 1
fi

if [ ! -d "$UMMRO_DIR" ]; then
    echo "ERROR: UMMRO repo not found at $UMMRO_DIR"
    echo "Expected: ${UMMRO_DIR}"
    exit 1
fi

# Create directories
mkdir -p "$LOOM_UMMRO_DIR"

# Sanitize branch name
BRANCH_NAME=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | cut -c1-40)
BRANCH="loom/${BRANCH_DATE}-${BRANCH_NAME}"

echo "====== UMMRO PR Workflow ======"
echo "Timestamp: $TIMESTAMP"
echo "Description: $DESCRIPTION"
echo "Branch: $BRANCH"
echo "Files: ${#FILES[@]} file(s)"
[ "${#FILES[@]}" -gt 0 ] && echo "  - ${FILES[*]}"
echo ""

# Switch to UMMRO repo
echo "[1/5] Switching to UMMRO repo..."
cd "$UMMRO_DIR"
git checkout main > /dev/null 2>&1 || git checkout master > /dev/null 2>&1
git pull --quiet
echo "✓ UMMRO repo updated"

# Create branch
echo "[2/5] Creating branch: $BRANCH"
git checkout -b "$BRANCH" > /dev/null 2>&1
echo "✓ Branch created"

# Copy files if specified
if [ "${#FILES[@]}" -gt 0 ]; then
    echo "[3/5] Copying files..."
    for f in "${FILES[@]}"; do
        if [ -f "$f" ]; then
            cp "$f" "$UMMRO_DIR/"
            echo "  ✓ Copied: $(basename "$f")"
        else
            echo "  ⚠ File not found: $f (skipping)"
        fi
    done
fi

# Create PR metadata file
PR_FILE="$LOOM_UMMRO_DIR/${TIMESTAMP}_pr.md"
cat > "$PR_FILE" << 'EOF'
# UMMRO PR Record

EOF

cat >> "$PR_FILE" << EOF
- **Description**: $DESCRIPTION
- **Created**: $TIMESTAMP
- **Branch**: $BRANCH
- **Files Copied**: ${#FILES[@]}
EOF

if [ "${#FILES[@]}" -gt 0 ]; then
    cat >> "$PR_FILE" << EOF

## Files
\`\`\`
$(printf '%s\n' "${FILES[@]}")
\`\`\`
EOF
fi

cat >> "$PR_FILE" << 'EOF'

## Status
- [ ] Files staged (git add)
- [ ] Changes committed (git commit)
- [ ] Branch pushed (git push -u origin BRANCH_NAME)
- [ ] PR created (gh pr create)

## Next Steps
1. Review changes in UMMRO working directory
2. Stage files: `git add .`
3. Commit: `git commit -m "desc"`
4. Push: `git push -u origin $BRANCH`
5. Create PR: `gh pr create --title "PR title" --body "details"`
6. Update this file status once PR is created

EOF

echo "[4/5] Saving PR metadata..."
echo "✓ Saved: $PR_FILE"

# Summary
echo "[5/5] Workflow complete"
echo ""
echo "====== Summary ======"
echo "UMMRO working directory: $UMMRO_DIR"
echo "Current branch: $BRANCH"
echo "PR record saved: $PR_FILE"
echo ""
echo "Next steps:"
echo "  1. cd $UMMRO_DIR"
echo "  2. Review changes: git diff main"
echo "  3. Stage files: git add ."
echo "  4. Commit: git commit -m '$DESCRIPTION'"
echo "  5. Push: git push -u origin $BRANCH"
echo "  6. Create PR: gh pr create"
echo "  7. Update PR record: $PR_FILE"
