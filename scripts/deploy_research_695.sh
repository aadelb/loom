#!/bin/bash
# Deploy and run Research Task 695: Mechanistic Interpretability
# Runs on Hetzner with proper isolation and error handling

set -euo pipefail

echo "[DEPLOY_695] Starting mechanistic interpretability research deployment"
echo "[DEPLOY_695] Target: Hetzner /opt/research-toolbox"
echo "[DEPLOY_695] Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# SSH to Hetzner and execute
ssh hetzner << 'EOF'
set -euo pipefail

echo "[HETZNER] Preparing environment"
cd /opt/research-toolbox

# Verify Python environment
if ! command -v python3 &> /dev/null; then
    echo "[HETZNER] ERROR: python3 not found"
    exit 1
fi

# Verify .env exists
if [ ! -f .env ]; then
    echo "[HETZNER] ERROR: .env not found in /opt/research-toolbox"
    exit 1
fi

# Verify output directory
mkdir -p /opt/research-toolbox/tmp
chmod 755 /opt/research-toolbox/tmp

echo "[HETZNER] Environment verified"
echo "[HETZNER] Running research_695.py..."

# Run the research script with timeout
timeout 3600 python3 /opt/research-toolbox/research_695.py || {
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        echo "[HETZNER] ERROR: Research timed out (>1 hour)"
    else
        echo "[HETZNER] ERROR: Research failed with exit code $exit_code"
    fi
    exit $exit_code
}

# Verify output file
if [ ! -f /opt/research-toolbox/tmp/research_695_interpretability.json ]; then
    echo "[HETZNER] ERROR: Output file not created"
    exit 1
fi

# Report stats
file_size=$(stat -f%z /opt/research-toolbox/tmp/research_695_interpretability.json 2>/dev/null || \
            stat -c%s /opt/research-toolbox/tmp/research_695_interpretability.json)
echo "[HETZNER] Output file size: $file_size bytes"

# Show sample of results
echo "[HETZNER] Sample of findings (first 10 queries):"
python3 << 'PYTHON'
import json
with open('/opt/research-toolbox/tmp/research_695_interpretability.json') as f:
    data = json.load(f)
    findings = data.get('findings', {})
    for i, (query, result) in enumerate(list(findings.items())[:10]):
        status = result.get('status', 'unknown')
        count = result.get('result_count', 0)
        print(f"  [{i+1}] {query[:60]:<60} {status} ({count} results)")

    success = sum(1 for r in findings.values() if r.get('status') == 'success')
    total = len(findings)
    print(f"\n  Total: {success}/{total} successful")
PYTHON

echo "[HETZNER] Research deployment complete"

EOF

echo "[DEPLOY_695] Deployment successful"
echo "[DEPLOY_695] Results file: /opt/research-toolbox/tmp/research_695_interpretability.json"
echo "[DEPLOY_695] To download locally:"
echo "  scp hetzner:/opt/research-toolbox/tmp/research_695_interpretability.json ."
