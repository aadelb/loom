# Loom Monitoring Stack - Complete Index

Professional-grade monitoring solution for Loom MCP Server with Prometheus, Grafana, and AlertManager.

## Quick Navigation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **QUICKSTART.md** | Get started in 5 minutes | 3 min |
| **README.md** | Complete setup & administration | 15 min |
| **MANIFEST.md** | Detailed file inventory | 10 min |
| **DEPLOYMENT_CHECKLIST.md** | Deployment verification | 5 min |
| **This file** | Navigation guide | 2 min |

## File Structure

### Configuration Files (YAML)

#### Core Monitoring
- **prometheus.yml** — Prometheus server configuration
  - Scrape interval: 15 seconds
  - Retention: 30 days
  - Scrape target: `127.0.0.1:8787/metrics`
  - Alert evaluation: Every 15 seconds

- **alerting-rules.yml** — Alert rules and recording rules
  - 9 alert rules (5 warning, 4 critical)
  - 6 recording rules for optimization
  - Thresholds for error rate, latency, memory

- **alertmanager.yml** — Alert routing and notifications
  - Email notifications (SMTP)
  - Slack integration
  - PagerDuty escalation
  - Alert grouping and inhibition

#### Docker Orchestration
- **docker-compose.yml** — Complete stack definition
  - 5 services: Prometheus, Grafana, AlertManager, Node Exporter, cAdvisor
  - Health checks for all services
  - Persistent volumes for data
  - Auto-provisioning of datasources and dashboards

#### Grafana Provisioning
- **grafana-provisioning-datasources.yml** — Auto-configure Prometheus datasource
- **grafana-provisioning-dashboards.yml** — Auto-configure dashboard provider

### Dashboard Definition

- **grafana-dashboard.json** — Production-ready Grafana dashboard
  - 8 comprehensive panels
  - Time range and tool name filters
  - Color-coded thresholds
  - Auto-refresh every 30 seconds

### Documentation Files (Markdown)

- **README.md** (497 lines, 13 KB)
  - Complete setup instructions
  - Docker Compose and manual installation
  - Dashboard panel descriptions
  - Metrics reference
  - PromQL query examples
  - Troubleshooting guide
  - Production deployment

- **QUICKSTART.md** (223 lines, 3.5 KB)
  - One-command setup
  - Quick reference
  - Common tasks
  - Troubleshooting quick links

- **MANIFEST.md** (370 lines, 7.5 KB)
  - Complete file manifest
  - Component descriptions
  - Metrics reference
  - Data flow and architecture

- **DEPLOYMENT_CHECKLIST.md** (200+ lines)
  - Pre-deployment checks
  - Installation steps
  - Service verification
  - Alert testing
  - Production readiness

- **INDEX.md** (this file)
  - Navigation guide
  - Quick reference

### Automation

- **setup.sh** (executable, 181 lines, 4.3 KB)
  - Validates Docker installation
  - Validates all configuration files
  - Pulls Docker images
  - Starts monitoring stack
  - Monitors service health

## Getting Started

### Fastest Way (5 minutes)

```bash
cd /Users/aadel/projects/loom/monitoring
bash setup.sh
```

Then access:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093

### Step-by-Step (10 minutes)

1. Read QUICKSTART.md
2. Run setup.sh
3. Access Grafana
4. View "Loom MCP Server" dashboard
5. Configure alerts in alertmanager.yml

### Detailed Setup (30 minutes)

1. Read README.md completely
2. Run setup.sh with understanding of each step
3. Verify all services are healthy
4. Configure real notification endpoints
5. Test alert notifications
6. Monitor dashboard for 10 minutes

## Key Metrics

### Tool Execution
```promql
loom_tool_calls_total{tool_name="...", status="success|error"}
loom_tool_duration_seconds{tool_name="..."}
loom_tool_errors_total{tool_name="...", error_type="..."}
```

### System Health
```promql
loom_circuit_breaker_open{tool_name="..."}
loom_active_connections
process_resident_memory_bytes
```

### Cache Performance
```promql
loom_cache_hits
loom_cache_misses
```

## Dashboard Panels

1. **Tool Calls Per Second** — Real-time throughput
2. **Error Rate** — Percentage of failed calls (threshold: 5%)
3. **P95 & P99 Latency** — Response time percentiles (threshold: 10s)
4. **Top 10 Tools** — Tools ranked by call volume
5. **Circuit Breaker Status** — Provider health (0=Closed, 1=Open)
6. **Memory Usage** — Process RAM (threshold: 6GB warning, 8GB critical)
7. **Active Connections** — Real-time client connections
8. **Cache Hit Rate** — Cache effectiveness (goal: >75%)

## Alert Rules Summary

### Warning Level (2h repeat)
- High error rate (>5% for 5min)
- High latency (P95 >10s for 5min)
- High memory (>6GB for 10min)
- No tool calls (for 10min)
- Low cache hit rate (<30% for 15min)

### Critical Level (5m repeat, PagerDuty escalation)
- Very high latency (P95 >30s for 2min)
- Circuit breaker open (>5min)
- Server unreachable (>1min)
- Critical memory (>8GB for 2min)

## Services & Ports

| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9090 | Metrics database & alerting |
| Grafana | 3000 | Dashboards & visualization |
| AlertManager | 9093 | Alert routing & notifications |
| Node Exporter | 9100 | System metrics (optional) |
| cAdvisor | 8080 | Container metrics (optional) |
| Loom | 8787 | Metrics endpoint (/metrics) |

## Architecture

```
Loom Server (8787)
  ↓ /metrics endpoint
Prometheus (9090)
  ├→ Evaluates alert rules
  ├→ Stores time-series data
  └→ Serves queries
      ├→ Grafana (3000)
      │   └→ Dashboard visualization
      └→ AlertManager (9093)
          ├→ Email
          ├→ Slack
          └→ PagerDuty
```

## File Sizes

```
Total: 96 KB

Breakdown:
├── Configurations: 14.9 KB
│   ├── prometheus.yml (1.2 KB)
│   ├── alerting-rules.yml (5.6 KB)
│   ├── alertmanager.yml (3.0 KB)
│   └── docker-compose.yml (4.3 KB)
├── Dashboard: 20 KB
│   └── grafana-dashboard.json
├── Documentation: 23.8 KB
│   ├── README.md (13 KB)
│   ├── QUICKSTART.md (3.5 KB)
│   ├── MANIFEST.md (7.5 KB)
│   └── DEPLOYMENT_CHECKLIST.md
├── Provisioning: 473 B
├── Automation: 4.3 KB
│   └── setup.sh
└── This index: (small)
```

## Validation Status

- ✓ All YAML files valid
- ✓ JSON dashboard valid
- ✓ Scripts executable
- ✓ Documentation complete
- ✓ Ready for deployment

## Next Actions

**Immediate (Now):**
1. Read QUICKSTART.md (3 min)
2. Run `bash setup.sh` (2 min)
3. Access Grafana (1 min)

**Short-term (1 hour):**
1. Configure alertmanager.yml with real endpoints
2. Test email/Slack/PagerDuty notifications
3. Adjust alert thresholds if needed

**Medium-term (1 day):**
1. Monitor dashboard patterns
2. Create runbooks for alerts
3. Document alert procedures

**Production (Before going live):**
1. Review README.md "Production Deployment"
2. Setup persistent volumes
3. Enable HTTPS
4. Configure high availability

## Support & References

- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- AlertManager Docs: https://prometheus.io/docs/alerting/
- PromQL Reference: https://prometheus.io/docs/prometheus/latest/querying/

## File Paths (Absolute)

```
/Users/aadel/projects/loom/monitoring/
├── prometheus.yml
├── alerting-rules.yml
├── alertmanager.yml
├── docker-compose.yml
├── grafana-dashboard.json
├── grafana-provisioning-datasources.yml
├── grafana-provisioning-dashboards.yml
├── setup.sh
├── README.md
├── QUICKSTART.md
├── MANIFEST.md
├── DEPLOYMENT_CHECKLIST.md
└── INDEX.md
```

## Quick Commands

```bash
# One-command setup
cd /Users/aadel/projects/loom/monitoring && bash setup.sh

# Start monitoring (if already setup)
docker-compose up -d

# Stop monitoring
docker-compose down

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f alertmanager

# Check service health
docker-compose ps

# Access services
Grafana:      http://localhost:3000 (admin/admin)
Prometheus:   http://localhost:9090
AlertManager: http://localhost:9093

# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload

# Query metrics directly
curl 'http://localhost:9090/api/v1/query?query=loom_tool_calls_total'
```

## Version Information

- **Prometheus**: v2.45.0
- **Grafana**: 10.0.0
- **AlertManager**: v0.25.0
- **Node Exporter**: v1.6.1
- **cAdvisor**: v0.47.0
- **Docker Compose**: v3.8

## Important Notes

- All services use container networking (172.28.0.0/16)
- Loom server must be accessible at `127.0.0.1:8787`
- prometheus-client must be installed in Loom environment
- First data point appears ~15 seconds after scrape starts
- Alerts need metric data to fire (requires 15-30 seconds of operation)
- Dashboard auto-refreshes every 30 seconds

## Customization Quick Links

- Add custom alerts: See alerting-rules.yml
- Modify dashboard: See grafana-dashboard.json or Grafana UI
- Change thresholds: Edit alerting-rules.yml or alertmanager.yml
- Add notification channels: Edit alertmanager.yml receivers
- Change scrape interval: Edit prometheus.yml (global section)

## Troubleshooting Quick Links

- No data in dashboard → See README.md "Grafana shows no data"
- Alerts not firing → See README.md "Alerts not firing"
- Service won't start → See docker-compose logs
- Prometheus can't reach Loom → Check `curl http://127.0.0.1:8787/metrics`

---

**Status**: Ready for Deployment ✓

**Created**: 2026-05-04

**Last Updated**: 2026-05-04

For detailed information, see individual documentation files.
