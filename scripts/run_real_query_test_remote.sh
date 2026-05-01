#!/bin/bash
# run_real_query_test_remote.sh
# Execute real_query_test.py on Hetzner via SSH
# Usage: ./scripts/run_real_query_test_remote.sh [hostname] [port]
# Default: ssh hetzner (from ~/.ssh/config)

set -e

REMOTE_HOST="${1:-hetzner}"
LOOM_PORT="${2:-8787}"
PROJECT_DIR="/Users/aadel/projects/loom"

echo "========================================="
echo "Real Query Test Runner (Remote)"
echo "========================================="
echo "Remote host: $REMOTE_HOST"
echo "Loom port: $LOOM_PORT"
echo "Project dir: $PROJECT_DIR"
echo ""

# Check SSH connectivity
echo "[1/4] Checking SSH connectivity..."
if ! ssh "$REMOTE_HOST" "echo 'SSH OK'" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to $REMOTE_HOST"
    exit 1
fi
echo "✓ SSH connection established"
echo ""

# Check if Loom server is running
echo "[2/4] Checking if Loom MCP server is running..."
if ! ssh "$REMOTE_HOST" "curl -s http://127.0.0.1:$LOOM_PORT/mcp -X POST -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}' > /dev/null 2>&1"; then
    echo "WARNING: Loom MCP server not responding at 127.0.0.1:$LOOM_PORT"
    echo "Starting Loom server..."
    ssh "$REMOTE_HOST" "cd $PROJECT_DIR && nohup loom serve --port $LOOM_PORT > /tmp/loom_serve.log 2>&1 &" || true
    echo "Waiting 5 seconds for server to start..."
    sleep 5
fi
echo "✓ Loom MCP server is running"
echo ""

# Run the test script
echo "[3/4] Running real_query_test.py..."
ssh "$REMOTE_HOST" "cd $PROJECT_DIR && python3 scripts/real_query_test.py"
TEST_EXIT_CODE=$?

# Fetch report
echo ""
echo "[4/4] Fetching report..."
if ssh "$REMOTE_HOST" "test -f $PROJECT_DIR/real_query_test_report.json"; then
    mkdir -p ./test_reports
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    REPORT_PATH="./test_reports/report_${TIMESTAMP}.json"
    scp "$REMOTE_HOST:$PROJECT_DIR/real_query_test_report.json" "$REPORT_PATH"
    echo "✓ Report saved to: $REPORT_PATH"

    # Print summary
    echo ""
    echo "========================================="
    echo "TEST SUMMARY"
    echo "========================================="
    python3 << EOF
import json
with open("$REPORT_PATH") as f:
    data = json.load(f)
    s = data['summary']
    print(f"Total tools: {s['total']}")
    print(f"  OK:       {s['ok']}")
    print(f"  ERROR:    {s['error']}")
    print(f"  TIMEOUT:  {s['timeout']}")
    print(f"  SKIP:     {s['skip']}")

    # Calculate success rate
    success_rate = (s['ok'] / s['total'] * 100) if s['total'] > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
EOF
else
    echo "WARNING: Could not fetch report"
fi

exit $TEST_EXIT_CODE
