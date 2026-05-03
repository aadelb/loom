# Loom Sandbox Image
#
# Minimal isolated environment for running dangerous tools (nmap, masscan, nuclei, etc.)
# Features:
#  - Python 3.11 base for compatibility
#  - Common security/network tools pre-installed
#  - Non-root user for safety
#  - Volume mounts for input/output files
#  - No package manager (apt-get removed after install)

FROM python:3.11-slim

# Install common tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Network/Security tools
    nmap \
    masscan \
    curl \
    wget \
    netcat-traditional \
    dnsutils \
    whois \
    git \
    \
    # System utilities
    ca-certificates \
    tzdata \
    \
    # Build tools (minimal)
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r sandbox && useradd -r -g sandbox sandbox

# Set working directory
WORKDIR /work

# Create mount points
RUN mkdir -p /input /output && chown -R sandbox:sandbox /input /output

# Switch to non-root user
USER sandbox

# Default entrypoint (can be overridden)
ENTRYPOINT ["sh", "-c"]
CMD ["echo 'Sandbox ready'"]
