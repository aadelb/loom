#!/bin/bash
# Run load test on Hetzner remote server
# Usage: ./scripts/run_load_test_remote.sh [--quick] [--output /path]

set -euo pipefail

# Configuration
HETZNER_HOST="${HETZNER_HOST:-hetzner}"
LOOM_PATH="${LOOM_PATH:-/opt/loom}"
OUTPUT_PATH="${OUTPUT_PATH:-/opt/research-toolbox/tmp/load_test_results.json}"
QUICK="${QUICK:-false}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --quick)
      QUICK="true"
      shift
      ;;
    --output)
      OUTPUT_PATH="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

echo "Load Test Configuration:"
echo "  Host: $HETZNER_HOST"
echo "  Loom Path: $LOOM_PATH"
echo "  Output: $OUTPUT_PATH"
echo "  Quick Mode: $QUICK"
echo ""

# Build command
CMD="cd $LOOM_PATH && PYTHONPATH=src python3 scripts/load_test.py --output $OUTPUT_PATH"
if [ "$QUICK" = "true" ]; then
  CMD="$CMD --quick"
fi

# Execute on remote
echo "Executing on $HETZNER_HOST..."
ssh "$HETZNER_HOST" "$CMD"

# Fetch results
echo ""
echo "Fetching results..."
TEMP_FILE="/tmp/load_test_results_$RANDOM.json"
scp "$HETZNER_HOST:$OUTPUT_PATH" "$TEMP_FILE"

# Display summary
echo ""
echo "================================"
echo "Load Test Summary"
echo "================================"
python3 - "$TEMP_FILE" << 'PYTHON'
import json
import sys

with open(sys.argv[1]) as f:
    report = json.load(f)

print(f"Timestamp: {report['timestamp']}")
print(f"Total Duration: {report['total_duration_sec']:.1f}s")
print(f"Overall Status: {report['overall_status']}")
print()
print("Test Results:")
for test in report['test_results']:
    print(f"  {test['name']}: {test['status']}")
    print(f"    Success Rate: {test['success_rate']}")
    print(f"    Throughput: {test['throughput_rps']} req/s")
    latency = test['latency_ms']
    print(f"    Latency: avg={latency['avg']}ms, p95={latency['p95']}ms, p99={latency['p99']}ms")

print()
summary = report['summary']
print(f"Summary: {summary['passed']} PASS, {summary['warned']} WARN, {summary['failed']} FAIL")
PYTHON

# Save locally
LOCAL_OUTPUT="load_test_results_$(date +%Y%m%d_%H%M%S).json"
cp "$TEMP_FILE" "$LOCAL_OUTPUT"
echo ""
echo "Results saved locally to: $LOCAL_OUTPUT"

# Cleanup
rm -f "$TEMP_FILE"
