# Email Tool Results Script

Automated health check script that runs Loom status tools and emails results.

## Overview

`email_tool_results.py` is a monitoring utility that:
- Runs 13 critical Loom status/health tools in parallel
- Collects execution times and results
- Generates a formatted health report
- Sends results via email (Gmail SMTP)

## Usage

### Local (Mac)

```bash
cd /Users/aadel/projects/loom
python3 scripts/email_tool_results.py
```

### Remote (Hetzner)

```bash
ssh hetzner "cd /opt/research-toolbox && python3 scripts/email_tool_results.py"
```

Or with explicit path:

```bash
scp scripts/email_tool_results.py hetzner:/tmp/
ssh hetzner "cd /opt/research-toolbox && python3 /tmp/email_tool_results.py"
```

## Tools Tested

The script runs the following status/health tools:

1. **research_cache_stats** — Cache system statistics
2. **research_circuit_status** — Circuit breaker state
3. **research_quota_status** — API quota usage
4. **research_registry_status** — Live registry status
5. **research_breaker_status** — Circuit breaker detailed status
6. **research_memory_status** — Memory usage metrics
7. **research_ratelimit_status** — Rate limiter state
8. **research_queue_status** — Request queue statistics
9. **research_scheduler_status** — Job scheduler state
10. **research_key_status** — Key rotation status
11. **research_deploy_status** — Deployment system status
12. **research_log_stats** — Logging statistics
13. **research_tor_status** — Tor network status

## Report Format

Example report sections:

```
Loom Tool Health Check Results
============================================================
Timestamp: 2026-05-04 18:10:37
Total Tools: 13
OK: 13
Errors: 0
Not Found: 0

Detailed Results:
------------------------------------------------------------
✓ research_cache_stats: OK (2ms, returned dict)
✓ research_circuit_status: OK (0ms, returned dict)
...

Performance:
Total Time: 425ms
Average: 32ms per successful tool

Environment:
Python: 3.12.8
Platform: linux
Loom Root: /opt/research-toolbox
```

## Email Configuration

The script requires SMTP credentials. On Hetzner, credentials are loaded from:

```bash
~/.claude/resources.env
```

Required environment variables:
- `SMTP_USER` — Gmail address (e.g., `ahmedalderai91@gmail.com`)
- `SMTP_APP_PASSWORD` — Gmail app-specific password

Or fallback:
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`

## Dependencies

Ensure these packages are installed:

```bash
pip install -e ".[all]"  # Full installation with extras
```

Key dependencies:
- `httpx` — HTTP client
- `pydantic` — Data validation
- `psutil` — System metrics
- `structlog` — Structured logging

## Scheduling

To run periodically on Hetzner, add to crontab:

```bash
# Every 6 hours
0 */6 * * * cd /opt/research-toolbox && python3 scripts/email_tool_results.py >> ~/.loom/health_checks.log 2>&1
```

Or use systemd timer:

```ini
# /etc/systemd/user/loom-health-check.timer
[Unit]
Description=Loom Health Check Timer
After=network-online.target

[Timer]
OnBootSec=1h
OnUnitActiveSec=6h
Unit=loom-health-check.service

[Install]
WantedBy=timers.target

# /etc/systemd/user/loom-health-check.service
[Unit]
Description=Loom Health Check
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/research-toolbox
ExecStart=/usr/bin/python3 scripts/email_tool_results.py
```

Enable with:

```bash
systemctl --user enable loom-health-check.timer
systemctl --user start loom-health-check.timer
```

## Exit Codes

- `0` — Success, email sent
- `1` — Failure, email not sent or tools failed

## Troubleshooting

### Email not sending

Check SMTP credentials:

```bash
echo $SMTP_USER $SMTP_APP_PASSWORD
```

Test manually:

```python
from loom.tools.email_report import research_email_report
import asyncio

result = asyncio.run(research_email_report(
    to="test@example.com",
    subject="Test",
    body="Test message"
))
print(result)
```

### Import errors

Ensure loom is installed:

```bash
cd /opt/research-toolbox && pip install -e .
```

Check Python path:

```bash
python3 -c "import sys; print('\n'.join(sys.path))"
```

### Tools failing

Individual tool failures are non-fatal. Check specific tool:

```python
from loom.tools.cache_mgmt import research_cache_stats
result = research_cache_stats()
print(result)
```

## Implementation Details

- **Parallel execution**: All 13 tools run concurrently via `asyncio.gather()`
- **Type handling**: Automatically detects sync vs async functions
- **Error isolation**: Single tool failure doesn't halt report generation
- **Path detection**: Auto-detects Hetzner vs local environment
- **Environment loading**: Parses `~/.claude/resources.env` for SMTP config

## Performance

Typical execution times on Hetzner:

| Tool | Time |
|------|------|
| research_deploy_status | 170-230ms |
| research_registry_status | 67-148ms |
| research_log_stats | 1-59ms |
| research_tor_status | 58ms |
| Others | <5ms |

**Total runtime**: ~425ms for full suite

## Author

Author: Ahmed Adel Bakr Alderai

Created: 2026-05-04
