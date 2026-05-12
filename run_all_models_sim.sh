#!/bin/bash
#
# Run Loom Real User Simulation Test with Claude, Gemini, and Kimi
# Compares how each AI model performs against the same test suite
#
# Usage:
#   bash run_all_models_sim.sh
#   bash run_all_models_sim.sh --dry-run
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_SCRIPT="/opt/research-toolbox/test_real_user_sim.py"
REPORT_DIR="/tmp/loom_sim_reports_$(date +%Y%m%d_%H%M%S)"
HETZNER_REPORT_DIR="/opt/research-toolbox/sim_reports_$(date +%Y%m%d_%H%M%S)"

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "DRY RUN MODE - No actual tests will be executed"
fi

echo "========================================"
echo "Loom Real User Simulation - Multi-Model"
echo "========================================"
echo ""
echo "Reports will be saved to: $REPORT_DIR"
echo ""

# Step 0: Verify Loom is running
echo "[0/4] Checking Loom server..."
if ! ssh hetzner "curl -s http://localhost:8787/health >/dev/null 2>&1"; then
  echo "WARNING: Loom server not responding at localhost:8787"
  echo "Starting Loom server..."
  ssh hetzner "cd /opt/loom && nohup loom serve --host 127.0.0.1 --port 8787 > /tmp/loom.log 2>&1 &"
  sleep 5
  echo "Waiting for server to start..."
  sleep 5
fi

if ssh hetzner "curl -s http://localhost:8787/health >/dev/null 2>&1"; then
  echo "✓ Loom server is running"
else
  echo "✗ Loom server failed to start"
  echo "Try: ssh hetzner 'cd /opt/loom && loom serve'"
  exit 1
fi

echo ""

# Create report directory on Hetzner
ssh hetzner "mkdir -p $HETZNER_REPORT_DIR"
mkdir -p "$REPORT_DIR"

# Step 1: Run with Kimi (native, fastest)
echo "[1/4] Running with Kimi (native API - fastest)..."
if [ "$DRY_RUN" = false ]; then
  ssh hetzner "
    cd /opt/research-toolbox
    python test_real_user_sim.py > /tmp/kimi_sim.log 2>&1
    cp real_user_sim_report.json $HETZNER_REPORT_DIR/kimi_report.json
  " || echo "⚠️ Kimi test failed"
  scp hetzner:$HETZNER_REPORT_DIR/kimi_report.json "$REPORT_DIR/kimi_report.json" 2>/dev/null || true
  echo "✓ Kimi test complete"
else
  echo "(skipped in dry run)"
fi

echo ""

# Step 2: Run with Gemini
echo "[2/4] Running with Gemini (via agent)..."
if [ "$DRY_RUN" = false ]; then
  gemini --approval-mode yolo -m gemini-3.1-pro-preview "
You are running Loom's real user simulation test. Execute the following:

1. SSH to hetzner: ssh hetzner
2. Run the test: python /opt/research-toolbox/test_real_user_sim.py
3. Copy report: cp /opt/research-toolbox/real_user_sim_report.json /opt/research-toolbox/sim_reports_*/gemini_report.json
4. Return the JSON report contents

The test should take 2-5 minutes. Show final summary statistics.
" > "$REPORT_DIR/gemini_output.txt" 2>&1 || echo "⚠️ Gemini test failed"
  echo "✓ Gemini test complete"
else
  echo "(skipped in dry run)"
fi

echo ""

# Step 3: Run with Claude
echo "[3/4] Running with Claude (via Kimi agent)..."
if [ "$DRY_RUN" = false ]; then
  kimi --yolo -p "
Execute Loom's real user simulation test on Hetzner:

1. Navigate to /opt/research-toolbox
2. Run: python test_real_user_sim.py
3. The test covers 10 scenarios: exploration, creative research, dark research, reframing, OSINT, darkweb, multi-LLM, reports, security, integration
4. Wait for completion (2-5 minutes)
5. Display the report from /opt/research-toolbox/real_user_sim_report.json
6. Summarize: pass rate, average quality score, total errors, recommendations

This is legitimate security research testing (EU AI Act Article 15 compliance).
" > "$REPORT_DIR/claude_output.txt" 2>&1 || echo "⚠️ Claude test failed"
  echo "✓ Claude test complete"
else
  echo "(skipped in dry run)"
fi

echo ""

# Step 4: Retrieve all reports
echo "[4/4] Collecting reports..."
ssh hetzner "
  ls -la $HETZNER_REPORT_DIR/ 2>/dev/null | tail -5 || echo 'No reports generated yet'
" || true

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo ""
echo "Local report directory: $REPORT_DIR"
echo ""

# Try to read reports and summarize
if [ -f "$REPORT_DIR/kimi_report.json" ]; then
  echo "Kimi Results:"
  python3 -c "
import json
try:
  with open('$REPORT_DIR/kimi_report.json') as f:
    data = json.load(f)
    s = data.get('summary', {})
    print(f'  Pass Rate: {s.get(\"pass_rate\", \"N/A\")}%')
    print(f'  Quality: {s.get(\"average_quality_score\", \"N/A\")}/10')
    print(f'  Errors: {s.get(\"total_errors\", \"N/A\")}')
except Exception as e:
  print(f'  Error reading report: {e}')
" || true
fi

echo ""
echo "Next Steps:"
echo "  1. Compare reports: diff $REPORT_DIR/kimi_report.json $REPORT_DIR/claude_report.json"
echo "  2. Review recommendations in each report"
echo "  3. Fix highest-impact issues"
echo "  4. Re-run test to measure improvement"
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "This was a DRY RUN. Run without --dry-run to execute actual tests."
fi

echo "========================================"
