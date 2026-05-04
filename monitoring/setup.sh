#!/bin/bash

set -e

echo "=== Loom Monitoring Stack Setup ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo ""

# Function to print status
print_status() {
    echo "[*] $1"
}

print_error() {
    echo "[!] $1"
}

print_success() {
    echo "[+] $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    print_error "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running. Please start Docker first."
    exit 1
fi

print_success "Docker is installed and running"
echo ""

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install Docker Compose first."
    print_error "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

print_success "Docker Compose is installed"
echo ""

# Validate configuration files
print_status "Validating configuration files..."

FILES=(
    "prometheus.yml"
    "alerting-rules.yml"
    "alertmanager.yml"
    "docker-compose.yml"
    "grafana-dashboard.json"
)

for file in "${FILES[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$file" ]; then
        print_error "Missing configuration file: $file"
        exit 1
    fi
    print_success "Found: $file"
done

echo ""

# Validate JSON files
print_status "Validating JSON files..."

if command -v python3 &> /dev/null; then
    python3 -m json.tool "$SCRIPT_DIR/grafana-dashboard.json" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_success "grafana-dashboard.json is valid JSON"
    else
        print_error "grafana-dashboard.json is invalid JSON"
        exit 1
    fi
fi

echo ""

# Validate YAML files
print_status "Validating YAML files..."

if command -v yamllint &> /dev/null; then
    for file in prometheus.yml alerting-rules.yml alertmanager.yml; do
        if yamllint -d relaxed "$SCRIPT_DIR/$file" > /dev/null 2>&1; then
            print_success "yamllint: $file is valid"
        else
            print_error "$file has YAML syntax issues"
            yamllint -d relaxed "$SCRIPT_DIR/$file"
        fi
    done
else
    print_status "yamllint not installed, skipping YAML validation"
    print_status "Install with: pip install yamllint"
fi

echo ""

# Create necessary directories
print_status "Creating data directories..."
mkdir -p "$SCRIPT_DIR/data/prometheus"
mkdir -p "$SCRIPT_DIR/data/grafana"
mkdir -p "$SCRIPT_DIR/data/alertmanager"
print_success "Data directories created"

echo ""

# Start the monitoring stack
print_status "Starting Loom monitoring stack with Docker Compose..."
cd "$SCRIPT_DIR"

docker-compose pull --quiet
if [ $? -eq 0 ]; then
    print_success "Docker images pulled successfully"
else
    print_error "Failed to pull Docker images"
    exit 1
fi

echo ""
docker-compose up -d
if [ $? -eq 0 ]; then
    print_success "Monitoring stack started successfully"
else
    print_error "Failed to start monitoring stack"
    docker-compose logs
    exit 1
fi

echo ""
print_status "Waiting for services to be healthy..."
sleep 5

# Check service health
RETRIES=30
RETRY=0
while [ $RETRY -lt $RETRIES ]; do
    if docker-compose ps | grep -q "healthy"; then
        print_success "All services are healthy"
        break
    fi
    RETRY=$((RETRY + 1))
    sleep 1
    if [ $((RETRY % 10)) -eq 0 ]; then
        print_status "Waiting for services... ($RETRY/$RETRIES)"
    fi
done

echo ""
print_status "Monitoring stack status:"
docker-compose ps

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Access the monitoring stack:"
echo "  Grafana:      http://localhost:3000 (admin/admin)"
echo "  Prometheus:   http://localhost:9090"
echo "  AlertManager: http://localhost:9093"
echo ""
echo "To stop the stack:"
echo "  docker-compose -f monitoring/docker-compose.yml down"
echo ""
echo "To view logs:"
echo "  docker-compose -f monitoring/docker-compose.yml logs -f"
echo ""
echo "To reload Prometheus configuration:"
echo "  curl -X POST http://localhost:9090/-/reload"
echo ""
echo "Dashboard will be available shortly at: http://localhost:3000/d/loom-monitoring"
echo ""
