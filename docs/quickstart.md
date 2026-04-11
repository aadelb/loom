# Quickstart — Get Loom Running in 5 Minutes

This guide walks you through installing Loom, starting the server, registering with Claude Code, and making your first research calls.

## Step 1: Install Loom

The recommended way to install Loom is from PyPI:

```bash
pip install loom-mcp
```

For browser-based scraping with stealth capabilities (Camoufox, Botasaurus), install the optional dependencies:

```bash
pip install "loom-mcp[stealth]"
```

For Anthropic Claude SDK support:

```bash
pip install "loom-mcp[anthropic]"
```

For everything (stealth + Anthropic + development tools):

```bash
pip install "loom-mcp[all]"
```

## Step 2: Install Browser Binaries

Loom uses Playwright and optional stealth libraries to fetch pages. Install browser binaries once:

```bash
loom install-browsers
```

This command downloads Chromium, Firefox, and Camoufox binaries (approximately 1.5 GB total). If you only need standard browser fetching without stealth:

```bash
playwright install chromium firefox
```

## Step 3: Start the MCP Server

Start the server in one terminal:

```bash
loom serve
```

You should see output similar to:

```
INFO:     Uvicorn running on http://127.0.0.1:8787
INFO:     MCP protocol on http://127.0.0.1:8787/mcp
```

The server listens on `http://127.0.0.1:8787/mcp` by default and is ready to accept MCP client connections.

## Step 4: Verify the Server is Running

Open another terminal and confirm the server is responding:

```bash
curl -sS http://127.0.0.1:8787/mcp \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
```

You should see a JSON response from the server. If the server doesn't respond, check that port 8787 is available (`lsof -i :8787`).

## Step 5: Register with Claude Code

Open your Claude Code settings file:

```bash
~/.claude/settings.json
```

Under the `mcpServers` key, add the Loom server configuration:

```json
{
  "mcpServers": {
    "loom": {
      "type": "http",
      "url": "http://127.0.0.1:8787/mcp"
    }
  }
}
```

Restart Claude Code. You should now see Loom's 23 tools available in the tool picker. Verify with:

```bash
claude mcp list
```

You should see `loom` in the list with 23 research tools.

## Step 6: Make Your First MCP Call

In Claude Code, use any of the 23 Loom tools. For example, fetch a web page:

```
"Use research_fetch to grab https://httpbin.org/html"
```

This returns a JSON object:

```json
{
  "url": "https://httpbin.org/html",
  "status": 200,
  "mode": "stealthy",
  "text": "<html>...",
  "html": "<html>...",
  "metadata": {
    "title": "...",
    "language": "en",
    "charset": "utf-8"
  },
  "cache_hit": false,
  "cached_at": null
}
```

## Step 7: Try the CLI

In a new terminal, use the `loom` CLI tool directly. Fetch a page:

```bash
loom fetch https://httpbin.org/html --mode http
```

Search the web:

```bash
loom search "prompt injection" --provider exa --n 5
```

Perform deep research (multi-step: search → fetch → analyze):

```bash
loom deep "what is SSRF" --depth 2
```

Extract markdown from a page:

```bash
loom markdown https://example.com --css "article"
```

## Step 8: Test with a Journey (Optional)

Loom includes a deterministic journey test that exercises all 23 tools. Run it with mocked fixtures (completes in ~30 seconds):

```bash
loom journey-test --fixtures tests/fixtures/journey --topic "test"
```

This generates a detailed `journey-out/report.md` showing which tools passed and which failed.

## Step 9: Set Up API Keys (Optional)

To use search and LLM features, configure API keys. Create a `.env` file in your working directory:

```bash
cat > .env << 'EOF'
# Search providers
EXA_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

# LLM providers (at least one required for llm tools)
NVIDIA_NIM_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Optional: Anthropic
ANTHROPIC_API_KEY=your_key_here
EOF
```

Then start the server with the environment loaded:

```bash
source .env && loom serve
```

## Next Steps

- See [docs/installation.md](installation.md) for platform-specific setup, Docker, and systemd
- See [docs/cli.md](cli.md) for complete CLI reference with all flags and examples
- See [docs/tools/](tools/) for detailed documentation of each MCP tool
- See [docs/deployment/](deployment/) for production deployment guides
- See [docs/providers/](providers/) for LLM and search provider setup

## Troubleshooting

**Server won't start**

Check that port 8787 is available:

```bash
lsof -i :8787
```

If port 8787 is in use, specify a different port:

```bash
loom serve --port 8788
```

**Claude Code doesn't see Loom**

After editing `~/.claude/settings.json`, restart Claude Code. Verify the server is running:

```bash
curl http://127.0.0.1:8787/mcp -X POST -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Check Claude Code logs in `~/.claude/logs/` for MCP connection errors.

**Fetch returns "url_rejected: blocked address"**

Loom blocks private IP ranges by default (10.0.0.0/8, 127.0.0.1, 169.254.169.254, etc.) for security. Verify the target URL resolves to a public address:

```bash
nslookup example.com
```

**"playwright: command not found" or browser errors**

Re-run the browser installation:

```bash
loom install-browsers
```

Or install manually:

```bash
playwright install chromium firefox
```

**LLM calls fail with "no provider available"**

Set at least one LLM provider API key:

```bash
export NVIDIA_NIM_API_KEY=your_key_here
loom serve
```

Or set `OPENAI_API_KEY` as a fallback. See [docs/providers/](providers/) for detailed setup instructions for each provider.

**High memory usage or hanging requests**

Check the current config:

```bash
loom config get
```

Lower the spider concurrency limit if running many parallel fetches:

```bash
loom config set SPIDER_CONCURRENCY 3
```

Increase request timeout if fetches are timing out:

```bash
loom config set EXTERNAL_TIMEOUT_SECS 60
```
