# Loom GUI Quick Start Guide

**Choose your interface and get started in 2 minutes.**

---

## Option A: React Dashboard (Recommended)

### 1-Minute Setup

```bash
# Terminal 1: Start Loom server
cd /Users/aadel/projects/loom
loom serve

# Terminal 2: Start dashboard
./scripts/launch_gui.sh

# Open browser → http://localhost:5173
```

### What You'll See

- **Tool Search:** Search bar at top to find tools by name
- **Categories:** Browse 641 tools organized by category
- **Test Tools:** Click any tool to fill parameters and execute
- **Results:** View formatted output with syntax highlighting
- **History:** See all recent tool calls and their results
- **Analytics:** View performance metrics and cost estimates

### First Steps

1. Search for "fetch"
2. Click `research_fetch`
3. Fill in URL: `https://example.com`
4. Click "Execute"
5. View results in formatted panel

---

## Option B: Swagger UI (Fastest API Testing)

### Instant Setup

```bash
# Start server
loom serve

# Open browser
open http://localhost:8787/docs
```

### Try a Tool

1. Scroll down to find `research_fetch`
2. Click the tool name to expand it
3. Click "Try it out" button
4. Fill in parameters:
   ```json
   {
     "url": "https://example.com",
     "timeout": 30
   }
   ```
5. Click "Execute"
6. View response below

### Pro Tip

Press `Ctrl+F` (or `Cmd+F` on Mac) to search for specific tools in Swagger UI.

---

## Option C: Redoc Documentation

### View API Docs

```bash
# Start server
loom serve

# Open browser
open http://localhost:8787/redoc
```

### Features

- Clean, readable API documentation
- Search across all tools
- Schema definitions
- Parameter descriptions
- Example responses

**Best for:** Team reference and documentation sharing

---

## Option D: Full Stack (All at Once)

### One-Command Everything

```bash
cd /Users/aadel/projects/loom
./scripts/launch_full_stack.sh
```

This starts:
- ✓ MCP Server (8787)
- ✓ React Dashboard (5173)
- ✓ Swagger UI (8787/docs)
- ✓ Redoc (8787/redoc)

Then access any interface:
- http://localhost:5173 → Dashboard
- http://localhost:8787/docs → Swagger
- http://localhost:8787/redoc → Redoc

---

## Option E: CLI (Command Line)

### No Browser Needed

```bash
# List available tools
loom tools --search "fetch"

# Execute a tool
loom fetch --url "https://example.com" --json

# Get help
loom fetch --help
```

---

## Common Tasks

### Find a Specific Tool

**Dashboard:** Use search box at top
**Swagger:** Ctrl+F to find in page
**CLI:** `loom tools --search "keyword"`

### Test a Tool

**Dashboard:**
1. Click tool name
2. Fill parameters
3. Click "Execute"

**Swagger:**
1. Click "Try it out"
2. Fill parameters
3. Click "Execute"

**CLI:**
```bash
loom <tool-name> <params>
```

### View API Documentation

**Swagger:** http://localhost:8787/docs (interactive)
**Redoc:** http://localhost:8787/redoc (read-only)
**JSON:** http://localhost:8787/openapi.json (raw spec)

### Export Results

**Dashboard:** Click "Export" → Choose format (JSON/CSV/PDF)
**CLI:** Use `--json` or `--csv` flag
**Swagger:** Copy/paste from response panel

---

## Troubleshooting

### "Cannot connect to server"

```bash
# Verify server is running
curl http://localhost:8787/health

# If not running, start it
loom serve
```

### "Tools not showing in Swagger"

```bash
# Check OpenAPI spec
curl http://localhost:8787/openapi.json | jq '.paths | length'

# Should show ~641 tools
```

### "Dashboard won't load"

```bash
# Check npm dependencies
cd /Users/aadel/projects/loom/dashboard
npm install

# Try again
npm run dev
```

### "Port already in use"

```bash
# Find what's using the port
lsof -i :5173  # For dashboard
lsof -i :8787  # For server

# Kill the process
kill -9 <PID>
```

---

## Keyboard Shortcuts

### Dashboard

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Search tools |
| `Ctrl+Enter` | Execute current tool |
| `Esc` | Close modal/results |

### Swagger UI

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` / `Cmd+F` | Search page |
| `Arrow keys` | Navigate results |
| `Enter` | Execute tool |

---

## Next Steps

1. **Choose your interface** (see options above)
2. **Start server:** `loom serve`
3. **Open dashboard/swagger** in browser
4. **Search for a tool** (e.g., "fetch", "search", "deep")
5. **Click and execute**
6. **View results**

That's it! You're ready to use all 641 Loom tools.

---

## Learn More

- **Full Guide:** See `docs/GUI_OPTIONS_AND_INTEGRATION.md`
- **API Reference:** See `docs/API_REFERENCE.md`
- **Tool Catalog:** See `docs/TOOL_CATALOG_GUIDE.md`

---

**Status: READY FOR USE**

Author: Ahmed Adel Bakr Alderai  
Last Updated: 2026-05-04
