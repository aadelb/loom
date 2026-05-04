# Loom Monitoring Stack - Deployment Checklist

Use this checklist to deploy and verify the monitoring stack.

## Pre-Deployment

- [ ] Docker is installed (`docker --version`)
- [ ] Docker daemon is running (`docker ps`)
- [ ] Docker Compose is installed (`docker-compose --version`)
- [ ] Loom MCP server is running on `127.0.0.1:8787`
- [ ] prometheus-client is installed in Loom environment (`pip list | grep prometheus`)
- [ ] At least 6 GB disk space available for metrics storage
- [ ] At least 4 GB RAM available for monitoring stack

## Installation

- [ ] Navigate to monitoring directory: `cd monitoring`
- [ ] Review setup.sh: `cat setup.sh`
- [ ] Run automated setup: `bash setup.sh`
  - [ ] Docker validation passes
  - [ ] Configuration files are valid
  - [ ] JSON validation passes
  - [ ] YAML validation passes
  - [ ] Services pull successfully
  - [ ] Containers start successfully
  - [ ] Services pass health checks

## Alternative: Manual Installation

- [ ] Pull Docker images: `docker-compose pull`
- [ ] Start stack: `docker-compose up -d`
- [ ] Wait 30 seconds for initialization
- [ ] Check services: `docker-compose ps`
  - [ ] prometheus: healthy
  - [ ] grafana: healthy
  - [ ] alertmanager: healthy
  - [ ] node-exporter: healthy (optional)
  - [ ] cadvisor: healthy (optional)

## Service Verification

- [ ] Prometheus is accessible: `curl http://localhost:9090`
  - [ ] Status page loads
  - [ ] Targets show (http://localhost:9090/targets)
  - [ ] Loom target shows "UP"
  - [ ] Metrics are being scraped

- [ ] Grafana is accessible: `curl http://localhost:3000`
  - [ ] Login page loads
  - [ ] Default credentials work (admin/admin)
  - [ ] Prometheus datasource is configured
  - [ ] Dashboard is imported

- [ ] AlertManager is accessible: `curl http://localhost:9093`
  - [ ] Web UI loads
  - [ ] Config is valid

## Metrics Verification

- [ ] Prometheus is collecting Loom metrics:
  ```bash
  curl http://localhost:9090/api/v1/query?query=loom_tool_calls_total
  ```
  - [ ] Returns results
  - [ ] Has data points

- [ ] Check metric labels exist:
  - [ ] loom_tool_calls_total
  - [ ] loom_tool_duration_seconds
  - [ ] loom_tool_errors_total
  - [ ] loom_circuit_breaker_open
  - [ ] loom_active_connections
  - [ ] loom_cache_hits
  - [ ] loom_cache_misses

## Dashboard Verification

- [ ] Navigate to Grafana: http://localhost:3000
- [ ] Login with admin/admin
- [ ] Dashboard is visible in menu
- [ ] Open dashboard: http://localhost:3000/d/loom-monitoring
- [ ] All 8 panels load:
  - [ ] Tool Calls Per Second - shows data
  - [ ] Error Rate - shows data
  - [ ] P95 & P99 Latency - shows data
  - [ ] Top 10 Tools - shows data
  - [ ] Circuit Breaker Status - shows table
  - [ ] Memory Usage - shows data
  - [ ] Active Connections - shows data
  - [ ] Cache Hit Rate - shows data
- [ ] Time range selector works
- [ ] Tool name filter works
- [ ] Dashboard refreshes every 30 seconds

## Alert Rules Verification

- [ ] Navigate to Prometheus Alerts: http://localhost:9090/alerts
- [ ] All alert rules are loaded:
  - [ ] LoomHighErrorRate
  - [ ] LoomHighLatency
  - [ ] LoomVeryHighLatency
  - [ ] LoomCircuitOpen
  - [ ] LoomHighMemory
  - [ ] LoomCriticalMemory
  - [ ] LoomDown
  - [ ] LoomNoToolCalls
  - [ ] LoomCacheHitRateLow
- [ ] Recording rules are loaded
- [ ] No errors in alert evaluation

## Alerting Configuration

- [ ] Edit alertmanager.yml:
  ```bash
  nano monitoring/alertmanager.yml
  ```
  - [ ] Update SMTP configuration (if using email)
  - [ ] Add Slack webhook URL (if using Slack)
  - [ ] Add PagerDuty service key (if using PagerDuty)
  - [ ] Update notification receivers with real addresses

- [ ] Reload AlertManager:
  ```bash
  docker-compose restart alertmanager
  ```

- [ ] Test notifications:
  - [ ] Send test alert via Prometheus
  - [ ] Verify email received (if configured)
  - [ ] Verify Slack message (if configured)
  - [ ] Verify PagerDuty incident (if configured)

## Performance Validation

- [ ] Check memory usage:
  ```bash
  docker stats
  ```
  - [ ] prometheus: < 2 GB
  - [ ] grafana: < 500 MB
  - [ ] alertmanager: < 100 MB

- [ ] Check disk usage:
  ```bash
  du -sh monitoring/data/*
  ```
  - [ ] prometheus_data: reasonable size (grows over time)

- [ ] Check query performance:
  - [ ] Prometheus queries complete < 1 second
  - [ ] Grafana dashboard loads < 3 seconds

## Monitoring Validation

- [ ] Generate some Loom traffic for 1 minute
- [ ] Check that metrics increase:
  ```bash
  curl 'http://localhost:9090/api/v1/query?query=rate(loom_tool_calls_total[1m])'
  ```

- [ ] Verify dashboard shows increased activity
- [ ] Check error rate metrics are calculated
- [ ] Verify latency percentiles are computed

## Backup & Recovery

- [ ] Document data backup location
- [ ] Setup backup cron job (optional):
  ```bash
  tar -czf loom-monitoring-backup-$(date +%Y%m%d).tar.gz monitoring/data/
  ```

- [ ] Test restore procedure (optional)

## Production Readiness

If deploying to production:

- [ ] Change Grafana default password
  ```bash
  # In docker-compose.yml, update GF_SECURITY_ADMIN_PASSWORD
  ```

- [ ] Configure persistent volumes for production persistence

- [ ] Setup HTTPS for Grafana and Prometheus (nginx reverse proxy recommended)

- [ ] Configure log rotation:
  ```bash
  docker-compose logs --tail 0 -f
  ```

- [ ] Setup metrics retention policy:
  - [ ] Edit prometheus.yml: `--storage.tsdb.retention.time=30d`
  - [ ] Restart Prometheus: `docker-compose restart prometheus`

- [ ] Implement remote storage backend (optional, for HA):
  - [ ] Thanos
  - [ ] M3DB
  - [ ] Amazon S3 + sidecar

- [ ] Setup Prometheus high availability (optional, for HA):
  - [ ] Run 2+ Prometheus instances
  - [ ] Configure deduplication labels

## Documentation

- [ ] Read README.md for detailed information
- [ ] Read QUICKSTART.md for quick reference
- [ ] Read MANIFEST.md for file inventory
- [ ] Keep documentation current as stack evolves

## Ongoing Maintenance

- [ ] Daily: Monitor alert patterns in AlertManager
- [ ] Daily: Check dashboard for anomalies
- [ ] Weekly: Review alert thresholds
- [ ] Weekly: Check disk usage trends
- [ ] Monthly: Update Docker images
- [ ] Monthly: Review and test disaster recovery
- [ ] Quarterly: Capacity planning

## Troubleshooting

If issues arise, consult:
- README.md "Troubleshooting" section
- QUICKSTART.md "Troubleshooting" section
- docker-compose logs: `docker-compose logs [service]`
- Prometheus UI: http://localhost:9090
- Grafana logs: `docker-compose logs grafana`

## Sign-Off

- [ ] Monitoring stack is deployed
- [ ] All services are healthy
- [ ] Dashboard is populated with data
- [ ] Alerts are configured and tested
- [ ] Documentation is reviewed
- [ ] Team is trained on usage
- [ ] Runbooks are prepared
- [ ] On-call rotation is setup

**Deployment Date:** _______________

**Deployed By:** _______________

**Verified By:** _______________

**Notes:**
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________
