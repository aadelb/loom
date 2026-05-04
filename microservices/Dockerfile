# Multi-stage Dockerfile for Loom MCP microservices
# Each service runs with different LOOM_SERVICE env var to enable/disable tools

ARG SERVICE_NAME=loom-core
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy project files
COPY . .

# Install Python dependencies into /build/venv
RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e ".[all]" 2>&1 | grep -v "already satisfied" || true

# ─────────────────────────────────────────────────────────────────────────────
# Runtime Stage
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

ARG SERVICE_NAME=loom-core

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 loom && \
    mkdir -p /home/loom/.cache/loom /home/loom/.loom/sessions && \
    chown -R loom:loom /home/loom

WORKDIR /app

# Copy built venv from builder stage
COPY --from=builder --chown=loom:loom /build/venv /app/venv

# Copy source code
COPY --chown=loom:loom src /app/src
COPY --chown=loom:loom pyproject.toml /app/

# Add venv to PATH
ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:$PYTHONPATH" \
    LOOM_SERVICE=${SERVICE_NAME}

# Use non-root user
USER loom

# Expose port (will be overridden by docker-compose)
EXPOSE 8787

# Health check with service-aware endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${LOOM_PORT:-8787}/health || exit 1

# Start Loom MCP server
ENTRYPOINT ["loom", "serve"]
CMD ["--host", "0.0.0.0", "--port", "${LOOM_PORT:-8787}"]
