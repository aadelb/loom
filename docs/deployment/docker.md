# Docker Deployment

Run Loom in Docker for easy portability, isolation, and scaling. The Docker image includes all dependencies (Playwright browsers, Camoufox, Python 3.11).

## Quick Start

Pull the latest image from GitHub Container Registry:

```bash
docker pull ghcr.io/aadelb/loom:latest
docker run -p 127.0.0.1:8787:8787 ghcr.io/aadelb/loom:latest
```

The server listens on `http://127.0.0.1:8787/mcp`.

Or build locally from the repository:

```bash
git clone https://github.com/aadelb/loom.git
cd loom
docker build -t loom:dev -f deploy/docker/Dockerfile .
docker run -p 127.0.0.1:8787:8787 loom:dev
```

## With Persistent Storage

Bind mount cache, logs, sessions, and optional config:

```bash
mkdir -p cache logs sessions
docker run -p 127.0.0.1:8787:8787 \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/sessions:/app/sessions \
  ghcr.io/aadelb/loom:latest
```

If you have a `config.json` file, mount it as read-only:

```bash
docker run -p 127.0.0.1:8787:8787 \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/config.json:/app/config.json:ro \
  ghcr.io/aadelb/loom:latest
```

## With Environment Variables

Pass API keys as environment variables:

```bash
docker run -p 127.0.0.1:8787:8787 \
  -e NVIDIA_NIM_API_KEY="your_key" \
  -e OPENAI_API_KEY="your_openai_key" \
  -e EXA_API_KEY="your_exa_key" \
  ghcr.io/aadelb/loom:latest
```

Or use a `.env` file:

```bash
docker run -p 127.0.0.1:8787:8787 \
  --env-file .env \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/sessions:/app/sessions \
  ghcr.io/aadelb/loom:latest
```

## docker-compose

For easier management and volume persistence, use docker-compose. Create `docker-compose.yml`:

```yaml
version: "3.9"

services:
  loom:
    image: ghcr.io/aadelb/loom:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8787:8787"
    volumes:
      - ./cache:/app/cache
      - ./logs:/app/logs
      - ./sessions:/app/sessions
      - ./config.json:/app/config.json:ro
    env_file: .env
    mem_limit: 16g
    cpus: "4.0"
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test:
        - "CMD"
        - "curl"
        - "-X"
        - "POST"
        - "-f"
        - "http://127.0.0.1:8787/mcp"
        - "-H"
        - "Content-Type: application/json"
        - "-d"
        - '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"hc","version":"1"}}}'
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s
```

Create `.env` from the example:

```bash
cp deploy/.env.example .env
# Edit .env with your API keys
nano .env
```

Start, view logs, and stop:

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f loom

# Stop and remove containers
docker-compose down

# Stop but keep containers (useful for quick restart)
docker-compose stop
docker-compose start
```

## Health Check

The Dockerfile includes a built-in health check that probes the MCP initialize endpoint:

```bash
# Check container health status
docker ps --filter "name=loom"

# Status column will show "healthy", "unhealthy", or "starting"
```

The health check runs every 30 seconds after a 40-second startup grace period. Check detailed health:

```bash
docker inspect --format='{{json .State.Health}}' <container_id> | jq
```

## Resource Limits

Loom performs heavy browser automation and caching. Set appropriate limits:

```bash
docker run -p 127.0.0.1:8787:8787 \
  --memory="16g" \
  --cpus="4.0" \
  ghcr.io/aadelb/loom:latest
```

In docker-compose (from template):

```yaml
mem_limit: 16g
cpus: "4.0"
```

Monitor real-time usage:

```bash
docker stats loom
```

If the container is killed for exceeding memory (exit code 137), increase the limit or reduce `SPIDER_CONCURRENCY` in your `.env` file.

## Networking

### Localhost Only (Default, Recommended)

```bash
docker run -p 127.0.0.1:8787:8787 ghcr.io/aadelb/loom:latest
```

Only accessible from your machine. Secure by default.

### Allow Remote Access

```bash
docker run -p 8787:8787 ghcr.io/aadelb/loom:latest
```

Accessible from any machine on your network. Use only if behind a firewall or on a private network.

**Warning:** Exposing the MCP endpoint to untrusted networks enables arbitrary research tool invocation (fetch, search, LLM calls cost money). Always use a reverse proxy with authentication in production.

## Updating

Pull the latest image:

```bash
docker pull ghcr.io/aadelb/loom:latest
docker-compose up -d --pull always
```

## Volumes and Persistence

| Mount Path | Purpose | Typical Size |
|-----------|---------|--|
| `/app/cache` | HTML, JSON, markdown cache | 1–10 GB |
| `/app/logs` | Application logs | 100–500 MB |
| `/app/sessions` | Browser session profiles | 100–500 MB |
| `/app/config.json` | Runtime config | < 1 MB |

Use named volumes for better management:

```bash
docker volume create loom-cache
docker volume create loom-logs
docker volume create loom-sessions

docker run -p 127.0.0.1:8787:8787 \
  -v loom-cache:/app/cache \
  -v loom-logs:/app/logs \
  -v loom-sessions:/app/sessions \
  ghcr.io/aadelb/loom:latest
```

Or bind-mount directories (lose data if you delete the local dir):

```bash
mkdir -p loom/{cache,logs,sessions}
docker run -p 127.0.0.1:8787:8787 \
  -v $(pwd)/loom/cache:/app/cache \
  -v $(pwd)/loom/logs:/app/logs \
  -v $(pwd)/loom/sessions:/app/sessions \
  ghcr.io/aadelb/loom:latest
```

## Troubleshooting

### Container exits with "Killed" (exit 137)

Out of memory. Increase the limit:

```yaml
mem_limit: 32g
```

Or reduce concurrency in `.env`:

```bash
SPIDER_CONCURRENCY=3
```

### Playwright fails to start inside container

The Dockerfile installs system dependencies for Chromium and Firefox. If you see browser errors, ensure the image is up-to-date:

```bash
docker pull ghcr.io/aadelb/loom:latest
docker-compose up -d --pull always
```

### Camoufox takes 30+ seconds to start

Camoufox (stealth Firefox) requires extra initialization. The health check accounts for this (40-second startup grace period). On the first run, it may be slower as it caches the Firefox distribution in `/app/cache`.

### Port 8787 already in use

Either kill the process or use a different port:

```bash
docker run -p 127.0.0.1:8788:8787 ghcr.io/aadelb/loom:latest
```

Then update your Claude Code config to use port 8788.

## Building Locally

To build your own image (e.g., for modifications):

```bash
git clone https://github.com/aadelb/loom.git
cd loom
docker build -t loom:custom -f deploy/docker/Dockerfile .
docker run -p 127.0.0.1:8787:8787 loom:custom
```

## Related Documentation

- [docs/installation.md](../installation.md) — Installation options
- [docs/deployment/systemd.md](systemd.md) — systemd service
- [docs/deployment/kubernetes.md](kubernetes.md) — Kubernetes deployment
- [docs/deployment/claude-code-integration.md](claude-code-integration.md) — Claude Code setup
