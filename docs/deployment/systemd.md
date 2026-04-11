# Running Loom as a systemd Service

Run Loom as a persistent, auto-restarting systemd service on Linux. This guide covers setup, systemd directives, and troubleshooting.

## Prerequisites

- Linux system with systemd (Ubuntu 18.04+, Debian 10+, RHEL 8+, etc.)
- Python 3.11+
- Virtual environment with Loom installed: `pip install loom-mcp[stealth]`
- Browsers installed: `python -m playwright install chromium firefox` (or use the install-browsers script if available)

## Step 1: Create a System User (Recommended)

```bash
sudo useradd -r -s /bin/bash -d /opt/loom loom
```

The `-r` flag creates a system user with no login shell; `-d /opt/loom` sets the home directory.

## Step 2: Prepare the Loom Directory

```bash
sudo mkdir -p /opt/loom/cache /opt/loom/logs /opt/loom/sessions /opt/loom/venv
sudo chown -R loom:loom /opt/loom
sudo chmod 755 /opt/loom
```

## Step 3: Install Loom in a Virtual Environment

```bash
sudo -u loom python3.11 -m venv /opt/loom/venv
sudo -u loom /opt/loom/venv/bin/pip install --upgrade pip
sudo -u loom /opt/loom/venv/bin/pip install loom-mcp[stealth]
```

This installs Loom with Camoufox and Botasaurus (stealth browser support).

## Step 4: Install Browsers

```bash
sudo -u loom /opt/loom/venv/bin/python -m playwright install chromium firefox
sudo -u loom /opt/loom/venv/bin/python -m camoufox fetch
```

This pre-downloads browser distributions to avoid startup delays.

## Step 5: Copy and Edit the systemd Unit

Copy the example file:

```bash
sudo cp deploy/systemd/loom.service.example /etc/systemd/system/loom.service
```

Edit it:

```bash
sudo nano /etc/systemd/system/loom.service
```

Update paths to match your setup. The example file provides:

```ini
[Unit]
Description=Loom MCP Research Server
Documentation=https://github.com/aadelb/loom
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=loom
Group=loom
WorkingDirectory=/opt/loom
EnvironmentFile=-/etc/loom/loom.env
Environment="PATH=/opt/loom/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="LOOM_PORT=8787"
Environment="LOOM_HOST=127.0.0.1"
ExecStart=/opt/loom/venv/bin/python -m loom.server
Restart=on-failure
RestartSec=10s
StartLimitInterval=60
StartLimitBurst=5
MemoryMax=16G
CPUQuota=400%
LimitNOFILE=65536
LimitNPROC=512
NoNewPrivileges=true
PrivateTmp=false
StandardOutput=journal
StandardError=journal
SyslogIdentifier=loom
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Key directives explained:

| Directive | Purpose |
|-----------|---------|
| `Type=simple` | Standard long-running service (Python -m loom.server blocks) |
| `Restart=on-failure` | Automatically restart if exit code != 0 |
| `RestartSec=10s` | Wait 10 seconds before restarting |
| `StartLimitInterval=60` + `StartLimitBurst=5` | Max 5 restarts per 60 seconds; after that, give up |
| `MemoryMax=16G` | Kill service if memory exceeds 16 GB |
| `CPUQuota=400%` | Limit to 4 CPU cores (400% = 4 * 100%) |
| `LimitNOFILE=65536` | Allow 65K open file descriptors (for many concurrent connections) |
| `LimitNPROC=512` | Allow 512 processes (Playwright spawns subprocesses) |
| `NoNewPrivileges=true` | Prevent service from gaining setuid/setgid privs |
| `PrivateTmp=false` | Keep `/tmp` shared with system (Playwright needs it for browser temp files) |
| `StandardOutput=journal` | Log to systemd journal (view with `journalctl`) |
| `TimeoutStopSec=30` | Grace period before SIGKILL on stop |

## Step 6: Create an Environment File (Optional)

If you prefer env vars in a file instead of the unit file:

```bash
sudo nano /etc/loom/loom.env
```

Example:

```bash
# Search providers
EXA_API_KEY=your_exa_key
TAVILY_API_KEY=your_tavily_key
FIRECRAWL_API_KEY=your_firecrawl_key

# LLM providers
NVIDIA_NIM_API_KEY=your_nim_key
NVIDIA_NIM_ENDPOINT=https://integrate.api.nvidia.com/v1
OPENAI_API_KEY=your_openai_key

# Service config
LOOM_HOST=127.0.0.1
LOOM_PORT=8787
LOOM_CACHE_DIR=/var/lib/loom/cache
LOOM_LOGS_DIR=/var/lib/loom/logs
LOOM_SESSIONS_DIR=/var/lib/loom/sessions
LOOM_LOG_LEVEL=INFO

# Tool config
SPIDER_CONCURRENCY=5
```

Protect it:

```bash
sudo chmod 600 /etc/loom/loom.env
sudo chown root:root /etc/loom/loom.env
```

## Step 7: Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable loom
sudo systemctl start loom
```

Verify it's running:

```bash
sudo systemctl status loom
```

Follow logs:

```bash
sudo journalctl -u loom -f
```

Test the endpoint:

```bash
curl -X POST http://127.0.0.1:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
```

## Common Commands

```bash
# Check status
sudo systemctl status loom

# View latest logs
sudo journalctl -u loom -n 50

# Follow logs in real-time
sudo journalctl -u loom -f

# View logs from last hour
sudo journalctl -u loom --since "1 hour ago"

# Restart the service
sudo systemctl restart loom

# Stop the service
sudo systemctl stop loom

# See all systemd properties
sudo systemctl show loom
```

## Troubleshooting

### Service won't start

Check systemd logs:

```bash
sudo journalctl -u loom -n 50
```

Common causes:

- **"No such file or directory"** — Check `WorkingDirectory`, `ExecStart`, `Environment` paths; verify venv path
- **"Browser not found"** — Run `sudo -u loom /opt/loom/venv/bin/python -m playwright install chromium firefox`
- **"Permission denied"** — Check file ownership: `sudo chown -R loom:loom /opt/loom`

Test manually:

```bash
sudo -u loom /opt/loom/venv/bin/python -m loom.server
```

### Service drops during heavy scraping

Increase memory limit in the unit file:

```ini
MemoryMax=32G
```

Then reload:

```bash
sudo systemctl daemon-reload && sudo systemctl restart loom
```

Check current memory usage:

```bash
ps aux | grep loom.server
```

### Port 8787 already in use

Find what's using it:

```bash
sudo lsof -i :8787
```

Change the port in the unit file:

```ini
Environment="LOOM_PORT=8788"
```

### Logs not appearing

Check journal storage:

```bash
sudo journalctl -u loom -n 20
```

If empty, check directory permissions:

```bash
sudo chown loom:loom /opt/loom/logs
sudo chmod 755 /opt/loom/logs
```

### Service exits with "exit code 1"

Check the Python error:

```bash
sudo journalctl -u loom -e
```

Common causes: missing API keys, bad config.json, disk full (cache directory).

## Uninstalling

```bash
sudo systemctl stop loom
sudo systemctl disable loom
sudo rm /etc/systemd/system/loom.service
sudo systemctl daemon-reload
sudo userdel loom
sudo rm -rf /opt/loom
```

## Related Documentation

- [docs/deployment/docker.md](docker.md) — Docker deployment
- [docs/deployment/kubernetes.md](kubernetes.md) — Kubernetes deployment
- [docs/deployment/claude-code-integration.md](claude-code-integration.md) — Claude Code setup
