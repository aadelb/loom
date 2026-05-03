# Docker Sandbox System

## Overview

The Docker Sandbox system provides isolated execution of dangerous subprocess tools (nmap, masscan, nuclei, torbot) by running them in ephemeral Docker containers. This prevents compromised tools from accessing the main server's filesystem.

## Architecture

### Components

1. **DockerSandbox** (`src/loom/sandbox.py`)
   - Main class managing sandboxed command execution
   - Handles Docker container lifecycle
   - Falls back to subprocess when Docker unavailable
   - Singleton instance via `get_sandbox()`

2. **SandboxTools** (`src/loom/tools/sandbox_tools.py`)
   - MCP tool exports: `research_sandbox_run`, `research_sandbox_status`
   - Input validation
   - JSON response formatting

3. **Dockerfile** (`docker/sandbox/Dockerfile`)
   - Minimal Python 3.11 base image
   - Pre-installed security/network tools
   - Non-root user for safety
   - ~600MB image size

### Configuration

Config keys in `src/loom/config.py`:

| Key | Default | Purpose |
|-----|---------|---------|
| `SANDBOX_ENABLED` | `true` | Enable/disable sandbox system |
| `SANDBOX_IMAGE` | `loom-sandbox:latest` | Docker image name |
| `SANDBOX_TIMEOUT_SECS` | `300` | Command timeout (10-3600 seconds) |
| `SANDBOX_MEMORY_LIMIT` | `512m` | Memory limit (e.g., "1g", "256m") |
| `SANDBOX_CPU_LIMIT` | `1` | CPU cores (1-4) |

## Building the Sandbox Image

### Prerequisites

- Docker (version 20.10+)
- Disk space (~1GB for build)

### Build Command

```bash
cd /Users/aadel/projects/loom
docker build -f docker/sandbox/Dockerfile -t loom-sandbox:latest docker/sandbox/
```

### Verify Image

```bash
docker images | grep loom-sandbox
docker run --rm loom-sandbox:latest echo "Sandbox works!"
```

### Image Contents

Pre-installed tools:
- **Network**: nmap, masscan, netcat, dnsutils, whois, curl, wget
- **VCS**: git
- **Utilities**: ca-certificates, tzdata
- **Build**: build-essential (for compiling native tools)

## Usage

### Via MCP Tool

```python
from loom.tools.sandbox_tools import research_sandbox_run

# Basic execution
result = await research_sandbox_run(
    command=["nmap", "-p", "80", "example.com"],
    timeout=60,
    network=True,  # Enable network (required for nmap)
    memory="512m",
)

# Check result
if result.text:
    data = json.loads(result.text)
    print(f"Exit code: {data['exit_code']}")
    print(f"Output: {data['stdout']}")
```

### Via Direct API

```python
from loom.sandbox import get_sandbox

sandbox = await get_sandbox()

# Run with isolation
result = await sandbox.run(
    command=["nuclei", "-u", "https://target.com"],
    timeout=300,
    network=True,
    memory="1g",
    cpus=2,
)

# Check execution mode
print(f"Mode: {result.mode}")  # "docker" or "fallback"
print(f"Container: {result.container_id}")
```

### With File I/O

```python
from loom.sandbox import get_sandbox

sandbox = await get_sandbox()

result = await sandbox.run_with_files(
    command=["nuclei", "-l", "/input/targets.txt", "-o", "/output/results.txt"],
    input_files={"targets.txt": "https://example.com\nhttps://example2.com"},
    output_dir="/output",
    network=True,
)

# Output files are automatically collected
```

## Security Considerations

### Isolation Layers

1. **Filesystem Isolation**: Container sees only `/work`, `/input`, `/output`
2. **Network Isolation**: Optional `--network=none` for completely isolated mode
3. **Resource Limits**: Memory (512MB default), CPU (1 core default)
4. **User Isolation**: Non-root `sandbox` user inside container
5. **Auto-cleanup**: Containers removed after execution

### Fallback Behavior

When Docker is unavailable:
- Automatically falls back to direct subprocess execution
- Returns warning in response
- Less isolated but continues operation

### Network Considerations

- `network=True` (default): Container has access to bridge network (required for nmap, nuclei, etc.)
- `network=False`: `--network=none` for air-gapped tools
- Never expose sensitive ports or credentials in env vars

## Performance Characteristics

### Latency

- **Docker mode**: ~200-500ms overhead per command (container creation + startup)
- **Fallback mode**: <10ms overhead (direct subprocess)

### Memory

- **Base image**: ~100MB
- **Per container**: 512MB minimum limit (configurable)
- **Concurrent**: Linux kernel limits (~30-50 containers at once with 512MB each)

### Disk

- **Image**: ~600MB
- **Container layer**: <1MB per container (auto-removed)

## Troubleshooting

### Docker Not Found

If `is_docker_available()` returns False:

```bash
# Check if Docker is installed
which docker

# Check if Docker daemon is running
docker ps
```

### Container Timeout

If command exceeds timeout:

```python
result = await sandbox.run(
    command=["slow_tool"],
    timeout=600,  # Increase timeout
)
```

### Permission Denied

If getting permission errors:

```bash
# Check Docker socket permissions
ls -l /var/run/docker.sock

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
```

### Memory Limit Issues

If OOM killed:

```python
result = await sandbox.run(
    command=["memory_intensive_tool"],
    memory="1g",  # Increase limit
)
```

## Testing

### Unit Tests

```bash
# Run sandbox tests
pytest tests/test_sandbox.py -v

# Run sandbox tools tests
pytest tests/test_sandbox_tools.py -v

# With coverage
pytest tests/test_sandbox*.py --cov=src/loom/sandbox --cov=src/loom/tools/sandbox_tools
```

### Integration Tests

```bash
# Build image first
docker build -f docker/sandbox/Dockerfile -t loom-sandbox:latest docker/sandbox/

# Run integration tests
pytest tests/test_sandbox*.py -v -m "not slow"
```

## Examples

### Running nmap

```python
result = await research_sandbox_run(
    command=["nmap", "-sV", "-p", "1-1000", "target.com"],
    timeout=120,
    network=True,
    memory="512m",
)
```

### Running nuclei

```python
result = await research_sandbox_run(
    command=[
        "nuclei",
        "-u", "https://target.com",
        "-t", "cves/",
        "-severity", "high"
    ],
    timeout=300,
    network=True,
    memory="1g",
    cpus=2,
)
```

### Checking Docker Status

```python
status = await research_sandbox_status()
data = json.loads(status.text)
print(f"Docker available: {data['docker_available']}")
print(f"Image: {data['sandbox_image']}")
print(f"Timeout: {data['sandbox_timeout']}s")
```

## Deployment

### Production Checklist

- [ ] Docker installed and running on all nodes
- [ ] `loom-sandbox:latest` image built and pulled to all nodes
- [ ] Resource limits configured appropriate to system capacity
- [ ] Log aggregation configured for sandbox execution events
- [ ] Network isolation tested for tools that need it
- [ ] File I/O tested with expected tool workflows
- [ ] Timeout values validated for expected tool execution times
- [ ] Fallback subprocess behavior understood and monitored

### Docker Registry

```bash
# Tag image for registry
docker tag loom-sandbox:latest myregistry.com/loom-sandbox:v1.0

# Push to registry
docker push myregistry.com/loom-sandbox:v1.0

# Pull on remote nodes
docker pull myregistry.com/loom-sandbox:v1.0
```

## Future Enhancements

- [ ] GPU support for compute-intensive tools
- [ ] Custom tool images per tool type
- [ ] Container resource pooling and reuse
- [ ] Output streaming for long-running commands
- [ ] Persistent volumes for tool state
- [ ] Multi-level sandboxing (nested containers)
- [ ] Custom network namespace support
