# Installation Guide

## Prerequisites

- Python 3.11 or later
- Loom MCP server running (see [Loom README](../README.md))

## Install from PyPI (Future)

```bash
pip install loom-sdk
```

## Install from Source

### 1. Clone the Repository

```bash
git clone https://github.com/aadelb/loom.git
cd loom/sdk
```

### 2. Create Virtual Environment (Optional but Recommended)

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n loom-sdk python=3.11
conda activate loom-sdk
```

### 3. Install Package

```bash
# Development install (editable)
pip install -e .

# With dev dependencies
pip install -e ".[dev]"

# Minimal install (production)
pip install .
```

### 4. Verify Installation

```bash
python -c "from loom_sdk import LoomClient; print('✓ Loom SDK installed successfully')"
```

## Start Loom Server

In a separate terminal:

```bash
# From loom root directory
loom serve

# Or using loom-server
loom-server
```

The server runs on `http://127.0.0.1:8787` by default.

## Run Examples

```bash
# Basic search
python examples/01_basic_search.py

# Deep research
python examples/02_deep_research.py

# Multi-LLM queries
python examples/03_multi_llm.py

# Bulk fetching
python examples/04_bulk_fetch.py

# Prompt reframing
python examples/05_prompt_reframe.py
```

## Configuration

### Environment Variables

The SDK uses defaults, but you can configure:

```bash
# Server URL (default: http://127.0.0.1:8787)
export LOOM_SERVER_URL="http://localhost:8787"

# API Key (if server requires authentication)
export LOOM_API_KEY="your-api-key"

# Request timeout in seconds (default: 300)
export LOOM_TIMEOUT="600"
```

### Programmatic Configuration

```python
from loom_sdk import LoomClient

client = LoomClient(
    server_url="http://127.0.0.1:8787",
    api_key="your-api-key",  # Optional
    timeout=600.0
)
```

## Development Setup

For contributing to the SDK:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run with coverage
pytest --cov=loom_sdk

# Type checking
mypy loom_sdk

# Code formatting
ruff format loom_sdk

# Linting
ruff check loom_sdk
```

## Troubleshooting

### ModuleNotFoundError: No module named 'loom_sdk'

→ Make sure to install the package:
```bash
pip install -e .
```

### Connection refused to 127.0.0.1:8787

→ Start the Loom server:
```bash
loom serve
```

### Import errors with pydantic or httpx

→ Reinstall dependencies:
```bash
pip install -e . --force-reinstall
```

### Type checking errors in IDE

→ Configure your IDE to use the virtual environment:
- VS Code: Select Python interpreter from `.venv/bin/python`
- PyCharm: Set project interpreter to venv
- Vim/Neovim: Use pyright LSP configured for venv

## Next Steps

1. Read the [API Reference](README.md#api-reference)
2. Run the [Examples](examples/)
3. Check [Troubleshooting](README.md#troubleshooting)
4. Review [Loom Server Docs](../docs/)
