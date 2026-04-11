# Installation Guide

Loom supports multiple installation methods: pip (local), pip from source, Docker, and systemd service.

## System Requirements

- **Python:** 3.11+ (tested on 3.11, 3.12, 3.13)
- **OS:** Linux or macOS (POSIX only; Windows via WSL2 supported experimentally)
- **RAM:** 2 GB minimum (browser operations may require 4-8 GB)
- **Disk:** 2 GB for browser binaries and cache

### Platform-Specific Prerequisites

**macOS:**

```bash
xcode-select --install
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev python3.11-dev
```

**Linux (RHEL/CentOS/Rocky):**

```bash
sudo yum install -y gcc gcc-c++ make openssl-devel python3.11-devel
```

## Option 1: pip Install (Recommended)

Install the latest release from PyPI:

```bash
pip install loom-mcp
```

### Optional Dependencies

| Extra | Purpose | Install Command |
|-------|---------|-----------------|
| `stealth` | Camoufox, Botasaurus, Patchright for anti-bot bypass | `pip install "loom-mcp[stealth]"` |
| `anthropic` | Anthropic Claude SDK for LLM calls | `pip install "loom-mcp[anthropic]"` |
| `dev` | pytest, mypy, ruff for development | `pip install "loom-mcp[dev]"` |
| `all` | All extras combined | `pip install "loom-mcp[all]"` |

### Install Browser Binaries

After installation, download the browser runtimes:

```bash
loom install-browsers
```

This runs `playwright install chromium firefox` and downloads Camoufox (~500 MB total).

To install Playwright browsers only (without Camoufox):

```bash
playwright install chromium firefox
```

### Verify Installation

Check that Loom is installed:

```bash
loom --version
```

Start the server and verify it works:

```bash
loom serve &
sleep 2
curl -X POST http://127.0.0.1:8787/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
kill %1
```

You should see JSON output listing all 23 tools.

## Option 2: Install from Source

Clone the repository and install in editable mode:

```bash
git clone https://github.com/aadelb/loom.git
cd loom
pip install -e .
loom install-browsers
loom serve
```

For development (with linting, type-checking, tests):

```bash
pip install -e ".[dev,stealth]"
```

Then run tests:

```bash
pytest tests/ -v --cov=src/loom
```

## Option 3: Docker

### Pull from Registry

Pull the pre-built image from GitHub Container Registry:

```bash
docker pull ghcr.io/aadelb/loom:latest
docker run -p 127.0.0.1:8787:8787 ghcr.io/aadelb/loom:latest
```

The server listens on `http://127.0.0.1:8787/mcp` (not accessible from other machines).

### Build Locally

```bash
docker build -t loom:latest -f deploy/docker/Dockerfile .
docker run -p 127.0.0.1:8787:8787 loom:latest
```

### Bind Directories

To persist cache, logs, and sessions:

```bash
docker run \
  -p 127.0.0.1:8787:8787 \
  -v ./cache:/app/cache \
  -v ./logs:/app/logs \
  -v ./sessions:/app/sessions \
  ghcr.io/aadelb/loom:latest
```

See [docs/deployment/docker.md](deployment/docker.md) for docker-compose, health checks, and resource limits.

## Option 4: systemd Service (Linux)

### Copy Service File

```bash
sudo cp deploy/systemd/loom.service.example /etc/systemd/system/loom.service
```

Edit the file to set the correct user and working directory:

```bash
sudo nano /etc/systemd/system/loom.service
```

Set these fields:

```ini
User=your_username
WorkingDirectory=/path/to/loom
Environment="PATH=/usr/local/bin:/usr/bin"
ExecStart=/usr/local/bin/python -m loom.server
```

### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable loom
sudo systemctl start loom
```

Check status and logs:

```bash
sudo systemctl status loom
sudo journalctl -u loom -f
```

See [docs/deployment/systemd.md](deployment/systemd.md) for full systemd setup, environment variables, and troubleshooting.

## Environment Variables

Create a `.env` file in your working directory or export environment variables:

```bash
# Server binding
LOOM_HOST=127.0.0.1
LOOM_PORT=8787

# Storage directories
LOOM_CACHE_DIR=./cache
LOOM_LOGS_DIR=./logs
LOOM_SESSIONS_DIR=./sessions
LOOM_CONFIG_PATH=./config.json

# Logging
LOOM_LOG_LEVEL=INFO

# Search provider API keys
EXA_API_KEY=
TAVILY_API_KEY=
FIRECRAWL_API_KEY=
BRAVE_API_KEY=

# LLM provider API keys
NVIDIA_NIM_API_KEY=
NVIDIA_NIM_ENDPOINT=https://integrate.api.nvidia.com/v1
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
VLLM_LOCAL_URL=http://localhost:9001/v1

# Tool configuration
SPIDER_CONCURRENCY=5
EXTERNAL_TIMEOUT_SECS=30
MAX_CHARS_HARD_CAP=200000
CACHE_TTL_DAYS=30
SESSION_TTL_MINUTES=480
```

See [deploy/.env.example](../deploy/.env.example) for the complete list with descriptions.

Load environment variables before starting the server:

```bash
export $(cat .env | xargs)
loom serve
```

Or use `python-dotenv`:

```bash
pip install python-dotenv
loom serve  # automatically loads .env
```

## Platform-Specific Notes

### macOS

Install Python via Homebrew or a version manager:

```bash
# Via Homebrew
brew install python@3.11

# Or via pyenv
pyenv install 3.11.0
pyenv local 3.11.0
```

Install Loom in a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install loom-mcp[stealth,anthropic]
loom install-browsers
loom serve
```

**Note:** On Apple Silicon (M1/M2/M3), all packages should install correctly. If you encounter issues with Playwright, install via Conda:

```bash
conda install -c conda-forge python=3.11 playwright
playwright install chromium firefox
```

### Linux (Ubuntu/Debian)

After installing system dependencies, use a version manager for Python:

```bash
# Via apt (Ubuntu 24.04 has Python 3.12)
sudo apt-get install python3.12 python3.12-venv python3.12-dev

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate
pip install loom-mcp[stealth]
loom install-browsers
```

### WSL2 (Windows Subsystem for Linux)

WSL2 on Windows 10/11 with Ubuntu is supported:

```bash
# Inside WSL2 terminal
sudo apt-get install -y build-essential libssl-dev python3.11-dev
pip install loom-mcp[stealth]
loom install-browsers
loom serve
```

WSL2 can then be accessed from Windows PowerShell via the same localhost address:

```powershell
# From PowerShell
Invoke-WebRequest -Uri "http://127.0.0.1:8787/mcp" -Method Post
```

**Note:** Native Windows support (outside WSL2) is not tested. Use WSL2 or Docker for Windows.

### Python Version Managers

Use `pyenv`, `asdf`, or `uv` to manage Python versions:

**pyenv:**

```bash
pyenv install 3.11.0
pyenv local 3.11.0
python -m venv venv
source venv/bin/activate
pip install loom-mcp[stealth]
```

**uv (fast Rust-based manager):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11
uv venv venv
source venv/bin/activate
pip install loom-mcp[stealth]
```

## Troubleshooting

**"playwright install failed" on Linux**

Playwright requires system libraries. Install them:

```bash
# Ubuntu/Debian
sudo apt-get install -y libgtk-3-0 libgconf-2-4 libnss3 libxss1 libasound2

# Or use Playwright's helper script
playwright install-deps
```

**"camoufox fetch timed out"**

Camoufox downloads a pre-built binary on first use. If the download is slow or fails:

```bash
# Retry with a timeout increase
export CAMOUFOX_DOWNLOAD_TIMEOUT=300
loom install-browsers

# Or fetch manually
python -m camoufox fetch --help
```

**"SSRF blocks my target URL"**

Loom blocks private IP ranges by default for security. Verify your target resolves to a public IP:

```bash
nslookup example.com
```

If you need to test SSRF internally, configure an HTTP proxy or bind Loom to an internal network:

```bash
LOOM_HOST=192.168.1.100 loom serve
```

**"429 rate limit from search provider"**

If you hit rate limits:

1. **Rotate API keys:** Use different Tavily/Exa keys across requests
2. **Lower concurrency:** `loom config set SPIDER_CONCURRENCY 2`
3. **Add delays:** Use the CLI with small batches instead of bulk operations
4. **Check provider limits:**
   - Exa: 100 requests/month on free tier
   - Tavily: 1000 requests/month on free tier
   - Firecrawl: 500 requests/month on free tier

**"Module not found" errors after install**

Reinstall in a clean virtual environment:

```bash
python -m venv venv --clear
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install loom-mcp[stealth,anthropic]
```

**Memory usage is high**

Browser processes can use 100-500 MB each. Close unused sessions:

```bash
loom session list
loom session close session-name
```

Or reduce the concurrency limit:

```bash
loom config set SPIDER_CONCURRENCY 2
```

## Updating Loom

To upgrade to the latest version:

```bash
pip install --upgrade loom-mcp
```

To upgrade browser binaries:

```bash
loom install-browsers
```

To downgrade to a specific version:

```bash
pip install loom-mcp==0.1.0
```

## Uninstalling

Remove the package:

```bash
pip uninstall loom-mcp
```

Optionally remove browser cache and sessions:

```bash
rm -rf ~/.cache/playwright
rm -rf ./sessions ./cache ./logs
```
