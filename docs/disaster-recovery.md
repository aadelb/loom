# Disaster Recovery Plan (DRP)

## Overview

This document defines the Loom MCP server disaster recovery procedures, objectives, and runbooks for operational continuity. The plan covers recovery from server crashes, data corruption, complete infrastructure loss, and security incidents.

**Last Updated:** 2026-05-04  
**Next Review:** 2026-08-04  
**Version:** 1.0

---

## Recovery Objectives

### Recovery Time Objective (RTO)

**RTO: 15 minutes** (maximum acceptable downtime)

| Scenario | Target RTO | Notes |
|----------|-----------|-------|
| Server restart | 2 minutes | systemctl restart + health check |
| Database restore from backup | 10 minutes | Latest full backup + recovery validation |
| Full server redeployment | 15 minutes | Hetzner provision + git deploy + restore backups |
| API key rotation | 5 minutes | Update environment, restart service |
| Emergency failover | 8 minutes | Switch to standby (if available) |

### Recovery Point Objective (RPO)

**RPO: 24 hours** (maximum acceptable data loss)

| Data Type | Backup Frequency | Retention |
|-----------|------------------|-----------|
| SQLite databases | Daily (00:00 UTC) | 30 days rolling |
| Application config | On change + daily | 60 days rolling |
| Session state | In-memory (hourly snapshots) | 7 days rolling |
| Logs | Continuous streaming | 14 days local, 90 days cold storage |
| Cache | Not backed up (non-critical) | Auto-rebuilt on demand |

---

## Critical Assets

### Tier 1 (Essential for operation)
- SQLite backup files (`~/.cache/loom/backups/`)
- Configuration files (`./config.json`, environment variables)
- Application source code (git repository)
- API keys and secrets (SecretManager)

### Tier 2 (Important for performance)
- Session state database
- Search provider credentials
- LLM provider API keys
- Billing/metering data

### Tier 3 (Non-critical)
- Cache files (auto-rebuilt)
- Logs (archived for forensics)
- Analytics data (reproducible)

---

## Disaster Scenarios & Runbooks

### Scenario 1: Server Crash / Restart Required

**Symptoms:**
- Service unresponsive
- High CPU/memory
- Kernel panic
- Network interface down

**RTO:** 2 minutes

#### Runbook: Immediate Recovery

```bash
# 1. SSH to Hetzner instance
ssh hetzner

# 2. Check system status
systemctl status research-toolbox.service
journalctl -u research-toolbox.service -n 50

# 3. Attempt graceful restart
systemctl restart research-toolbox.service

# 4. Verify service is running
systemctl is-active research-toolbox.service

# 5. Health check
curl -s http://127.0.0.1:8787/health | jq .

# 6. Monitor logs for errors
journalctl -u research-toolbox.service -f
```

**If graceful restart fails:**

```bash
# Force restart (may lose in-memory session data)
systemctl kill research-toolbox.service
systemctl start research-toolbox.service

# Wait 5 seconds for startup
sleep 5

# Verify again
curl -s http://127.0.0.1:8787/health | jq .
```

**Escalation (if still failing):**
- Check disk space: `df -h /opt /home ~/.cache`
- Check file descriptor limits: `ulimit -n`
- Restart systemd: `systemctl restart systemd-logind`
- Last resort: Server redeployment (see Scenario 3)

---

### Scenario 2: Data Corruption Detected

**Symptoms:**
- `PRAGMA integrity_check` failure
- "corrupted database" errors in logs
- Backup verification script reports corruption
- Application errors reading database

**RTO:** 10 minutes

#### Runbook: Database Recovery

```bash
# 1. SSH to Hetzner and verify corruption
ssh hetzner
cd /Users/aadel/projects/loom
./scripts/verify_backups.sh --verbose

# 2. Identify which backup(s) are corrupted
find ~/.cache/loom -name "*.db" -exec sqlite3 {} "PRAGMA integrity_check;" \;

# 3. Stop the service to prevent further corruption
systemctl stop research-toolbox.service

# 4. List available backups
ls -lht /opt/research-toolbox/backups/*/

# 5. Restore from latest valid backup
BACKUP_FILE="/opt/research-toolbox/backups/$(date +%Y-%m-%d)/latest.db"
cp "$BACKUP_FILE" ~/.cache/loom/research.db.backup
cp "$BACKUP_FILE" ~/.cache/loom/research.db

# 6. Verify restored database
sqlite3 ~/.cache/loom/research.db "PRAGMA integrity_check;"

# 7. Restart service
systemctl start research-toolbox.service

# 8. Run health check
sleep 2
curl -s http://127.0.0.1:8787/health | jq .

# 9. Run application tests
pytest tests/test_storage.py -v --tb=short
```

**If corruption persists after restore:**

```bash
# Attempt point-in-time recovery (PITR) from older backup
BACKUP_DIR="/opt/research-toolbox/backups"
OLD_BACKUP=$(ls -t "$BACKUP_DIR"/*/latest.db | head -2 | tail -1)

# Restore from 1 day ago
cp "$OLD_BACKUP" ~/.cache/loom/research.db

# Verify and restart
sqlite3 ~/.cache/loom/research.db "PRAGMA integrity_check;"
systemctl start research-toolbox.service
```

**If no valid backup available:**
- Rebuild from git + recreate initial state
- See Scenario 3 (Full Redeployment)

---

### Scenario 3: Complete Server Loss / Full Redeployment

**Symptoms:**
- Hetzner instance terminated/corrupted
- All data lost
- Need to rebuild from scratch

**RTO:** 15 minutes

#### Runbook: Full Redeployment

```bash
# 1. Provision new Hetzner instance (done via console/terraform)
# Ensure:
#   - Ubuntu 22.04 LTS
#   - 4 CPU, 8 GB RAM, 100 GB SSD
#   - Public IP assigned
#   - SSH key configured

# 2. SSH to new instance
ssh -i ~/.ssh/hetzner_key root@<NEW_IP>

# 3. Clone repository
cd /tmp
git clone https://github.com/aadel/loom.git
cd loom

# 4. Install system dependencies
apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip \
  git curl sqlite3 build-essential libssl-dev libffi-dev

# 5. Create Python environment and install Loom
python3.11 -m venv venv
source venv/bin/activate
pip install -e ".[all]"

# 6. Restore configuration from backup
# (Assuming config backed up to cloud storage or git)
mkdir -p ~/.config/loom
gsutil cp gs://loom-backups/config.json ~/.config/loom/
gsutil cp gs://loom-backups/.env ~/.config/loom/

# 7. Load environment variables
export $(cat ~/.config/loom/.env | xargs)

# 8. Restore latest database backup
mkdir -p ~/.cache/loom
gsutil cp gs://loom-backups/latest/research.db ~/.cache/loom/

# 9. Verify database integrity
sqlite3 ~/.cache/loom/research.db "PRAGMA integrity_check;"

# 10. Start service in tmux/systemd
# For tmux (temporary):
tmux new-session -d -s loom "loom serve --host 0.0.0.0 --port 8787"

# For systemd (permanent):
sudo tee /etc/systemd/system/research-toolbox.service > /dev/null <<EOF
[Unit]
Description=Loom Research Toolbox MCP Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/root/loom/venv/bin/loom serve --host 0.0.0.0 --port 8787
Restart=on-failure
RestartSec=10s
Environment="PATH=/root/loom/venv/bin"
StandardOutput=append:/var/log/loom.log
StandardError=append:/var/log/loom.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable research-toolbox.service
sudo systemctl start research-toolbox.service

# 11. Health check
sleep 5
curl -s http://127.0.0.1:8787/health | jq .

# 12. Run verification tests
cd /root/loom
source venv/bin/activate
pytest tests/test_config.py tests/test_storage.py -v

# 13. Update DNS/endpoint if applicable
# Update any load balancer or DNS records to point to new IP
```

**Validation Checklist:**
- [ ] Service started successfully
- [ ] Health check returns 200 OK
- [ ] Database integrity verified
- [ ] API endpoints responding
- [ ] Logs show no critical errors
- [ ] Backup verification passed
- [ ] All API keys loaded from environment

---

### Scenario 4: API Key Compromise

**Symptoms:**
- Suspicious activity on provider accounts
- Unauthorized usage spike
- Provider notification of compromise
- Security audit finds exposed key in logs/code

**RTO:** 5 minutes

#### Runbook: Key Rotation

```bash
# 1. Identify compromised key
# Check logs for which provider
grep -i "groq\|nvidia\|deepseek\|gemini\|openai" /var/log/loom.log | grep -i error

# 2. Revoke compromised key in provider console
# Example for Groq:
# - Log in to https://console.groq.com
# - Delete the compromised API key
# - Generate new key
# - Copy to clipboard

# 3. Update environment variable
# SSH to server
ssh hetzner

# 4. Stop the service
systemctl stop research-toolbox.service

# 5. Update .env file with new key
nano ~/.config/loom/.env
# Find and update:
# GROQ_API_KEY=<NEW_KEY>

# 6. Reload environment
source ~/.config/loom/.env

# 7. Restart service
systemctl start research-toolbox.service

# 8. Verify service is running
sleep 2
curl -s http://127.0.0.1:8787/health | jq .

# 9. Test provider connectivity
curl -X POST http://127.0.0.1:8787/research_llm_summarize \
  -H "Content-Type: application/json" \
  -d '{"text":"test","model":"groq"}'

# 10. Check provider billing/usage
# - Groq: https://console.groq.com/usage
# - Verify no unauthorized charges
# - Set usage alerts/limits if available

# 11. Audit logs for exposures
journalctl -u research-toolbox.service | grep -i "GROQ_API_KEY"
# Should return NO matches (key should never appear in logs)

# 12. Document incident
echo "Incident: Key rotation for <PROVIDER> on $(date)" >> /var/log/loom-incidents.log
echo "Old key ID: <ID>" >> /var/log/loom-incidents.log
echo "Timestamp: $(date -u)" >> /var/log/loom-incidents.log
```

**Prevention:**
- Never log API keys (use masking in logs)
- Rotate keys quarterly
- Use restricted permissions (read-only where possible)
- Monitor provider dashboards for usage anomalies
- Implement API rate limiting to catch misuse

---

### Scenario 5: Network Connectivity Loss

**Symptoms:**
- Service cannot reach external APIs
- Search providers returning timeouts
- LLM provider calls failing
- Ping to gateway failing

**RTO:** 8 minutes

#### Runbook: Network Recovery

```bash
# 1. Check physical connectivity
ssh hetzner
ip link show
ip route show
ping 8.8.8.8

# 2. Check DNS resolution
nslookup google.com
cat /etc/resolv.conf

# 3. If DNS failing, update nameservers
sudo tee /etc/resolv.conf > /dev/null <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

sudo systemctl restart systemd-resolved

# 4. Verify default gateway
ip route show | grep default

# 5. If gateway missing, add route
sudo ip route add default via <GATEWAY_IP>

# 6. Check iptables/firewall rules
sudo iptables -L -n
sudo ufw status

# 7. Verify service can reach external endpoints
curl -I https://www.google.com
curl -I https://api.groq.com

# 8. If only specific API unreachable
# - Check provider status page
# - Verify API key still valid
# - Check IP rate limiting
# - Look for provider maintenance notifications

# 9. Restart service after connectivity restored
systemctl restart research-toolbox.service

# 10. Run connectivity test
# Create temp test script
cat > /tmp/test_connectivity.py << 'PYTEST'
import requests
import pytest

@pytest.mark.asyncio
async def test_google_connectivity():
    response = requests.get('https://www.google.com', timeout=5)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_groq_api():
    # Test Groq endpoint
    pass

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
PYTEST

python3 /tmp/test_connectivity.py
```

**If still failing:**
- Contact Hetzner support
- Check if server is being rate-limited
- Verify no firewall rules blocking outbound
- Request new public IP if compromised

---

## Backup & Restore Procedures

### Backup Strategy (3-2-1 Rule)

- **3 copies:** Production + local backup + cloud backup
- **2 media types:** SQLite (local) + Cloud Storage (GCS/S3)
- **1 offsite:** Google Cloud Storage (geo-redundant)

### Daily Backup Schedule

```
00:00 UTC (Midnight):
  - Create full SQLite backup
  - Copy to local /opt/research-toolbox/backups/
  - Upload to gs://loom-backups/

06:00 UTC:
  - Verify all backups (run verify_backups.sh)
  - Alert if verification fails

12:00 UTC:
  - Sync cold storage (archive older than 30 days)

18:00 UTC:
  - Prune local backups (keep only last 5 days + latest)
```

### Backup Verification

```bash
# Run daily verification
/Users/aadel/projects/loom/scripts/verify_backups.sh

# Run manual verification
sqlite3 ~/.cache/loom/research.db "PRAGMA integrity_check;"

# Expected output: "ok"
# If output contains anything else, database is corrupted
```

### Restore from Backup

```bash
# 1. Stop service
systemctl stop research-toolbox.service

# 2. Backup current database
cp ~/.cache/loom/research.db ~/.cache/loom/research.db.corrupted

# 3. Restore from backup
BACKUP_DIR="/opt/research-toolbox/backups/$(date +%Y-%m-%d)"
cp "$BACKUP_DIR"/latest.db ~/.cache/loom/research.db

# 4. Verify integrity
sqlite3 ~/.cache/loom/research.db "PRAGMA integrity_check;"

# 5. If verify fails, try older backup
for backup_file in /opt/research-toolbox/backups/*/latest.db; do
    sqlite3 "$backup_file" "PRAGMA integrity_check;" && break
done

# 6. Restart service
systemctl start research-toolbox.service

# 7. Health check
curl -s http://127.0.0.1:8787/health | jq .
```

---

## Testing & Validation

### Monthly DR Drill

Execute a full disaster recovery drill to validate procedures:

```bash
# 1. Create test instance (don't use production)
# 2. Follow Scenario 3 (Full Redeployment) runbook
# 3. Measure actual RTO (should be <15 min)
# 4. Document any issues or improvements
# 5. Update runbooks based on findings
# 6. Schedule next drill
```

### Automated Backup Verification

```bash
# Add to crontab (runs daily at 06:00 UTC)
0 6 * * * /Users/aadel/projects/loom/scripts/verify_backups.sh >> /var/log/backup_verification.log 2>&1

# Monitor for failures
grep ERROR /var/log/backup_verification.log
```

### Load Testing Recovery

After any major update:
1. Run load test against recovered instance
2. Verify performance metrics match baseline
3. Test all API endpoints
4. Verify LLM provider fallback cascade

---

## Communication & Escalation

### Incident Severity Levels

| Level | Impact | Response Time | Contact |
|-------|--------|---------------|---------|
| Critical | Service down, data loss risk | Immediate (5 min) | Ahmed (primary), OnCall |
| High | Degraded service, some features down | 15 minutes | Ahmed, Senior Engineer |
| Medium | Minor issues, workaround available | 1 hour | Ahmed |
| Low | Cosmetic/informational | Next business day | Ticket system |

### Escalation Contacts

**Primary:** Ahmed Adel Bakr Alderai  
**Email:** ahmedalderai22@gmail.com  
**Phone:** (To be added)  
**On-call:** (To be configured)

**Escalation:** If primary not responding within 10 minutes, activate backup contact

### Incident Communication Template

```
INCIDENT NOTIFICATION

Severity: [CRITICAL/HIGH/MEDIUM/LOW]
Service: Loom Research Toolbox MCP Server
Start Time: [YYYY-MM-DD HH:MM:SS UTC]
Status: [ONGOING/INVESTIGATING/RESOLVED]

Description:
[Brief description of issue]

Impact:
- [Item 1]
- [Item 2]
- [Item 3]

Actions Taken:
1. [Action 1]
2. [Action 2]

ETA to Resolution: [Time or "Unknown"]

Next Update: [Time]
```

---

## Monitoring & Alerting

### Critical Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| Service down | 1 minute | Immediate restart |
| Database corruption | Detection | Restore from backup |
| High disk usage | > 90% | Alert, archive cold data |
| API rate limit | > 80% of quota | Reduce requests, contact provider |
| Memory usage | > 85% | Investigate, consider restart |
| CPU usage | > 90% sustained | Investigate load, consider restart |

### Monitoring Dashboard

Access at: `http://127.0.0.1:8787/dashboard` (if available)

**Key metrics:**
- Service uptime
- Request latency (p50, p95, p99)
- Error rate (by provider)
- Cache hit rate
- Database size
- Backup completion status

### Log Monitoring

```bash
# Watch service logs in real-time
journalctl -u research-toolbox.service -f

# Search for errors
journalctl -u research-toolbox.service | grep -i error

# Export logs for analysis
journalctl -u research-toolbox.service --since "2 days ago" > /tmp/loom_logs.txt
```

---

## Prevention Measures

### Regular Maintenance

- **Weekly:** Monitor logs for warnings/errors
- **Monthly:** Backup verification drill
- **Quarterly:** Full disaster recovery simulation
- **Quarterly:** API key rotation
- **Semi-annually:** Security audit
- **Annually:** Full documentation review

### Security Hardening

- [ ] SSH key-based auth only (no passwords)
- [ ] Firewall rules restrict to necessary ports
- [ ] API keys stored in SecretManager
- [ ] No secrets in application code
- [ ] SSL/TLS for all communications
- [ ] Regular security patches applied
- [ ] Intrusion detection monitoring
- [ ] Audit logging enabled

### Capacity Planning

- Current usage: Monitor monthly
- Forecast growth: 20% YoY expected
- Scale triggers:
  - Database size > 80% of allocated storage
  - CPU consistently > 75%
  - Memory consistently > 80%
  - API rate limit approaching quota

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-04 | Ahmed Adel Bakr Alderai | Initial creation |
| | | | |

### Review History

- [ ] Review: 2026-08-04
- [ ] Review: 2026-11-04
- [ ] Review: 2027-02-04

---

## References

- Architecture Document: `/docs/ARCHITECTURE_DESIGN.md`
- API Reference: `/docs/API_REFERENCE_V2.md`
- Configuration Guide: `/CLAUDE.md`
- Backup Manager Code: `/src/loom/backup_manager.py`
- Verification Script: `/scripts/verify_backups.sh`
- Disaster Recovery Tests: `/scripts/dr_test.sh`

---

## Appendix A: Backup Directory Structure

```
/opt/research-toolbox/backups/
├── 2026-05-04/
│   ├── latest.db                 # Most recent full backup
│   ├── research.db.gz            # Compressed backup
│   ├── metadata.json             # Backup metadata
│   └── manifest.txt              # File listing
├── 2026-05-03/
│   ├── latest.db
│   ├── research.db.gz
│   ├── metadata.json
│   └── manifest.txt
└── ...
```

---

## Appendix B: Verification Checklist

Run this checklist after any disaster recovery:

- [ ] Service responding to health checks
- [ ] Database passes PRAGMA integrity_check
- [ ] All API keys validated
- [ ] Backup files verified
- [ ] Recent queries working
- [ ] LLM providers reachable
- [ ] Search providers working
- [ ] Logs show no errors
- [ ] Performance metrics nominal
- [ ] Incident documented
- [ ] Team notified of resolution

---

**Document End**
