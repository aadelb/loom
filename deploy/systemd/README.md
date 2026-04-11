# systemd Deployment Guide for Loom

This directory contains a systemd service unit template for running Loom as a background service on Linux systems.

## Prerequisites

- Linux system with systemd
- Python 3.11+ installed
- Loom installed in a virtualenv (recommended: `/opt/loom/venv`)
- User `loom` exists (created during installation)
- Directories `/var/lib/loom/{cache,logs,sessions}` exist with proper permissions

## Installation

### 1. Create the `loom` User

```bash
sudo useradd -r -s /bin/false -d /var/lib/loom loom
```

Or if you want to use your own user:

```bash
sudo useradd -r -s /bin/bash -d /var/lib/loom -m loom
```

### 2. Create Required Directories

```bash
sudo mkdir -p /var/lib/loom/{cache,logs,sessions}
sudo mkdir -p /etc/loom
sudo chown -R loom:loom /var/lib/loom
sudo chmod 750 /var/lib/loom
```

### 3. Install Loom in a Virtualenv

```bash
# As root or with sudo
sudo -u loom python3 -m venv /opt/loom/venv
sudo -u loom /opt/loom/venv/bin/pip install --upgrade pip wheel
sudo -u loom /opt/loom/venv/bin/pip install loom-mcp[stealth]

# Install browsers
sudo -u loom /opt/loom/venv/bin/playwright install chromium firefox
sudo -u loom /opt/loom/venv/bin/python -m camoufox fetch
```

### 4. Copy Configuration

```bash
# Copy environment template
sudo cp deploy/.env.example /etc/loom/loom.env
sudo chown loom:loom /etc/loom/loom.env
sudo chmod 640 /etc/loom/loom.env

# Edit with your API keys
sudo nano /etc/loom/loom.env
```

### 5. Install the systemd Unit

```bash
sudo cp deploy/systemd/loom.service.example /etc/systemd/system/loom.service
```

Optionally, customize the unit file for your environment:

```bash
sudo nano /etc/systemd/system/loom.service
```

Key settings to verify:

- `User=loom` — should match the user created in step 1
- `WorkingDirectory=/opt/loom` — where Loom is installed
- `ExecStart=...` — path to the Python executable and module

### 6. Reload systemd Configuration

```bash
sudo systemctl daemon-reload
```

### 7. Enable the Service

```bash
sudo systemctl enable loom
```

This ensures Loom starts automatically on boot.

### 8. Start the Service

```bash
sudo systemctl start loom
```

### 9. Verify the Service is Running

```bash
sudo systemctl status loom
```

Expected output:

```
● loom.service - Loom MCP Research Server
   Loaded: loaded (/etc/systemd/system/loom.service; enabled; vendor preset: enabled)
   Active: active (running) since ...
```

## Managing the Service

### View Status

```bash
sudo systemctl status loom
```

### View Logs

```bash
# Last 50 lines, follow mode
sudo journalctl -u loom -f -n 50

# Last 24 hours
sudo journalctl -u loom --since "24 hours ago"

# Errors only
sudo journalctl -u loom -p err
```

### Restart the Service

```bash
sudo systemctl restart loom
```

### Stop the Service

```bash
sudo systemctl stop loom
```

### Disable from Auto-start

```bash
sudo systemctl disable loom
```

## Accessing the Service

Once running, the MCP server is available at:

```
http://127.0.0.1:8787/mcp
```

### Test with curl

```bash
curl -X POST http://127.0.0.1:8787/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2024-11-05",
      "capabilities":{},
      "clientInfo":{"name":"test","version":"1"}
    }
  }'
```

### Test with Claude Code or MCP Client

Configure your MCP client to connect to `http://127.0.0.1:8787/mcp`.

## Configuration

Edit `/etc/loom/loom.env` to set:

- API keys for search providers (Exa, Tavily, Firecrawl, Brave)
- LLM provider credentials (NVIDIA NIM, OpenAI, Anthropic)
- Service settings (port, log level, cache TTL)

After changing configuration:

```bash
sudo systemctl restart loom
```

Check that the new configuration was loaded:

```bash
sudo journalctl -u loom -n 10
```

## Troubleshooting

### Service won't start

Check for errors:

```bash
sudo systemctl status loom
sudo journalctl -u loom -n 30
```

Common issues:

- **File not found error** — verify the Python path in `ExecStart` is correct
- **Permission denied** — check `/var/lib/loom` ownership: `ls -ld /var/lib/loom`
- **Port already in use** — verify no other process uses port 8787: `sudo lsof -i :8787`

### Service crashes after a few seconds

Check the logs:

```bash
sudo journalctl -u loom -n 50 --no-pager
```

Common causes:

- Invalid API keys in `/etc/loom/loom.env`
- Browser installation failed — re-run: `sudo -u loom /opt/loom/venv/bin/playwright install`
- Missing disk space — check: `df -h /var/lib/loom`

### High memory or CPU usage

Monitor in real-time:

```bash
watch 'systemctl status loom | grep CPU'
```

Adjust limits in the service file:

```bash
sudo nano /etc/systemd/system/loom.service
# Edit MemoryMax and CPUQuota
sudo systemctl daemon-reload
sudo systemctl restart loom
```

### Health check failing

The service includes a health check. Monitor it:

```bash
curl http://127.0.0.1:8787/mcp
```

If failing, check logs and verify the service is actually running:

```bash
ps aux | grep loom.server
```

## Security

The systemd unit is configured with security best practices:

- **NoNewPrivileges=true** — prevents privilege escalation
- **PrivateTmp=false** — allows temporary files (needed by Playwright)
- **File limits** — 65536 open files to support many concurrent requests
- **Memory limit** — capped at 16 GB to prevent OOM scenarios
- **CPU limit** — capped at 400% (4 cores) to prevent runaway computation

For production deployments, additionally consider:

- Running behind a reverse proxy (Caddy, nginx) for TLS/authentication
- Restricting network access via firewall rules
- Monitoring with Prometheus/Grafana
- Regular log rotation via logrotate

## Advanced Configuration

### Using a Custom virtualenv Path

If you installed Loom elsewhere, update the `ExecStart` line:

```bash
sudo nano /etc/systemd/system/loom.service
# Change ExecStart=/custom/path/venv/bin/python -m loom.server
sudo systemctl daemon-reload
sudo systemctl restart loom
```

### Running as Your User (Not Recommended for Production)

If you want to run as your own user instead of creating a `loom` user:

```bash
sudo nano /etc/systemd/system/loom.service
# Change User=yourname
# Change WorkingDirectory=/home/yourname/loom
sudo systemctl daemon-reload
sudo systemctl restart loom
```

### Custom Logging

By default, logs go to journalctl. To also write to a file:

```bash
sudo nano /etc/systemd/system/loom.service
# Add or modify StandardOutput and StandardError
# Example:
# StandardOutput=journal
# StandardError=journal
# SyslogIdentifier=loom

sudo systemctl daemon-reload
sudo systemctl restart loom
```

View file logs:

```bash
sudo tail -f /var/lib/loom/logs/loom.log
```

### Running Multiple Instances

To run multiple Loom instances on different ports:

```bash
sudo cp /etc/systemd/system/loom.service /etc/systemd/system/loom@8788.service
sudo nano /etc/systemd/system/loom@8788.service
# Edit: ExecStart with --port 8788
# Edit: EnvironmentFile=/etc/loom/loom.8788.env (for separate configs)

sudo systemctl daemon-reload
sudo systemctl start loom@8788
```

## Uninstallation

To remove Loom and its configuration:

```bash
# Stop and disable the service
sudo systemctl stop loom
sudo systemctl disable loom

# Remove the unit file
sudo rm /etc/systemd/system/loom.service
sudo systemctl daemon-reload

# Remove configuration and data
sudo rm -rf /etc/loom /var/lib/loom

# Remove the user (optional)
sudo userdel loom

# Remove the virtualenv (optional)
sudo rm -rf /opt/loom
```
