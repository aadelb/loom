#!/bin/bash
# Install browser binaries for Loom
# Usage: ./scripts/install-browsers.sh

set -e

echo "Installing Playwright browsers (Chromium, Firefox)..."
python -m playwright install chromium firefox

echo "Fetching Camoufox Firefox distribution for stealth browsing..."
python -m camoufox fetch

echo "✅ Browser installation complete!"
