# Integrating Loom with Claude Code

Register Loom as an MCP server in Claude Code to access 23 research tools (search, fetch, scrape, LLM, sessions, etc.) from within your Claude Code or Claude Desktop conversations.

## Local Setup (Recommended for macOS)

If you're running Loom locally on your Mac:

1. **Install Loom**:
   ```bash
   pip install loom-mcp
   loom install-browsers
   loom serve &  # Start in background
   ```

2. **Edit `~/.claude/settings.json`**:
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

3. **Restart Claude Code** and use the research tools.

## Remote Setup with SSH Forwarding

If you're running Loom on a remote server (e.g., Hetzner), use SSH port forwarding to access it securely from Claude Code on your Mac.

### 1. Create an SSH Tunnel

In a terminal, create a persistent tunnel:

```bash
ssh -L 127.0.0.1:8787:127.0.0.1:8787 user@remote-server.com
```

This forwards your Mac's local port 8787 to the remote Loom server's 127.0.0.1:8787 (which only listens locally on the remote box).

### 2. Register with Claude Code

Edit `~/.claude/settings.json`:

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

### 3. Keep SSH Tunnel Persistent

The tunnel must stay open. Use a macOS LaunchAgent for background persistence.

Create `~/Library/LaunchAgents/com.user.loom-ssh-forward.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.loom-ssh-forward</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-N</string>
        <string>-L</string>
        <string>127.0.0.1:8787:127.0.0.1:8787</string>
        <string>-o</string>
        <string>ServerAliveInterval=60</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
        <string>user@remote-server.com</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/loom-ssh-forward.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/loom-ssh-forward.err</string>
</dict>
</plist>
```

Load it (runs on next login; or manually start now):

```bash
launchctl load ~/Library/LaunchAgents/com.user.loom-ssh-forward.plist
launchctl start com.user.loom-ssh-forward  # Start immediately
```

Verify it's active:

```bash
launchctl list | grep loom
lsof -i :8787  # Should show ssh listening on 8787
```

Check logs if needed:

```bash
tail -f /tmp/loom-ssh-forward.log
```

To stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.user.loom-ssh-forward.plist
```

The LaunchAgent will auto-restart if the SSH connection drops, keeping the tunnel alive.

## Docker + Claude Code

If running Loom in Docker, register it the same way:

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

Start the container:

```bash
docker run -p 127.0.0.1:8787:8787 ghcr.io/aadelb/loom:latest
```

Or with docker-compose:

```bash
cd deploy/docker && docker-compose up -d
```

Verify it's running:

```bash
curl -X POST http://127.0.0.1:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
```

## Troubleshooting

### Claude Code doesn't detect Loom

1. **Verify Loom is running**:
   ```bash
   curl -X POST http://127.0.0.1:8787/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
   ```
   Should return a JSON response with `result.tools`.

2. **Validate `~/.claude/settings.json` syntax**:
   ```bash
   python3 -m json.tool ~/.claude/settings.json
   ```

3. **Restart Claude Code** — it only reads the config file at startup.

4. **Verify registration**:
   ```bash
   claude mcp list
   ```
   Should show `loom` with 23+ tools.

### SSH tunnel keeps disconnecting

The LaunchAgent plist already includes keep-alive settings. To debug:

```bash
# Check if tunnel is running
lsof -i :8787

# Check logs
tail -f /tmp/loom-ssh-forward.err
```

If it's dropping frequently, manually restart it:

```bash
launchctl stop com.user.loom-ssh-forward
launchctl start com.user.loom-ssh-forward
```

Or test with a manual SSH connection first:

```bash
ssh -N -L 127.0.0.1:8787:127.0.0.1:8787 user@remote-server.com
# Leave this open in a terminal; test curl in another terminal
curl http://127.0.0.1:8787/mcp
```

### "Connection refused"

1. **Is the tunnel open?**
   ```bash
   lsof -i :8787
   ```

2. **Is Loom running on the remote box?**
   ```bash
   ssh user@remote-server.com "sudo systemctl status loom"
   ```

3. **Is the remote firewall blocking port 8787?**
   ```bash
   ssh user@remote-server.com "sudo ufw status"
   ```

### MCP endpoint timeouts

Loom can take time to start (Playwright/Camoufox initialization). If you see timeouts:

- **Local:** Wait 5–10 seconds after starting; health check grace period is 30–40 seconds
- **Remote:** Same; check `sudo journalctl -u loom -f` to watch startup

## Security

- **SSH tunnel:** Encrypted end-to-end; traffic to your local port 8787 is tunneled securely to the remote server
- **Localhost-only:** Loom binds to 127.0.0.1:8787 on the remote box (not exposed to the internet), and your Mac's port 8787 also only accepts local connections (unless you explicitly change it)
- **API keys:** Stored in environment or `.env` on the remote server; never transmitted to Claude Code or your Mac
- **Sessions:** Browser profiles and cookies stay on the remote server; Claude Code never sees them directly

This is secure enough for macOS local dev + remote server workflows. For production cloud access, add a reverse proxy with TLS and basic auth.

## Related Documentation

- [docs/installation.md](../installation.md) — Installation options
- [docs/deployment/docker.md](docker.md) — Docker deployment
- [docs/deployment/systemd.md](systemd.md) — systemd service
- [docs/deployment/kubernetes.md](kubernetes.md) — Kubernetes deployment
- [docs/tools/research_sessions.md](../tools/research_sessions.md) — Session management
