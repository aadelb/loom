# Loom Microservices Architecture

This directory contains the configuration for deploying Loom as a distributed microservices system using Docker Compose. The monolithic MCP server is split into four specialized services with a shared infrastructure layer (Redis, PostgreSQL) and an Nginx API Gateway for intelligent routing.

## Architecture Overview

```
                           ┌─────────────────────────────────────┐
                           │   API Gateway (Nginx)               │
                           │   Port: 8800                        │
                           │ - Rate limiting per service         │
                           │ - Intelligent routing               │
                           │ - Health checks                     │
                           └────────────┬────────────────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
                ▼                       ▼                       ▼
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  LOOM-CORE       │  │ LOOM-REDTEAM     │  │  LOOM-INTEL      │
        │  Port: 8787      │  │ Port: 8788       │  │  Port: 8789      │
        │                  │  │                  │  │                  │
        │ Research Tools:  │  │ AI Safety:       │  │ OSINT & Dark Web:│
        │ - fetch          │  │ - reframe        │  │ - dark_forum     │
        │ - search         │  │ - safety_filter  │  │ - threat_profile │
        │ - deep           │  │ - crescendo      │  │ - social_graph   │
        │ - markdown       │  │ - consensus      │  │ - leak_scan      │
        │ - spider         │  │ - adversarial    │  │ - osint          │
        │ - llm            │  │                  │  │ - privacy        │
        └──────────────────┘  └──────────────────┘  └──────────────────┘
                │                       │                       │
                └───────────────────────┼───────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │   LOOM-INFRA (Port: 8790)             │
                    │   Infrastructure Services:            │
                    │   - billing                           │
                    │   - auth                              │
                    │   - jobs (batch)                      │
                    │   - monitoring                        │
                    │   - config                            │
                    │   - session                           │
                    └───────────────────────────────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
                ▼                       ▼                       ▼
        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
        │    Redis     │        │  PostgreSQL  │        │  S3/Storage  │
        │ Port: 6379   │        │ Port: 5432   │        │  (Optional)  │
        │              │        │              │        │              │
        │ - Cache      │        │ - Audit logs │        │ - Archive    │
        │ - Sessions   │        │ - Configs    │        │ - Exports    │
        │ - Locks      │        │ - Billing    │        │              │
        │ - Queues     │        │ - Auth       │        │              │
        └──────────────┘        └──────────────┘        └──────────────┘
```

## Service Boundaries

### LOOM-CORE (Port 8787)
**Purpose:** Primary research and data gathering

**Tools Enabled:**
- `research_fetch` — Single-URL scraping with Scrapling 3-tier escalation
- `research_search` — Multi-provider semantic search (Exa, Tavily, Brave, DuckDuckGo, Arxiv, etc.)
- `research_deep` — 12-stage deep research pipeline
- `research_markdown` — HTML-to-Markdown conversion (Crawl4AI, Trafilatura)
- `research_spider` — Concurrent multi-URL fetching
- `research_llm_*` — LLM integration tools (summarize, extract, classify, translate)
- `research_session_*` — Browser session management

**Database Access:** Redis DB 0, PostgreSQL (loom_shared schema)

**Resource Profile:**
- CPU: High (web scraping + LLM calls)
- Memory: Medium (cached pages, sessions)
- Network: High (external requests)

**Scaling:** Horizontal (stateless, requests → Redis cache)

---

### LOOM-REDTEAM (Port 8788)
**Purpose:** AI safety testing and adversarial attacks

**Tools Enabled:**
- `research_reframe_*` — Prompt reframing/jailbreak strategies (957 total)
- `research_safety_*` — Safety filter mapping, compliance checking
- `research_crescendo_loop` — Incremental harm escalation
- `research_consensus_*` — Multi-model consensus and pressure
- `research_adversarial_*` — Adversarial debate frameworks
- `research_model_profile` — Model capability profiling

**Database Access:** Redis DB 1, PostgreSQL (loom_shared schema)

**Resource Profile:**
- CPU: Very high (LLM reasoning, strategy evaluation)
- Memory: High (strategy registry, attack traces)
- Network: Medium (LLM APIs only)

**Scaling:** Vertical preferred (shared strategy registry); horizontal with Redis sync

---

### LOOM-INTEL (Port 8789)
**Purpose:** OSINT, dark web, threat intelligence, privacy research

**Tools Enabled:**
- `research_dark_*` — Dark web search and forum scraping
- `research_threat_*` — Threat intelligence and adversary profiling
- `research_osint_*` — Open-source intelligence gathering
- `research_privacy_*` — Privacy exposure audits, fingerprinting, anti-forensics
- `research_leak_scan` — Breach database + paste site scanning
- `research_social_graph` — Relationship mapping across platforms
- `research_passive_recon` — DNS, WHOIS, ASN enrichment
- `research_infra_*` — Infrastructure correlation and graveyard analysis

**Database Access:** Redis DB 2, PostgreSQL (loom_shared schema)

**Resource Profile:**
- CPU: Medium (parsing, regex, analysis)
- Memory: Medium (session management)
- Network: Very high (dark web, external APIs)

**Scaling:** Horizontal (stateless, request → Redis cache)

**Special Notes:**
- `TOR_ENABLED` flag controls Tor integration (disabled by default)
- Consider rate limits on darknet queries to avoid IP blocking

---

### LOOM-INFRA (Port 8790)
**Purpose:** Infrastructure, billing, authentication, operations

**Tools Enabled:**
- `research_billing_*` — Cost tracking, credit management, usage metering
- `research_auth_*` — API key validation, authorization policies
- `research_batch_*` — Job queue submission, status polling, orchestration
- `research_config_*` — Runtime configuration management
- `research_session_persistent` — Session lifecycle (create, list, close)
- `research_monitoring_*` — Metrics, health checks, dashboards
- `research_rate_limits` — Per-user/per-service rate limit enforcement
- `research_validate_startup` — Health check and validation

**Database Access:** Redis DB 3, PostgreSQL (loom_shared schema)

**Resource Profile:**
- CPU: Low
- Memory: Low
- Network: Low (internal only)

**Scaling:** Horizontal (stateless, distributed lock via PostgreSQL)

---

## Deployment Instructions

### Prerequisites

- Docker & Docker Compose (v1.28+)
- 8+ GB available RAM
- 20+ GB disk space
- Bash shell

### Quick Start

```bash
cd /Users/aadel/projects/loom/microservices

# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your API keys
nano .env

# 3. Create service-specific configs (optional — uses defaults if missing)
mkdir -p services/{core,redteam,intel,infra}/
# (sample configs in services/ subdir — or omit to use compiled defaults)

# 4. Start all services
docker-compose up -d

# 5. Verify services are healthy
docker-compose ps
curl http://localhost:8800/status
```

### Environment Setup

Before running `docker-compose up -d`:

1. **API Keys:** Edit `.env` and add your credentials for:
   - LLM providers (Groq, DeepSeek, Gemini, etc.)
   - Search providers (Exa, Tavily, Firecrawl, etc.)
   - Infrastructure (VastAI, Stripe, Joplin, etc.)

2. **Database:** Postgres password in `.env` should match `docker-compose.yml`:
   ```bash
   # Default is fine for dev/test, change for production
   POSTGRES_PASSWORD=loom_secure_password_change_in_prod
   ```

3. **Feature Flags:** Enable/disable tool categories per service:
   ```bash
   # In .env, set to true/false
   ENABLE_DARK_WEB_TOOLS=true  # in loom-intel only
   ENABLE_BILLING_TOOLS=true   # in loom-infra only
   ```

### Service-Specific Configuration

Each service can have its own `config.json` (optional):

```bash
# Create directory
mkdir -p services/core

# Create config (overrides defaults from CONFIG dict)
cat > services/core/config.json <<'EOF'
{
  "SPIDER_CONCURRENCY": 10,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "MAX_SPIDER_URLS": 100,
  "DEFAULT_SEARCH_PROVIDER": "exa"
}
EOF
```

If no config files exist, services use compiled defaults from `src/loom/config.py`.

### Verifying Deployment

```bash
# Check service health
curl http://localhost:8800/health     # Gateway
curl http://localhost:8787/health     # Core
curl http://localhost:8788/health     # RedTeam
curl http://localhost:8789/health     # Intel
curl http://localhost:8790/health     # Infra

# View all services
docker-compose ps

# Check logs
docker-compose logs -f loom-core      # Core service
docker-compose logs -f loom-gateway   # Gateway
```

### Logs & Debugging

```bash
# Tail all service logs
docker-compose logs -f --tail 100

# Single service logs
docker-compose logs -f loom-redteam --tail 50

# Shell into a container
docker-compose exec loom-core bash
```

### Stopping Services

```bash
# Stop all containers (preserve volumes)
docker-compose stop

# Stop and remove containers (preserve volumes)
docker-compose down

# Full cleanup (WARNING: deletes data!)
docker-compose down -v
```

## Scaling Strategy

### Horizontal Scaling (add more replicas)

For **stateless services** (Core, Intel), scale up with Docker Compose or Kubernetes:

```yaml
# docker-compose.override.yml (extends docker-compose.yml)
version: '3.8'
services:
  loom-core:
    deploy:
      replicas: 3  # Scale to 3 instances
  
  loom-intel:
    deploy:
      replicas: 2  # Scale to 2 instances
```

Then update Nginx to round-robin across replicas:

```nginx
upstream loom_core {
    least_conn;
    server loom-core-1:8787 max_fails=3 fail_timeout=30s;
    server loom-core-2:8787 max_fails=3 fail_timeout=30s;
    server loom-core-3:8787 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

### Vertical Scaling (add more resources)

For **compute-heavy services** (RedTeam with LLM reasoning):

```bash
# Increase memory limit
docker-compose exec loom-redteam env | grep _SIZE

# Or update docker-compose.yml:
services:
  loom-redteam:
    # ... other config
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 16G
        reservations:
          cpus: "2.0"
          memory: 8G
```

### Database Scaling

**PostgreSQL:**
- Replicate with streaming replication (primary → standby)
- Use connection pooling (PgBouncer) for high concurrency
- Partition large tables (audit logs, billing records) by time

**Redis:**
- Use Redis Cluster for horizontal partitioning
- Sentinel for HA (automatic failover)
- Update `REDIS_URL` to point to cluster endpoint

## Routing & Request Flow

### Nginx Gateway Routing Rules

| Pattern | Service | Rate Limit | Timeout |
|---------|---------|------------|---------|
| `/v1/tools/research_fetch*` | loom-core | 100 req/s | 300s |
| `/v1/tools/research_search*` | loom-core | 100 req/s | 300s |
| `/v1/tools/research_deep*` | loom-core | 100 req/s | 300s |
| `/v1/tools/research_reframe*` | loom-redteam | 50 req/s | 300s |
| `/v1/tools/research_safety*` | loom-redteam | 50 req/s | 300s |
| `/v1/tools/research_dark*` | loom-intel | 75 req/s | 600s |
| `/v1/tools/research_threat*` | loom-intel | 75 req/s | 600s |
| `/v1/billing/*` | loom-infra | 200 req/s | 60s |
| `/v1/config/*` | loom-infra | 200 req/s | 60s |
| `/*` (fallback) | loom-core | 100 req/s | 300s |

### Example Request Flow

```
Client → Gateway (8800)
  ↓
/v1/tools/research_fetch?url=...
  ↓
Gateway reads pattern, routes to loom-core:8787
  ↓
Rate limiter checks: 100 req/s burst 20
  ↓
Proxy to upstream, X-Service: core header added
  ↓
Response → Client (via gateway)
```

## Performance Tuning

### Redis Optimization

```bash
# Increase max memory and eviction policy
docker-compose exec redis redis-cli CONFIG SET maxmemory 4gb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### PostgreSQL Optimization

```bash
# Check current config
docker-compose exec postgres psql -U loom -d loom_shared -c "SHOW shared_buffers;"

# For 8 GB system:
# shared_buffers = 2GB (25% of RAM)
# effective_cache_size = 6GB (75% of RAM)
# work_mem = 32MB
```

### Nginx Optimization

- Adjust `worker_connections` (default 1024)
- Increase `proxy_buffering` for large responses
- Enable compression: `gzip on;`

## Monitoring & Observability

### Health Checks

Each service exposes `/health` endpoint:

```bash
curl -s http://localhost:8787/health | jq
{
  "status": "ok",
  "service": "core",
  "uptime_seconds": 3600,
  "tools_registered": 45
}
```

### Metrics (Prometheus)

Services export Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8787/metrics | grep loom_tool_calls_total
loom_tool_calls_total{tool_name="research_fetch", status="ok"} 1234
```

### Logs

All services log to stdout (captured by Docker):

```bash
docker-compose logs -f | grep "ERROR\|WARN"
```

## Security & Network

### API Authentication

Each request to Gateway should include API key:

```bash
curl -H "X-Loom-API-Key: your-secret-key" http://localhost:8800/v1/tools/research_fetch?url=...
```

**Note:** API key validation happens in `loom-infra` service. Configure in `.env`:

```bash
API_KEY_REQUIRED=true
API_KEY_HEADER=X-Loom-API-Key
```

### Network Isolation

In production, use internal Docker network only (no ports exposed):

```yaml
# docker-compose.prod.yml
services:
  loom-core:
    ports: []  # No external port
    networks:
      - loom-network  # Internal only
```

Then put Nginx behind reverse proxy (Traefik, HAProxy, etc.) with SSL/TLS.

### Rate Limiting

Nginx enforces per-service rate limits:

- **loom-core:** 100 req/s
- **loom-redteam:** 50 req/s
- **loom-intel:** 75 req/s
- **loom-infra:** 200 req/s

Override in `gateway/nginx.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=core_limit:10m rate=100r/s;
```

## Troubleshooting

### Service fails to start

```bash
# Check logs
docker-compose logs loom-core | tail -20

# Common issues:
# 1. Port already in use: change LOOM_PORT in .env
# 2. Missing API keys: set in .env
# 3. Database connection: check POSTGRES_PASSWORD matches
```

### Slow requests / timeouts

```bash
# Check service metrics
curl http://localhost:8787/metrics | grep duration

# Increase timeout in .env
EXTERNAL_TIMEOUT_SECS=60

# Check Nginx upstream response time
docker-compose logs loom-gateway | grep upstream_response_time
```

### Redis/PostgreSQL down

```bash
# Check status
docker-compose ps

# Restart infrastructure
docker-compose restart redis postgres

# Verify connectivity from services
docker-compose exec loom-core redis-cli -h redis ping
docker-compose exec loom-core psql postgresql://loom:pass@postgres/loom_shared -c "SELECT 1"
```

### High memory usage

```bash
# Check container memory
docker stats

# Reduce concurrency
SPIDER_CONCURRENCY=5
LLM_MAX_PARALLEL=6

# Clear cache
docker-compose exec redis redis-cli FLUSHDB
```

## Migration from Monolith

To migrate from the original monolithic server:

1. **Backward Compatibility:** All microservices implement the same MCP tool interface
2. **Data Migration:** Export config/sessions from old server, import to new PostgreSQL
3. **Cutover:** Point clients from `http://localhost:8787` to `http://localhost:8800` (Gateway)
4. **Validation:** Run integration tests against gateway to verify routing

## Production Deployment (Kubernetes)

For Kubernetes, convert this Docker Compose to Helm charts:

```bash
# Generate Kubernetes manifests
kompose convert -f docker-compose.yml

# Deploy to K8s
kubectl apply -f loom-core-deployment.yaml
kubectl apply -f loom-redteam-deployment.yaml
kubectl apply -f loom-intel-deployment.yaml
kubectl apply -f loom-infra-deployment.yaml
kubectl apply -f loom-gateway-deployment.yaml
kubectl apply -f redis-statefulset.yaml
kubectl apply -f postgres-statefulset.yaml
```

See `deploy/k8s/` for example manifests (when available).

## Files & Structure

```
microservices/
├── docker-compose.yml         ← Main orchestration config
├── Dockerfile                 ← Shared multi-stage build
├── .env.example               ← Environment template
├── gateway/
│   └── nginx.conf             ← Routing, rate limiting
├── services/
│   ├── core/
│   │   └── config.json        ← (Optional) Service-specific config
│   ├── redteam/
│   │   └── config.json
│   ├── intel/
│   │   └── config.json
│   └── infra/
│       └── config.json
└── README.md                  ← This file
```

## References

- **Server Code:** `src/loom/server.py` (tool registration)
- **Config Schema:** `src/loom/config.py` (ConfigModel)
- **Tools Reference:** `docs/tools-reference.md` (220+ tools)
- **API Docs:** `docs/api.md` (MCP endpoints)

---

**Author:** Ahmed Adel Bakr Alderai  
**Last Updated:** 2026-05-04  
**Status:** Planning Phase (Architecture Only)
