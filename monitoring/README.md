# Loom MCP Server Monitoring Stack

Comprehensive monitoring solution for the Loom MCP server using Prometheus, Grafana, and Alertmanager.

## Architecture Overview

```
Loom MCP Server (localhost:8787)
           ↓
    /metrics endpoint
           ↓
    Prometheus (localhost:9090)
           ↓
      ┌────┴─────┐
      ↓          ↓
   Grafana   Alertmanager
(localhost:3000) (localhost:9093)
```

## Components

### 1. Grafana Dashboard (`grafana-dashboard.json`)

Production-ready dashboard with 8 key panels:

- **Tool Calls Per Second**: Real-time throughput monitoring
- **Error Rate**: 5-minute rolling error percentage with threshold alerting
- **P95 & P99 Latency**: Histogram-based latency percentiles
- **Top 10 Tools**: Tools ranked by call volume (stacked bar chart)
- **Circuit Breaker Status**: Table view of provider health (0=Closed/Healthy, 1=Open/Failing)
- **Memory Usage**: Process resident memory with threshold warnings
- **Active Connections**: Real-time connection count
- **Cache Hit Rate**: Percentage of cache hits vs misses

**Variables:**
- Time Range Selector: 5m, 15m, 1h, 6h, 24h
- Tool Name Filter: Multi-select dropdown (auto-populated from metrics)

**Refresh Rate:** 30s (configurable)

### 2. Prometheus Configuration (`prometheus.yml`)

Scrape configuration:

```yaml
Job: "loom"
Target: 127.0.0.1:8787/metrics
Interval: 15s
Timeout: 10s
Metrics Filter: Retains only loom_* metrics
```

Additional jobs for system monitoring:
- `prometheus`: Self-monitoring at 9090
- `node-exporter`: System metrics at 9100 (optional)

### 3. Alerting Rules (`alerting-rules.yml`)

**Production Alerts:**

| Alert | Condition | Duration | Severity | Action |
|-------|-----------|----------|----------|--------|
| **LoomHighErrorRate** | Error rate > 5% | 5m | Warning | Check recent deployments, review error logs |
| **LoomHighLatency** | P95 latency > 10s | 5m | Warning | Investigate slow tools, check resource usage |
| **LoomVeryHighLatency** | P95 latency > 30s | 2m | Critical | Immediate investigation required |
| **LoomCircuitOpen** | Circuit breaker open | 5m | Critical | Service degraded; restart provider or escalate |
| **LoomHighMemory** | Memory > 6GB | 10m | Warning | Review memory usage, check for leaks |
| **LoomCriticalMemory** | Memory > 8GB | 2m | Critical | Risk of OOM; restart service immediately |
| **LoomDown** | Server unreachable | 1m | Critical | Restart service; check server logs |
| **LoomNoToolCalls** | No calls for 10m | 10m | Warning | Service idle or inactive; check client connections |
| **LoomCacheHitRateLow** | Hit rate < 30% | 15m | Info | Review cache strategy; consider TTL adjustment |

**Recording Rules:**

Pre-computed metrics for faster dashboard queries:
- `loom:calls:rate1m` — 1-minute call rate
- `loom:errors:rate1m` — 1-minute error rate
- `loom:error_rate:percentage` — Error rate percentage
- `loom:latency:p95` — P95 latency
- `loom:latency:p99` — P99 latency
- `loom:cache_hit_rate:percentage` — Cache hit rate

## Setup Instructions

### Prerequisites

- Docker & Docker Compose (recommended) OR manual installation
- Loom MCP server running on `127.0.0.1:8787`
- Python 3.9+ with prometheus-client installed (for Loom metrics export)

### Option A: Docker Compose (Recommended)

1. **Create docker-compose.yml in project root:**

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: loom-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/alerting-rules.yml:/etc/prometheus/alerting-rules.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"
    networks:
      - loom-monitoring
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: loom-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana-dashboard.json:/etc/grafana/provisioning/dashboards/loom-dashboard.json:ro
    networks:
      - loom-monitoring
    restart: unless-stopped
    depends_on:
      - prometheus

  alertmanager:
    image: prom/alertmanager:latest
    container_name: loom-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    command:
      - "--config.file=/etc/alertmanager/alertmanager.yml"
      - "--storage.path=/alertmanager"
    networks:
      - loom-monitoring
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  loom-monitoring:
    driver: bridge
```

2. **Start the stack:**

```bash
docker-compose up -d
```

3. **Access services:**
   - Grafana: http://localhost:3000 (default: admin/admin)
   - Prometheus: http://localhost:9090
   - Alertmanager: http://localhost:9093

### Option B: Manual Installation (Linux/macOS)

1. **Install Prometheus:**

```bash
# macOS
brew install prometheus

# Linux
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-2.45.0.linux-amd64.tar.gz
cd prometheus-2.45.0.linux-amd64
```

2. **Configure Prometheus:**

```bash
# Copy the configuration file
cp monitoring/prometheus.yml /etc/prometheus/prometheus.yml
cp monitoring/alerting-rules.yml /etc/prometheus/alerting-rules.yml

# Start Prometheus
./prometheus --config.file=/etc/prometheus/prometheus.yml
```

3. **Install Grafana:**

```bash
# macOS
brew install grafana

# Start Grafana
brew services start grafana

# Linux (systemd)
sudo apt-get install grafana-server
sudo systemctl start grafana-server
```

4. **Install Alertmanager:**

```bash
# macOS
brew install alertmanager

# Start Alertmanager
alertmanager --config.file=monitoring/alertmanager.yml
```

### Loom Server Configuration

Ensure Loom server exports metrics (already configured in `src/loom/server.py`):

```python
# Metrics are automatically registered if prometheus-client is installed
pip install prometheus-client
```

The `/metrics` endpoint is automatically exposed on port 8787.

## Importing the Dashboard

### Via Grafana UI:

1. Open Grafana (http://localhost:3000)
2. Login with admin/admin
3. Click **+ → Import Dashboard**
4. Paste content from `grafana-dashboard.json`
5. Select Prometheus data source
6. Click **Import**

### Via API:

```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana-dashboard.json \
  --user admin:admin
```

### Via Grafana Provisioning:

Mount the dashboard file in the Grafana container:

```yaml
volumes:
  - ./monitoring/grafana-dashboard.json:/etc/grafana/provisioning/dashboards/loom-dashboard.json:ro
```

## Configuring Alerts

### Email Notifications

Edit `monitoring/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: "smtp.gmail.com:587"
  smtp_auth_username: "your-email@gmail.com"
  smtp_auth_password: "your-app-password"
  smtp_from: "loom-alerts@example.com"

route:
  receiver: "email"
  group_by: ["alertname", "severity"]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: "email"
    email_configs:
      - to: "ops@example.com"
        headers:
          Subject: "Loom Alert: {{ .GroupLabels.alertname }}"
```

### Slack Notifications

Add to `alertmanager.yml`:

```yaml
receivers:
  - name: "slack"
    slack_configs:
      - api_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        channel: "#alerts"
        title: "{{ .GroupLabels.alertname }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
```

### PagerDuty Integration

```yaml
receivers:
  - name: "pagerduty"
    pagerduty_configs:
      - service_key: "YOUR_SERVICE_KEY"
        description: "{{ .GroupLabels.alertname }}"
```

## Metrics Reference

### Core Tool Metrics

```promql
# Total tool calls (success/error)
loom_tool_calls_total{tool_name="research_fetch", status="success|error"}

# Tool execution duration histogram (buckets: 0.1s, 0.5s, 1s, 2.5s, 5s, 10s, 30s, 60s)
loom_tool_duration_seconds_bucket{tool_name="research_fetch", le="1"}

# Tool errors by type
loom_tool_errors_total{tool_name="research_fetch", error_type="timeout|validation|api_error"}
```

### System Metrics

```promql
# Circuit breaker status (0=closed, 1=open)
loom_circuit_breaker_open{tool_name="research_fetch"}

# Active client connections
loom_active_connections

# Cache statistics
loom_cache_hits
loom_cache_misses

# Process metrics (standard Go runtime)
process_resident_memory_bytes
process_cpu_seconds_total
```

## Query Examples

### Find slowest tools:

```promql
topk(5, histogram_quantile(0.95, loom_tool_duration_seconds_bucket))
```

### Error rate by tool:

```promql
loom:error_rate:percentage{tool_name=~"research_.*"}
```

### Cache effectiveness:

```promql
loom:cache_hit_rate:percentage
```

### Tool availability:

```promql
(rate(loom_tool_calls_total{status="success"}[5m]) / rate(loom_tool_calls_total[5m])) * 100
```

## Troubleshooting

### Prometheus cannot scrape Loom

**Problem:** Prometheus shows "down" for loom job

**Solution:**
1. Verify Loom is running: `curl http://127.0.0.1:8787/metrics`
2. Check network connectivity: `ping 127.0.0.1`
3. Ensure prometheus.yml has correct IP/port
4. Reload Prometheus config: `curl -X POST http://localhost:9090/-/reload`

### Grafana shows "no data"

**Problem:** Dashboard panels display "No data" even though Prometheus has metrics

**Solution:**
1. Verify data source: Grafana Settings → Data Sources → Test Prometheus
2. Check metric names: `curl http://localhost:9090/api/v1/labels`
3. Try raw query in Prometheus UI: http://localhost:9090/graph
4. Verify time range in dashboard matches data availability

### Alerts not firing

**Problem:** Alert conditions are met but no notifications received

**Solution:**
1. Check Alertmanager status: http://localhost:9093
2. Verify alerting rules loaded: http://localhost:9090/alerts
3. Test notification config: `amtool config routes`
4. Check Alertmanager logs for configuration errors

### High memory usage

**Problem:** Prometheus or Grafana using excessive RAM

**Solution:**
1. Reduce Prometheus retention: `--storage.tsdb.retention.time=7d`
2. Lower scrape frequency: change `scrape_interval` in prometheus.yml
3. Increase query timeout to prevent runaway queries
4. Monitor specific metrics: `curl http://localhost:9090/api/v1/query?query=process_resident_memory_bytes`

## Performance Tuning

### For high-cardinality metrics:

```yaml
# prometheus.yml
metric_relabel_configs:
  - source_labels: [__name__]
    regex: "loom_tool_calls_total"
    action: "keep"  # Drop unwanted metrics early
```

### For large deployments:

1. Use remote storage (Thanos, M3DB)
2. Increase Prometheus scrape workers: `--query.max-concurrency=20`
3. Enable compression in Prometheus
4. Use recording rules for frequent queries

### Grafana optimization:

1. Reduce dashboard refresh rate: 30s → 60s
2. Disable unused panels
3. Use `clamp_max` in queries to prevent cardinality explosion
4. Enable query caching

## Maintenance

### Daily

- Monitor dashboard for anomalies
- Review alert firing patterns
- Check storage usage: `du -sh /path/to/prometheus/data`

### Weekly

- Review alerting rules effectiveness
- Check for missing metrics or gaps
- Clean up old dashboard versions

### Monthly

- Update Prometheus/Grafana/Alertmanager versions
- Review and rotate notification credentials
- Analyze performance trends
- Capacity planning for growing metrics volume

## Production Deployment

### Recommended Setup:

```
Load Balancer
    ↓
┌─────────────────────┐
│  Loom Cluster       │ (3+ instances)
└─────┬───────────────┘
      ↓
┌─────────────────────┐
│ Prometheus + HA     │ (2 instances with Thanos)
└─────┬───────────────┘
      ↓
┌─────────────────────┐
│ Grafana + Alertmgr  │
└─────────────────────┘
```

### High Availability:

1. Run 2+ Prometheus instances
2. Use Thanos for long-term storage
3. Setup Alertmanager clustering
4. Use persistent volumes for data
5. Configure service discovery (Consul, etcd)

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## License

This monitoring configuration is part of the Loom project.
