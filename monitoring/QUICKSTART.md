# Loom Monitoring - Quick Start Guide

Get Loom MCP Server monitoring up and running in 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- Loom MCP server running on `localhost:8787`
- `prometheus-client` installed in Loom environment (`pip install prometheus-client`)

## One-Command Setup

```bash
cd monitoring
bash setup.sh
```

This script will:
1. Validate Docker installation
2. Check all configuration files
3. Pull Docker images
4. Start Prometheus, Grafana, and Alertmanager
5. Display service URLs

## Manual Setup (if setup.sh fails)

```bash
cd monitoring
docker-compose up -d
```

## Verify Installation

```bash
# Check all services are running
docker-compose ps

# Check Prometheus is scraping metrics
curl http://localhost:9090/api/v1/query?query=loom_tool_calls_total

# Check Grafana is accessible
curl http://localhost:3000/api/health
```

## Access Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | — |
| **Alertmanager** | http://localhost:9093 | — |

## Import Dashboard

The dashboard is **automatically provisioned** in Grafana when using docker-compose.

If manual import needed:
1. Login to Grafana (admin/admin)
2. Click **+ → Import Dashboard**
3. Upload `grafana-dashboard.json`
4. Select "Prometheus" data source
5. Click **Import**

## Common Tasks

### View Real-Time Metrics

```bash
# In Prometheus UI
http://localhost:9090/graph
# Query: loom_tool_calls_total
```

### Check if Alerts Are Firing

```bash
# In Prometheus UI
http://localhost:9090/alerts

# Or via API
curl http://localhost:9090/api/v1/alerts
```

### Configure Notifications

Edit `alertmanager.yml` and update notification receivers (email, Slack, PagerDuty).

Then reload config:

```bash
docker-compose restart alertmanager
```

### View Prometheus Logs

```bash
docker-compose logs -f prometheus
```

### View Grafana Logs

```bash
docker-compose logs -f grafana
```

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove All Data

```bash
docker-compose down -v
```

## Troubleshooting

### "No Data" in Grafana Dashboard

1. Verify Loom is running: `curl http://127.0.0.1:8787/metrics`
2. Check Prometheus scraped any metrics:
   ```bash
   curl http://localhost:9090/api/v1/targets | grep loom
   ```
3. Wait 30 seconds for first data point

### Prometheus Shows "Down" for Loom

1. Check Loom is accessible:
   ```bash
   curl http://127.0.0.1:8787/
   ```
2. Verify `/metrics` endpoint exists:
   ```bash
   curl http://127.0.0.1:8787/metrics
   ```

### Alerts Not Firing

1. Check alert rules loaded: http://localhost:9090/alerts
2. Verify alertmanager is running: `docker-compose ps`
3. Check alertmanager logs: `docker-compose logs alertmanager`

### High Resource Usage

1. Reduce Prometheus retention:
   ```yaml
   # In docker-compose.yml, modify prometheus command:
   - "--storage.tsdb.retention.time=7d"
   ```
2. Restart: `docker-compose restart prometheus`

## Dashboard Panels

| Panel | What It Shows |
|-------|---------------|
| **Tool Calls Per Second** | Real-time throughput |
| **Error Rate** | Percentage of failed calls (threshold: 5%) |
| **P95 & P99 Latency** | Response time percentiles (threshold: 10s) |
| **Top 10 Tools** | Tools by call volume |
| **Circuit Breaker Status** | Health of external services |
| **Memory Usage** | Process RAM consumption (threshold: 6GB) |
| **Active Connections** | Current connected clients |
| **Cache Hit Rate** | Cache effectiveness (goal: >75%) |

## Key Metrics

```promql
# Tool calls per second
rate(loom_tool_calls_total[1m])

# Error rate percentage
(rate(loom_tool_errors_total[5m]) / rate(loom_tool_calls_total[5m])) * 100

# P95 latency
histogram_quantile(0.95, loom_tool_duration_seconds_bucket)

# Top tools by volume
topk(10, rate(loom_tool_calls_total[5m]))

# Cache hit rate
(loom_cache_hits / (loom_cache_hits + loom_cache_misses)) * 100
```

## What's Being Monitored

✓ Tool execution calls and errors  
✓ Response latency (p50, p95, p99)  
✓ Circuit breaker status  
✓ Memory usage  
✓ Active connections  
✓ Cache statistics  
✓ Error types and patterns  

## Production Setup

For production deployment:

1. **Update Alertmanager config** with real notification endpoints
2. **Set strong Grafana password** (don't use default admin/admin)
3. **Configure persistent volumes** or remote storage
4. **Setup Prometheus backup** strategy
5. **Enable HTTPS** for all services
6. **Configure resource limits** in docker-compose.yml

See `README.md` for detailed production guidelines.

## Support

- **Prometheus docs**: https://prometheus.io/docs/
- **Grafana docs**: https://grafana.com/docs/
- **Alertmanager docs**: https://prometheus.io/docs/alerting/latest/
- **Loom project**: https://github.com/yourusername/loom

## Next Steps

1. Access Grafana: http://localhost:3000
2. Open dashboard: "Loom MCP Server"
3. Monitor for 5 minutes to verify data flow
4. Configure alerting notifications
5. Set up on-call rotation in PagerDuty/Slack
