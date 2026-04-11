FROM python:3.11-slim

# System dependencies for Playwright browsers (Chromium, Firefox) and Camoufox
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
      libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
      libasound2 libpango-1.0-0 libcairo2 libcups2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy configuration files first (better caching)
COPY pyproject.toml README.md LICENSE ./

# Copy source code
COPY src/ src/

# Install Python dependencies with stealth extras (includes Camoufox, Botasaurus)
RUN pip install --no-cache-dir ".[stealth]"

# Install Playwright browsers (Chromium, Firefox)
RUN playwright install chromium firefox

# Fetch Camoufox Firefox distribution for stealth browsing
RUN python -m camoufox fetch

# Create non-root runtime user and required directories
RUN useradd -r -u 1000 loom && \
    mkdir -p /app/cache /app/logs /app/sessions /app/config && \
    chown -R loom:loom /app

USER loom

EXPOSE 8787

# Environment variables for the service
ENV LOOM_HOST=0.0.0.0 \
    LOOM_PORT=8787 \
    LOOM_CACHE_DIR=/app/cache \
    LOOM_LOGS_DIR=/app/logs \
    LOOM_SESSIONS_DIR=/app/sessions

# Health check: ping the MCP initialize endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -sS -f -X POST http://127.0.0.1:8787/mcp \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"hc","version":"1"}}}' \
      || exit 1

ENTRYPOINT ["python", "-m", "loom.server"]
