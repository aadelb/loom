# Loom Monitoring Stack - File Manifest

Complete file listing and purpose for the Loom MCP Server monitoring infrastructure.

## File Inventory

### Core Configuration Files

#### 1. `prometheus.yml` (1.2 KB)
**Purpose:** Prometheus server configuration and scrape targets

**Contents:**
- Global settings (scrape interval: 15s, evaluation interval: 15s)
- Scrape job for Loom server at `127.0.0.1:8787/metrics`
- Metric filtering to keep only `loom_*` metrics
- Prometheus self-monitoring job
- Optional Node Exporter job for system metrics
- Alertmanager configuration for alert routing

**Key Settings:**
```yaml
scrape_interval: 15s      # Collect metrics every 15 seconds
evaluation_interval: 15s  # Evaluate alert rules every 15 seconds
retention: 30 days        # Keep data for 30 days (configurable)
```

**Metrics Collected:**
- `loom_tool_calls_total` (counter)
- `loom_tool_duration_seconds` (histogram)
- `loom_tool_errors_total` (counter)
- `loom_circuit_breaker_open` (gauge)
- `loom_active_connections` (gauge)
- `loom_cache_hits` / `loom_cache_misses` (counters)

#### 2. `alerting-rules.yml` (5.6 KB)
**Purpose:** Prometheus alert rules and recording rules

**Alert Rules (9 total):**
1. `LoomHighErrorRate` — Error rate > 5% for 5 minutes (WARNING)
2. `LoomHighLatency` — P95 latency > 10s for 5 minutes (WARNING)
3. `LoomVeryHighLatency` — P95 latency > 30s for 2 minutes (CRITICAL)
4. `LoomCircuitOpen` — Circuit breaker open > 5 minutes (CRITICAL)
5. `LoomHighMemory` — Memory > 6GB for 10 minutes (WARNING)
6. `LoomCriticalMemory` — Memory > 8GB for 2 minutes (CRITICAL)
7. `LoomDown` — Server unreachable > 1 minute (CRITICAL)
8. `LoomNoToolCalls` — No calls for 10 minutes (WARNING)
9. `LoomCacheHitRateLow` — Cache hit rate < 30% for 15 minutes (INFO)

**Recording Rules (6 total):**
Pre-computed metrics for faster queries:
- `loom:calls:rate1m` — 1-minute call rate
- `loom:errors:rate1m` — 1-minute error rate
- `loom:error_rate:percentage` — Error rate %
- `loom:latency:p95` — P95 latency
- `loom:latency:p99` — P99 latency
- `loom:cache_hit_rate:percentage` — Cache hit rate %

#### 3. `alertmanager.yml` (3.0 KB)
**Purpose:** AlertManager configuration for notification routing

**Features:**
- Email notifications (SMTP configuration)
- Slack webhook integration
- PagerDuty escalation
- Alert grouping by severity and component
- Inhibition rules (suppress less-critical alerts when critical ones fire)
- Custom email templates support

**Notification Routes:**
- Critical → PagerDuty + Slack + Email (5m repeat)
- Warning → Slack + Email (2h repeat)
- Info → Email digest (24h repeat)

**Inhibition Rules:**
- Critical alerts suppress warning/info alerts
- LoomDown suppresses other Loom alerts for same instance

#### 4. `grafana-dashboard.json` (20 KB)
**Purpose:** Grafana dashboard definition in JSON format

**Panels (8 total):**
1. **Tool Calls Per Second** (timeseries) — Real-time throughput visualization
   - Query: `rate(loom_tool_calls_total{status="success"}[1m])`
   - Displays by tool name

2. **Error Rate** (timeseries) — 5-minute rolling error percentage
   - Query: `(rate(loom_tool_errors_total[5m]) / rate(loom_tool_calls_total[5m])) * 100`
   - Red threshold at 5%

3. **P95 & P99 Latency** (timeseries) — Response time percentiles
   - Queries: `histogram_quantile(0.95/0.99, loom_tool_duration_seconds_bucket)`
   - Red threshold at 10s for P95

4. **Top 10 Tools by Call Volume** (stacked bars) — Tool ranking
   - Query: `topk(10, rate(loom_tool_calls_total[5m]) * 60)`
   - Calls per minute

5. **Circuit Breaker Status** (table) — Provider health
   - Query: `loom_circuit_breaker_open{tool_name=~"$tool_name"}`
   - Displays tool name and status (0=Closed, 1=Open)

6. **Memory Usage** (timeseries) — Process resident memory
   - Query: `process_resident_memory_bytes / 1e6` (in MB)
   - Yellow at 4GB, Red at 6GB

7. **Active Connections** (timeseries) — Real-time connection count
   - Query: `loom_active_connections`

8. **Cache Hit Rate** (timeseries) — Cache effectiveness
   - Query: `(loom_cache_hits / (loom_cache_hits + loom_cache_misses)) * 100`
   - Red < 50%, Yellow < 75%, Green >= 75%

**Variables:**
- Time range selector (5m, 15m, 1h, 6h, 24h)
- Tool name multi-select filter (auto-populated from Prometheus)

**Refresh Rate:** 30 seconds

#### 5. `docker-compose.yml` (4.3 KB)
**Purpose:** Docker Compose orchestration for the entire monitoring stack

**Services (5 total):**

1. **prometheus** — Time-series database
   - Image: `prom/prometheus:v2.45.0`
   - Port: 9090
   - Volumes: prometheus_data (30-day retention)
   - Healthcheck: /-/healthy endpoint

2. **grafana** — Visualization and dashboarding
   - Image: `grafana/grafana:10.0.0`
   - Port: 3000
   - Default user: admin / admin
   - Auto-provisions datasources and dashboards

3. **alertmanager** — Alert routing and notification
   - Image: `prom/alertmanager:v0.25.0`
   - Port: 9093
   - Volumes: alertmanager_data

4. **node-exporter** — System metrics collector
   - Image: `prom/node-exporter:v1.6.1`
   - Port: 9100
   - Collects CPU, memory, disk, network metrics

5. **cadvisor** — Container metrics collector
   - Image: `gcr.io/cadvisor/cadvisor:v0.47.0`
   - Port: 8080
   - Collects Docker container metrics

**Network:**
- Custom bridge network (172.28.0.0/16)
- All services communicate via container names

**Volumes:**
- `prometheus_data` — Prometheus TSDB storage
- `grafana_data` — Grafana configuration and dashboards
- `alertmanager_data` — AlertManager state

### Provisioning Files

#### 6. `grafana-provisioning-datasources.yml` (232 bytes)
**Purpose:** Auto-configure Prometheus datasource in Grafana

**Configuration:**
- Datasource: "Prometheus"
- URL: `http://prometheus:9090`
- Default: true
- Scrape interval: 15s

#### 7. `grafana-provisioning-dashboards.yml` (241 bytes)
**Purpose:** Auto-configure dashboard provider in Grafana

**Configuration:**
- Provider name: "Loom Dashboards"
- Folder: "Loom"
- Type: file-based provisioning
- Path: `/etc/grafana/provisioning/dashboards`

### Documentation Files

#### 8. `README.md` (13 KB)
**Comprehensive monitoring guide with:**
- Architecture overview
- Component descriptions
- Setup instructions (Docker Compose and manual)
- Dashboard panel documentation
- Metrics reference
- PromQL query examples
- Alerting configuration
- Troubleshooting guide
- Performance tuning recommendations
- Production deployment guidance
- High availability setup

#### 9. `QUICKSTART.md` (3.5 KB)
**Quick reference for immediate setup:**
- One-command setup
- Manual setup fallback
- Service URLs and credentials
- Common tasks
- Quick troubleshooting
- Next steps

#### 10. `MANIFEST.md` (this file)
**Complete file inventory and documentation**

### Automation Script

#### 11. `setup.sh` (4.3 KB, executable)
**Purpose:** Automated setup script for the monitoring stack

**Functions:**
- Validates Docker installation
- Checks Docker daemon is running
- Validates all configuration files
- Validates JSON and YAML syntax
- Creates data directories
- Pulls Docker images
- Starts containers with docker-compose
- Monitors service health
- Displays service URLs and next steps

**Usage:**
```bash
bash setup.sh
```

**Error Handling:**
- Exits with error codes if Docker missing
- Validates all files before starting
- Provides helpful error messages

## Metrics Exported by Loom

The Loom server exports the following metrics (when `prometheus-client` is installed):

### Counter Metrics
```
loom_tool_calls_total{tool_name="...", status="success|error"}
loom_tool_errors_total{tool_name="...", error_type="..."}
loom_cache_hits
loom_cache_misses
```

### Histogram Metrics
```
loom_tool_duration_seconds_bucket{tool_name="...", le="..."}
loom_tool_duration_seconds_count{tool_name="..."}
loom_tool_duration_seconds_sum{tool_name="..."}
```

### Gauge Metrics
```
loom_circuit_breaker_open{tool_name="..."}
loom_active_connections
process_resident_memory_bytes
```

## File Size Summary

```
Total monitoring files: 11
Total size: ~152 KB

Breakdown:
- Configuration files: 14.9 KB (prometheus, alerting, alertmanager, docker-compose)
- Dashboard definition: 20 KB (Grafana dashboard JSON)
- Provisioning files: 473 bytes (Grafana datasource & dashboard provider)
- Documentation: 16.5 KB (README, QUICKSTART, MANIFEST)
- Setup script: 4.3 KB (bash setup automation)
- Provisioning files: 232 bytes
```

## Network Ports

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | Grafana | Web UI for dashboards |
| 8787 | Loom | MCP server metrics endpoint |
| 9090 | Prometheus | Metrics database and API |
| 9093 | AlertManager | Alert routing and notifications |
| 9100 | Node Exporter | System metrics (optional) |
| 8080 | cAdvisor | Container metrics (optional) |

## Data Flow

```
Loom Server (8787)
   ↓ (HTTP GET /metrics)
Prometheus (9090)
   ↓ (stores metrics)
   ├→ Grafana (3000) — visualize
   ├→ AlertManager (9093) — trigger alerts
   └→ Recording Rules — pre-compute metrics
      ├→ Email
      ├→ Slack
      └→ PagerDuty
```

## Getting Started

1. **Quick Start (5 minutes):**
   ```bash
   cd monitoring
   bash setup.sh
   ```
   Then open http://localhost:3000

2. **Manual Setup:**
   ```bash
   cd monitoring
   docker-compose up -d
   ```

3. **Production Deployment:**
   - See README.md "Production Deployment" section
   - Configure alerting endpoints in alertmanager.yml
   - Setup persistent volumes
   - Enable HTTPS
   - Configure high availability

## Maintenance

| Task | Frequency | Command |
|------|-----------|---------|
| Check health | Daily | `docker-compose ps` |
| Review alerts | Daily | http://localhost:9093 |
| Check storage | Weekly | `du -sh data/*` |
| Update images | Monthly | `docker-compose pull` |
| Backup data | Monthly | Custom backup script |
| Test alerts | Monthly | Manual trigger in Prometheus |

## Customization

### Add Custom Metrics

1. In Loom server, register custom metrics:
   ```python
   from prometheus_client import Gauge
   custom_metric = Gauge('loom_custom_metric', 'Description')
   ```

2. Add queries to `alerting-rules.yml`

3. Create dashboard panels in `grafana-dashboard.json`

### Add Custom Alerts

1. Add alert rule to `alerting-rules.yml`
2. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`
3. Test in Prometheus UI: http://localhost:9090/alerts

### Change Notification Recipients

Edit `alertmanager.yml` and update receiver configurations.

## Troubleshooting Quick Links

- No data in Grafana? → See README.md "Grafana shows no data"
- Alerts not firing? → See README.md "Alerts not firing"
- High memory? → See README.md "Troubleshooting: High memory usage"
- Service down? → Check `docker-compose logs` and `docker-compose ps`

## References

- Prometheus: https://prometheus.io/docs/
- Grafana: https://grafana.com/docs/
- AlertManager: https://prometheus.io/docs/alerting/latest/
- PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
