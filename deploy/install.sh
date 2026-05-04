#!/usr/bin/env bash
# Loom MCP Research Server - Production Installation Script
#
# Usage:
#   sudo bash deploy/install.sh
#   sudo bash deploy/install.sh --prefix /opt/custom-path
#   sudo bash deploy/install.sh --user-home /home/custom-user
#
# This script:
# 1. Creates the 'loom' system user
# 2. Sets up directory structure (/opt/research-toolbox, /var/log/loom, etc.)
# 3. Installs systemd service unit
# 4. Configures log rotation with logrotate
# 5. Enables and optionally starts the service

set -euo pipefail

# ── Configuration ──
INSTALL_PREFIX="${INSTALL_PREFIX:-/opt/research-toolbox}"
LOOM_USER="${LOOM_USER:-loom}"
LOOM_GROUP="${LOOM_GROUP:-loom}"
LOOM_HOME="${LOOM_HOME:-/var/lib/loom}"
LOOM_LOG_DIR="${LOOM_LOG_DIR:-/var/log/loom}"
LOOM_CONFIG_DIR="${LOOM_CONFIG_DIR:-/etc/loom}"
AUTO_START="${AUTO_START:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── Logging Functions ──
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# ── Preflight Checks ──
log_info "Running preflight checks..."

if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use: sudo bash deploy/install.sh)"
    exit 1
fi

if ! command -v systemctl &> /dev/null; then
    log_error "systemd is required but not found. This script is for Linux systems with systemd."
    exit 1
fi

if ! command -v logrotate &> /dev/null; then
    log_warn "logrotate not found. Log rotation will not be configured."
fi

log_success "Preflight checks passed"

# ── Create System User ──
log_info "Setting up '${LOOM_USER}' user..."

if id "${LOOM_USER}" &>/dev/null; then
    log_warn "User '${LOOM_USER}' already exists. Skipping user creation."
else
    # Create system user with nologin shell
    useradd \
        --system \
        --shell /usr/sbin/nologin \
        --home-dir "${LOOM_HOME}" \
        --create-home \
        --comment "Loom MCP Research Server" \
        "${LOOM_USER}"
    log_success "Created user '${LOOM_USER}'"
fi

# ── Create Directory Structure ──
log_info "Creating directory structure..."

mkdir -p "${LOOM_LOG_DIR}"
mkdir -p "${LOOM_CONFIG_DIR}"
mkdir -p "${LOOM_HOME}/cache"
mkdir -p "${LOOM_HOME}/sessions"
mkdir -p "${LOOM_HOME}/sessions/browser"

# Set ownership
chown -R "${LOOM_USER}:${LOOM_GROUP}" "${LOOM_HOME}"
chown -R "${LOOM_USER}:${LOOM_GROUP}" "${LOOM_LOG_DIR}"
chown -R root:root "${LOOM_CONFIG_DIR}"  # Config readable by root only initially

# Set permissions
chmod 750 "${LOOM_HOME}"
chmod 750 "${LOOM_LOG_DIR}"
chmod 755 "${LOOM_CONFIG_DIR}"

log_success "Created directory structure"

# ── Install systemd Service Unit ──
log_info "Installing systemd service unit..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "${SCRIPT_DIR}/loom.service" ]]; then
    log_error "Service file not found: ${SCRIPT_DIR}/loom.service"
    exit 1
fi

cp "${SCRIPT_DIR}/loom.service" /etc/systemd/system/loom.service
chmod 644 /etc/systemd/system/loom.service

log_success "Installed /etc/systemd/system/loom.service"

# ── Install logrotate Configuration ──
log_info "Installing logrotate configuration..."

if [[ -f "${SCRIPT_DIR}/loom-logrotate.conf" ]]; then
    if command -v logrotate &> /dev/null; then
        cp "${SCRIPT_DIR}/loom-logrotate.conf" /etc/logrotate.d/loom
        chmod 644 /etc/logrotate.d/loom
        log_success "Installed /etc/logrotate.d/loom"
    else
        log_warn "logrotate not installed; skipping log rotation setup"
    fi
else
    log_warn "logrotate config not found: ${SCRIPT_DIR}/loom-logrotate.conf"
fi

# ── Reload systemd Configuration ──
log_info "Reloading systemd configuration..."
systemctl daemon-reload
log_success "systemd configuration reloaded"

# ── Enable Service ──
log_info "Enabling Loom service..."
systemctl enable loom
log_success "Loom service enabled (will start on boot)"

# ── Optional: Start Service ──
if [[ "${AUTO_START}" == "true" ]]; then
    log_info "Starting Loom service..."
    systemctl start loom
    sleep 2
    if systemctl is-active --quiet loom; then
        log_success "Loom service started successfully"
    else
        log_error "Loom service failed to start. Check logs:"
        echo "  sudo journalctl -u loom -n 50"
        exit 1
    fi
else
    log_info "Service not auto-started. To start manually, run:"
    echo "  sudo systemctl start loom"
fi

# ── Print Summary ──
cat <<EOF

${GREEN}═══════════════════════════════════════════════════════════════${NC}
${GREEN}  Loom Installation Complete${NC}
${GREEN}═══════════════════════════════════════════════════════════════${NC}

${BLUE}Service Configuration:${NC}
  Service Unit:      /etc/systemd/system/loom.service
  Config Directory:  ${LOOM_CONFIG_DIR}
  Log Directory:     ${LOOM_LOG_DIR}
  Data Directory:    ${LOOM_HOME}
  User:              ${LOOM_USER}:${LOOM_GROUP}

${BLUE}Common Commands:${NC}
  View status:       sudo systemctl status loom
  View logs:         sudo journalctl -u loom -f
  Restart service:   sudo systemctl restart loom
  Stop service:      sudo systemctl stop loom

${BLUE}Next Steps:${NC}
  1. Configure environment variables:
     sudo nano ${LOOM_CONFIG_DIR}/loom.env

  2. Verify API keys are set (Groq, NVIDIA NIM, etc.)

  3. Start the service:
     sudo systemctl start loom

  4. Test the service:
     curl http://127.0.0.1:8787/health

  5. Monitor in real-time:
     sudo journalctl -u loom -f

${GREEN}═══════════════════════════════════════════════════════════════${NC}

EOF

exit 0
