#!/usr/bin/env bash
# Loom publish pipeline. Run from the repo root.
# This script is idempotent through the "git init" and "git add" phases,
# but stops at each remote/destructive step for confirmation.

set -euo pipefail

REPO_NAME="${REPO_NAME:-loom}"
GH_USER="${GH_USER:-aadelb}"
VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
TAG="v${VERSION}"

confirm() {
    read -r -p "$1 [y/N] " reply
    [[ "$reply" == "y" || "$reply" == "Y" ]]
}

echo "=== Loom publish pipeline ==="
echo "Repo:    ${GH_USER}/${REPO_NAME}"
echo "Version: ${VERSION}"
echo "Tag:     ${TAG}"
echo

# 1. Preflight
echo "[1/7] Preflight checks"
ruff check src/loom || { echo "ruff failed"; exit 1; }
pytest tests/ -q -m "not integration and not live" || { echo "pytest failed"; exit 1; }
python3 -m build --sdist --wheel --outdir dist/ || { echo "build failed"; exit 1; }
echo "  OK"

# 2. Git init if needed
echo "[2/7] Git state"
if [ ! -d .git ]; then
    git init -b main
fi
git add -A
git status --short

# 3. Initial commit
echo "[3/7] Initial commit"
if [ -z "$(git log --oneline 2>/dev/null)" ]; then
    confirm "Create initial commit?" || exit 0
    git commit -m "feat: initial release (v${VERSION})

Loom — smart internet research MCP server.

Author: Ahmed Adel Bakr Alderai"
fi

# 4. Create GitHub repo
echo "[4/7] GitHub repo"
if ! gh repo view "${GH_USER}/${REPO_NAME}" >/dev/null 2>&1; then
    confirm "Create public GitHub repo ${GH_USER}/${REPO_NAME}?" || exit 0
    gh repo create "${GH_USER}/${REPO_NAME}" --public \
        --description "Smart internet research MCP server" \
        --source=. --remote=origin --push
else
    echo "  repo exists — skipping create"
    git remote get-url origin >/dev/null 2>&1 || git remote add origin "git@github.com:${GH_USER}/${REPO_NAME}.git"
fi

# 5. Push main
echo "[5/7] Push main"
confirm "git push -u origin main?" || exit 0
git push -u origin main

# 6. Tag + push tag
echo "[6/7] Tag ${TAG}"
if ! git rev-parse "${TAG}" >/dev/null 2>&1; then
    confirm "Create tag ${TAG}?" || exit 0
    git tag -a "${TAG}" -m "Release ${VERSION}"
    confirm "Push tag ${TAG}?" || exit 0
    git push origin "${TAG}"
fi

# 7. Verify CI + release
echo "[7/7] Verification"
echo "  GitHub Actions: gh run watch"
echo "  PyPI:           https://pypi.org/project/loom-mcp/${VERSION}/"
echo "  GHCR:           ghcr.io/${GH_USER}/${REPO_NAME}:${VERSION}"
echo
echo "Done."
