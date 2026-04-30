#!/bin/bash
# Deploy Loom v3 to Hetzner with all API keys
# Usage: bash scripts/deploy_to_hetzner.sh

set -e

REMOTE="hetzner"
REMOTE_PATH="/opt/research-toolbox"
ENV_SOURCE="$HOME/.claude/resources.env"

echo "=== Loom v3 Deployment to Hetzner ==="

# 1. Sync code to Hetzner
echo "[1/5] Syncing code..."
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='tmp/' --exclude='test-results/' --exclude='graphify-out/' \
  --exclude='.venv/' --exclude='venv/' \
  ./ "$REMOTE:$REMOTE_PATH/"

# 2. Deploy API keys
echo "[2/5] Deploying API keys..."
if [ -f "$ENV_SOURCE" ]; then
  # Extract Loom-relevant keys and create .env
  grep -E "^(GROQ_|NVIDIA_NIM|DEEPSEEK_|GOOGLE_AI|MOONSHOT_|OPENAI_|ANTHROPIC_API_KEY|EXA_|TAVILY_|BRAVE_|NEWS_API|COINMARKETCAP|INVESTING_|VASTAI_|STRIPE_|SMTP_|JOPLIN_|TOR_|BINANCE_|COINDESK_|VERCEL_)" "$ENV_SOURCE" > /tmp/loom_deploy_env.tmp 2>/dev/null || true

  # Map key names to what Loom expects
  sed -i '' 's/GOOGLE_AI_KEY_1/GOOGLE_AI_KEY/' /tmp/loom_deploy_env.tmp 2>/dev/null || true
  sed -i '' 's/ANTHROPIC_API_KEY_LOOM/ANTHROPIC_API_KEY/' /tmp/loom_deploy_env.tmp 2>/dev/null || true

  scp /tmp/loom_deploy_env.tmp "$REMOTE:$REMOTE_PATH/.env"
  rm /tmp/loom_deploy_env.tmp
  ssh "$REMOTE" "chmod 600 $REMOTE_PATH/.env"
  echo "  Keys deployed: $(ssh $REMOTE 'wc -l < '$REMOTE_PATH'/.env') keys"
else
  echo "  WARNING: $ENV_SOURCE not found"
fi

# 3. Install/update on Hetzner
echo "[3/5] Installing dependencies..."
ssh "$REMOTE" "cd $REMOTE_PATH && pip install -e '.[all]' --quiet 2>&1 | tail -3"

# 4. Restart service
echo "[4/5] Restarting service..."
ssh "$REMOTE" "systemctl restart research-toolbox.service 2>/dev/null || cd $REMOTE_PATH && nohup python -m loom.cli serve > /var/log/loom.log 2>&1 &"
sleep 3

# 5. Verify
echo "[5/5] Verifying deployment..."
TOOL_COUNT=$(ssh "$REMOTE" "curl -s http://127.0.0.1:8787/mcp -X POST -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{},\"clientInfo\":{\"name\":\"deploy-check\",\"version\":\"1.0\"}}}' 2>/dev/null | grep -o 'research_' | wc -l" 2>/dev/null || echo "0")

echo ""
echo "=== Deployment Complete ==="
echo "Tools available: ~$TOOL_COUNT"
echo "Server: http://127.0.0.1:8787/mcp (on Hetzner)"
echo "SSH tunnel: ssh -f -N -L 8787:127.0.0.1:8787 hetzner"
