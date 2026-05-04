#!/bin/bash
set -e

# Loom React Dashboard Launcher
# Starts the React dashboard on port 5173
# Requires Loom MCP server running on localhost:8787

DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dashboard" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Loom React Dashboard Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if server is running
echo "Checking Loom MCP server status..."
if ! curl -s http://localhost:8787/health > /dev/null 2>&1; then
    echo ""
    echo "❌ Error: Loom server is not running on localhost:8787"
    echo ""
    echo "Start it in a separate terminal with:"
    echo "  loom serve"
    echo ""
    exit 1
fi
echo "✓ Loom MCP server is running on port 8787"
echo ""

# Navigate to dashboard directory
cd "$DASHBOARD_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
    echo "✓ Dependencies installed"
    echo ""
fi

# Start development server
echo "Starting React dashboard on http://localhost:5173"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

npm run dev
