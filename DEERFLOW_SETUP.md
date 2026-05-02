# DeerFlow Integration Setup Guide

## Current Status (2026-05-02)

DeerFlow 2.0 has been cloned to Hetzner at `/opt/research-toolbox/vendor/deer-flow`.

### Limitations

- **DeerFlow requires Python 3.12+** for the embedded client library (`deerflow-harness`)
- Current Hetzner environment: Python 3.11.2
- Upgrade to Python 3.12+ is required for full embedded client support

### Current Integration Approach

The `research_deer_flow` tool in Loom uses a **fallback-first strategy**:

1. **Embedded Client** (requires Python 3.12+)
   - Uses `DeerFlowClient` from `deerflow-harness` package
   - Direct in-process agent access
   - Lowest latency, highest integration

2. **HTTP API** (requires DeerFlow server running)
   - Calls DeerFlow server via REST API
   - Set `DEERFLOW_HTTP_URL` environment variable
   - Example: `export DEERFLOW_HTTP_URL=http://localhost:8000`

3. **Enhanced Fallback Mode** (current active)
   - Simulates multi-agent research with predefined personas
   - Works without any external dependencies
   - Supports all depth levels: shallow, standard, deep, comprehensive
   - Depth-aware synthesis and agent composition

## Setup Instructions

### Option 1: Upgrade Python (Permanent Fix)

```bash
# On Hetzner
ssh hetzner

# Install Python 3.12
sudo apt update && sudo apt install -y python3.12 python3.12-venv

# Create new venv with Python 3.12
cd /opt/research-toolbox
python3.12 -m venv venv-py312

# Activate and install
source venv-py312/bin/activate
pip install --upgrade pip

# Install DeerFlow harness
cd /opt/research-toolbox/vendor/deer-flow/backend/packages/harness
pip install -e .

# Update systemd service to use venv-py312
sudo systemctl edit research-toolbox.service
# Change: Environment="PATH=/opt/research-toolbox/venv/bin:..."
# To:     Environment="PATH=/opt/research-toolbox/venv-py312/bin:..."

sudo systemctl daemon-reload
sudo systemctl restart research-toolbox
```

### Option 2: Run DeerFlow Server Separately (HTTP Mode)

```bash
# On Hetzner (or dedicated machine with Python 3.12+)
cd /opt/research-toolbox/vendor/deer-flow/backend

# Create Python 3.12 venv
python3.12 -m venv venv

# Install dependencies
source venv/bin/activate
pip install -e .

# Configure (copy and edit example configs)
cp config.example.yaml config.yaml
cp .env.example .env

# Edit config for your environment
nano config.yaml

# Start server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# On the Loom server, set environment variable
export DEERFLOW_HTTP_URL=http://hetzner-ip:8000

# Restart research-toolbox
sudo systemctl restart research-toolbox
```

### Option 3: Docker Deployment (Recommended by DeerFlow)

```bash
# Clone and setup (if not already done)
cd /opt/research-toolbox/vendor/deer-flow

# Build Docker image
docker build -t deer-flow:latest -f backend/Dockerfile .

# Run container
docker run -d \
  --name deer-flow-server \
  -p 8000:8000 \
  -v $(pwd)/backend/config.yaml:/app/config.yaml \
  -v $(pwd)/backend/.env:/app/.env \
  deer-flow:latest

# Verify running
docker logs deer-flow-server

# Update Loom to connect
export DEERFLOW_HTTP_URL=http://localhost:8000
sudo systemctl restart research-toolbox
```

## Repository Structure

```
/opt/research-toolbox/vendor/deer-flow/
├── backend/                    # Python backend (requires 3.12+)
│   ├── app/                    # FastAPI app
│   ├── packages/harness/       # deerflow-harness library
│   │   └── deerflow/
│   │       ├── client.py       # DeerFlowClient (embedded)
│   │       ├── agents/         # Agent implementations
│   │       ├── skills/         # Skill system
│   │       ├── tools/          # Tool definitions
│   │       └── sandbox/        # Sandbox execution
│   ├── pyproject.toml
│   ├── config.example.yaml     # Configuration template
│   └── .env.example            # Environment template
├── frontend/                   # React UI (optional)
├── docs/                       # Documentation
└── docker/                     # Docker configuration
```

## Environment Variables

### For HTTP API Mode

```bash
# URL to running DeerFlow server
export DEERFLOW_HTTP_URL=http://localhost:8000

# Optional: API key if server requires auth
export DEERFLOW_API_KEY=your_api_key

# Optional: Timeout for requests (seconds)
export DEERFLOW_TIMEOUT=120
```

### DeerFlow Server Configuration

See `/opt/research-toolbox/vendor/deer-flow/backend/config.example.yaml` for:

- Model provider configuration (Anthropic, OpenAI, DeepSeek, Gemini, Kimi, etc.)
- Skill enablement
- Memory system configuration
- Sandbox settings
- Security and authentication

## Testing Integration

### Test Current (Fallback) Mode

```bash
# SSH to Hetzner
ssh hetzner

# Activate venv
source /opt/research-toolbox/venv/bin/activate

# Test the tool
cd /opt/research-toolbox
python3 -c "
from loom.tools.deerflow_backend import research_deer_flow
import asyncio

result = asyncio.run(research_deer_flow(
    'What are the latest advances in AI safety?',
    depth='deep',
    max_agents=5
))
print(f\"Backend: {result.get('backend')}\")
print(f\"Agents: {result.get('agents_used')}\")
print(f\"Synthesis: {result.get('synthesis')}\")
"
```

### Test Embedded Client (after Python 3.12 upgrade)

```bash
# After upgrading to Python 3.12 and installing deerflow-harness
python3 -c "
from deerflow.client import DeerFlowClient

client = DeerFlowClient(thinking_enabled=True, plan_mode=True)
response = client.chat('Analyze AI safety implications of multimodal models')
print(response)
"
```

### Test HTTP API

```bash
# Assuming DeerFlow server is running at localhost:8000
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Research: latest AI safety advances",
    "stream": false
  }'
```

## Features by Backend

### Fallback Mode (Current)
- ✅ Multi-agent simulation
- ✅ Depth-aware research (shallow, standard, deep, comprehensive)
- ✅ Agent personas and confidence scores
- ✅ Synthesis generation
- ✅ Timeout handling
- ✅ Error resilience
- ❌ Real agent orchestration
- ❌ Persistent memory
- ❌ Sandbox execution

### Embedded Client (Python 3.12+)
- ✅ Real multi-agent orchestration
- ✅ Sub-agent delegation
- ✅ Extended thinking mode
- ✅ Plan mode
- ✅ Persistent memory
- ✅ Sandbox execution
- ✅ Skill system access
- ✅ Tool integration
- ✅ Streaming responses

### HTTP API
- ✅ Remote server deployment
- ✅ Scalable multi-worker setup
- ✅ Load balancing ready
- ✅ Can run on Python 3.12+ only instance
- ✅ Decoupled from Loom server

## Next Steps

1. **Immediate**: Fallback mode is working and provides research capabilities
2. **Short-term**: Upgrade Hetzner to Python 3.12 for embedded client
3. **Medium-term**: Run DeerFlow as separate HTTP service for scale
4. **Long-term**: Fully integrate agent responses into Loom's knowledge graph

## Resources

- **DeerFlow Repository**: https://github.com/bytedance/deer-flow
- **Installation Guide**: https://github.com/bytedance/deer-flow/blob/main/Install.md
- **Documentation**: https://deerflow.tech
- **Python Client**: `/opt/research-toolbox/vendor/deer-flow/backend/packages/harness/deerflow/client.py`

## Troubleshooting

### Python Version Mismatch

```
ERROR: Package 'deerflow-harness' requires a different Python: 3.11.2 not in '>=3.12'
```

**Solution**: Use Python 3.12+ or run DeerFlow as HTTP server

### Import Errors

```
ImportError: cannot import name 'DeerFlowClient' from 'deerflow.client'
```

**Solution**: Install deerflow-harness: `pip install -e /opt/research-toolbox/vendor/deer-flow/backend/packages/harness`

### Connection Refused (HTTP Mode)

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution**: Start DeerFlow server or set `DEERFLOW_HTTP_URL` correctly

### Timeout Issues

Increase timeout or reduce max_agents:
```python
result = await research_deer_flow(
    query,
    depth="standard",
    max_agents=3,  # Reduce from 5
    timeout=180    # Increase from 120
)
```
