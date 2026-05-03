# Docker Sandbox - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependency

```bash
pip install aiodocker
```

### 2. Build Sandbox Image

```bash
cd /Users/aadel/projects/loom
docker build -f docker/sandbox/Dockerfile -t loom-sandbox:latest docker/sandbox/
```

### 3. Verify It Works

```bash
docker run --rm loom-sandbox:latest echo "Sandbox ready!"
```

## Usage

### Via MCP Tool (Recommended)

```python
from loom.tools.sandbox_tools import research_sandbox_run
import json

# Run nmap
result = await research_sandbox_run(
    command=["nmap", "-p", "80,443", "example.com"],
    timeout=60,
    network=True,
)

# Parse result
data = json.loads(result.text)
if data["success"]:
    print(f"Output:\n{data['stdout']}")
else:
    print(f"Error: {data['stderr']}")
```

### Via Direct API

```python
from loom.sandbox import get_sandbox

sandbox = await get_sandbox()
result = await sandbox.run(
    command=["nmap", "-p", "22", "target.com"],
    timeout=30,
    network=True,  # Required for network tools
)

print(f"Exit code: {result.exit_code}")
print(f"Mode: {result.mode}")  # "docker" or "fallback"
```

## Configuration

Edit `config.json`:

```json
{
  "SANDBOX_ENABLED": true,
  "SANDBOX_IMAGE": "loom-sandbox:latest",
  "SANDBOX_TIMEOUT_SECS": 300,
  "SANDBOX_MEMORY_LIMIT": "512m",
  "SANDBOX_CPU_LIMIT": 1
}
```

Or set via environment:

```bash
export LOOM_CONFIG_PATH=/path/to/config.json
```

## Common Use Cases

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
        "nuclei", "-u", "https://target.com",
        "-t", "cves/2024", "-severity", "critical"
    ],
    timeout=300,
    network=True,
    memory="1g",  # More memory for nuclei
    cpus=2,
)
```

### Running with file input/output

```python
from loom.sandbox import get_sandbox

sandbox = await get_sandbox()
result = await sandbox.run_with_files(
    command=["nmap", "-l", "/input/targets.txt", "-oN", "/output/results.txt"],
    input_files={"targets.txt": "target1.com\ntarget2.com"},
    output_dir="/output",
    network=True,
)
```

### Checking sandbox status

```python
from loom.tools.sandbox_tools import research_sandbox_status
import json

status = await research_sandbox_status()
data = json.loads(status.text)

print(f"Docker available: {data['docker_available']}")
print(f"Sandbox image: {data['sandbox_image']}")
print(f"Docker version: {data['docker_version']}")
```

## Troubleshooting

### "Docker not available"

```bash
# Check if Docker is installed
which docker

# Check if daemon is running
docker ps

# If not running (macOS)
open -a Docker

# If not running (Linux)
sudo systemctl start docker
```

### "Command timed out"

Increase timeout parameter:

```python
result = await research_sandbox_run(
    command=["slow_tool"],
    timeout=600,  # Was 300
)
```

### "Out of memory"

Increase memory limit:

```python
result = await research_sandbox_run(
    command=["memory_heavy_tool"],
    memory="1g",  # Was "512m"
)
```

### "Permission denied"

```bash
# Check Docker socket (Linux)
ls -l /var/run/docker.sock

# Add user to docker group
sudo usermod -aG docker $USER

# Restart Docker (macOS)
open -a Docker
```

## Testing

### Run Unit Tests

```bash
pytest tests/test_sandbox.py -v
pytest tests/test_sandbox_tools.py -v
```

### Run Integration Tests

```bash
# First build image
docker build -f docker/sandbox/Dockerfile -t loom-sandbox:latest docker/sandbox/

# Then run tests
pytest tests/test_sandbox*.py -v
```

### Test with Real Tool

```bash
# Test nmap (if installed)
result = await research_sandbox_run(
    command=["nmap", "--version"],
)
```

## Performance Tips

1. **Use `network=False` for CPU-bound tools** — Saves network overhead
2. **Increase memory for data-intensive tools** — nuclei, yara, etc.
3. **Increase cpus for parallel tools** — masscan, nuclei with threads
4. **Set timeout based on tool** — Quick scans: 60s, Deep scans: 300s+

## Limits

| Parameter | Min | Max | Default |
|-----------|-----|-----|---------|
| Timeout | 1s | 3600s | 300s |
| Memory | 128m | 4g | 512m |
| CPUs | 1 | 4 | 1 |

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Check stdout |
| 1-125 | Tool error | Check stderr |
| 124 | Timeout | Increase timeout |
| Docker error | Container failed | Check logs |

## File Paths

| Path | Location | Use |
|------|----------|-----|
| `/work` | Container working dir | Default CWD |
| `/input` | Volume mount | Read input files |
| `/output` | Volume mount | Write results |

## Next Steps

1. **Build the image** — `docker build -f docker/sandbox/Dockerfile -t loom-sandbox:latest docker/sandbox/`
2. **Run tests** — `pytest tests/test_sandbox*.py -v`
3. **Try first tool** — Run nmap or nuclei in sandbox
4. **Integrate with server** — Add to server.py MCP tools
5. **Deploy to production** — Push image to Docker registry

## Resources

- Full docs: `/Users/aadel/projects/loom/docs/sandbox-setup.md`
- Source code: `/Users/aadel/projects/loom/src/loom/sandbox.py`
- Tools: `/Users/aadel/projects/loom/src/loom/tools/sandbox_tools.py`
- Tests: `/Users/aadel/projects/loom/tests/test_sandbox*.py`

## Support

Check logs for detailed error info:

```python
import logging
logging.getLogger("loom.sandbox").setLevel(logging.DEBUG)

# Or check structured logs in ~/.loom/logs/
```
