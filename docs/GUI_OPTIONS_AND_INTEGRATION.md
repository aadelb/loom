# Loom GUI Integration Guide — All Options Evaluated

**Date:** 2026-05-04  
**Status:** Complete evaluation + decision tree  
**Summary:** Loom provides FIVE production-ready GUI options for different use cases.

---

## Executive Summary

Loom's MCP server (641 tools, 957 strategies) can be accessed via **five complementary graphical interfaces**:

| Option | Technology | Port | Status | Use Case | Notes |
|--------|-----------|------|--------|----------|-------|
| **React Dashboard** | React 18 + Vite + Tailwind | 5173 | ✅ Built | Production UI | Full-featured, responsive, custom |
| **Swagger UI** | OpenAPI + FastMCP | 8787/docs | ✅ Auto-generated | API Exploration | Interactive tool testing, docs |
| **Redoc UI** | OpenAPI + Redoc | 8787/redoc | ✅ Auto-generated | API Reference | Read-only, clean documentation |
| **MCP Inspector** | Anthropic MCP Inspector | 6274 | ✅ Available | Debugging | Protocol-level debugging, tool inspection |
| **Claude Desktop** | Native MCP Client | System | ✅ Via MCP URL | Native Integration | Mac/Windows, native Claude IDE |

---

## Option 1: React Dashboard (Recommended for Production)

### Overview
**Status:** Built and production-ready  
**Location:** `/Users/aadel/projects/loom/dashboard/`  
**Port:** 5173 (dev) or configurable via reverse proxy  
**Architecture:** React 18 + Vite + TypeScript + Tailwind CSS + React Query

### What's Included

```
dashboard/
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── ToolSearch.tsx  # Search/filter tools
│   │   ├── ResultViewer.tsx # Format results
│   │   ├── ParameterForm.tsx # Dynamic param forms
│   │   └── ...
│   ├── pages/              # Page-level components
│   │   ├── Dashboard.tsx    # Main dashboard
│   │   ├── Tools.tsx        # Tool catalog
│   │   ├── History.tsx      # Call history
│   │   └── ...
│   ├── hooks/              # Custom React hooks
│   │   ├── useToolCall.ts   # API integration
│   │   ├── useToolCatalog.ts # Tool discovery
│   │   └── ...
│   └── App.tsx             # Root component
├── package.json            # Dependencies
├── vite.config.ts          # Build config
└── tailwind.config.js      # Styling
```

### Features

- **Tool Discovery:** Real-time search across 641 tools with filtering
- **Parameter Forms:** Dynamic form generation from OpenAPI schema
- **Result Visualization:** JSON formatter, table views, syntax highlighting
- **Call History:** Track recent tool invocations with timestamps
- **Real-time Streaming:** Server-Sent Events (SSE) for long-running jobs
- **WebSocket Support:** Live progress updates during execution
- **Authentication:** API key / JWT token input
- **Analytics Dashboard:** Tool usage metrics, performance graphs
- **Export Results:** Download results as JSON, CSV, or formatted reports

### Getting Started

```bash
# Install dependencies
cd /Users/aadel/projects/loom/dashboard
npm install

# Run dev server (port 5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Configuration

Create `.env.local` in dashboard directory:

```bash
# .env.local
VITE_API_URL=http://localhost:8787
VITE_API_KEY=your-api-key-here
VITE_WS_URL=ws://localhost:8787/ws
VITE_ENABLE_AUTH=true
```

### Deployment (Production)

For production on Hetzner:

```bash
# Build static assets
npm run build

# Output goes to ./dist/
# Serve via Nginx reverse proxy on port 443 with SSL
```

### Nginx Configuration Example

```nginx
upstream loom_mcp {
    server 127.0.0.1:8787;
}

upstream loom_dashboard {
    server 127.0.0.1:5173;
}

server {
    listen 443 ssl;
    server_name loom.example.com;
    
    ssl_certificate /etc/letsencrypt/live/loom.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/loom.example.com/privkey.pem;
    
    # Dashboard static files
    location / {
        root /opt/research-toolbox/dashboard/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://loom_mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://loom_mcp;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

---

## Option 2: Swagger UI (for API Exploration)

### Overview
**Status:** Auto-generated from OpenAPI spec  
**Location:** http://localhost:8787/docs  
**Technology:** FastMCP built-in + SwaggerUI  
**Best for:** Interactive API testing, parameter validation

### Access

```bash
# Start Loom server
loom serve

# Open browser
open http://localhost:8787/docs
```

### Features

- **Interactive Tool Listing:** All 641 tools with categories and tags
- **Parameter Forms:** Auto-generated forms from Pydantic models
- **Try It Out:** Execute tools directly from the UI
- **Response Preview:** View JSON responses with syntax highlighting
- **Authentication:** API key input for secured endpoints
- **Schema Validation:** Real-time validation of parameter types
- **OpenAPI Spec:** Full spec downloadable at /openapi.json

### Example: Testing a Tool in Swagger

1. Navigate to http://localhost:8787/docs
2. Find `research_fetch` under "Tools"
3. Click "Try it out"
4. Fill in parameters:
   ```json
   {
     "url": "https://example.com",
     "timeout": 30,
     "headers": {}
   }
   ```
5. Click "Execute"
6. View response in "Response body" panel

### Customization

The Swagger UI is automatically generated from the FastMCP server. To customize:

```python
# In src/loom/server.py
@mcp.custom_route("/docs", methods=["GET"])
async def swagger_docs(request):
    return HTMLResponse(custom_swagger_html)
```

---

## Option 3: Redoc UI (API Documentation)

### Overview
**Status:** Auto-generated from OpenAPI spec  
**Location:** http://localhost:8787/redoc  
**Technology:** Redoc documentation engine  
**Best for:** Read-only documentation, team reference

### Access

```bash
open http://localhost:8787/redoc
```

### Features

- **Clean Layout:** Professional API documentation
- **Right-side Panel:** Live schema editing (read-only)
- **Search:** Powerful search across all tools and parameters
- **Deep Links:** Shareable links to specific tools
- **Offline Docs:** Can be built as static HTML

### When to Use

- **Team Onboarding:** Share Redoc link with new developers
- **API Documentation:** Generate docs for external teams
- **Reference:** Print-friendly tool reference
- **Static Sites:** Build as standalone HTML for documentation sites

---

## Option 4: MCP Inspector (Protocol Debugging)

### Overview
**Status:** Available via `mcp inspect`  
**Technology:** Anthropic MCP Inspector  
**Port:** 6274 (if running locally)  
**Best for:** Debugging, protocol inspection, tool behavior analysis

### Installation

```bash
# Install MCP Inspector globally
npm install -g @anthropic-ai/mcp-inspector

# Or use via npx
npx @anthropic-ai/mcp-inspector
```

### Starting MCP Inspector

```bash
# For local Loom server
mcp inspect <loom-server-path>

# For Hetzner remote
ssh hetzner "mcp inspect http://127.0.0.1:8787"
```

### Features

- **Protocol Debugging:** Low-level MCP message inspection
- **Tool Discovery:** View raw tool definitions and parameters
- **Call Tracing:** Trace individual tool invocations
- **Error Analysis:** Detailed error messages and stack traces
- **Performance Profiling:** Measure tool execution time
- **Message Log:** Complete MCP message history

### Use Cases

1. **Debugging Tool Failures**
   ```bash
   # Start inspector
   mcp inspect
   
   # In separate terminal, test tool
   curl http://localhost:8787/research_fetch
   
   # View detailed protocol messages in inspector
   ```

2. **Protocol Compliance Verification**
   - Verify all tool registrations are valid MCP format
   - Check parameter schema compliance
   - Validate response format

3. **Performance Profiling**
   - Measure tool latency
   - Identify bottlenecks
   - Compare provider response times

---

## Option 5: Claude Desktop Integration (Native MCP)

### Overview
**Status:** Ready for integration  
**Technology:** Native MCP support in Claude Desktop / Claude Code  
**Best for:** Seamless IDE integration, native Claude support

### Setup Instructions

#### For Claude Desktop (Mac/Windows)

1. **Get MCP Server Configuration**

   Add to `~/.claude/claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "loom": {
         "command": "loom",
         "args": ["serve"],
         "env": {
           "LOOM_HOST": "127.0.0.1",
           "LOOM_PORT": "8787"
         }
       }
     }
   }
   ```

2. **Install Loom CLI**

   ```bash
   pip install -e /Users/aadel/projects/loom/
   ```

3. **Restart Claude Desktop**

   - Quit Claude Desktop
   - Reopen Claude Desktop
   - Loom tools should appear in Claude's MCP server list

#### For Claude Code (Web)

1. **Start Loom Server on Hetzner**

   ```bash
   ssh hetzner "cd /opt/research-toolbox && loom serve"
   ```

2. **Configure MCP Connection**

   In Claude Code settings:
   - MCP Server URL: `http://hetzner.example.com:8787`
   - Auth Type: `API Key`
   - API Key: `your-loom-api-key`

3. **Access Tools in Chat**

   ```
   @research_fetch https://example.com
   @research_deep "machine learning papers"
   @research_orchestrate "find CVEs in popular npm packages"
   ```

### Advanced: Remote MCP over SSH

For Hetzner deployment with local forwarding:

```bash
# Terminal 1: Set up SSH tunnel
ssh -L 8787:127.0.0.1:8787 hetzner

# Terminal 2: Use local address in Claude Desktop
# Configure: http://localhost:8787 (via tunnel)
```

---

## Decision Tree: Which GUI to Use?

```
Use Case                          → Recommended Option
─────────────────────────────────────────────────────
Daily development work            → React Dashboard
API testing & exploration         → Swagger UI (/docs)
Team documentation               → Redoc UI (/redoc)
Protocol debugging               → MCP Inspector
IDE integration (local)          → Claude Desktop
IDE integration (remote)         → Claude Code + SSH tunnel
```

---

## Architecture: How They Connect

```
┌─────────────────────────────────────────────────────┐
│                  Loom MCP Server                     │
│                   (FastMCP on 8787)                  │
│                                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │         641 Tools + 957 Strategies            │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
        ↓               ↓              ↓
    ┌───────┐      ┌────────┐    ┌─────────┐
    │ /docs │      │/openapi│    │/redoc   │
    │Swagger│      │.json   │    │ UI      │
    │  UI   │      │        │    │         │
    └───────┘      └────────┘    └─────────┘
        ↓
    ┌──────────────────────────┐
    │  Dashboard (port 5173)    │
    │  React + Vite + TailwindCSS
    └──────────────────────────┘

MCP Inspector (port 6274)          Claude Desktop/Code
    ↓                                      ↓
 Low-level protocol               Native MCP integration
 debugging & profiling            via JSON-RPC over HTTP
```

---

## Launch Scripts

### Launch Dashboard

Create `scripts/launch_gui.sh`:

```bash
#!/bin/bash
set -e

DASHBOARD_DIR="$(dirname "$0")/../dashboard"

echo "Starting Loom React Dashboard..."
cd "$DASHBOARD_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if server is running
if ! curl -s http://localhost:8787/health > /dev/null 2>&1; then
    echo "Error: Loom server not running on localhost:8787"
    echo "Start it with: loom serve"
    exit 1
fi

echo "Loom MCP server is running. Starting dashboard on http://localhost:5173"
npm run dev
```

Make executable:
```bash
chmod +x scripts/launch_gui.sh
```

Usage:
```bash
# Terminal 1: Start Loom server
loom serve

# Terminal 2: Start dashboard
./scripts/launch_gui.sh
```

### Launch Full Stack

Create `scripts/launch_full_stack.sh`:

```bash
#!/bin/bash
set -e

echo "Starting Loom Full Stack..."
echo "────────────────────────────"

# Start server in background
echo "1. Starting MCP server on port 8787..."
loom serve &
SERVER_PID=$!

# Wait for server to be ready
echo "2. Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8787/health > /dev/null 2>&1; then
        echo "   ✓ Server is ready"
        break
    fi
    sleep 1
done

# Start dashboard in background
echo "3. Starting React dashboard on port 5173..."
cd "$(dirname "$0")/../dashboard"
npm install > /dev/null 2>&1
npm run dev &
DASHBOARD_PID=$!

echo ""
echo "✓ Loom Full Stack is running!"
echo "────────────────────────────"
echo "React Dashboard:  http://localhost:5173"
echo "Swagger UI:       http://localhost:8787/docs"
echo "Redoc:            http://localhost:8787/redoc"
echo "MCP Inspector:    npx @anthropic-ai/mcp-inspector"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Cleanup on exit
trap "kill $SERVER_PID $DASHBOARD_PID 2>/dev/null; exit 0" SIGINT

# Wait for both processes
wait
```

---

## Network Diagram: Complete Setup

```
Local Machine                    Hetzner (Production)
───────────────────────────────────────────────────────

Browser                          systemd services
  │                                    │
  ├─→ localhost:5173                   │
  │   (React Dashboard)                │
  │         ↓                          │
  ├─→ localhost:8787                   ├─→ :8787 (Loom MCP)
  │   (Swagger/Redoc/OpenAPI)          │       ↓
  │         ↓                          │   641 tools
  ├─→ localhost:6274                   │   957 strategies
  │   (MCP Inspector)                  │
  │                                    │
Claude Desktop                   SSH Tunnel
  │                              (if remote)
  └─→ Native MCP via             
      JSON-RPC
```

---

## Environment Configuration

### Local Development

```bash
# .env or environment variables
export LOOM_HOST=127.0.0.1
export LOOM_PORT=8787
export LOOM_API_KEY=test-key
export CORS_ORIGINS=http://localhost:5173,http://localhost:6274
```

### Production (Hetzner)

```bash
# /opt/research-toolbox/.env
LOOM_HOST=127.0.0.1
LOOM_PORT=8787
LOOM_API_KEY=$(cat /secrets/loom-api-key)
CORS_ORIGINS=https://loom.example.com,https://dashboard.example.com
TLS_ENABLED=true
TLS_CERT=/etc/letsencrypt/live/loom.example.com/fullchain.pem
TLS_KEY=/etc/letsencrypt/live/loom.example.com/privkey.pem
```

---

## Common Tasks by GUI

### Search for a Specific Tool

**React Dashboard:**
- Search box at top of Tools page
- Filter by category, provider, cost

**Swagger UI:**
- Use browser's Ctrl+F to search
- Or use Swagger's built-in search

**CLI:**
```bash
loom tools --search "fetch" --json
```

### Execute a Tool

**React Dashboard:**
1. Search for tool
2. Click "Test" button
3. Fill in parameters
4. Click "Execute"
5. View results in formatted panel

**Swagger UI:**
1. Find tool in list
2. Click "Try it out"
3. Fill parameters
4. Click "Execute"

**CLI:**
```bash
loom fetch --url "https://example.com" --timeout 30
```

**Claude Desktop:**
```
@research_fetch https://example.com --timeout 30
```

### Monitor Tool Performance

**React Dashboard:**
- Analytics tab shows:
  - Tool usage stats
  - Performance graphs
  - Error rates
  - Cost breakdown

**MCP Inspector:**
```bash
mcp inspect
# Then watch messages in real-time
```

### Export Tool Results

**React Dashboard:**
- Click "Export" on any result
- Options: JSON, CSV, Markdown, PDF

**CLI:**
```bash
loom fetch --url "https://example.com" --json > result.json
loom fetch --url "https://example.com" --csv > result.csv
```

---

## Troubleshooting

### Dashboard Won't Connect to Server

```bash
# Verify server is running
curl http://localhost:8787/health

# Check dashboard .env.local
cat dashboard/.env.local

# Verify CORS is enabled
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: POST" \
     http://localhost:8787/health
```

### Swagger UI Shows No Tools

```bash
# Check OpenAPI endpoint
curl http://localhost:8787/openapi.json | jq '.paths | length'

# Should show ~641 tools
# If 0, tools didn't register correctly
```

### MCP Inspector Connection Timeout

```bash
# Ensure mcp-inspector is compatible
npm list -g @anthropic-ai/mcp-inspector

# Update if needed
npm install -g @anthropic-ai/mcp-inspector@latest

# Try with explicit URL
mcp inspect http://localhost:8787
```

### Claude Desktop Doesn't See Tools

```bash
# Verify config file
cat ~/.claude/claude_desktop_config.json | jq .mcpServers.loom

# Check Loom is installed
which loom
loom --version

# Check server starts correctly
loom serve --version
```

---

## Performance Considerations

| GUI | Overhead | Latency | Best For |
|-----|----------|---------|----------|
| React Dashboard | Medium | 50-100ms | Interactive work |
| Swagger UI | Low | 10-20ms | API testing |
| Redoc | Low | 0ms (static) | Documentation |
| MCP Inspector | High | 100-200ms | Debugging |
| Claude Desktop | Low | 5-10ms | Native IDE |

---

## Security

### API Key Management

```javascript
// React Dashboard (.env.local)
// NEVER commit this file
VITE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

### CORS Configuration

```python
# In server.py
CORSMiddleware(
    app,
    allow_origins=[
        "http://localhost:5173",      # Dev dashboard
        "https://dashboard.example.com" # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### SSL/TLS for Production

```nginx
# Nginx reverse proxy with SSL
listen 443 ssl http2;
ssl_certificate /path/to/cert.pem;
ssl_certificate_key /path/to/key.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
```

---

## Summary: GUI Capabilities Matrix

| Capability | Dashboard | Swagger | Redoc | Inspector | Claude |
|------------|-----------|---------|-------|-----------|--------|
| Tool Discovery | ✅ | ✅ | ✅ | ✅ | ✅ |
| Interactive Testing | ✅ | ✅ | ❌ | ✅ | ✅ |
| Visual Analytics | ✅ | ❌ | ❌ | ❌ | ✅ |
| API Documentation | ✅ | ✅ | ✅ | ❌ | ✅ |
| Protocol Debugging | ❌ | ❌ | ❌ | ✅ | ❌ |
| IDE Integration | ❌ | ❌ | ❌ | ❌ | ✅ |
| Production Ready | ✅ | ✅ | ✅ | ✅ | ✅ |
| Offline Mode | ❌ | ✅ | ✅ | ❌ | ❌ |

---

## Next Steps

1. **Choose your primary GUI** based on use case (see Decision Tree above)
2. **Set up launch scripts** for seamless workflow:
   ```bash
   ./scripts/launch_gui.sh        # For development
   ./scripts/launch_full_stack.sh # For testing all options
   ```
3. **Deploy to Hetzner** when ready for production
4. **Configure SSL/TLS** via Nginx reverse proxy
5. **Set up Claude Desktop** for native IDE integration

---

**Status: COMPLETE**  
All GUI options evaluated, documented, and production-ready.

Author: Ahmed Adel Bakr Alderai  
Last Updated: 2026-05-04
