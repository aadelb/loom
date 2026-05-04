# Loom Production Deployment Guide

This directory contains production-ready systemd and logrotate configurations for deploying Loom MCP Research Server on Linux systems with systemd.

## Contents

- **loom.service** — systemd service unit (production-hardened)
- **loom-logrotate.conf** — logrotate configuration for log rotation and retention
- **install.sh** — Automated installation script (creates user, directories, enables service)
- **README.md** — This file

## Quick Start

### Automated Installation (Recommended)

```bash
sudo bash deploy/install.sh
```

This script will:
1. Create the `loom` system user and group
2. Set up required directories with proper permissions
3. Install the systemd service unit
4. Configure log rotation
5. Enable the service for auto-start on boot

### Manual Installation

If you prefer manual setup or need to customize paths:

```bash
# 1. Create user
sudo useradd --system --shell /usr/sbin/nologin \
  --home-dir /var/lib/loom --create-home loom

# 2. Create directories
sudo mkdir -p /var/log/loom /var/lib/loom/{cache,sessions}
sudo mkdir -p /etc/loom
sudo chown -R loom:loom /var/log/loom /var/lib/loom
sudo chmod 750 /var/lib/loom /var/log/loom

# 3. Copy service file
sudo cp deploy/loom.service /etc/systemd/system/loom.service

# 4. Install logrotate config
sudo cp deploy/loom-logrotate.conf /etc/logrotate.d/loom

# 5. Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable loom
```

## Configuration

### Environment Variables

Create `/etc/loom/loom.env` with your API keys and configuration:

```bash
# API Keys - Search Providers
EXA_API_KEY=your_exa_key_here
TAVILY_API_KEY=your_tavily_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here
BRAVE_API_KEY=your_brave_key_here

# API Keys - LLM Providers
GROQ_API_KEY=your_groq_key_here
NVIDIA_NIM_API_KEY=your_nvidia_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
MOONSHOT_API_KEY=your_moonshot_key_here

# Service Settings
LOOM_HOST=127.0.0.1
LOOM_PORT=8787
LOOM_LOG_LEVEL=INFO
TOR_ENABLED=false
TOR_SOCKS5_PROXY=127.0.0.1:9050
```

Set restrictive permissions:
```bash
sudo chmod 640 /etc/loom/loom.env
sudo chown loom:loom /etc/loom/loom.env
```

### Service Configuration

Edit `/etc/systemd/system/loom.service` if you need to customize:

- `User=loom` — System user running the service
- `WorkingDirectory=/opt/research-toolbox` — Installation directory
- `MemoryMax=8G` — Memory limit (adjust for your hardware)
- `CPUQuota=400%` — CPU limit (4 cores; adjust as needed)

After editing, reload systemd:
```bash
sudo systemctl daemon-reload
sudo systemctl restart loom
```

### Log Rotation

Logrotate is configured to:
- **Rotate application logs** (`/var/log/loom/*.log`) daily, keep 30 days
- **Rotate SQLite WAL files** (`/var/lib/loom/**/*.wal`) weekly, keep 4 weeks
- **Rotate SQLite journal files** weekly, keep 7 days
- **Rotate audit logs** monthly, keep 12 months

Manually trigger rotation:
```bash
sudo logrotate -f /etc/logrotate.d/loom
```

Test configuration (dry-run):
```bash
sudo logrotate -d /etc/logrotate.d/loom
```

## Operations

### Start the Service

```bash
sudo systemctl start loom
```

### Stop the Service

```bash
sudo systemctl stop loom
```

### Restart the Service

```bash
sudo systemctl restart loom
```

### View Service Status

```bash
sudo systemctl status loom
```

Expected output:
```
● loom.service - Loom MCP Research Server
   Loaded: loaded (/etc/systemd/system/loom.service; enabled; vendor preset: enabled)
   Active: active (running) since Sat 2026-05-04 12:34:56 UTC; 2min 30s ago
   Main PID: 12345 (python)
   Tasks: 42
   Memory: 256.5M
   CPU: 1.2s
```

### View Logs

```bash
# Real-time (follow mode)
sudo journalctl -u loom -f

# Last 100 lines
sudo journalctl -u loom -n 100

# Last 24 hours
sudo journalctl -u loom --since "24 hours ago"

# Only errors
sudo journalctl -u loom -p err

# Export to file
sudo journalctl -u loom > /tmp/loom_logs.txt
```

### Check Resource Usage

```bash
# Memory and CPU
watch systemctl status loom

# More detailed
ps aux | grep -E "(loom|PID)"
```

### Test Service Health

```bash
# Check if port is listening
sudo netstat -tlnp | grep 8787

# Test HTTP endpoint
curl -I http://127.0.0.1:8787/health

# Full MCP initialization test
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

## Troubleshooting

### Service Won't Start

1. Check for errors:
   ```bash
   sudo systemctl status loom
   sudo journalctl -u loom -n 50
   ```

2. Verify file permissions:
   ```bash
   ls -ld /var/lib/loom /var/log/loom
   ls -l /etc/systemd/system/loom.service
   ```

3. Check if port is already in use:
   ```bash
   sudo lsof -i :8787
   ```

4. Verify the virtualenv path exists:
   ```bash
   ls -la /opt/research-toolbox/venv/bin/python
   ```

### High Memory or CPU Usage

1. Monitor in real-time:
   ```bash
   watch -n 1 'systemctl status loom | grep -E "(Memory|CPU)"'
   ```

2. Check which tool is consuming resources:
   ```bash
   sudo journalctl -u loom -f | grep -i "memory\|cpu"
   ```

3. Adjust limits in service file:
   ```bash
   sudo nano /etc/systemd/system/loom.service
   # Change MemoryMax and CPUQuota
   sudo systemctl daemon-reload
   sudo systemctl restart loom
   ```

### Service Crashes Repeatedly

1. Check log for error patterns:
   ```bash
   sudo journalctl -u loom | tail -50
   ```

2. Common causes:
   - **Missing API keys** → Check `/etc/loom/loom.env`
   - **Invalid configuration** → Check syntax and permissions
   - **Browser installation issue** → Re-install Playwright: `python -m playwright install`
   - **Disk space full** → Check: `df -h /var/lib/loom /var/log/loom`

3. If still failing, check with Python directly:
   ```bash
   sudo -u loom /opt/research-toolbox/venv/bin/python -c "from loom import server; print('OK')"
   ```

### Log Files Growing Too Large

1. Check current log sizes:
   ```bash
   du -sh /var/log/loom/*
   ```

2. Manually rotate logs:
   ```bash
   sudo logrotate -f /etc/logrotate.d/loom
   ```

3. Check logrotate configuration:
   ```bash
   sudo logrotate -d /etc/logrotate.d/loom
   ```

4. Reduce log level if needed:
   ```bash
   sudo nano /etc/loom/loom.env
   # Set LOOM_LOG_LEVEL=WARN
   sudo systemctl restart loom
   ```

## Security Hardening

### Service-Level Security

The systemd unit includes several security hardening measures:

```ini
NoNewPrivileges=true      # Prevent privilege escalation
PrivateTmp=false          # Allow /tmp for Playwright (can be set to true if using PrivateTmp=true)
StandardOutput=journal    # Logs go to systemd journal (not world-readable by default)
```

### Additional Hardening (Optional)

For enhanced security, add to service file:

```ini
# Filesystem restrictions
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/loom /var/log/loom /var/cache/loom

# Process restrictions
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

# Device restrictions
PrivateDevices=yes

# Capability restrictions
AmbientCapabilities=
CapabilityBoundingSet=
```

**Note:** Strict security settings may impact Playwright/browser functionality. Test after applying.

### Network Security

For production deployments:

1. **Use a reverse proxy** (nginx, Caddy):
   ```nginx
   server {
       listen 443 ssl http2;
       server_name loom.example.com;
       
       location / {
           proxy_pass http://127.0.0.1:8787;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. **Enable firewall rules**:
   ```bash
   sudo ufw allow 443/tcp from 10.0.0.0/8  # TLS from internal networks
   sudo ufw deny 8787/tcp                   # Block direct access
   ```

3. **Add authentication** at reverse proxy level (OAuth, mTLS, API keys)

## Monitoring

### Prometheus Metrics

If Prometheus support is enabled, metrics are available at:
```
http://127.0.0.1:8787/metrics
```

### Systemd Timer for Health Checks

Create `/etc/systemd/system/loom-health-check.timer`:
```ini
[Unit]
Description=Loom Health Check
Requires=loom-health-check.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/loom-health-check.service`:
```ini
[Unit]
Description=Loom Health Check Service
After=loom.service

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -f http://127.0.0.1:8787/health || systemctl restart loom
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable loom-health-check.timer
sudo systemctl start loom-health-check.timer
```

### Grafana Dashboard

Import a Grafana dashboard for Loom metrics:

1. Add Prometheus data source pointing to `http://localhost:9090`
2. Create panels for:
   - `loom_tool_calls_total` — Tool invocations
   - `loom_tool_duration_seconds` — Tool execution time
   - `loom_tool_errors_total` — Tool failures

## Uninstallation

To remove Loom from the system:

```bash
# Stop and disable the service
sudo systemctl stop loom
sudo systemctl disable loom

# Remove systemd files
sudo rm /etc/systemd/system/loom.service
sudo rm /etc/logrotate.d/loom
sudo systemctl daemon-reload

# Remove configuration and data
sudo rm -rf /etc/loom /var/lib/loom /var/log/loom

# Remove user (optional)
sudo userdel loom

# Remove virtualenv (optional)
sudo rm -rf /opt/research-toolbox
```

## Upgrading Loom

1. Stop the service:
   ```bash
   sudo systemctl stop loom
   ```

2. Backup current installation:
   ```bash
   sudo cp -r /opt/research-toolbox /opt/research-toolbox.backup
   ```

3. Upgrade via pip:
   ```bash
   sudo -u loom /opt/research-toolbox/venv/bin/pip install --upgrade loom-mcp[stealth]
   ```

4. Re-install browsers (if needed):
   ```bash
   sudo -u loom /opt/research-toolbox/venv/bin/playwright install
   ```

5. Restart the service:
   ```bash
   sudo systemctl start loom
   ```

6. Verify:
   ```bash
   sudo journalctl -u loom -n 20
   curl http://127.0.0.1:8787/health
   ```

## Performance Tuning

### Memory Configuration

Adjust based on workload:

```bash
# Small (1-2 concurrent users)
MemoryMax=2G

# Medium (5-10 concurrent users)
MemoryMax=4G

# Large (20+ concurrent users)
MemoryMax=8G

# Very Large (50+ concurrent users)
MemoryMax=16G
```

### CPU Configuration

Adjust based on available cores:

```bash
# Single core
CPUQuota=100%

# Dual core
CPUQuota=200%

# Quad core (default)
CPUQuota=400%

# Octa core
CPUQuota=800%
```

### Connection Limits

For high-concurrency scenarios, increase file descriptor limits:

```ini
[Service]
LimitNOFILE=262144
LimitNPROC=1024
```

### Cache Configuration

Edit `/etc/loom/loom.env`:

```bash
# Cache settings
LOOM_CACHE_DIR=/var/lib/loom/cache
CACHE_TTL=3600
CACHE_MAX_SIZE=10GB
```

## Reference

### Service File Location
- System service: `/etc/systemd/system/loom.service`

### Configuration File Locations
- Environment: `/etc/loom/loom.env`

### Data Directories
- Home/runtime: `/var/lib/loom/`
- Logs: `/var/log/loom/`
- Cache: `/var/lib/loom/cache/`
- Sessions: `/var/lib/loom/sessions/`

### Logs
- Systemd journal: `sudo journalctl -u loom -f`
- Audit logs: `/var/log/loom/audit.log`

### Key Commands
- Status: `sudo systemctl status loom`
- Start: `sudo systemctl start loom`
- Restart: `sudo systemctl restart loom`
- Logs: `sudo journalctl -u loom -f`
- Health: `curl http://127.0.0.1:8787/health`

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u loom -n 50`
2. Review configuration: `sudo cat /etc/loom/loom.env | grep -v '^#'`
3. Test connectivity: `curl -v http://127.0.0.1:8787/health`
4. Check resources: `systemctl status loom`
