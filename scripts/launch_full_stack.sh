#!/bin/bash
set -e

# Loom Full Stack Launcher
# Starts all components:
# - MCP Server (port 8787)
# - React Dashboard (port 5173)
# - Optionally: MCP Inspector (port 6274)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DASHBOARD_DIR="$PROJECT_ROOT/dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo "${YELLOW}Shutting down Loom Full Stack...${NC}"
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "  Stopping MCP server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    if [ -n "$DASHBOARD_PID" ] && kill -0 "$DASHBOARD_PID" 2>/dev/null; then
        echo "  Stopping Dashboard (PID: $DASHBOARD_PID)..."
        kill "$DASHBOARD_PID" 2>/dev/null || true
    fi
    echo "${GREEN}✓ All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "${BLUE}  Loom Full Stack Launcher${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Start MCP Server
echo "${BLUE}[1/3]${NC} Starting MCP Server on port 8787..."
loom serve &
SERVER_PID=$!
echo "  PID: $SERVER_PID"

# Step 2: Wait for server to be ready
echo ""
echo "${BLUE}[2/3]${NC} Waiting for server to be ready (max 30s)..."
READY=false
for i in {1..30}; do
    if curl -s http://localhost:8787/health > /dev/null 2>&1; then
        echo "  ${GREEN}✓${NC} Server is ready"
        READY=true
        break
    fi
    echo -n "."
    sleep 1
done

if [ "$READY" = false ]; then
    echo ""
    echo "${RED}✗ Server failed to start within 30 seconds${NC}"
    cleanup
    exit 1
fi

# Step 3: Start Dashboard
echo ""
echo "${BLUE}[3/3]${NC} Starting React Dashboard on port 5173..."

cd "$DASHBOARD_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies..."
    npm install > /dev/null 2>&1 || true
fi

npm run dev &
DASHBOARD_PID=$!
echo "  PID: $DASHBOARD_PID"

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "${GREEN}✓ Loom Full Stack is running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Access the following interfaces:"
echo ""
echo "  ${BLUE}React Dashboard:${NC}    http://localhost:5173"
echo "  ${BLUE}Swagger UI:${NC}         http://localhost:8787/docs"
echo "  ${BLUE}Redoc Docs:${NC}         http://localhost:8787/redoc"
echo "  ${BLUE}OpenAPI Spec:${NC}       http://localhost:8787/openapi.json"
echo "  ${BLUE}Health Check:${NC}       http://localhost:8787/health"
echo ""
echo "Optional: Start MCP Inspector in another terminal"
echo "  npx @anthropic-ai/mcp-inspector"
echo ""
echo "Press ${YELLOW}Ctrl+C${NC} to stop all services..."
echo ""

# Wait for both processes
wait
