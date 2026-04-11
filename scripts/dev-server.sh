#!/bin/bash
# Start Loom server for local development
# Usage: ./scripts/dev-server.sh

set -e

cd "$(dirname "$0")/.."
exec python -m loom.server
