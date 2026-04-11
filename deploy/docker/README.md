# Docker Deployment Guide for Loom

This directory contains Docker and docker-compose configurations to run Loom as a containerized service.

## Prerequisites

- Docker 20.10+ (with BuildKit enabled)
- docker-compose 1.29+ (or `docker compose` plugin)
- At least 16 GB free disk space for browser binaries and cache

## Building the Image

### Option 1: Build Locally

```bash
docker build -t ghcr.io/aadelb/loom:latest -f deploy/docker/Dockerfile .
```

### Option 2: Pull Pre-built Image

```bash
docker pull ghcr.io/aadelb/loom:latest
```

## Running with docker-compose

1. **Copy the environment template:**

```bash
cp deploy/.env.example .env
```

Edit `.env` and add your API keys for search providers (Exa, Tavily, Firecrawl, Brave) and LLM providers (NVIDIA NIM, OpenAI, Anthropic).

2. **Create required directories:**

```bash
mkdir -p cache logs sessions
```

3. **Start the service:**

```bash
docker-compose -f deploy/docker/docker-compose.yml up -d
```

4. **Verify the service is healthy:**

```bash
docker-compose -f deploy/docker/docker-compose.yml ps
# Should show "healthy" status after ~30 seconds
```

5. **Test the MCP endpoint:**

```bash
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

## Running with docker run

```bash
docker run -d \
  --name loom \
  --restart unless-stopped \
  -p 127.0.0.1:8787:8787 \
  -v $PWD/cache:/app/cache \
  -v $PWD/logs:/app/logs \
  -v $PWD/sessions:/app/sessions \
  --env-file .env \
  --memory 16g \
  --cpus 4.0 \
  --security-opt no-new-privileges:true \
  ghcr.io/aadelb/loom:latest
```

## Managing the Container

### View logs

```bash
docker-compose -f deploy/docker/docker-compose.yml logs -f loom
# Or with plain docker:
docker logs -f loom
```

### Restart the service

```bash
docker-compose -f deploy/docker/docker-compose.yml restart loom
# Or:
docker restart loom
```

### Stop the service

```bash
docker-compose -f deploy/docker/docker-compose.yml down
# Or:
docker stop loom && docker rm loom
```

### Check health status

```bash
docker-compose -f deploy/docker/docker-compose.yml ps
# Or:
docker inspect loom --format='{{.State.Health.Status}}'
```

## Data Persistence

The docker-compose configuration creates three named volumes:

- **cache/** — cached web content, keyed by content hash. Survives container restarts.
- **logs/** — application logs (if enabled). Useful for debugging.
- **sessions/** — persistent browser sessions (for login-protected pages).

To wipe cached data:

```bash
docker-compose -f deploy/docker/docker-compose.yml exec loom \
  rm -rf /app/cache/*
```

## Configuration

All configuration is passed via environment variables from `.env`. See `deploy/.env.example` for a complete list of supported variables.

Key variables:

- `LOOM_PORT` — port to bind (default: 8787)
- `LOOM_LOG_LEVEL` — log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `EXA_API_KEY`, `TAVILY_API_KEY`, etc. — search provider credentials

## Security

- The container runs as non-root user `loom` (UID 1000)
- Network access is localhost-only by default (`127.0.0.1:8787`)
- File system is read-only except for `/app/cache`, `/app/logs`, `/app/sessions`
- Enable `no-new-privileges:true` to prevent privilege escalation

## Resource Limits

The default compose configuration reserves:

- **Memory:** 16 GB (soft limit)
- **CPUs:** 4.0 cores

Adjust these in `docker-compose.yml` based on your hardware.

## Troubleshooting

### Container won't start

Check the logs:

```bash
docker-compose -f deploy/docker/docker-compose.yml logs loom
```

Common issues:

- Missing `.env` file or invalid API keys — service may fail silently
- Insufficient memory — reduce `mem_limit` or increase system RAM
- Port 8787 already in use — change the port mapping in compose

### Health check failing

If the health check reports "unhealthy":

```bash
docker-compose -f deploy/docker/docker-compose.yml ps
docker logs loom | tail -20
```

The service may still be initializing (takes ~30 seconds on first startup). Wait a moment and retry the health check.

### Browser operations slow or hanging

Reduce concurrent operations by setting environment variables:

```bash
# In .env:
SPIDER_CONCURRENCY=2
```

Restart the container for changes to take effect.

## Building a Custom Image

To build with custom configuration:

```bash
docker build \
  -t ghcr.io/aadelb/loom:custom \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -f deploy/docker/Dockerfile .
```

## Multi-Platform Builds

To build for multiple platforms (e.g., arm64 for Apple Silicon):

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/aadelb/loom:latest \
  --push \
  -f deploy/docker/Dockerfile .
```

Requires `docker buildx` (included in Docker Desktop).
