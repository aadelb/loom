#!/bin/bash

# Deploy and run research_704.py on Hetzner
# Usage: ./deploy_research_704.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCRIPT_NAME="research_704.py"

echo "=========================================="
echo "Deploying Research 704 to Hetzner"
echo "=========================================="
echo ""

# Copy script to Hetzner
echo "[1/3] Copying research script to Hetzner..."
scp "$SCRIPT_DIR/$SCRIPT_NAME" hetzner:/opt/research-toolbox/scripts/ || {
    echo "ERROR: Failed to copy script to Hetzner"
    exit 1
}

# Create output directory
echo "[2/3] Creating output directory on Hetzner..."
ssh hetzner "mkdir -p /opt/research-toolbox/tmp" || {
    echo "ERROR: Failed to create output directory"
    exit 1
}

# Run the script on Hetzner
echo "[3/3] Running research script on Hetzner..."
ssh hetzner "cd /opt/research-toolbox && python3 scripts/$SCRIPT_NAME" || {
    echo "ERROR: Failed to run research script"
    exit 1
}

echo ""
echo "=========================================="
echo "Research 704 Complete!"
echo "=========================================="
echo ""
echo "Output file:"
echo "  /opt/research-toolbox/tmp/research_704_competitive.json"
echo ""
echo "To view results:"
echo "  ssh hetzner cat /opt/research-toolbox/tmp/research_704_competitive.json | jq ."
